"""Unit tests for CheckpointService.

Story Reference: Story 5.1 - Implement Checkpoint Service
Tests cover: checkpoint detection, pause mechanism, state persistence, resume
"""

import asyncio
import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from core.checkpoint.service import (
    FIXED_CHECKPOINTS,
    CheckpointDecision,
    CheckpointResult,
    CheckpointService,
    CheckpointState,
)
from methodologies.protocols import Checkpoint, CheckpointStatus


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_spec_dir():
    """Create a temporary directory for spec files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def checkpoint_service(temp_spec_dir):
    """Create a CheckpointService instance for testing."""
    return CheckpointService(
        task_id="test-task-123",
        spec_dir=temp_spec_dir,
        methodology="native",
    )


@pytest.fixture
def custom_checkpoints():
    """Custom checkpoint definitions for testing."""
    return [
        Checkpoint(
            id="custom_checkpoint_1",
            name="Custom Checkpoint 1",
            description="First custom checkpoint",
            phase_id="phase_a",
            status=CheckpointStatus.PENDING,
            requires_approval=True,
        ),
        Checkpoint(
            id="custom_checkpoint_2",
            name="Custom Checkpoint 2",
            description="Second custom checkpoint",
            phase_id="phase_b",
            status=CheckpointStatus.PENDING,
            requires_approval=False,
        ),
    ]


# =============================================================================
# Task 1: CheckpointService class initialization tests
# =============================================================================


class TestCheckpointServiceInit:
    """Tests for CheckpointService initialization."""

    def test_init_with_defaults(self, temp_spec_dir):
        """Test initialization with default checkpoints."""
        service = CheckpointService(
            task_id="task-1",
            spec_dir=temp_spec_dir,
        )

        assert service.task_id == "task-1"
        assert service.spec_dir == temp_spec_dir
        assert service.methodology == "native"
        assert service.checkpoints == FIXED_CHECKPOINTS
        assert len(service.checkpoints) == 3

    def test_init_with_custom_checkpoints(self, temp_spec_dir, custom_checkpoints):
        """Test initialization with custom checkpoints."""
        service = CheckpointService(
            task_id="task-2",
            spec_dir=temp_spec_dir,
            methodology="custom",
            checkpoints=custom_checkpoints,
        )

        assert service.checkpoints == custom_checkpoints
        assert len(service.checkpoints) == 2

    def test_init_creates_state_file_path(self, temp_spec_dir):
        """Test that state file path is correctly configured."""
        service = CheckpointService(
            task_id="task-3",
            spec_dir=temp_spec_dir,
        )

        expected_path = temp_spec_dir / "checkpoint_state.json"
        assert service._state_file == expected_path


# =============================================================================
# Task 2: Checkpoint detection tests
# =============================================================================


class TestCheckpointDetection:
    """Tests for checkpoint detection functionality."""

    def test_get_checkpoint_for_phase_exists(self, checkpoint_service):
        """Test finding checkpoint for a phase that has one."""
        checkpoint = checkpoint_service._get_checkpoint_for_phase("plan")

        assert checkpoint is not None
        assert checkpoint.id == "after_planning"
        assert checkpoint.phase_id == "plan"

    def test_get_checkpoint_for_phase_not_exists(self, checkpoint_service):
        """Test finding checkpoint for a phase that doesn't have one."""
        checkpoint = checkpoint_service._get_checkpoint_for_phase("nonexistent")

        assert checkpoint is None

    def test_get_checkpoint_by_id_exists(self, checkpoint_service):
        """Test finding checkpoint by ID when it exists."""
        checkpoint = checkpoint_service._get_checkpoint_by_id("after_coding")

        assert checkpoint is not None
        assert checkpoint.id == "after_coding"
        assert checkpoint.phase_id == "coding"

    def test_get_checkpoint_by_id_not_exists(self, checkpoint_service):
        """Test finding checkpoint by ID when it doesn't exist."""
        checkpoint = checkpoint_service._get_checkpoint_by_id("nonexistent")

        assert checkpoint is None

    def test_has_checkpoint_for_phase(self, checkpoint_service):
        """Test has_checkpoint_for_phase method."""
        assert checkpoint_service.has_checkpoint_for_phase("plan") is True
        assert checkpoint_service.has_checkpoint_for_phase("coding") is True
        assert checkpoint_service.has_checkpoint_for_phase("validate") is True
        assert checkpoint_service.has_checkpoint_for_phase("unknown") is False

    def test_fixed_checkpoints_content(self):
        """Test that FIXED_CHECKPOINTS has correct structure (FR27)."""
        assert len(FIXED_CHECKPOINTS) == 3

        # Verify after_planning
        planning = next(c for c in FIXED_CHECKPOINTS if c.id == "after_planning")
        assert planning.phase_id == "plan"
        assert planning.requires_approval is True

        # Verify after_coding
        coding = next(c for c in FIXED_CHECKPOINTS if c.id == "after_coding")
        assert coding.phase_id == "coding"
        assert coding.requires_approval is True

        # Verify after_validation
        validation = next(c for c in FIXED_CHECKPOINTS if c.id == "after_validation")
        assert validation.phase_id == "validate"
        assert validation.requires_approval is True


# =============================================================================
# Task 3: Pause mechanism tests
# =============================================================================


class TestPauseMechanism:
    """Tests for pause mechanism functionality."""

    def test_is_paused_initially_false(self, checkpoint_service):
        """Test that service is not paused initially."""
        assert checkpoint_service.is_paused() is False
        assert checkpoint_service.get_current_checkpoint() is None

    @pytest.mark.asyncio
    async def test_check_and_pause_no_checkpoint(self, checkpoint_service):
        """Test check_and_pause when no checkpoint exists for phase."""
        result = await checkpoint_service.check_and_pause("nonexistent_phase")

        assert result is None
        assert checkpoint_service.is_paused() is False

    @pytest.mark.asyncio
    async def test_check_and_pause_with_checkpoint(self, temp_spec_dir):
        """Test check_and_pause when checkpoint exists."""
        service = CheckpointService(
            task_id="test-task",
            spec_dir=temp_spec_dir,
        )

        # Start the check_and_pause in a task
        async def pause_and_resume():
            # Small delay to let the pause start
            await asyncio.sleep(0.1)
            # Resume from another "thread"
            service.resume("approve", "Looks good!")

        # Run both concurrently
        pause_task = asyncio.create_task(
            service.check_and_pause("plan", artifacts=["spec.md"])
        )
        resume_task = asyncio.create_task(pause_and_resume())

        result = await pause_task
        await resume_task

        assert result is not None
        assert result.checkpoint_id == "after_planning"
        assert result.decision == "approve"
        assert result.feedback == "Looks good!"
        assert result.resumed_at is not None

    def test_emit_checkpoint_reached_calls_callback(self, checkpoint_service):
        """Test that checkpoint event callback is called."""
        callback_called = []

        def mock_callback(event_data):
            callback_called.append(event_data)

        checkpoint_service._event_callback = mock_callback

        checkpoint = FIXED_CHECKPOINTS[0]
        state = CheckpointState(
            task_id="test-task-123",
            checkpoint_id=checkpoint.id,
            phase_id=checkpoint.phase_id,
            paused_at=datetime.now(),
        )

        checkpoint_service._emit_checkpoint_reached(checkpoint, state)

        assert len(callback_called) == 1
        event = callback_called[0]
        assert event["event"] == "checkpoint_reached"
        assert event["checkpoint_id"] == checkpoint.id
        assert event["task_id"] == "test-task-123"

    def test_emit_checkpoint_handles_callback_exception(self, checkpoint_service, caplog):
        """Test that callback exceptions are caught and logged."""
        def failing_callback(event_data):
            raise ValueError("Callback failed!")

        checkpoint_service._event_callback = failing_callback

        checkpoint = FIXED_CHECKPOINTS[0]
        state = CheckpointState(
            task_id="test-task-123",
            checkpoint_id=checkpoint.id,
            phase_id=checkpoint.phase_id,
            paused_at=datetime.now(),
        )

        # Should not raise, but should log error
        checkpoint_service._emit_checkpoint_reached(checkpoint, state)

        assert "Error in checkpoint event callback" in caplog.text
        assert "Callback failed!" in caplog.text


# =============================================================================
# Task 4: State persistence tests
# =============================================================================


class TestStatePersistence:
    """Tests for checkpoint state persistence."""

    def test_save_state_creates_file(self, checkpoint_service, temp_spec_dir):
        """Test that save_state creates the state file."""
        state = CheckpointState(
            task_id="test-task-123",
            checkpoint_id="after_planning",
            phase_id="plan",
            paused_at=datetime.now(),
            artifacts=["spec.md"],
            context={"key": "value"},
            is_paused=True,
        )

        checkpoint_service._save_state(state)

        state_file = temp_spec_dir / "checkpoint_state.json"
        assert state_file.exists()

        with open(state_file) as f:
            data = json.load(f)

        assert data["task_id"] == "test-task-123"
        assert data["checkpoint_id"] == "after_planning"
        assert data["phase_id"] == "plan"
        assert data["artifacts"] == ["spec.md"]
        assert data["context"] == {"key": "value"}
        assert data["is_paused"] is True

    def test_load_state_returns_state(self, checkpoint_service, temp_spec_dir):
        """Test that load_state correctly loads persisted state."""
        # First save state
        original_state = CheckpointState(
            task_id="test-task-123",
            checkpoint_id="after_coding",
            phase_id="coding",
            paused_at=datetime.now(),
            artifacts=["code.py", "test.py"],
            context={"progress": 50},
            is_paused=True,
        )
        checkpoint_service._save_state(original_state)

        # Then load it
        loaded_state = checkpoint_service.load_state()

        assert loaded_state is not None
        assert loaded_state.task_id == original_state.task_id
        assert loaded_state.checkpoint_id == original_state.checkpoint_id
        assert loaded_state.phase_id == original_state.phase_id
        assert loaded_state.artifacts == original_state.artifacts
        assert loaded_state.context == original_state.context
        assert loaded_state.is_paused is True

    def test_load_state_returns_none_when_no_file(self, checkpoint_service):
        """Test that load_state returns None when no file exists."""
        state = checkpoint_service.load_state()
        assert state is None

    def test_clear_state_removes_file(self, checkpoint_service, temp_spec_dir):
        """Test that clear_state removes the state file."""
        # First create a state file
        state = CheckpointState(
            task_id="test-task-123",
            checkpoint_id="after_planning",
            phase_id="plan",
            paused_at=datetime.now(),
        )
        checkpoint_service._save_state(state)

        state_file = temp_spec_dir / "checkpoint_state.json"
        assert state_file.exists()

        # Now clear it
        checkpoint_service.clear_state()

        assert not state_file.exists()

    def test_clear_state_no_error_when_no_file(self, checkpoint_service):
        """Test that clear_state doesn't error when no file exists."""
        # Should not raise
        checkpoint_service.clear_state()


class TestCheckpointState:
    """Tests for CheckpointState dataclass."""

    def test_to_dict(self):
        """Test CheckpointState serialization."""
        now = datetime.now()
        state = CheckpointState(
            task_id="task-1",
            checkpoint_id="cp-1",
            phase_id="phase-1",
            paused_at=now,
            artifacts=["file.md"],
            context={"foo": "bar"},
            is_paused=True,
        )

        data = state.to_dict()

        assert data["task_id"] == "task-1"
        assert data["checkpoint_id"] == "cp-1"
        assert data["phase_id"] == "phase-1"
        assert data["paused_at"] == now.isoformat()
        assert data["artifacts"] == ["file.md"]
        assert data["context"] == {"foo": "bar"}
        assert data["is_paused"] is True

    def test_from_dict(self):
        """Test CheckpointState deserialization."""
        now = datetime.now()
        data = {
            "task_id": "task-2",
            "checkpoint_id": "cp-2",
            "phase_id": "phase-2",
            "paused_at": now.isoformat(),
            "artifacts": ["a.md", "b.md"],
            "context": {"x": 1},
            "is_paused": False,
        }

        state = CheckpointState.from_dict(data)

        assert state.task_id == "task-2"
        assert state.checkpoint_id == "cp-2"
        assert state.phase_id == "phase-2"
        assert state.artifacts == ["a.md", "b.md"]
        assert state.context == {"x": 1}
        assert state.is_paused is False


# =============================================================================
# Task 5: Resume mechanism tests
# =============================================================================


class TestResumeMechanism:
    """Tests for resume mechanism functionality."""

    def test_resume_when_not_paused_logs_warning(self, checkpoint_service, caplog):
        """Test that resume logs warning when not paused."""
        checkpoint_service.resume("approve")

        # Should log warning but not crash
        assert "no checkpoint is active" in caplog.text.lower()

    @pytest.mark.asyncio
    async def test_resume_with_approve_decision(self, temp_spec_dir):
        """Test resume with approve decision."""
        service = CheckpointService(
            task_id="test-task",
            spec_dir=temp_spec_dir,
        )

        async def delayed_resume():
            await asyncio.sleep(0.1)
            service.resume("approve", "Approved!")

        pause_task = asyncio.create_task(service.check_and_pause("plan"))
        resume_task = asyncio.create_task(delayed_resume())

        result = await pause_task
        await resume_task

        assert result.decision == "approve"
        assert result.feedback == "Approved!"

    @pytest.mark.asyncio
    async def test_resume_with_reject_decision(self, temp_spec_dir):
        """Test resume with reject decision."""
        service = CheckpointService(
            task_id="test-task",
            spec_dir=temp_spec_dir,
        )

        async def delayed_resume():
            await asyncio.sleep(0.1)
            service.resume("reject", "Needs more work")

        pause_task = asyncio.create_task(service.check_and_pause("plan"))
        resume_task = asyncio.create_task(delayed_resume())

        result = await pause_task
        await resume_task

        assert result.decision == "reject"
        assert result.feedback == "Needs more work"

    @pytest.mark.asyncio
    async def test_resume_with_revise_decision(self, temp_spec_dir):
        """Test resume with revise decision."""
        service = CheckpointService(
            task_id="test-task",
            spec_dir=temp_spec_dir,
        )

        async def delayed_resume():
            await asyncio.sleep(0.1)
            service.resume("revise", "Please update the tests")

        pause_task = asyncio.create_task(service.check_and_pause("plan"))
        resume_task = asyncio.create_task(delayed_resume())

        result = await pause_task
        await resume_task

        assert result.decision == "revise"
        assert result.feedback == "Please update the tests"


# =============================================================================
# Protocol interface tests
# =============================================================================


class TestProtocolInterface:
    """Tests for CheckpointService Protocol compliance."""

    def test_create_checkpoint_method_exists(self, checkpoint_service):
        """Test that create_checkpoint method exists (Protocol requirement)."""
        assert hasattr(checkpoint_service, "create_checkpoint")
        assert callable(checkpoint_service.create_checkpoint)

    def test_create_checkpoint_saves_state(self, checkpoint_service, temp_spec_dir):
        """Test that create_checkpoint saves checkpoint state."""
        checkpoint_service.create_checkpoint(
            "after_planning",
            {"artifacts": ["plan.md"], "phase_id": "plan"},
        )

        state_file = temp_spec_dir / "checkpoint_state.json"
        assert state_file.exists()

        state = checkpoint_service.load_state()
        assert state is not None
        assert state.checkpoint_id == "after_planning"
        assert state.artifacts == ["plan.md"]


# =============================================================================
# Recovery tests
# =============================================================================


class TestRecovery:
    """Tests for checkpoint recovery functionality."""

    @pytest.mark.asyncio
    async def test_recover_from_state_no_state(self, checkpoint_service):
        """Test recovery when no state file exists."""
        result = await checkpoint_service.recover_from_state()
        assert result is None

    @pytest.mark.asyncio
    async def test_recover_from_state_not_paused(self, temp_spec_dir):
        """Test recovery when state exists but is not paused."""
        service = CheckpointService(
            task_id="test-task",
            spec_dir=temp_spec_dir,
        )

        # Create a non-paused state
        state = CheckpointState(
            task_id="test-task",
            checkpoint_id="after_planning",
            phase_id="plan",
            paused_at=datetime.now(),
            is_paused=False,  # Not paused
        )
        service._save_state(state)

        result = await service.recover_from_state()
        assert result is None

    @pytest.mark.asyncio
    async def test_recover_from_state_success(self, temp_spec_dir):
        """Test successful recovery from paused state."""
        service = CheckpointService(
            task_id="test-task",
            spec_dir=temp_spec_dir,
        )

        # Create a paused state
        state = CheckpointState(
            task_id="test-task",
            checkpoint_id="after_planning",
            phase_id="plan",
            paused_at=datetime.now(),
            artifacts=["spec.md"],
            is_paused=True,
        )
        service._save_state(state)

        async def delayed_resume():
            await asyncio.sleep(0.1)
            service.resume("approve", "Recovered and approved")

        recover_task = asyncio.create_task(service.recover_from_state())
        resume_task = asyncio.create_task(delayed_resume())

        result = await recover_task
        await resume_task

        assert result is not None
        assert result.checkpoint_id == "after_planning"
        assert result.decision == "approve"
        assert result.feedback == "Recovered and approved"
        assert result.metadata.get("recovered") is True


# =============================================================================
# CheckpointDecision enum tests
# =============================================================================


class TestCheckpointDecision:
    """Tests for CheckpointDecision enum."""

    def test_decision_values(self):
        """Test that enum has correct values."""
        assert CheckpointDecision.APPROVE.value == "approve"
        assert CheckpointDecision.REJECT.value == "reject"
        assert CheckpointDecision.REVISE.value == "revise"

    def test_is_valid_with_valid_values(self):
        """Test is_valid returns True for valid decision strings."""
        assert CheckpointDecision.is_valid("approve") is True
        assert CheckpointDecision.is_valid("reject") is True
        assert CheckpointDecision.is_valid("revise") is True

    def test_is_valid_with_invalid_values(self):
        """Test is_valid returns False for invalid decision strings."""
        assert CheckpointDecision.is_valid("invalid") is False
        assert CheckpointDecision.is_valid("APPROVE") is False  # Case sensitive
        assert CheckpointDecision.is_valid("") is False
        assert CheckpointDecision.is_valid("accept") is False


# =============================================================================
# Create checkpoint return value tests
# =============================================================================


class TestCreateCheckpointReturnValue:
    """Tests for create_checkpoint return value (L3 fix)."""

    def test_create_checkpoint_returns_state(self, checkpoint_service, temp_spec_dir):
        """Test that create_checkpoint returns CheckpointState."""
        result = checkpoint_service.create_checkpoint(
            "after_planning",
            {"artifacts": ["plan.md"], "phase_id": "plan"},
        )

        assert result is not None
        assert isinstance(result, CheckpointState)
        assert result.checkpoint_id == "after_planning"
        assert result.artifacts == ["plan.md"]
        assert result.is_paused is True
