"""HTTP Proxy Server Implementation"""

import socket
import threading
import logging
from typing import Tuple, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class HTTPProxyServer:
    """A simple multi-threaded HTTP proxy server."""

    HTTP_VERSION = "HTTP/1.1"

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8080,
        timeout: int = 30,
        buffer_size: int = 8192
    ):
        """
        Initialize the HTTP proxy server.

        Args:
            host: The host address to bind to.
            port: The port number to listen on.
            timeout: Connection timeout in seconds.
            buffer_size: Buffer size for data transfer.
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.buffer_size = buffer_size
        self.server_socket: Optional[socket.socket] = None
        self.running = False

    def start(self) -> None:
        """Start the proxy server."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(100)
        self.running = True

        logger.info(f"HTTP Proxy Server started on {self.host}:{self.port}")

        while self.running:
            try:
                client_socket, client_address = self.server_socket.accept()
                logger.debug(f"New connection from {client_address}")
                thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, client_address),
                    daemon=True
                )
                thread.start()
            except Exception as e:
                if self.running:
                    logger.error(f"Error accepting connection: {e}")

    def stop(self) -> None:
        """Stop the proxy server."""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        logger.info("HTTP Proxy Server stopped")

    def _handle_client(self, client_socket: socket.socket, client_address: Tuple[str, int]) -> None:
        """Handle a single client connection."""
        try:
            request_data = client_socket.recv(self.buffer_size)
            if not request_data:
                return

            request = self._parse_request(request_data)
            if not request:
                self._send_error(client_socket, 400, "Bad Request")
                return

            method, url, headers, body = request

            if method == "CONNECT":
                self._send_error(client_socket, 405, "CONNECT method not supported")
                return

            # Parse target URL
            parsed_url = urlparse(url)
            if not parsed_url.hostname:
                self._send_error(client_socket, 400, "Invalid URL")
                return

            target_host = parsed_url.hostname
            target_port = parsed_url.port or 80
            target_path = parsed_url.path or "/"
            if parsed_url.query:
                target_path += "?" + parsed_url.query

            logger.info(f"{client_address[0]} - {method} {url}")

            # Forward the request
            self._forward_request(
                client_socket, method, target_host, target_port,
                target_path, headers, body, request_data
            )

        except Exception as e:
            logger.error(f"Error handling client {client_address}: {e}")
            try:
                self._send_error(client_socket, 500, "Internal Server Error")
            except:
                pass
        finally:
            client_socket.close()

    def _parse_request(self, request_data: bytes) -> Optional[Tuple[str, str, dict, bytes]]:
        """
        Parse the HTTP request.

        Returns:
            Tuple of (method, url, headers_dict, body) or None if parsing fails.
        """
        try:
            # Split headers and body
            if b"\r\n\r\n" in request_data:
                header_part, body = request_data.split(b"\r\n\r\n", 1)
            else:
                header_part = request_data
                body = b""

            header_lines = header_part.decode("utf-8", errors="ignore").split("\r\n")
            if not header_lines:
                return None

            # Parse request line
            request_line = header_lines[0].split()
            if len(request_line) < 2:
                return None

            method = request_line[0]
            url = request_line[1]

            # Parse headers
            headers = {}
            for line in header_lines[1:]:
                if ":" in line:
                    key, value = line.split(":", 1)
                    headers[key.strip().lower()] = value.strip()

            return method, url, headers, body

        except Exception as e:
            logger.debug(f"Failed to parse request: {e}")
            return None

    def _forward_request(
        self, client_socket: socket.socket, method: str,
        target_host: str, target_port: int, target_path: str,
        headers: dict, body: bytes, original_request: bytes
    ) -> None:
        """Forward the request to the target server and return the response."""
        target_socket = None
        try:
            # Connect to target server
            target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target_socket.settimeout(self.timeout)
            target_socket.connect((target_host, target_port))

            # Build and send the request
            forward_request = self._build_forward_request(
                method, target_host, target_port, target_path, headers, body
            )
            target_socket.sendall(forward_request)

            # Forward the response back to client
            while True:
                response_data = target_socket.recv(self.buffer_size)
                if not response_data:
                    break
                client_socket.sendall(response_data)

        except socket.timeout:
            logger.warning(f"Timeout connecting to {target_host}:{target_port}")
            self._send_error(client_socket, 504, "Gateway Timeout")
        except socket.gaierror:
            logger.warning(f"DNS resolution failed for {target_host}")
            self._send_error(client_socket, 502, "Bad Gateway")
        except ConnectionRefusedError:
            logger.warning(f"Connection refused by {target_host}:{target_port}")
            self._send_error(client_socket, 502, "Bad Gateway")
        except Exception as e:
            logger.error(f"Error forwarding request to {target_host}:{target_port}: {e}")
            self._send_error(client_socket, 502, "Bad Gateway")
        finally:
            if target_socket:
                target_socket.close()

    def _build_forward_request(
        self, method: str, target_host: str, target_port: int,
        target_path: str, headers: dict, body: bytes
    ) -> bytes:
        """Build the request to forward to the target server."""
        # Request line
        request_lines = [f"{method} {target_path} HTTP/1.1"]

        # Forward headers (modify hop-by-hop headers)
        skip_headers = {
            "proxy-connection", "connection", "keep-alive",
            "proxy-authenticate", "proxy-authorization",
            "te", "trailers", "transfer-encoding", "upgrade"
        }

        for key, value in headers.items():
            if key.lower() not in skip_headers:
                request_lines.append(f"{key}: {value}")

        # Ensure Host header
        if "host" not in headers:
            if target_port == 80:
                request_lines.append(f"Host: {target_host}")
            else:
                request_lines.append(f"Host: {target_host}:{target_port}")

        # Build request
        request_str = "\r\n".join(request_lines) + "\r\n\r\n"
        return request_str.encode("utf-8") + body

    def _send_error(self, client_socket: socket.socket, code: int, message: str) -> None:
        """Send an error response to the client."""
        body = f"<html><body><h1>{code} {message}</h1></body></html>"
        response = (
            f"{self.HTTP_VERSION} {code} {message}\r\n"
            f"Content-Type: text/html\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Connection: close\r\n"
            f"\r\n"
            f"{body}"
        )
        try:
            client_socket.sendall(response.encode("utf-8"))
        except:
            pass


def run_server(host: str = "0.0.0.0", port: int = 8080) -> None:
    """Convenience function to start the proxy server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    server = HTTPProxyServer(host, port)
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.stop()


if __name__ == "__main__":
    run_server()
