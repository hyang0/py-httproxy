"""Test script for HTTP Proxy Server"""

import asyncio
import warnings
warnings.filterwarnings('ignore')

from httproxy.server import HTTPProxyServer


async def test_http():
    """Test HTTP GET request."""
    try:
        reader, writer = await asyncio.open_connection('127.0.0.1', 9999)
        writer.write(b'GET http://example.com/ HTTP/1.1\r\nHost: example.com\r\n\r\n')
        await writer.drain()

        resp = b''
        while True:
            try:
                data = await asyncio.wait_for(reader.read(8192), timeout=10)
                if not data:
                    break
                resp += data
            except asyncio.TimeoutError:
                break

        writer.close()
        await writer.wait_closed()

        print(f'[HTTP] example.com: {len(resp)} bytes')
        return b'200' in resp.split(b'\r\n')[0]
    except Exception as e:
        print(f'[HTTP] FAILED: {e}')
        return False


async def test_connect():
    """Test CONNECT method."""
    try:
        reader, writer = await asyncio.open_connection('127.0.0.1', 9999)
        writer.write(b'CONNECT www.baidu.com:443 HTTP/1.1\r\nHost: www.baidu.com:443\r\n\r\n')
        await writer.drain()

        resp = await reader.read(1024)
        print(f'[CONNECT] Response: {resp.strip()}')

        writer.close()
        await writer.wait_closed()

        return b'200' in resp
    except Exception as e:
        print(f'[CONNECT] FAILED: {e}')
        return False


async def main():
    print('Starting HTTP Proxy Server...')

    proxy = HTTPProxyServer(host='127.0.0.1', port=9999, timeout=30)
    server_task = asyncio.create_task(proxy.start())

    await asyncio.sleep(0.5)

    print()
    print('Running tests...')
    print('=' * 40)

    # Test HTTP
    http_ok = await test_http()
    print(f'HTTP GET: {"PASS" if http_ok else "FAIL"}')

    # Test CONNECT
    connect_ok = await test_connect()
    print(f'CONNECT: {"PASS" if connect_ok else "FAIL"}')

    print('=' * 40)
    print(f'Results: {"PASS" if http_ok and connect_ok else "FAIL"}')

    server_task.cancel()
    try:
        await server_task
    except asyncio.CancelledError:
        pass

    await proxy.stop()


if __name__ == '__main__':
    asyncio.run(main())
