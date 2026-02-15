"""
Memory Tools
=============

MCP tools for Graphiti-based semantic memory (knowledge graph).
Requires GRAPHITI_ENABLED=true in the environment.
"""

from __future__ import annotations

from mcp_server.config import get_project_dir
from mcp_server.server import mcp
from mcp_server.services.memory_service import MemoryService


def _get_service() -> MemoryService:
    return MemoryService(get_project_dir())


@mcp.tool()
async def memory_search(query: str, limit: int = 10) -> dict:
    """Search the project's semantic memory (Graphiti knowledge graph).

    Finds relevant stored knowledge including codebase discoveries,
    session insights, patterns, gotchas, and task outcomes.

    Requires GRAPHITI_ENABLED=true in environment.

    Args:
        query: Search query describing what you're looking for
        limit: Maximum number of results to return (default 10)

    Returns:
        List of relevant memory entries with content and relevance scores
    """
    service = _get_service()
    return await service.search(query, limit)


@mcp.tool()
async def memory_add_episode(content: str, source: str = "mcp") -> dict:
    """Add a new episode/fact to the project's memory.

    Stores information in the knowledge graph for future retrieval.
    Use this to record insights, patterns, or important findings.

    Requires GRAPHITI_ENABLED=true in environment.

    Args:
        content: The information to store (insight, pattern, discovery, etc.)
        source: Source identifier for the episode (default: mcp)

    Returns:
        Confirmation of successful storage
    """
    service = _get_service()
    return await service.add_episode(content, source)


@mcp.tool()
async def memory_get_recent(limit: int = 10) -> dict:
    """Get recent memory entries.

    Retrieves the most recent entries from the project's knowledge graph.

    Requires GRAPHITI_ENABLED=true in environment.

    Args:
        limit: Maximum number of entries to return (default 10)

    Returns:
        List of recent memory entries
    """
    service = _get_service()
    return await service.get_recent(limit)
