"""
QA Tools
=========

MCP tools for running QA reviews, getting reports, and manual approval.
"""

from __future__ import annotations

import asyncio
import logging

from mcp_server.config import get_project_dir
from mcp_server.operations import OperationStatus, tracker
from mcp_server.server import mcp

logger = logging.getLogger(__name__)


@mcp.tool()
async def qa_start_review(spec_id: str) -> dict:
    """Start QA review for a completed build. This is a long-running operation.

    Runs the QA reviewer agent which validates the implementation against
    the spec's acceptance criteria. The agent reads code, runs tests, and
    produces a detailed QA report.

    Args:
        spec_id: Spec folder name or prefix (e.g. '001' or '001-my-feature')

    Returns:
        An operation_id to poll with operation_get_status() for progress
    """
    op = tracker.create("qa_review", f"QA review for: {spec_id}")

    async def _run() -> None:
        try:
            from mcp_server.services.qa_service import QAService

            service = QAService(get_project_dir())

            tracker.update(
                op.id,
                status=OperationStatus.RUNNING,
                progress=10,
                message="Starting QA review session...",
            )

            result = await service.start_review(spec_id=spec_id)

            status = result.get("status", "error")
            if status == "approved":
                tracker.update(
                    op.id,
                    status=OperationStatus.COMPLETED,
                    progress=100,
                    message="QA approved - all acceptance criteria validated",
                    result=result,
                )
            elif status == "rejected":
                tracker.update(
                    op.id,
                    status=OperationStatus.COMPLETED,
                    progress=100,
                    message="QA rejected - issues found, see report",
                    result=result,
                )
            else:
                tracker.update(
                    op.id,
                    status=OperationStatus.FAILED,
                    error=result.get("error", "QA review failed"),
                    result=result,
                )
        except Exception as e:
            logger.exception("qa_start_review operation failed")
            tracker.update(
                op.id,
                status=OperationStatus.FAILED,
                error=str(e),
            )

    op._task = asyncio.create_task(_run())
    return {
        "operation_id": op.id,
        "message": "QA review started. Poll operation_get_status() for progress.",
    }


@mcp.tool()
def qa_get_report(spec_id: str) -> dict:
    """Get the QA report for a spec.

    Returns the full QA report including validation results, issues found,
    and the qa_signoff status from the implementation plan.

    Args:
        spec_id: Spec folder name or prefix

    Returns:
        QA report content, fix requests, and signoff status
    """
    from mcp_server.services.qa_service import QAService

    service = QAService(get_project_dir())
    return service.get_report(spec_id)


@mcp.tool()
def qa_approve(spec_id: str) -> dict:
    """Manually approve a spec that's in QA review.

    Use this to bypass the automated QA review and mark a spec as approved.
    This updates the implementation_plan.json qa_signoff status.

    Args:
        spec_id: Spec folder name or prefix

    Returns:
        Whether the approval was successful
    """
    from mcp_server.services.qa_service import QAService

    service = QAService(get_project_dir())
    return service.approve(spec_id)
