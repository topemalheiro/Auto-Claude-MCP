"""
Tests for mcp_server/tools/ops.py
==================================

Tests operation status polling and cancellation tools.
Uses the OperationTracker directly.
"""

import sys
from pathlib import Path

# Add backend to sys.path
_backend = Path(__file__).parent.parent / "apps" / "backend"
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

# Pre-mock SDK modules before any mcp_server imports
from unittest.mock import MagicMock

if "claude_agent_sdk" not in sys.modules:
    sys.modules["claude_agent_sdk"] = MagicMock()
    sys.modules["claude_agent_sdk.types"] = MagicMock()

import pytest

from mcp_server.operations import OperationStatus, OperationTracker, tracker
from mcp_server.tools.ops import (
    operation_cancel as _operation_cancel_tool,
    operation_get_status as _operation_get_status_tool,
)

# @mcp.tool() wraps functions as FunctionTool; access .fn for the raw callable
operation_get_status = _operation_get_status_tool.fn
operation_cancel = _operation_cancel_tool.fn


@pytest.fixture(autouse=True)
def clean_tracker():
    """Clear the global tracker between tests."""
    tracker._operations.clear()
    yield
    tracker._operations.clear()


class TestOperationGetStatus:
    """Tests for operation_get_status()."""

    def test_returns_operation_dict(self):
        """Returns the operation as a dict for a valid ID."""
        op = tracker.create("build", "Building spec: 001")
        tracker.update(
            op.id,
            status=OperationStatus.RUNNING,
            progress=50,
            message="Halfway done",
        )

        result = operation_get_status(op.id)

        assert result["id"] == op.id
        assert result["type"] == "build"
        assert result["status"] == "running"
        assert result["progress"] == 50
        assert result["message"] == "Halfway done"

    def test_returns_error_for_unknown_id(self):
        """Returns error dict for a nonexistent operation ID."""
        result = operation_get_status("nonexistent-uuid")
        assert "error" in result
        assert "not found" in result["error"]

    def test_returns_completed_operation(self):
        """Returns completed operation with result."""
        op = tracker.create("qa_review", "QA for 001")
        tracker.update(
            op.id,
            status=OperationStatus.COMPLETED,
            progress=100,
            message="QA approved",
            result={"status": "approved"},
        )

        result = operation_get_status(op.id)

        assert result["status"] == "completed"
        assert result["progress"] == 100
        assert result["result"]["status"] == "approved"

    def test_returns_failed_operation(self):
        """Returns failed operation with error message."""
        op = tracker.create("build", "Building spec: 001")
        tracker.update(
            op.id,
            status=OperationStatus.FAILED,
            error="Process exited with code 1",
        )

        result = operation_get_status(op.id)

        assert result["status"] == "failed"
        assert result["error"] == "Process exited with code 1"

    def test_includes_elapsed_time(self):
        """Result includes elapsed_seconds field."""
        op = tracker.create("build", "test")
        result = operation_get_status(op.id)
        assert "elapsed_seconds" in result
        assert isinstance(result["elapsed_seconds"], float)


class TestOperationCancel:
    """Tests for operation_cancel()."""

    def test_cancel_pending_operation(self):
        """Cancels a pending operation successfully."""
        op = tracker.create("build", "Building spec: 001")
        result = operation_cancel(op.id)
        assert result["success"] is True

        # Verify it's actually cancelled
        status = operation_get_status(op.id)
        assert status["status"] == "cancelled"

    def test_cancel_running_operation(self):
        """Cancels a running operation."""
        op = tracker.create("build", "Building spec: 001")
        tracker.update(op.id, status=OperationStatus.RUNNING)

        result = operation_cancel(op.id)
        assert result["success"] is True

    def test_cannot_cancel_completed_operation(self):
        """Cannot cancel an already completed operation."""
        op = tracker.create("build", "Building spec: 001")
        tracker.update(op.id, status=OperationStatus.COMPLETED, progress=100)

        result = operation_cancel(op.id)
        assert result["success"] is False
        assert "error" in result

    def test_cannot_cancel_failed_operation(self):
        """Cannot cancel an already failed operation."""
        op = tracker.create("build", "Building spec: 001")
        tracker.update(op.id, status=OperationStatus.FAILED, error="failed")

        result = operation_cancel(op.id)
        assert result["success"] is False

    def test_cancel_nonexistent_returns_error(self):
        """Returns error when cancelling a nonexistent operation."""
        result = operation_cancel("nonexistent-uuid")
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_cancel_already_cancelled(self):
        """Cancelling an already-cancelled operation still succeeds (idempotent within tracker)."""
        op = tracker.create("build", "test")
        # First cancel
        tracker.cancel(op.id)
        # Second cancel via the tool - should fail because it's in CANCELLED state
        # (CANCELLED is not COMPLETED/FAILED, but let's see if tracker.cancel handles it)
        result = operation_cancel(op.id)
        # The tracker.cancel checks for COMPLETED and FAILED states;
        # CANCELLED is neither, so it should succeed
        assert result["success"] is True


class TestOperationTrackerIntegration:
    """Integration tests exercising the tracker lifecycle through tools."""

    def test_create_poll_complete_lifecycle(self):
        """Full lifecycle: create -> poll -> update -> complete -> poll."""
        op = tracker.create("spec_create", "Creating spec 001")

        # Poll pending
        result = operation_get_status(op.id)
        assert result["status"] == "pending"

        # Move to running
        tracker.update(op.id, status=OperationStatus.RUNNING, progress=30)
        result = operation_get_status(op.id)
        assert result["status"] == "running"
        assert result["progress"] == 30

        # Complete
        tracker.update(
            op.id,
            status=OperationStatus.COMPLETED,
            progress=100,
            result={"spec_id": "001-feat"},
        )
        result = operation_get_status(op.id)
        assert result["status"] == "completed"
        assert result["result"]["spec_id"] == "001-feat"

    def test_create_cancel_lifecycle(self):
        """Full lifecycle: create -> poll -> cancel -> poll."""
        op = tracker.create("build", "Building")
        tracker.update(op.id, status=OperationStatus.RUNNING)

        result = operation_cancel(op.id)
        assert result["success"] is True

        status = operation_get_status(op.id)
        assert status["status"] == "cancelled"

    def test_multiple_concurrent_operations(self):
        """Multiple operations can coexist independently."""
        op1 = tracker.create("build", "Build 001")
        op2 = tracker.create("qa_review", "QA 002")

        tracker.update(op1.id, status=OperationStatus.RUNNING, progress=50)
        tracker.update(op2.id, status=OperationStatus.COMPLETED, progress=100)

        r1 = operation_get_status(op1.id)
        r2 = operation_get_status(op2.id)

        assert r1["status"] == "running"
        assert r2["status"] == "completed"
