"""
Insights Tools
===============

MCP tools for AI-powered codebase insights and Q&A.
"""

from __future__ import annotations

import asyncio

from mcp_server.config import get_project_dir
from mcp_server.operations import OperationStatus, tracker
from mcp_server.server import mcp
from mcp_server.services.insights_service import InsightsService


def _get_service() -> InsightsService:
    return InsightsService(get_project_dir())


@mcp.tool()
async def insights_ask(
    question: str, history: list | None = None, model: str = "sonnet"
) -> dict:
    """Ask an AI question about the codebase. Long-running operation.

    The AI agent has access to the codebase and can read files, search,
    and explore to answer questions about architecture, patterns, bugs, etc.

    Args:
        question: The question to ask about the codebase
        history: Optional conversation history as list of {role, content} dicts
        model: Model to use (haiku, sonnet, opus)

    Returns:
        Operation ID to poll with operation_get_status()
    """
    service = _get_service()
    op = tracker.create("insights_ask", "Processing question...")

    async def _run():
        try:
            tracker.update(
                op.id,
                status=OperationStatus.RUNNING,
                progress=10,
                message="AI is exploring the codebase...",
            )
            result = await service.ask(question, history, model)
            if "error" in result:
                tracker.update(
                    op.id, status=OperationStatus.FAILED, error=result["error"]
                )
            else:
                tracker.update(
                    op.id,
                    status=OperationStatus.COMPLETED,
                    progress=100,
                    message="Question answered",
                    result=result,
                )
        except Exception as e:
            tracker.update(op.id, status=OperationStatus.FAILED, error=str(e))

    op._task = asyncio.create_task(_run())
    return {
        "operation_id": op.id,
        "message": "Insights query started. Poll operation_get_status() for the answer.",
    }


@mcp.tool()
def insights_suggest_tasks() -> dict:
    """Get AI-suggested tasks based on recent insights conversations.

    Returns task suggestions derived from ideation data or previous
    insights conversations.

    Returns:
        List of task suggestions with title, description, category, impact
    """
    service = _get_service()
    return service.suggest_tasks()
