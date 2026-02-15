"""
Operations Management Tools
============================

Tools for polling long-running operation status and cancelling operations.
"""

from __future__ import annotations

from mcp_server.operations import tracker
from mcp_server.server import mcp


@mcp.tool()
def operation_get_status(operation_id: str) -> dict:
    """Get the status of a long-running operation.

    Use this to poll for progress on operations started by tools like
    spec_create, build_start, qa_start_review, etc.

    Args:
        operation_id: The operation ID returned by the tool that started the operation

    Returns:
        Operation status including progress (0-100), message, and result when complete
    """
    op = tracker.get(operation_id)
    if op is None:
        return {"error": f"Operation {operation_id} not found"}
    return op.to_dict()


@mcp.tool()
def operation_cancel(operation_id: str) -> dict:
    """Cancel a running operation.

    Args:
        operation_id: The operation ID to cancel

    Returns:
        Whether the cancellation was successful
    """
    success = tracker.cancel(operation_id)
    if not success:
        op = tracker.get(operation_id)
        if op is None:
            return {"success": False, "error": "Operation not found"}
        return {
            "success": False,
            "error": f"Cannot cancel operation in {op.status.value} state",
        }
    return {"success": True, "message": "Operation cancelled"}
