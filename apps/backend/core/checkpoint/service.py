"""CheckpointService implementation for Semi-Auto execution mode.

This module implements the CheckpointService that manages pause points
during Semi-Auto task execution. It handles checkpoint detection, state
persistence, and resume functionality.

Story Reference: Story 5.1 - Implement Checkpoint Service
Architecture Source: architecture.md#Checkpoint-Service
"""

import asyncio
import json
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from methodologies.protocols import Checkpoint, CheckpointStatus

logger = logging.getLogger(__name__)


# =============================================================================
# Checkpoint Decision Enum
# =============================================================================


class CheckpointDecision(Enum):
    """Valid decisions for checkpoint resume.

    Attributes:
        APPROVE: User approves the checkpoint, continue execution
        REJECT: User rejects the checkpoint, stop execution
        REVISE: User requests revision, may continue with modifications
    """

    APPROVE = "approve"
    REJECT = "reject"
    REVISE = "revise"

    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Check if a string is a valid decision value."""
        return value in {d.value for d in cls}


# =============================================================================
# Fixed Checkpoints Definition (FR27)
# =============================================================================

FIXED_CHECKPOINTS: list[Checkpoint] = [
    Checkpoint(
        id="after_planning",
        name="Planning Review",
        description="Review implementation plan before coding begins",
        phase_id="plan",
        status=CheckpointStatus.PENDING,
        requires_approval=True,
    ),
    Checkpoint(
        id="after_coding",
        name="Code Review",
        description="Review implemented code before validation",
        phase_id="coding",
        status=CheckpointStatus.PENDING,
        requires_approval=True,
    ),
    Checkpoint(
        id="after_validation",
        name="Validation Review",
        description="Review QA results before completion",
        phase_id="validate",
        status=CheckpointStatus.PENDING,
        requires_approval=True,
    ),
]


# =============================================================================
# Checkpoint Result Dataclass
# =============================================================================


@dataclass
class FeedbackAttachment:
    """Attachment associated with checkpoint feedback (Story 5.3).

    Attributes:
        id: Unique identifier for the attachment
        type: Type of attachment ('file' or 'link')
        name: Display name for the attachment
        path: File path (for files) or URL (for links)
        size: File size in bytes (for files)
        mime_type: MIME type (for files)
    """

    id: str
    type: str  # 'file' or 'link'
    name: str
    path: str
    size: int | None = None
    mime_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize attachment to dictionary."""
        result = {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "path": self.path,
        }
        if self.size is not None:
            result["size"] = self.size
        if self.mime_type is not None:
            result["mime_type"] = self.mime_type
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FeedbackAttachment":
        """Deserialize attachment from dictionary."""
        return cls(
            id=data["id"],
            type=data["type"],
            name=data["name"],
            path=data["path"],
            size=data.get("size"),
            mime_type=data.get("mime_type"),
        )


@dataclass
class CheckpointFeedback:
    """Feedback entry for a checkpoint (Story 5.3).

    Attributes:
        id: Unique identifier for the feedback entry
        checkpoint_id: ID of the checkpoint this feedback belongs to
        feedback: The feedback text
        attachments: List of attached files or links
        created_at: When the feedback was submitted
    """

    id: str
    checkpoint_id: str
    feedback: str
    attachments: list[FeedbackAttachment] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Serialize feedback to dictionary."""
        return {
            "id": self.id,
            "checkpoint_id": self.checkpoint_id,
            "feedback": self.feedback,
            "attachments": [a.to_dict() for a in self.attachments],
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CheckpointFeedback":
        """Deserialize feedback from dictionary."""
        return cls(
            id=data["id"],
            checkpoint_id=data["checkpoint_id"],
            feedback=data["feedback"],
            attachments=[FeedbackAttachment.from_dict(a) for a in data.get("attachments", [])],
            created_at=datetime.fromisoformat(data["created_at"]),
        )


@dataclass
class CheckpointResult:
    """Result from a checkpoint pause/resume cycle.

    Attributes:
        checkpoint_id: ID of the checkpoint that was reached
        decision: User's decision - one of CheckpointDecision values
            (approve, reject, revise). Use CheckpointDecision.is_valid()
            to validate.
        feedback: Optional user feedback or comments
        attachments: Optional list of attached files/links (Story 5.3)
        resumed_at: Timestamp when execution resumed
        metadata: Additional context from the checkpoint
    """

    checkpoint_id: str
    decision: str  # One of CheckpointDecision values: "approve", "reject", "revise"
    feedback: str | None = None
    attachments: list[FeedbackAttachment] = field(default_factory=list)
    resumed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Checkpoint State Dataclass
# =============================================================================


@dataclass
class CheckpointState:
    """Persisted state at a checkpoint for recovery.

    Attributes:
        task_id: ID of the task being executed
        checkpoint_id: ID of the checkpoint reached
        phase_id: ID of the current phase
        paused_at: Timestamp when paused
        artifacts: List of artifact paths produced so far
        context: Additional execution context
        is_paused: Whether execution is currently paused
        feedback_history: History of feedback provided at checkpoints (Story 5.3)
    """

    task_id: str
    checkpoint_id: str
    phase_id: str
    paused_at: datetime
    artifacts: list[str] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    is_paused: bool = True
    feedback_history: list[CheckpointFeedback] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize state to dictionary for JSON persistence."""
        return {
            "task_id": self.task_id,
            "checkpoint_id": self.checkpoint_id,
            "phase_id": self.phase_id,
            "paused_at": self.paused_at.isoformat(),
            "artifacts": self.artifacts,
            "context": self.context,
            "is_paused": self.is_paused,
            "feedback_history": [f.to_dict() for f in self.feedback_history],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CheckpointState":
        """Deserialize state from dictionary."""
        return cls(
            task_id=data["task_id"],
            checkpoint_id=data["checkpoint_id"],
            phase_id=data["phase_id"],
            paused_at=datetime.fromisoformat(data["paused_at"]),
            artifacts=data.get("artifacts", []),
            context=data.get("context", {}),
            is_paused=data.get("is_paused", True),
            feedback_history=[CheckpointFeedback.from_dict(f) for f in data.get("feedback_history", [])],
        )


# =============================================================================
# Checkpoint Event Callback Type
# =============================================================================

CheckpointEventCallback = Callable[[dict[str, Any]], None] | None


# =============================================================================
# CheckpointService Implementation
# =============================================================================


class CheckpointService:
    """Service for managing Semi-Auto execution checkpoints.

    The CheckpointService manages pause points in Semi-Auto execution mode.
    It detects when checkpoints are reached, persists state, emits events
    to the frontend, and handles resume operations.

    Story Reference: Story 5.1 - Implement Checkpoint Service
    Architecture Source: architecture.md#Checkpoint-Service

    Attributes:
        task_id: Unique identifier for the current task
        spec_dir: Directory for spec-related files (used for state persistence)
        checkpoints: List of checkpoint definitions for this methodology
        _resume_event: Asyncio event for blocking until resumed
        _decision: User's decision after checkpoint review
        _feedback: User's feedback after checkpoint review
        _current_checkpoint_id: ID of the currently active checkpoint
        _state_file: Path to the checkpoint state file

    Example:
        service = CheckpointService(
            task_id="task-123",
            spec_dir=Path("/path/to/spec"),
            methodology="native"
        )

        # During phase execution
        result = await service.check_and_pause("plan")
        if result:
            print(f"Checkpoint decision: {result.decision}")
    """

    def __init__(
        self,
        task_id: str,
        spec_dir: Path,
        methodology: str = "native",
        checkpoints: list[Checkpoint] | None = None,
    ) -> None:
        """Initialize the CheckpointService.

        Args:
            task_id: Unique identifier for the task
            spec_dir: Directory for spec-related files
            methodology: Name of the methodology (for custom checkpoints)
            checkpoints: Custom checkpoint definitions (uses FIXED_CHECKPOINTS if None)
        """
        self.task_id = task_id
        self.spec_dir = Path(spec_dir)
        self.methodology = methodology

        # Use provided checkpoints or fixed defaults
        self.checkpoints = checkpoints if checkpoints is not None else FIXED_CHECKPOINTS

        # Resume synchronization
        self._resume_event = asyncio.Event()
        self._decision: str | None = None
        self._feedback: str | None = None
        self._attachments: list[FeedbackAttachment] = []
        self._current_checkpoint_id: str | None = None

        # State persistence
        self._state_file = self.spec_dir / "checkpoint_state.json"
        self._feedback_history_file = self.spec_dir / "feedback_history.json"

        # Event callback (to be set by framework)
        self._event_callback: CheckpointEventCallback = None

        logger.debug(
            f"CheckpointService initialized for task {task_id} "
            f"with {len(self.checkpoints)} checkpoints"
        )

    # =========================================================================
    # Public Interface (matches CheckpointService Protocol)
    # =========================================================================

    def create_checkpoint(
        self, checkpoint_id: str, data: dict[str, Any]
    ) -> CheckpointState:
        """Create a checkpoint for user review.

        This method is part of the CheckpointService Protocol interface.
        It saves checkpoint state and prepares for pause.

        Args:
            checkpoint_id: Unique identifier for the checkpoint
            data: Data to be reviewed at the checkpoint

        Returns:
            CheckpointState that was created and persisted
        """
        checkpoint = self._get_checkpoint_by_id(checkpoint_id)
        if not checkpoint:
            logger.warning(f"Checkpoint {checkpoint_id} not found, creating ad-hoc")
            checkpoint = Checkpoint(
                id=checkpoint_id,
                name=checkpoint_id.replace("_", " ").title(),
                description="Ad-hoc checkpoint",
                phase_id=data.get("phase_id", "unknown"),
            )

        # Save state
        state = CheckpointState(
            task_id=self.task_id,
            checkpoint_id=checkpoint_id,
            phase_id=checkpoint.phase_id,
            paused_at=datetime.now(),
            artifacts=data.get("artifacts", []),
            context=data,
            is_paused=True,
        )
        self._save_state(state)
        logger.info(f"Checkpoint {checkpoint_id} created for task {self.task_id}")
        return state

    async def check_and_pause(
        self,
        phase_id: str,
        artifacts: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> CheckpointResult | None:
        """Check if a checkpoint exists for the phase and pause if so.

        This is the primary method called during phase execution to handle
        checkpoint logic. If a checkpoint is defined for the given phase,
        execution pauses until the user resumes.

        Args:
            phase_id: ID of the phase that just completed
            artifacts: List of artifact paths produced so far
            context: Additional execution context to persist

        Returns:
            CheckpointResult if a checkpoint was reached and resumed,
            None if no checkpoint for this phase
        """
        checkpoint = self._get_checkpoint_for_phase(phase_id)
        if not checkpoint:
            logger.debug(f"No checkpoint defined for phase {phase_id}")
            return None

        logger.info(
            f"Checkpoint '{checkpoint.id}' reached for phase {phase_id} "
            f"in task {self.task_id}"
        )

        # Save checkpoint state
        state = CheckpointState(
            task_id=self.task_id,
            checkpoint_id=checkpoint.id,
            phase_id=phase_id,
            paused_at=datetime.now(),
            artifacts=artifacts or [],
            context=context or {},
            is_paused=True,
        )
        self._save_state(state)

        # Store current checkpoint ID
        self._current_checkpoint_id = checkpoint.id

        # Emit checkpoint event to frontend
        self._emit_checkpoint_reached(checkpoint, state)

        # Wait for resume
        logger.debug(f"Waiting for resume signal for checkpoint {checkpoint.id}")
        await self._resume_event.wait()
        self._resume_event.clear()

        # Build result (Story 5.3: include attachments)
        result = CheckpointResult(
            checkpoint_id=checkpoint.id,
            decision=self._decision or "approve",
            feedback=self._feedback,
            attachments=self._attachments,
            resumed_at=datetime.now(),
            metadata={"phase_id": phase_id, "artifacts": artifacts or []},
        )

        # Update state to reflect resumed status
        state.is_paused = False
        self._save_state(state)

        # Reset decision/feedback/attachments for next checkpoint
        self._decision = None
        self._feedback = None
        self._attachments = []
        self._current_checkpoint_id = None

        logger.info(
            f"Checkpoint {checkpoint.id} resumed with decision: {result.decision}"
        )
        return result

    def resume(
        self,
        decision: str,
        feedback: str | None = None,
        attachments: list[dict[str, Any]] | None = None,
    ) -> None:
        """Resume execution from a checkpoint.

        Called by the frontend/framework when the user has reviewed the
        checkpoint and made a decision.

        Args:
            decision: User's decision (approve, reject, revise)
            feedback: Optional feedback or comments from user
            attachments: Optional list of attachment dicts (Story 5.3)
        """
        if not self._current_checkpoint_id:
            logger.warning("resume() called but no checkpoint is active")
            return

        logger.info(
            f"Resuming checkpoint {self._current_checkpoint_id} "
            f"with decision: {decision}"
        )

        self._decision = decision
        self._feedback = feedback

        # Convert attachment dicts to FeedbackAttachment objects (Story 5.3)
        self._attachments = []
        if attachments:
            for a in attachments:
                self._attachments.append(FeedbackAttachment.from_dict(a))

        # Save feedback with attachments to history if provided (Story 5.3)
        if feedback:
            self._save_feedback_to_history(
                self._current_checkpoint_id,
                feedback,
                self._attachments,
            )

        self._resume_event.set()

    def get_current_checkpoint(self) -> Checkpoint | None:
        """Get the currently active checkpoint, if any.

        Returns:
            The Checkpoint object if execution is paused at a checkpoint,
            None otherwise
        """
        if not self._current_checkpoint_id:
            return None
        return self._get_checkpoint_by_id(self._current_checkpoint_id)

    def is_paused(self) -> bool:
        """Check if execution is currently paused at a checkpoint.

        Returns:
            True if paused at a checkpoint, False otherwise
        """
        return self._current_checkpoint_id is not None

    def set_event_callback(
        self, callback: Callable[[dict[str, Any]], None] | None
    ) -> None:
        """Set the callback for checkpoint events.

        The callback is invoked when a checkpoint is reached to notify
        the frontend/framework. The callback receives a dictionary with
        event details including task_id, checkpoint_id, phase_id, etc.

        Args:
            callback: Callback function accepting dict[str, Any], or None to disable
        """
        self._event_callback = callback

    # =========================================================================
    # State Persistence
    # =========================================================================

    def _save_state(self, state: CheckpointState) -> None:
        """Save checkpoint state to JSON file.

        Args:
            state: CheckpointState to persist
        """
        try:
            self.spec_dir.mkdir(parents=True, exist_ok=True)
            with open(self._state_file, "w") as f:
                json.dump(state.to_dict(), f, indent=2)
            logger.debug(f"Checkpoint state saved to {self._state_file}")
        except OSError as e:
            logger.error(f"Failed to save checkpoint state: {e}")
            raise

    def load_state(self) -> CheckpointState | None:
        """Load checkpoint state from JSON file.

        Returns:
            CheckpointState if file exists, None otherwise
        """
        if not self._state_file.exists():
            logger.debug(f"No checkpoint state file at {self._state_file}")
            return None

        try:
            with open(self._state_file) as f:
                data = json.load(f)
            state = CheckpointState.from_dict(data)
            logger.debug(f"Loaded checkpoint state from {self._state_file}")
            return state
        except (OSError, json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to load checkpoint state: {e}")
            return None

    def clear_state(self) -> None:
        """Remove checkpoint state file.

        Called after successful task completion to clean up.
        """
        if self._state_file.exists():
            try:
                self._state_file.unlink()
                logger.debug(f"Removed checkpoint state file {self._state_file}")
            except OSError as e:
                logger.warning(f"Failed to remove checkpoint state: {e}")

    # =========================================================================
    # Feedback History (Story 5.3)
    # =========================================================================

    def _save_feedback_to_history(
        self,
        checkpoint_id: str,
        feedback: str,
        attachments: list[FeedbackAttachment] | None = None,
    ) -> CheckpointFeedback:
        """Save feedback with attachments to the history file.

        Args:
            checkpoint_id: ID of the checkpoint this feedback is for
            feedback: The feedback text
            attachments: Optional list of attachments

        Returns:
            The created CheckpointFeedback object
        """
        # Create feedback entry
        feedback_entry = CheckpointFeedback(
            id=str(uuid.uuid4()),
            checkpoint_id=checkpoint_id,
            feedback=feedback,
            attachments=attachments or [],
            created_at=datetime.now(),
        )

        # Load existing history
        history = self.load_feedback_history()

        # Append new entry
        history.append(feedback_entry)

        # Save updated history
        self._save_feedback_history(history)

        logger.debug(f"Saved feedback for checkpoint {checkpoint_id}")
        return feedback_entry

    def _save_feedback_history(self, history: list[CheckpointFeedback]) -> None:
        """Save feedback history to JSON file.

        Args:
            history: List of feedback entries to save
        """
        try:
            self.spec_dir.mkdir(parents=True, exist_ok=True)
            with open(self._feedback_history_file, "w") as f:
                json.dump([fb.to_dict() for fb in history], f, indent=2)
            logger.debug(f"Feedback history saved to {self._feedback_history_file}")
        except OSError as e:
            logger.error(f"Failed to save feedback history: {e}")
            raise

    def load_feedback_history(self) -> list[CheckpointFeedback]:
        """Load feedback history from JSON file.

        Returns:
            List of feedback entries, empty if file doesn't exist
        """
        if not self._feedback_history_file.exists():
            logger.debug(f"No feedback history file at {self._feedback_history_file}")
            return []

        try:
            with open(self._feedback_history_file) as f:
                data = json.load(f)
            history = [CheckpointFeedback.from_dict(fb) for fb in data]
            logger.debug(f"Loaded {len(history)} feedback entries from history")
            return history
        except (OSError, json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to load feedback history: {e}")
            return []

    def get_feedback_for_checkpoint(
        self, checkpoint_id: str
    ) -> list[CheckpointFeedback]:
        """Get all feedback entries for a specific checkpoint.

        Args:
            checkpoint_id: ID of the checkpoint to get feedback for

        Returns:
            List of feedback entries for the checkpoint
        """
        history = self.load_feedback_history()
        return [fb for fb in history if fb.checkpoint_id == checkpoint_id]

    def clear_feedback_history(self) -> None:
        """Remove feedback history file.

        Called after successful task completion to clean up.
        """
        if self._feedback_history_file.exists():
            try:
                self._feedback_history_file.unlink()
                logger.debug(f"Removed feedback history file {self._feedback_history_file}")
            except OSError as e:
                logger.warning(f"Failed to remove feedback history: {e}")

    # =========================================================================
    # Checkpoint Detection
    # =========================================================================

    def _get_checkpoint_for_phase(self, phase_id: str) -> Checkpoint | None:
        """Get the checkpoint definition for a phase, if any.

        Args:
            phase_id: ID of the phase to check

        Returns:
            Checkpoint if one is defined for this phase, None otherwise
        """
        for checkpoint in self.checkpoints:
            if checkpoint.phase_id == phase_id:
                return checkpoint
        return None

    def _get_checkpoint_by_id(self, checkpoint_id: str) -> Checkpoint | None:
        """Get a checkpoint by its ID.

        Args:
            checkpoint_id: ID of the checkpoint to find

        Returns:
            Checkpoint if found, None otherwise
        """
        for checkpoint in self.checkpoints:
            if checkpoint.id == checkpoint_id:
                return checkpoint
        return None

    def has_checkpoint_for_phase(self, phase_id: str) -> bool:
        """Check if a checkpoint is defined for a phase.

        Args:
            phase_id: ID of the phase to check

        Returns:
            True if a checkpoint exists, False otherwise
        """
        return self._get_checkpoint_for_phase(phase_id) is not None

    # =========================================================================
    # Event Emission
    # =========================================================================

    def _emit_checkpoint_reached(
        self, checkpoint: Checkpoint, state: CheckpointState
    ) -> None:
        """Emit an event indicating a checkpoint has been reached.

        This notifies the frontend that user review is needed.

        Args:
            checkpoint: The checkpoint that was reached
            state: Current checkpoint state
        """
        # Get feedback history for this task (Story 5.3)
        feedback_history = self.load_feedback_history()

        event_data = {
            "event": "checkpoint_reached",
            "task_id": self.task_id,
            "checkpoint_id": checkpoint.id,
            "checkpoint_name": checkpoint.name,
            "checkpoint_description": checkpoint.description,
            "phase_id": state.phase_id,
            "paused_at": state.paused_at.isoformat(),
            "artifacts": state.artifacts,
            "requires_approval": checkpoint.requires_approval,
            "feedback_history": [fb.to_dict() for fb in feedback_history],  # Story 5.3
        }

        logger.debug(f"Emitting checkpoint_reached event: {event_data}")

        # Call the callback if set
        # Note: Actual IPC emission will be handled by the framework
        # when integrating with the frontend
        if self._event_callback:
            try:
                self._event_callback(event_data)
            except Exception as e:
                logger.error(f"Error in checkpoint event callback: {e}")

    # =========================================================================
    # Recovery Support
    # =========================================================================

    async def recover_from_state(self) -> CheckpointResult | None:
        """Attempt to recover from a persisted checkpoint state.

        This is called on startup to handle recovery from a crash
        or restart while paused at a checkpoint.

        Returns:
            CheckpointResult if recovered and resumed, None if no state
        """
        state = self.load_state()
        if not state or not state.is_paused:
            logger.debug("No paused checkpoint state to recover from")
            return None

        logger.info(
            f"Recovering from checkpoint {state.checkpoint_id} "
            f"for task {state.task_id}"
        )

        checkpoint = self._get_checkpoint_by_id(state.checkpoint_id)
        if not checkpoint:
            logger.warning(f"Cannot recover: checkpoint {state.checkpoint_id} not found")
            return None

        # Restore state and wait for resume
        self._current_checkpoint_id = checkpoint.id

        # Re-emit the checkpoint event
        self._emit_checkpoint_reached(checkpoint, state)

        # Wait for resume
        await self._resume_event.wait()
        self._resume_event.clear()

        result = CheckpointResult(
            checkpoint_id=checkpoint.id,
            decision=self._decision or "approve",
            feedback=self._feedback,
            attachments=self._attachments,
            resumed_at=datetime.now(),
            metadata={
                "phase_id": state.phase_id,
                "artifacts": state.artifacts,
                "recovered": True,
            },
        )

        # Update state
        state.is_paused = False
        self._save_state(state)

        self._decision = None
        self._feedback = None
        self._attachments = []
        self._current_checkpoint_id = None

        logger.info(f"Recovered checkpoint {checkpoint.id} with decision: {result.decision}")
        return result
