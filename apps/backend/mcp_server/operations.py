"""
Long-Running Operation Tracker
===============================

Tracks async operations (spec creation, builds, QA, etc.) so MCP clients
can poll for progress. Tools that start long-running work return an
operation_id immediately; clients poll operation_get_status() for updates.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class OperationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Operation:
    """Represents a long-running operation."""

    id: str
    type: str  # e.g. "spec_create", "build", "qa_review"
    status: OperationStatus = OperationStatus.PENDING
    progress: int = 0  # 0-100
    message: str = ""
    result: Any = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    _task: asyncio.Task | None = field(default=None, repr=False)

    def to_dict(self) -> dict:
        """Serialize for MCP response."""
        return {
            "id": self.id,
            "type": self.type,
            "status": self.status.value,
            "progress": self.progress,
            "message": self.message,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "elapsed_seconds": round(time.time() - self.created_at, 1),
        }


class OperationTracker:
    """Manages the lifecycle of long-running operations."""

    def __init__(self, max_completed: int = 100):
        self._operations: dict[str, Operation] = {}
        self._max_completed = max_completed

    def create(self, operation_type: str, message: str = "") -> Operation:
        """Create a new operation and return it."""
        op = Operation(
            id=str(uuid.uuid4()),
            type=operation_type,
            status=OperationStatus.PENDING,
            message=message or f"Starting {operation_type}...",
        )
        self._operations[op.id] = op
        self._cleanup_old()
        return op

    def get(self, operation_id: str) -> Operation | None:
        """Get an operation by ID."""
        return self._operations.get(operation_id)

    def update(
        self,
        operation_id: str,
        *,
        status: OperationStatus | None = None,
        progress: int | None = None,
        message: str | None = None,
        result: Any = None,
        error: str | None = None,
    ) -> Operation | None:
        """Update an operation's state."""
        op = self._operations.get(operation_id)
        if op is None:
            return None

        if status is not None:
            op.status = status
        if progress is not None:
            op.progress = max(0, min(100, progress))
        if message is not None:
            op.message = message
        if result is not None:
            op.result = result
        if error is not None:
            op.error = error
        op.updated_at = time.time()
        return op

    def cancel(self, operation_id: str) -> bool:
        """Cancel a running operation."""
        op = self._operations.get(operation_id)
        if op is None:
            return False
        if op.status in (OperationStatus.COMPLETED, OperationStatus.FAILED):
            return False

        # Cancel the asyncio task if it exists
        if op._task and not op._task.done():
            op._task.cancel()

        op.status = OperationStatus.CANCELLED
        op.message = "Operation cancelled by user"
        op.updated_at = time.time()
        return True

    def list_active(self) -> list[Operation]:
        """List all active (non-terminal) operations."""
        return [
            op
            for op in self._operations.values()
            if op.status in (OperationStatus.PENDING, OperationStatus.RUNNING)
        ]

    def _cleanup_old(self) -> None:
        """Remove old completed operations to prevent memory growth."""
        completed = [
            op
            for op in self._operations.values()
            if op.status
            in (
                OperationStatus.COMPLETED,
                OperationStatus.FAILED,
                OperationStatus.CANCELLED,
            )
        ]
        if len(completed) > self._max_completed:
            # Sort by created_at, remove oldest
            completed.sort(key=lambda o: o.created_at)
            for op in completed[: len(completed) - self._max_completed]:
                del self._operations[op.id]


# Global singleton
tracker = OperationTracker()
