"""Tests for lifecycle"""

from pathlib import Path

import pytest

from runners.github.lifecycle import (
    ConflictResult,
    ConflictType,
    IssueLifecycle,
    IssueLifecycleState,
    LifecycleManager,
    StateTransition,
)


@pytest.fixture
def temp_state_dir(tmp_path: Path) -> Path:
    """Create a temporary state directory."""
    return tmp_path / "state"


@pytest.fixture
def lifecycle_manager(temp_state_dir: Path) -> LifecycleManager:
    """Create a LifecycleManager instance for testing."""
    return LifecycleManager(state_dir=temp_state_dir)


def test_IssueLifecycleState_terminal_states():
    """Test IssueLifecycleState.terminal_states"""
    result = IssueLifecycleState.terminal_states()
    assert result is not None
    assert IssueLifecycleState.MERGED in result
    assert IssueLifecycleState.CLOSED in result
    assert IssueLifecycleState.WONT_FIX in result
    assert IssueLifecycleState.SPAM in result
    assert IssueLifecycleState.DUPLICATE in result


def test_IssueLifecycleState_blocks_auto_fix():
    """Test IssueLifecycleState.blocks_auto_fix"""
    result = IssueLifecycleState.blocks_auto_fix()
    assert result is not None
    assert IssueLifecycleState.SPAM in result
    assert IssueLifecycleState.DUPLICATE in result
    assert IssueLifecycleState.REJECTED in result
    assert IssueLifecycleState.WONT_FIX in result


def test_IssueLifecycleState_requires_triage_first():
    """Test IssueLifecycleState.requires_triage_first"""
    result = IssueLifecycleState.requires_triage_first()
    assert result is not None
    assert IssueLifecycleState.NEW in result
    assert IssueLifecycleState.TRIAGING in result


def test_ConflictResult_to_dict():
    """Test ConflictResult.to_dict"""
    instance = ConflictResult(
        has_conflict=True,
        conflict_type=ConflictType.TRIAGE_REQUIRED,
        message="Triage required",
        blocking_state=IssueLifecycleState.NEW,
        resolution_hint="Run triage first",
    )
    result = instance.to_dict()
    assert result is not None
    assert result["has_conflict"] is True
    assert result["conflict_type"] == "triage_required"
    assert result["message"] == "Triage required"
    assert result["blocking_state"] == "new"
    assert result["resolution_hint"] == "Run triage first"


def test_StateTransition_to_dict():
    """Test StateTransition.to_dict"""
    instance = StateTransition(
        from_state=IssueLifecycleState.NEW,
        to_state=IssueLifecycleState.TRIAGED,
        timestamp="2025-01-01T00:00:00Z",
        actor="test_user",
        reason="Test transition",
        metadata={"key": "value"},
    )
    result = instance.to_dict()
    assert result is not None
    assert result["from_state"] == "new"
    assert result["to_state"] == "triaged"
    assert result["timestamp"] == "2025-01-01T00:00:00Z"
    assert result["actor"] == "test_user"
    assert result["reason"] == "Test transition"
    assert result["metadata"] == {"key": "value"}


def test_StateTransition_from_dict():
    """Test StateTransition.from_dict"""
    data = {
        "from_state": "new",
        "to_state": "triaged",
        "timestamp": "2025-01-01T00:00:00Z",
        "actor": "test_user",
        "reason": "Test transition",
        "metadata": {"key": "value"},
    }
    result = StateTransition.from_dict(data)
    assert result is not None
    assert result.from_state == IssueLifecycleState.NEW
    assert result.to_state == IssueLifecycleState.TRIAGED
    assert result.timestamp == "2025-01-01T00:00:00Z"
    assert result.actor == "test_user"
    assert result.reason == "Test transition"
    assert result.metadata == {"key": "value"}


def test_IssueLifecycle_can_transition_to():
    """Test IssueLifecycle.can_transition_to"""
    instance = IssueLifecycle(issue_number=123, repo="owner/repo")
    # Can transition from NEW to TRIAGING
    result = instance.can_transition_to(IssueLifecycleState.TRIAGING)
    assert result is True
    # Cannot transition from NEW to MERGED directly
    result = instance.can_transition_to(IssueLifecycleState.MERGED)
    assert result is False


def test_IssueLifecycle_transition():
    """Test IssueLifecycle.transition"""
    instance = IssueLifecycle(issue_number=123, repo="owner/repo")
    result = instance.transition(
        new_state=IssueLifecycleState.TRIAGING,
        actor="test_user",
        reason="Starting triage",
    )
    assert result is not None
    assert result.has_conflict is False
    assert instance.current_state == IssueLifecycleState.TRIAGING
    assert len(instance.transitions) == 1


def test_IssueLifecycle_transition_invalid():
    """Test IssueLifecycle.transition with invalid transition"""
    instance = IssueLifecycle(issue_number=123, repo="owner/repo")
    result = instance.transition(
        new_state=IssueLifecycleState.MERGED,
        actor="test_user",
    )
    assert result is not None
    assert result.has_conflict is True
    assert result.conflict_type == ConflictType.INVALID_TRANSITION


def test_IssueLifecycle_check_auto_fix_allowed():
    """Test IssueLifecycle.check_auto_fix_allowed"""
    # NEW state requires triage
    instance = IssueLifecycle(issue_number=123, repo="owner/repo")
    result = instance.check_auto_fix_allowed()
    assert result is not None
    assert result.has_conflict is True
    assert result.conflict_type == ConflictType.TRIAGE_REQUIRED

    # SPAM state blocks auto-fix
    instance.current_state = IssueLifecycleState.SPAM
    result = instance.check_auto_fix_allowed()
    assert result is not None
    assert result.has_conflict is True
    assert result.conflict_type == ConflictType.BLOCKED_BY_CLASSIFICATION

    # APPROVED_FOR_FIX allows auto-fix
    instance.current_state = IssueLifecycleState.APPROVED_FOR_FIX
    result = instance.check_auto_fix_allowed()
    assert result is not None
    assert result.has_conflict is False


def test_IssueLifecycle_check_pr_review_required():
    """Test IssueLifecycle.check_pr_review_required"""
    # PR_CREATED state requires review
    instance = IssueLifecycle(
        issue_number=123, repo="owner/repo", current_state=IssueLifecycleState.PR_CREATED
    )
    result = instance.check_pr_review_required()
    assert result is not None
    assert result.has_conflict is True
    assert result.conflict_type == ConflictType.REVIEW_REQUIRED

    # PR_APPROVED does not require review
    instance.current_state = IssueLifecycleState.PR_APPROVED
    result = instance.check_pr_review_required()
    assert result is not None
    assert result.has_conflict is False


def test_IssueLifecycle_acquire_lock():
    """Test IssueLifecycle.acquire_lock"""
    instance = IssueLifecycle(issue_number=123, repo="owner/repo")
    result = instance.acquire_lock("test_component")
    assert result is True
    assert instance.locked_by == "test_component"
    assert instance.locked_at is not None

    # Cannot acquire again
    result = instance.acquire_lock("another_component")
    assert result is False


def test_IssueLifecycle_release_lock():
    """Test IssueLifecycle.release_lock"""
    instance = IssueLifecycle(issue_number=123, repo="owner/repo")
    instance.acquire_lock("test_component")
    result = instance.release_lock("test_component")
    assert result is True
    assert instance.locked_by is None

    # Cannot release again
    result = instance.release_lock("test_component")
    assert result is False


def test_IssueLifecycle_release_lock_wrong_component():
    """Test IssueLifecycle.release_lock with wrong component"""
    instance = IssueLifecycle(issue_number=123, repo="owner/repo")
    instance.acquire_lock("test_component")
    result = instance.release_lock("wrong_component")
    assert result is False


def test_IssueLifecycle_is_locked():
    """Test IssueLifecycle.is_locked"""
    instance = IssueLifecycle(issue_number=123, repo="owner/repo")
    assert instance.is_locked() is False

    instance.acquire_lock("test_component")
    assert instance.is_locked() is True


def test_IssueLifecycle_to_dict():
    """Test IssueLifecycle.to_dict"""
    instance = IssueLifecycle(
        issue_number=123,
        repo="owner/repo",
        current_state=IssueLifecycleState.NEW,
        spec_id="spec-001",
        pr_number=456,
    )
    result = instance.to_dict()
    assert result is not None
    assert result["issue_number"] == 123
    assert result["repo"] == "owner/repo"
    assert result["current_state"] == "new"
    assert result["spec_id"] == "spec-001"
    assert result["pr_number"] == 456


def test_IssueLifecycle_from_dict():
    """Test IssueLifecycle.from_dict"""
    data = {
        "issue_number": 123,
        "repo": "owner/repo",
        "current_state": "new",
        "spec_id": "spec-001",
        "pr_number": 456,
        "transitions": [],
        "locked_by": None,
        "locked_at": None,
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
    }
    result = IssueLifecycle.from_dict(data)
    assert result is not None
    assert result.issue_number == 123
    assert result.repo == "owner/repo"
    assert result.current_state == IssueLifecycleState.NEW
    assert result.spec_id == "spec-001"
    assert result.pr_number == 456


def test_LifecycleManager___init__(temp_state_dir: Path):
    """Test LifecycleManager.__init__"""
    instance = LifecycleManager(state_dir=temp_state_dir)
    assert instance.state_dir == temp_state_dir
    assert instance.lifecycle_dir == temp_state_dir / "lifecycle"
    assert instance.lifecycle_dir.exists()


def test_LifecycleManager_get(lifecycle_manager: LifecycleManager):
    """Test LifecycleManager.get"""
    # Get non-existent lifecycle
    result = lifecycle_manager.get("owner/repo", 123)
    assert result is None


def test_LifecycleManager_get_or_create(lifecycle_manager: LifecycleManager):
    """Test LifecycleManager.get_or_create"""
    # Create new lifecycle
    result = lifecycle_manager.get_or_create("owner/repo", 123)
    assert result is not None
    assert result.issue_number == 123
    assert result.repo == "owner/repo"

    # Get existing lifecycle
    result2 = lifecycle_manager.get_or_create("owner/repo", 123)
    assert result2.issue_number == 123
    assert result2.repo == "owner/repo"


def test_LifecycleManager_save(lifecycle_manager: LifecycleManager):
    """Test LifecycleManager.save"""
    lifecycle = IssueLifecycle(issue_number=123, repo="owner/repo")
    lifecycle_manager.save(lifecycle)
    # Should not raise

    # Verify it was saved
    result = lifecycle_manager.get("owner/repo", 123)
    assert result is not None
    assert result.issue_number == 123


def test_LifecycleManager_transition(lifecycle_manager: LifecycleManager):
    """Test LifecycleManager.transition"""
    result = lifecycle_manager.transition(
        repo="owner/repo",
        issue_number=123,
        new_state=IssueLifecycleState.TRIAGING,
        actor="test_user",
    )
    assert result is not None
    assert result.has_conflict is False


def test_LifecycleManager_check_conflict(lifecycle_manager: LifecycleManager):
    """Test LifecycleManager.check_conflict"""
    # Check for new issue (requires triage)
    result = lifecycle_manager.check_conflict("owner/repo", 123, "auto_fix")
    assert result is not None
    assert result.has_conflict is True
    assert result.conflict_type == ConflictType.TRIAGE_REQUIRED


def test_LifecycleManager_acquire_lock(lifecycle_manager: LifecycleManager):
    """Test LifecycleManager.acquire_lock"""
    result = lifecycle_manager.acquire_lock("owner/repo", 123, "test_component")
    assert result is True

    # Verify lock was acquired
    lifecycle = lifecycle_manager.get("owner/repo", 123)
    assert lifecycle is not None
    assert lifecycle.locked_by == "test_component"


def test_LifecycleManager_release_lock(lifecycle_manager: LifecycleManager):
    """Test LifecycleManager.release_lock"""
    lifecycle_manager.acquire_lock("owner/repo", 123, "test_component")
    result = lifecycle_manager.release_lock("owner/repo", 123, "test_component")
    assert result is True

    # Verify lock was released
    lifecycle = lifecycle_manager.get("owner/repo", 123)
    assert lifecycle is not None
    assert lifecycle.locked_by is None


def test_LifecycleManager_get_all_in_state(lifecycle_manager: LifecycleManager):
    """Test LifecycleManager.get_all_in_state"""
    # Create multiple lifecycles
    lifecycle1 = lifecycle_manager.get_or_create("owner/repo", 123)
    lifecycle1.current_state = IssueLifecycleState.NEW
    lifecycle_manager.save(lifecycle1)

    lifecycle2 = lifecycle_manager.get_or_create("owner/repo", 124)
    lifecycle2.current_state = IssueLifecycleState.NEW
    lifecycle_manager.save(lifecycle2)

    lifecycle3 = lifecycle_manager.get_or_create("owner/repo", 125)
    lifecycle3.current_state = IssueLifecycleState.TRIAGED
    lifecycle_manager.save(lifecycle3)

    # Get all in NEW state
    result = lifecycle_manager.get_all_in_state("owner/repo", IssueLifecycleState.NEW)
    assert len(result) == 2
    assert all(l.current_state == IssueLifecycleState.NEW for l in result)


def test_LifecycleManager_get_summary(lifecycle_manager: LifecycleManager):
    """Test LifecycleManager.get_summary"""
    # Create multiple lifecycles
    lifecycle1 = lifecycle_manager.get_or_create("owner/repo", 123)
    lifecycle1.current_state = IssueLifecycleState.NEW
    lifecycle_manager.save(lifecycle1)

    lifecycle2 = lifecycle_manager.get_or_create("owner/repo", 124)
    lifecycle2.current_state = IssueLifecycleState.NEW
    lifecycle_manager.save(lifecycle2)

    lifecycle3 = lifecycle_manager.get_or_create("owner/repo", 125)
    lifecycle3.current_state = IssueLifecycleState.TRIAGED
    lifecycle_manager.save(lifecycle3)

    # Get summary
    result = lifecycle_manager.get_summary("owner/repo")
    assert result is not None
    assert result.get("new") == 2
    assert result.get("triaged") == 1


def test_LifecycleManager_check_conflict_locked(lifecycle_manager: LifecycleManager):
    """Test LifecycleManager.check_conflict with locked issue"""
    # Lock the issue
    lifecycle_manager.acquire_lock("owner/repo", 123, "test_component")

    # Check for conflict
    result = lifecycle_manager.check_conflict("owner/repo", 123, "auto_fix")
    assert result is not None
    assert result.has_conflict is True
    assert result.conflict_type == ConflictType.CONCURRENT_OPERATION
