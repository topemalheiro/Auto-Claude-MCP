"""
Auto Claude MCP Server
======================

FastMCP server instance with all tool registrations.
Tools are organized into modules under mcp_server/tools/.
Each module's register() function adds tools to the server.
"""

from __future__ import annotations

import logging

from fastmcp import FastMCP

logger = logging.getLogger(__name__)

# Create the FastMCP server instance
mcp = FastMCP(
    "Auto Claude",
    instructions=(
        "Auto Claude is an autonomous multi-agent coding framework. "
        "Use these tools to manage tasks, create specs, run builds, "
        "perform QA reviews, manage workspaces, and more. "
        "Long-running operations return an operation_id - "
        "poll with operation_get_status() for progress."
    ),
)


def register_all_tools() -> None:
    """Register all tool modules with the MCP server.

    Each tool module defines functions decorated with @mcp.tool()
    that are imported here to trigger registration.
    """
    # Phase 1: Project & Task management
    # Phase 2: Core autonomous pipeline
    # Phase 3: Feature tools
    # Operations management (poll long-running ops)
    from mcp_server.tools import (
        execution,  # noqa: F401
        github,  # noqa: F401
        ideation,  # noqa: F401
        insights,  # noqa: F401
        memory,  # noqa: F401
        ops,  # noqa: F401
        project,  # noqa: F401
        qa,  # noqa: F401
        roadmap,  # noqa: F401
        specs,  # noqa: F401
        tasks,  # noqa: F401
        workspace,  # noqa: F401
    )

    logger.info("All MCP tools registered successfully")
