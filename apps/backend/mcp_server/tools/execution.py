"""
Execution Tools
================

MCP tools for starting, stopping, and monitoring builds.
"""

from __future__ import annotations

import asyncio
import logging

from mcp_server.config import get_project_dir
from mcp_server.operations import OperationStatus, tracker
from mcp_server.server import mcp

logger = logging.getLogger(__name__)


@mcp.tool()
async def build_start(
    spec_id: str,
    model: str = "sonnet",
    thinking_level: str = "medium",
) -> dict:
    """Start building/implementing a spec. This is a long-running operation.

    Spawns the autonomous coding pipeline which creates a worktree, runs
    the planner, then executes each subtask with parallel agents.

    Args:
        spec_id: Spec folder name or prefix (e.g. '001' or '001-my-feature')
        model: Model to use - 'sonnet' (fast), 'opus' (thorough)
        thinking_level: Reasoning depth - 'low', 'medium', 'high'

    Returns:
        An operation_id to poll with operation_get_status() for progress
    """
    op = tracker.create("build", f"Building spec: {spec_id}")

    async def _run() -> None:
        try:
            from mcp_server.services.execution_service import ExecutionService

            service = ExecutionService(get_project_dir())

            tracker.update(
                op.id,
                status=OperationStatus.RUNNING,
                progress=5,
                message="Spawning build process...",
            )

            proc = await service.start_build(
                spec_id=spec_id,
                model=model,
                thinking_level=thinking_level,
            )

            tracker.update(
                op.id,
                status=OperationStatus.RUNNING,
                progress=10,
                message="Build process started, waiting for completion...",
            )

            # Wait for the process to complete
            await proc.wait()

            if proc.returncode == 0:
                progress_info = service.get_progress(spec_id)
                tracker.update(
                    op.id,
                    status=OperationStatus.COMPLETED,
                    progress=100,
                    message="Build completed successfully",
                    result=progress_info,
                )
            else:
                logs = service.get_logs(spec_id, tail=20)
                tracker.update(
                    op.id,
                    status=OperationStatus.FAILED,
                    error=f"Build exited with code {proc.returncode}",
                    result={
                        "exit_code": proc.returncode,
                        "tail_logs": logs.get("lines", []),
                    },
                )
        except Exception as e:
            logger.exception("build_start operation failed")
            tracker.update(
                op.id,
                status=OperationStatus.FAILED,
                error=str(e),
            )

    op._task = asyncio.create_task(_run())
    return {
        "operation_id": op.id,
        "message": "Build started. Poll operation_get_status() for progress.",
    }


@mcp.tool()
def build_stop(spec_id: str) -> dict:
    """Stop a running build.

    Terminates the build subprocess. The worktree and any partial changes
    are preserved so the build can be resumed later.

    Args:
        spec_id: Spec folder name or prefix

    Returns:
        Whether the build was successfully stopped
    """
    from mcp_server.services.execution_service import ExecutionService

    service = ExecutionService(get_project_dir())
    return service.stop_build(spec_id)


@mcp.tool()
def build_get_progress(spec_id: str) -> dict:
    """Get progress of a running or completed build.

    Shows subtask completion status, QA state, and whether the build
    is still running.

    Args:
        spec_id: Spec folder name or prefix

    Returns:
        Build progress including subtask completion and QA status
    """
    from mcp_server.services.execution_service import ExecutionService

    service = ExecutionService(get_project_dir())
    return service.get_progress(spec_id)


@mcp.tool()
def build_get_logs(spec_id: str, tail: int = 50) -> dict:
    """Get recent build logs for a spec.

    Returns the most recent log lines from the build process output.

    Args:
        spec_id: Spec folder name or prefix
        tail: Number of recent lines to return (default 50)

    Returns:
        Recent log lines from the build
    """
    from mcp_server.services.execution_service import ExecutionService

    service = ExecutionService(get_project_dir())
    return service.get_logs(spec_id, tail=tail)
