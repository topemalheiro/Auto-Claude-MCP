"""
GitHub Tools
=============

MCP tools for GitHub automation: PR review, issue triage, auto-fix.
Long-running operations return an operation_id for polling.
"""

from __future__ import annotations

import asyncio

from mcp_server.config import get_project_dir
from mcp_server.operations import OperationStatus, tracker
from mcp_server.server import mcp
from mcp_server.services.github_service import GitHubService


def _get_service() -> GitHubService:
    return GitHubService(get_project_dir())


@mcp.tool()
async def github_review_pr(
    pr_number: int, repo: str | None = None, model: str = "sonnet"
) -> dict:
    """Review a pull request with AI. Long-running operation - returns operation_id.

    Performs a multi-pass AI code review including security, quality,
    structural analysis, and AI comment triage.

    Args:
        pr_number: The PR number to review
        repo: Repository in owner/repo format (auto-detected from git remote if omitted)
        model: Model to use (haiku, sonnet, opus)

    Returns:
        Operation ID to poll with operation_get_status()
    """
    service = _get_service()
    op = tracker.create("github_review_pr", f"Starting review of PR #{pr_number}...")

    async def _run():
        try:
            tracker.update(
                op.id,
                status=OperationStatus.RUNNING,
                progress=10,
                message=f"Reviewing PR #{pr_number}...",
            )
            result = await service.review_pr(pr_number, repo, model)
            if "error" in result:
                tracker.update(
                    op.id, status=OperationStatus.FAILED, error=result["error"]
                )
            else:
                tracker.update(
                    op.id,
                    status=OperationStatus.COMPLETED,
                    progress=100,
                    message="Review complete",
                    result=result,
                )
        except Exception as e:
            tracker.update(op.id, status=OperationStatus.FAILED, error=str(e))

    op._task = asyncio.create_task(_run())
    return {
        "operation_id": op.id,
        "message": f"PR #{pr_number} review started. Poll operation_get_status() for progress.",
    }


@mcp.tool()
async def github_list_issues(
    state: str = "open", limit: int = 30, repo: str | None = None
) -> dict:
    """List GitHub issues for the project.

    Args:
        state: Issue state filter: open, closed, or all
        limit: Maximum number of issues to return
        repo: Repository in owner/repo format (auto-detected if omitted)

    Returns:
        List of issues with number, title, state, labels, author
    """
    service = _get_service()
    return await service.list_issues(state, limit, repo)


@mcp.tool()
async def github_auto_fix(issue_number: int, repo: str | None = None) -> dict:
    """Automatically fix a GitHub issue by creating a spec and building it. Long-running.

    Creates a specification from the issue, builds it through the autonomous
    pipeline (planner -> coder -> QA), and optionally creates a PR.

    Args:
        issue_number: The issue number to auto-fix
        repo: Repository in owner/repo format (auto-detected if omitted)

    Returns:
        Operation ID to poll with operation_get_status()
    """
    service = _get_service()
    op = tracker.create(
        "github_auto_fix", f"Starting auto-fix for issue #{issue_number}..."
    )

    async def _run():
        try:
            tracker.update(
                op.id,
                status=OperationStatus.RUNNING,
                progress=10,
                message=f"Auto-fixing issue #{issue_number}...",
            )
            result = await service.auto_fix_issue(issue_number, repo)
            if "error" in result:
                tracker.update(
                    op.id, status=OperationStatus.FAILED, error=result["error"]
                )
            else:
                tracker.update(
                    op.id,
                    status=OperationStatus.COMPLETED,
                    progress=100,
                    message="Auto-fix complete",
                    result=result,
                )
        except Exception as e:
            tracker.update(op.id, status=OperationStatus.FAILED, error=str(e))

    op._task = asyncio.create_task(_run())
    return {
        "operation_id": op.id,
        "message": f"Auto-fix for issue #{issue_number} started. Poll operation_get_status() for progress.",
    }


@mcp.tool()
def github_get_review(pr_number: int) -> dict:
    """Get the most recent review result for a PR.

    Returns the saved review data including findings, verdict, and summary.

    Args:
        pr_number: The PR number to get the review for

    Returns:
        Review result with findings, verdict, blockers, and summary
    """
    service = _get_service()
    return service.get_review(pr_number)


@mcp.tool()
async def github_triage_issues(
    issue_numbers: list[int], repo: str | None = None
) -> dict:
    """Triage and classify GitHub issues. Long-running.

    Analyzes issues for duplicates, spam, feature creep, and assigns
    categories, priority, and suggested labels.

    Args:
        issue_numbers: List of issue numbers to triage
        repo: Repository in owner/repo format (auto-detected if omitted)

    Returns:
        Operation ID to poll with operation_get_status()
    """
    service = _get_service()
    op = tracker.create(
        "github_triage_issues",
        f"Starting triage of {len(issue_numbers)} issues...",
    )

    async def _run():
        try:
            tracker.update(
                op.id,
                status=OperationStatus.RUNNING,
                progress=10,
                message=f"Triaging {len(issue_numbers)} issues...",
            )
            result = await service.triage_issues(issue_numbers, repo)
            if "error" in result:
                tracker.update(
                    op.id, status=OperationStatus.FAILED, error=result["error"]
                )
            else:
                tracker.update(
                    op.id,
                    status=OperationStatus.COMPLETED,
                    progress=100,
                    message=f"Triaged {result.get('count', 0)} issues",
                    result=result,
                )
        except Exception as e:
            tracker.update(op.id, status=OperationStatus.FAILED, error=str(e))

    op._task = asyncio.create_task(_run())
    return {
        "operation_id": op.id,
        "message": f"Triage of {len(issue_numbers)} issues started. Poll operation_get_status() for progress.",
    }
