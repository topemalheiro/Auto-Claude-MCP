"""Checkpoint service for Semi-Auto execution mode.

This module provides the CheckpointService for managing pause points
during Semi-Auto task execution.

Story Reference: Story 5.1 - Implement Checkpoint Service
Architecture Source: architecture.md#Checkpoint-Service
"""

from core.checkpoint.service import (
    CheckpointDecision,
    CheckpointResult,
    CheckpointService,
    CheckpointState,
    FIXED_CHECKPOINTS,
)

__all__ = [
    "CheckpointDecision",
    "CheckpointResult",
    "CheckpointService",
    "CheckpointState",
    "FIXED_CHECKPOINTS",
]
