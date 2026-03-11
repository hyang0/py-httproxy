"""Tests for HTTP Proxy Server"""

import socket
import threading
import time
import pytest
from httproxy.server import HTTPProxyServer
from httproxy.cli import parse_args


@pytest.fixture
def proxy_server():
    """Create and start a proxy server for testing."""
    server = HTTPProxyServer(host="127.0.0.1", port=8888)
    thread = threading.Thread(target=server.start, daemon=True)
    thread.start()
    time.sleep(0.1)  # Wait for server to start
    yield server
    server.stop()


class TestCLI:
    """Test cases for CLI."""

    def test_default_args(self):
        """Test default argument values."""
        args = parse_args([])
        assert args.bind == "0.0.0.0"
        assert args.port == 8080
        assert args.log_level == "INFO"
        assert args.timeout == 30
        assert args.buffer_size == 8192

    def test_custom_args(self):
        """Test custom argument values."""
        args = parse_args(["-b", "127.0.0.1", "-p", "9999", "-l", "DEBUG"])
        assert args.bind == "127.0.0.1"
        assert args.port == 9999
        assert args.log_level == "DEBUG"

    def test_long_options(self):
        """Test long option names."""
        args = parse_args([
            "--bind", "localhost",
            "--port", "3128",
            "--log-level", "WARNING",
            "--timeout", "60",
            "--buffer-size", "16384"
        ])
        assert args.bind == "localhost"
        assert args.port == 3128
        assert args.log_level == "WARNING"
        assert args.timeout == 60
        assert args.buffer_size == 16384


class TestHTTPProxyServer:
    """Test cases for HTTPProxyServer."""

    def test_parse_request_valid(self):
        """Test parsing a valid HTTP request."""
        server = HTTPProxyServer()
        request = b"GET http://example.com/path HTTP/1.1\r\nHost: example.com\r\n\r\n"
        result = server._parse_request(request)

        assert result is not None
        method, url, headers, body = result
        assert method == "GET"
        assert url == "http://example.com/path"
        assert headers.get("host") == "example.com"
        assert body == b""

    def test_parse_request_with_body(self):
        """Test parsing a request with body."""
        server = HTTPProxyServer()
        request = b"POST http://example.com/api HTTP/1.1\r\nContent-Length: 11\r\n\r\nHello World"
        result = server._parse_request(request)

        assert result is not None
        method, url, headers, body = result
        assert method == "POST"
        assert body == b"Hello World"

    def test_parse_request_invalid(self):
        """Test parsing an invalid request."""
        server = HTTPProxyServer()
        result = server._parse_request(b"INVALID")
        assert result is None

    def test_build_forward_request(self):
        """Test building a forward request."""
        server = HTTPProxyServer()
        headers = {"user-agent": "test"}
        body = b"test body"

        request = server._build_forward_request(
            method="POST",
            target_host="example.com",
            target_port=80,
            target_path="/api",
            headers=headers,
            body=body
        )

        assert b"POST /api HTTP/1.1" in request
        assert b"Host: example.com" in request
        assert b"user-agent: test" in request
        assert body in request

    def test_build_forward_request_preserves_host(self):
        """Test that custom Host header is preserved."""
        server = HTTPProxyServer()
        headers = {"host": "custom.example.com"}

        request = server._build_forward_request(
            method="GET",
            target_host="example.com",
            target_port=80,
            target_path="/",
            headers=headers,
            body=b""
        )

        assert b"Host: custom.example.com" in request

    def test_skip_hop_by_hop_headers(self):
        """Test that hop-by-hop headers are not forwarded."""
        server = HTTPProxyServer()
        headers = {
            "connection": "keep-alive",
            "proxy-connection": "keep-alive",
            "user-agent": "test",
        }

        request = server._build_forward_request(
            method="GET",
            target_host="example.com",
            target_port=80,
            target_path="/",
            headers=headers,
            body=b""
        )

        assert b"connection" not in request.lower()
        assert b"proxy-connection" not in request.lower()
        assert b"user-agent: test" in request
