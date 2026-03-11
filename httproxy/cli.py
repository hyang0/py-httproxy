"""Command-line interface for HTTP Proxy Server."""

import argparse
import logging
import sys
from .server import HTTPProxyServer, run_server


def parse_args(args=None):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="httproxy",
        description="An async HTTP/HTTPS proxy server.",
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
        "-v", "--version",
        action="version",
        version="%(prog)s 0.1.1"
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

    run_server(
        host=options.bind,
        port=options.port,
        timeout=options.timeout
    )


if __name__ == "__main__":
    main()
