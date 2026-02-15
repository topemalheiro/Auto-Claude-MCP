"""
Auto Claude MCP Server Entry Point
===================================

Usage:
    python -m mcp_server --project-dir /path/to/project
    python -m mcp_server --project-dir /path/to/project --transport sse --port 8642
"""

from __future__ import annotations

import argparse
import logging
import sys

# Configure logging to stderr (stdout is reserved for MCP protocol over stdio)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("mcp_server")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Auto Claude MCP Server - control plane for the autonomous coding pipeline",
    )
    parser.add_argument(
        "--project-dir",
        required=True,
        help="Path to the project directory to manage",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="MCP transport to use (default: stdio)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8642,
        help="Port for SSE/HTTP transport (default: 8642)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host for SSE/HTTP transport (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Initialize project context (adds backend to sys.path, loads .env)
    from mcp_server.config import initialize

    initialize(args.project_dir)

    # Import server and register tools AFTER initialization
    # (tools need backend modules on sys.path)
    from mcp_server.server import mcp, register_all_tools

    register_all_tools()

    logger.info(
        "Starting Auto Claude MCP server (transport=%s, project=%s)",
        args.transport,
        args.project_dir,
    )

    # For stdio transport, redirect any stray stdout prints to stderr
    # to prevent corrupting the MCP JSON-RPC protocol
    if args.transport == "stdio":
        # Capture any prints from backend modules that write to stdout
        _original_stdout = sys.stdout
        sys.stdout = sys.stderr

    # Run the server
    if args.transport == "stdio":
        mcp.run(transport="stdio")
    elif args.transport == "sse":
        mcp.run(transport="sse", host=args.host, port=args.port)
    elif args.transport == "streamable-http":
        mcp.run(transport="streamable-http", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
