"""Command-line interface for HTTP Proxy Server."""

import argparse
import logging
import sys
from .server import HTTPProxyServer


def parse_args(args=None):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="httproxy",
        description="A simple multi-threaded HTTP proxy server.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  httproxy                          Start on default 0.0.0.0:8080
  httproxy -p 3128                  Start on port 3128
  httproxy -b 127.0.0.1 -p 8888     Bind to localhost:8888
  httproxy --log-level DEBUG        Enable debug logging
        """
    )

    parser.add_argument(
        "-b", "--bind",
        default="0.0.0.0",
        metavar="HOST",
        help="host address to bind to (default: 0.0.0.0)"
    )

    parser.add_argument(
        "-p", "--port",
        type=int,
        default=8080,
        metavar="PORT",
        help="port to listen on (default: 8080)"
    )

    parser.add_argument(
        "-l", "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        metavar="LEVEL",
        help="logging level (default: INFO)"
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        metavar="SECONDS",
        help="connection timeout in seconds (default: 30)"
    )

    parser.add_argument(
        "--buffer-size",
        type=int,
        default=8192,
        metavar="BYTES",
        help="buffer size for data transfer (default: 8192)"
    )

    parser.add_argument(
        "-v", "--version",
        action="version",
        version="%(prog)s 0.1.0"
    )

    return parser.parse_args(args)


def main(args=None):
    """Main entry point for CLI."""
    options = parse_args(args)

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, options.log_level),
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    logger = logging.getLogger(__name__)
    logger.info(f"Starting HTTP Proxy Server on {options.bind}:{options.port}")

    server = HTTPProxyServer(
        host=options.bind,
        port=options.port,
        timeout=options.timeout,
        buffer_size=options.buffer_size
    )

    try:
        server.start()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)
    finally:
        server.stop()


if __name__ == "__main__":
    main()
