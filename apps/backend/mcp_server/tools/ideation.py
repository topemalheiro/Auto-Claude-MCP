"""
Ideation Tools
===============

MCP tools for AI-powered project ideation and improvement discovery.
"""

from __future__ import annotations

import asyncio

from mcp_server.config import get_project_dir
from mcp_server.operations import OperationStatus, tracker
from mcp_server.server import mcp
from mcp_server.services.ideation_service import IdeationService


def _get_service() -> IdeationService:
    return IdeationService(get_project_dir())


@mcp.tool()
async def ideation_generate(
    types: list[str] | None = None,
    refresh: bool = False,
    model: str = "sonnet",
) -> dict:
    """Generate ideas for project improvements. Long-running.

    Analyzes the codebase and generates actionable improvement ideas
    across multiple categories.

    Args:
        types: Ideation types to generate. Options: low_hanging_fruit,
               ui_ux_improvements, high_value_features. Defaults to all.
        refresh: Force regeneration of existing ideation data
        model: Model to use (haiku, sonnet, opus)

    Returns:
        Operation ID to poll with operation_get_status()
    """
    service = _get_service()
    op = tracker.create("ideation_generate", "Starting ideation generation...")

    async def _run():
        try:
            tracker.update(
                op.id,
                status=OperationStatus.RUNNING,
                progress=10,
                message="Analyzing project for improvement ideas...",
            )
            result = await service.generate(types=types, refresh=refresh, model=model)
            if "error" in result:
                tracker.update(
                    op.id, status=OperationStatus.FAILED, error=result["error"]
                )
            else:
                tracker.update(
                    op.id,
                    status=OperationStatus.COMPLETED,
                    progress=100,
                    message="Ideation complete",
                    result=result,
                )
        except Exception as e:
            tracker.update(op.id, status=OperationStatus.FAILED, error=str(e))

    op._task = asyncio.create_task(_run())
    return {
        "operation_id": op.id,
        "message": "Ideation generation started. Poll operation_get_status() for progress.",
    }


@mcp.tool()
def ideation_get() -> dict:
    """Get previously generated ideation results.

    Returns all generated ideas with their categories, priorities,
    effort estimates, and implementation suggestions.

    Returns:
        Ideation data with ideas grouped by type and priority
    """
    service = _get_service()
    return service.get_ideation()
