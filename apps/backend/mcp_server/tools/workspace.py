"""
Workspace Tools
================

MCP tools for managing git worktrees: list, diff, merge, discard, and PR creation.
"""

from __future__ import annotations

import asyncio
import logging

from mcp_server.config import get_project_dir
from mcp_server.operations import OperationStatus, tracker
from mcp_server.server import mcp

logger = logging.getLogger(__name__)


@mcp.tool()
def workspace_list() -> dict:
    """List all active git worktrees for the project.

    Each spec gets its own isolated worktree. This shows all active
    worktrees with their branch, change stats, and age.

    Returns:
        List of worktrees with branch, stats, and age information
    """
    from mcp_server.services.workspace_service import WorkspaceService

    service = WorkspaceService(get_project_dir())
    return service.list_worktrees()


@mcp.tool()
def workspace_diff(spec_id: str) -> dict:
    """Get the git diff for a spec's worktree.

    Shows all changes made in the spec's branch compared to the base branch,
    including a file-level summary and the full diff content.

    Args:
        spec_id: Spec folder name or prefix (e.g. '001' or '001-my-feature')

    Returns:
        Changed files summary and full diff content
    """
    from mcp_server.services.workspace_service import WorkspaceService

    service = WorkspaceService(get_project_dir())
    return service.get_diff(spec_id)


@mcp.tool()
async def workspace_merge(spec_id: str, strategy: str = "auto") -> dict:
    """Merge a spec's worktree changes back to the main branch.

    Args:
        spec_id: Spec folder name or prefix
        strategy: 'auto' for standard git merge, 'no-commit' to stage without committing

    Returns:
        Whether the merge was successful
    """
    from mcp_server.services.workspace_service import WorkspaceService

    service = WorkspaceService(get_project_dir())
    return await service.merge(spec_id, strategy=strategy)


@mcp.tool()
def workspace_discard(spec_id: str) -> dict:
    """Discard a spec's worktree and its branch.

    Permanently removes the worktree directory and deletes the associated
    git branch. This cannot be undone.

    Args:
        spec_id: Spec folder name or prefix

    Returns:
        Whether the discard was successful
    """
    from mcp_server.services.workspace_service import WorkspaceService

    service = WorkspaceService(get_project_dir())
    return service.discard(spec_id)


@mcp.tool()
async def workspace_create_pr(
    spec_id: str,
    title: str | None = None,
    body: str | None = None,
) -> dict:
    """Create a pull request from a spec's worktree branch.

    Pushes the branch to origin and creates a PR/MR on the detected
    git hosting provider (GitHub or GitLab). This is a long-running operation.

    Args:
        spec_id: Spec folder name or prefix
        title: PR title (defaults to spec name)
        body: PR body (defaults to spec summary)

    Returns:
        An operation_id to poll with operation_get_status() for progress
    """
    op = tracker.create("create_pr", f"Creating PR for: {spec_id}")

    async def _run() -> None:
        try:
            from mcp_server.services.workspace_service import WorkspaceService

            service = WorkspaceService(get_project_dir())

            tracker.update(
                op.id,
                status=OperationStatus.RUNNING,
                progress=20,
                message="Pushing branch and creating PR...",
            )

            result = await service.create_pr(
                spec_id=spec_id,
                title=title,
                body=body,
            )

            if result.get("success"):
                pr_url = result.get("pr_url", "")
                tracker.update(
                    op.id,
                    status=OperationStatus.COMPLETED,
                    progress=100,
                    message=f"PR created: {pr_url}" if pr_url else "PR created",
                    result=result,
                )
            else:
                tracker.update(
                    op.id,
                    status=OperationStatus.FAILED,
                    error=result.get("error", "PR creation failed"),
                    result=result,
                )
        except Exception as e:
            logger.exception("workspace_create_pr operation failed")
            tracker.update(
                op.id,
                status=OperationStatus.FAILED,
                error=str(e),
            )

    op._task = asyncio.create_task(_run())
    return {
        "operation_id": op.id,
        "message": "PR creation started. Poll operation_get_status() for progress.",
    }
