"""
Spec Tools
===========

MCP tools for creating and inspecting specifications.
"""

from __future__ import annotations

import asyncio
import logging

from mcp_server.config import get_project_dir
from mcp_server.operations import OperationStatus, tracker
from mcp_server.server import mcp

logger = logging.getLogger(__name__)


@mcp.tool()
async def spec_create(
    task_description: str,
    model: str = "sonnet",
    thinking_level: str = "medium",
) -> dict:
    """Create a specification for a task. This is a long-running operation.

    The spec creation pipeline runs multiple AI phases (discovery, requirements,
    complexity assessment, spec writing, planning) to produce a complete
    implementation-ready specification.

    Args:
        task_description: What you want to build (be specific and detailed)
        model: Model to use - 'sonnet' (fast), 'opus' (thorough)
        thinking_level: How much the AI reasons - 'low', 'medium', 'high'

    Returns:
        An operation_id to poll with operation_get_status() for progress
    """
    op = tracker.create("spec_create", f"Creating spec for: {task_description[:80]}")

    async def _run() -> None:
        try:
            from mcp_server.services.spec_service import SpecService

            tracker.update(
                op.id,
                status=OperationStatus.RUNNING,
                progress=5,
                message="Initializing spec pipeline...",
            )

            service = SpecService(get_project_dir())

            tracker.update(
                op.id,
                status=OperationStatus.RUNNING,
                progress=10,
                message="Running spec creation phases...",
            )

            result = await service.create_spec(
                task_description=task_description,
                model=model,
                thinking_level=thinking_level,
            )

            if result.get("success"):
                tracker.update(
                    op.id,
                    status=OperationStatus.COMPLETED,
                    progress=100,
                    message="Spec created successfully",
                    result=result,
                )
            else:
                tracker.update(
                    op.id,
                    status=OperationStatus.FAILED,
                    progress=100,
                    message="Spec creation failed",
                    error=result.get("error", "Unknown error"),
                    result=result,
                )
        except Exception as e:
            logger.exception("spec_create operation failed")
            tracker.update(
                op.id,
                status=OperationStatus.FAILED,
                error=str(e),
            )

    op._task = asyncio.create_task(_run())
    return {
        "operation_id": op.id,
        "message": "Spec creation started. Poll operation_get_status() for progress.",
    }


@mcp.tool()
def spec_get_status(spec_id: str) -> dict:
    """Get the current status of a spec (which phases have completed).

    Shows whether discovery, requirements, spec writing, and planning
    phases are complete, and the overall readiness state.

    Args:
        spec_id: Spec folder name or prefix (e.g. '001' or '001-my-feature')

    Returns:
        Status including completed phases and overall state
    """
    from mcp_server.services.spec_service import SpecService

    service = SpecService(get_project_dir())
    return service.get_spec_status(spec_id)


@mcp.tool()
def spec_get_content(spec_id: str) -> dict:
    """Get the full content of a spec including spec.md, requirements, and plan.

    Returns the complete specification content so you can understand what
    will be built and how.

    Args:
        spec_id: Spec folder name or prefix (e.g. '001' or '001-my-feature')

    Returns:
        Full spec content including spec.md, requirements.json, implementation_plan.json
    """
    from mcp_server.services.spec_service import SpecService

    service = SpecService(get_project_dir())
    return service.get_spec_content(spec_id)


@mcp.tool()
def spec_list() -> dict:
    """List all specs in the project with their status.

    Returns:
        List of specs with their current status and phase completion
    """
    from mcp_server.services.spec_service import SpecService

    service = SpecService(get_project_dir())
    specs = service.list_specs()
    return {"specs": specs, "count": len(specs)}
