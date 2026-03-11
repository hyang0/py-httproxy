"""HTTP Proxy Server Implementation using asyncio"""

import asyncio
import logging
import socket
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


async def copy_stream(src: asyncio.StreamReader, dst: asyncio.StreamWriter) -> None:
    """Copy data from src to dst bidirectionally."""
    try:
        while True:
            data = await src.read(65536)
            if not data:
                break
            dst.write(data)
            await dst.drain()
    except (ConnectionResetError, BrokenPipeError, OSError):
        pass
    except Exception:
        pass
    finally:
        try:
            dst.close()
            await dst.wait_closed()
        except:
            pass


class HTTPProxyServer:
    """Async HTTP/HTTPS proxy server."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080, timeout: int = 30):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.server: Optional[asyncio.Server] = None

    async def handle_client(self, reader: asyncio.StreamReader,
                            writer: asyncio.StreamWriter) -> None:
        """Handle a client connection."""
        remote_reader = None
        remote_writer = None

        try:
            # Read request with timeout
            data = await asyncio.wait_for(reader.read(65536), timeout=self.timeout)
            if not data:
                return

            # Parse request line
            header_end = data.find(b"\r\n\r\n")
            if header_end == -1:
                return

            header_part = data[:header_end].decode("utf-8", errors="ignore")
            body = data[header_end + 4:]

            lines = header_part.split("\r\n")
            if not lines:
                return

            request_line = lines[0].split()
            if len(request_line) < 2:
                return

            method = request_line[0]
            url = request_line[1]

            # Parse headers
            headers = {}
            for line in lines[1:]:
                if ":" in line:
                    key, value = line.split(":", 1)
                    headers[key.strip().lower()] = value.strip()

            client_addr = writer.get_extra_info('peername')
            client_ip = client_addr[0] if client_addr else 'unknown'

            if method == "CONNECT":
                # HTTPS tunnel
                if ":" in url:
                    host, port_str = url.rsplit(":", 1)
                    port = int(port_str)
                else:
                    host = url
                    port = 443

                logger.info(f"{client_ip} - CONNECT {host}:{port}")

                # Connect to target
                try:
                    remote_reader, remote_writer = await asyncio.wait_for(
                        asyncio.open_connection(host, port),
                        timeout=self.timeout
                    )
                except Exception as e:
                    logger.warning(f"Connection failed {host}:{port}: {e}")
                    writer.write(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
                    await writer.drain()
                    return

                # Send success response
                writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                await writer.drain()

                # Bidirectional tunnel
                await asyncio.gather(
                    copy_stream(reader, remote_writer),
                    copy_stream(remote_reader, writer),
                    return_exceptions=True
                )
            else:
                # HTTP request
                parsed = urlparse(url)
                if not parsed.hostname:
                    return

                target_host = parsed.hostname
                target_port = parsed.port or 80
                target_path = parsed.path or "/"
                if parsed.query:
                    target_path += "?" + parsed.query

                logger.info(f"{client_ip} - {method} {target_host}:{target_port}{target_path}")

                # Build forward request
                forward_headers = []
                skip_headers = {"proxy-connection", "connection", "keep-alive",
                                "proxy-authenticate", "proxy-authorization",
                                "te", "trailers", "transfer-encoding", "upgrade"}

                for key, value in headers.items():
                    if key not in skip_headers:
                        forward_headers.append(f"{key}: {value}")

                # Ensure Host header
                if "host" not in headers:
                    if target_port == 80:
                        forward_headers.append(f"Host: {target_host}")
                    else:
                        forward_headers.append(f"Host: {target_host}:{target_port}")

                request_line = f"{method} {target_path} HTTP/1.1"
                forward_data = "\r\n".join([request_line] + forward_headers) + "\r\n\r\n"
                forward_data = forward_data.encode() + body

                # Connect to target
                try:
                    remote_reader, remote_writer = await asyncio.wait_for(
                        asyncio.open_connection(target_host, target_port),
                        timeout=self.timeout
                    )
                except Exception as e:
                    logger.warning(f"Connection failed {target_host}:{target_port}: {e}")
                    writer.write(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
                    await writer.drain()
                    return

                # Send request
                remote_writer.write(forward_data)
                await remote_writer.drain()

                # Forward response
                await copy_stream(remote_reader, writer)

        except asyncio.TimeoutError:
            pass
        except Exception as e:
            logger.debug(f"Error: {e}")
        finally:
            if remote_writer:
                try:
                    remote_writer.close()
                    await remote_writer.wait_closed()
                except:
                    pass
            try:
                writer.close()
                await writer.wait_closed()
            except:
                pass

    async def start(self) -> None:
        """Start the proxy server."""
        self.server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port
        )
        logger.info(f"HTTP Proxy Server started on {self.host}:{self.port}")

        async with self.server:
            await self.server.serve_forever()

    async def stop(self) -> None:
        """Stop the proxy server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        logger.info("HTTP Proxy Server stopped")


def run_server(host: str = "0.0.0.0", port: int = 8080, timeout: int = 30) -> None:
    """Start the proxy server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    proxy = HTTPProxyServer(host, port, timeout)

    try:
        asyncio.run(proxy.start())
    except KeyboardInterrupt:
        print("\nShutting down...")
        asyncio.run(proxy.stop())


if __name__ == "__main__":
    run_server()
