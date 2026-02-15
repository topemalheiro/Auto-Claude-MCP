"""
Roadmap Tools
==============

MCP tools for AI-powered strategic roadmap generation.
"""

from __future__ import annotations

import asyncio

from mcp_server.config import get_project_dir
from mcp_server.operations import OperationStatus, tracker
from mcp_server.server import mcp
from mcp_server.services.roadmap_service import RoadmapService


def _get_service() -> RoadmapService:
    return RoadmapService(get_project_dir())


@mcp.tool()
async def roadmap_generate(refresh: bool = False, model: str = "sonnet") -> dict:
    """Generate a strategic roadmap for the project. Long-running.

    Analyzes the project structure, existing features, and codebase to
    generate a phased roadmap with prioritized features.

    Args:
        refresh: Force regeneration even if a roadmap already exists
        model: Model to use (haiku, sonnet, opus)

    Returns:
        Operation ID to poll with operation_get_status()
    """
    service = _get_service()
    op = tracker.create("roadmap_generate", "Starting roadmap generation...")

    async def _run():
        try:
            tracker.update(
                op.id,
                status=OperationStatus.RUNNING,
                progress=10,
                message="Analyzing project for roadmap generation...",
            )
            result = await service.generate(refresh=refresh, model=model)
            if "error" in result:
                tracker.update(
                    op.id, status=OperationStatus.FAILED, error=result["error"]
                )
            else:
                tracker.update(
                    op.id,
                    status=OperationStatus.COMPLETED,
                    progress=100,
                    message="Roadmap generated",
                    result=result,
                )
        except Exception as e:
            tracker.update(op.id, status=OperationStatus.FAILED, error=str(e))

    op._task = asyncio.create_task(_run())
    return {
        "operation_id": op.id,
        "message": "Roadmap generation started. Poll operation_get_status() for progress.",
    }


@mcp.tool()
def roadmap_get() -> dict:
    """Get the current roadmap data.

    Returns the previously generated roadmap including vision, phases,
    features with priorities, and implementation details.

    Returns:
        Roadmap data with vision, phases, features, and priority breakdown
    """
    service = _get_service()
    return service.get_roadmap()


@mcp.tool()
async def roadmap_refresh(model: str = "sonnet") -> dict:
    """Refresh/regenerate the roadmap. Long-running.

    Forces a complete regeneration of the roadmap, analyzing current
    project state and creating updated phases and features.

    Args:
        model: Model to use (haiku, sonnet, opus)

    Returns:
        Operation ID to poll with operation_get_status()
    """
    service = _get_service()
    op = tracker.create("roadmap_refresh", "Starting roadmap refresh...")

    async def _run():
        try:
            tracker.update(
                op.id,
                status=OperationStatus.RUNNING,
                progress=10,
                message="Refreshing roadmap...",
            )
            result = await service.generate(refresh=True, model=model)
            if "error" in result:
                tracker.update(
                    op.id, status=OperationStatus.FAILED, error=result["error"]
                )
            else:
                tracker.update(
                    op.id,
                    status=OperationStatus.COMPLETED,
                    progress=100,
                    message="Roadmap refreshed",
                    result=result,
                )
        except Exception as e:
            tracker.update(op.id, status=OperationStatus.FAILED, error=str(e))

    op._task = asyncio.create_task(_run())
    return {
        "operation_id": op.id,
        "message": "Roadmap refresh started. Poll operation_get_status() for progress.",
    }
