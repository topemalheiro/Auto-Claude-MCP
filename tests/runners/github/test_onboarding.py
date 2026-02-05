"""Tests for onboarding"""

from datetime import datetime, timedelta, timezone

import pytest

from runners.github.onboarding import (
    ChecklistItem,
    EnablementLevel,
    OnboardingManager,
    OnboardingPhase,
    OnboardingState,
    SetupResult,
)


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary state directory."""
    return tmp_path / "state"


@pytest.fixture
def mock_gh_provider():
    """Create a mock GitHub provider."""
    from unittest.mock import MagicMock

    provider = MagicMock()
    provider.repo_exists.return_value = True
    provider.has_label.return_value = True
    provider.create_label.return_value = True
    return provider


@pytest.fixture
def onboarding_manager(temp_state_dir, mock_gh_provider):
    """Create an OnboardingManager instance for testing."""
    return OnboardingManager(
        repo="owner/repo",
        state_dir=temp_state_dir,
        gh_provider=mock_gh_provider,
    )


def test_ChecklistItem_to_dict():
    """Test ChecklistItem.to_dict"""
    instance = ChecklistItem(
        id="item-001",
        title="Test Item",
        description="Test description",
        completed=True,
        required=True,
        completed_at=datetime.now(timezone.utc),
        error=None,
    )
    result = instance.to_dict()
    assert result is not None
    assert result["id"] == "item-001"
    assert result["title"] == "Test Item"
    assert result["description"] == "Test description"
    assert result["completed"] is True
    assert result["required"] is True


def test_SetupResult_to_dict():
    """Test SetupResult.to_dict"""
    item1 = ChecklistItem(
        id="item-001",
        title="Test Item 1",
        description="Test description 1",
        completed=True,
        required=True,
    )
    item2 = ChecklistItem(
        id="item-002",
        title="Test Item 2",
        description="Test description 2",
        completed=False,
        required=False,
    )
    instance = SetupResult(
        success=True,
        phase=OnboardingPhase.TEST_MODE,
        checklist=[item1, item2],
        errors=[],
        warnings=["Test warning"],
        dry_run=False,
    )
    result = instance.to_dict()
    assert result is not None
    assert result["success"] is True
    assert result["phase"] == "test_mode"
    assert result["completion_rate"] == 0.5
    assert result["required_complete"] is True
    assert result["dry_run"] is False
    assert len(result["checklist"]) == 2


def test_OnboardingState_to_dict():
    """Test OnboardingState.to_dict"""
    instance = OnboardingState(
        repo="owner/repo",
        phase=OnboardingPhase.TEST_MODE,
        started_at=datetime.now(timezone.utc),
        completed_items=["item-001"],
        enablement_level=EnablementLevel.COMMENT_ONLY,
        test_mode_ends_at=datetime.now(timezone.utc) + timedelta(days=7),
        auto_upgrade_enabled=True,
        triage_accuracy=0.95,
        triage_actions=100,
    )
    result = instance.to_dict()
    assert result is not None
    assert result["repo"] == "owner/repo"
    assert result["phase"] == "test_mode"
    assert result["enablement_level"] == "comment_only"
    assert result["triage_accuracy"] == 0.95
    assert result["triage_actions"] == 100


def test_OnboardingState_from_dict():
    """Test OnboardingState.from_dict"""
    now = datetime.now(timezone.utc)
    data = {
        "repo": "owner/repo",
        "phase": "test_mode",
        "started_at": now.isoformat(),
        "completed_items": ["item-001"],
        "enablement_level": "comment_only",
        "test_mode_ends_at": (now + timedelta(days=7)).isoformat(),
        "auto_upgrade_enabled": True,
        "triage_accuracy": 0.95,
        "triage_actions": 100,
        "review_accuracy": 0.0,
        "review_actions": 0,
    }
    result = OnboardingState.from_dict(data)
    assert result is not None
    assert result.repo == "owner/repo"
    assert result.phase == OnboardingPhase.TEST_MODE
    assert result.enablement_level == EnablementLevel.COMMENT_ONLY


def test_OnboardingManager___init__(temp_state_dir, mock_gh_provider):
    """Test OnboardingManager.__init__"""
    instance = OnboardingManager(
        repo="owner/repo",
        state_dir=temp_state_dir,
        gh_provider=mock_gh_provider,
    )
    assert instance.repo == "owner/repo"
    assert instance.state_dir == temp_state_dir
    assert instance.gh_provider == mock_gh_provider


def test_OnboardingManager_get_state(onboarding_manager):
    """Test OnboardingManager.get_state"""
    result = onboarding_manager.get_state()
    assert result is not None
    assert result.repo == "owner/repo"
    assert result.phase == OnboardingPhase.NOT_STARTED


def test_OnboardingManager_save_state(onboarding_manager):
    """Test OnboardingManager.save_state"""
    # Update state through the manager
    state = onboarding_manager.get_state()
    state.phase = OnboardingPhase.TEST_MODE
    state.started_at = datetime.now(timezone.utc)
    state.enablement_level = EnablementLevel.COMMENT_ONLY
    onboarding_manager.save_state()
    # Should not raise

    # Verify state was saved
    new_state = onboarding_manager.get_state()
    assert new_state.phase == OnboardingPhase.TEST_MODE


@pytest.mark.asyncio
async def test_OnboardingManager_run_setup(onboarding_manager):
    """Test OnboardingManager.run_setup"""
    result = await onboarding_manager.run_setup(dry_run=True, skip_labels=True)
    assert result is not None
    assert isinstance(result, SetupResult)
    assert result.dry_run is True


def test_OnboardingManager_is_test_mode(onboarding_manager):
    """Test OnboardingManager.is_test_mode"""
    # Initially not in test mode
    assert onboarding_manager.is_test_mode() is False

    # Set to test mode
    state = onboarding_manager.get_state()
    state.phase = OnboardingPhase.TEST_MODE
    state.test_mode_ends_at = datetime.now(timezone.utc) + timedelta(days=1)
    onboarding_manager.save_state()

    assert onboarding_manager.is_test_mode() is True


def test_OnboardingManager_get_enablement_level(onboarding_manager):
    """Test OnboardingManager.get_enablement_level"""
    result = onboarding_manager.get_enablement_level()
    assert result is not None
    assert result == EnablementLevel.OFF


def test_OnboardingManager_can_perform_action(onboarding_manager):
    """Test OnboardingManager.can_perform_action"""
    # Initially OFF, can't perform actions
    allowed, reason = onboarding_manager.can_perform_action("triage")
    assert allowed is False
    assert reason == "Automation is disabled"

    # Set to COMMENT_ONLY
    state = onboarding_manager.get_state()
    state.enablement_level = EnablementLevel.COMMENT_ONLY
    onboarding_manager.save_state()

    # COMMENT_ONLY allows comments but not actions
    allowed, reason = onboarding_manager.can_perform_action("comment")
    assert allowed is True
    assert reason == "Comment-only mode"

    allowed, reason = onboarding_manager.can_perform_action("triage")
    assert allowed is False


def test_OnboardingManager_record_action(onboarding_manager):
    """Test OnboardingManager.record_action"""
    onboarding_manager.record_action("triage", was_correct=True)

    state = onboarding_manager.get_state()
    assert state.triage_actions == 1


def test_OnboardingManager_check_progression(onboarding_manager):
    """Test OnboardingManager.check_progression"""
    # Initially in NOT_STARTED phase
    should_upgrade, message = onboarding_manager.check_progression()
    assert isinstance(should_upgrade, bool)
    assert isinstance(message, (str, type(None)))

    # Set to test mode with past end date
    state = onboarding_manager.get_state()
    state.phase = OnboardingPhase.TEST_MODE
    state.test_mode_ends_at = datetime.now(timezone.utc) - timedelta(days=1)
    onboarding_manager.save_state()

    should_upgrade, message = onboarding_manager.check_progression()
    assert should_upgrade is True


def test_OnboardingManager_upgrade_level(onboarding_manager):
    """Test OnboardingManager.upgrade_level"""
    # Set to test mode with past end date to enable upgrade
    state = onboarding_manager.get_state()
    state.phase = OnboardingPhase.TEST_MODE
    state.test_mode_ends_at = datetime.now(timezone.utc) - timedelta(days=1)
    onboarding_manager.save_state()

    # Now upgrade should move to TRIAGE_ENABLED
    result = onboarding_manager.upgrade_level()
    assert result is True

    state = onboarding_manager.get_state()
    assert state.phase == OnboardingPhase.TRIAGE_ENABLED
    assert state.enablement_level == EnablementLevel.TRIAGE_ONLY

    # Test that upgrade returns False when no progression available
    result2 = onboarding_manager.upgrade_level()
    assert result2 is False


def test_OnboardingManager_set_enablement_level(onboarding_manager):
    """Test OnboardingManager.set_enablement_level"""
    onboarding_manager.set_enablement_level(EnablementLevel.TRIAGE_ONLY)
    state = onboarding_manager.get_state()
    assert state.enablement_level == EnablementLevel.TRIAGE_ONLY


def test_OnboardingManager_get_checklist(onboarding_manager):
    """Test OnboardingManager.get_checklist"""
    result = onboarding_manager.get_checklist()
    assert result is not None
    assert isinstance(result, list)


def test_OnboardingManager_get_status_summary(onboarding_manager):
    """Test OnboardingManager.get_status_summary"""
    result = onboarding_manager.get_status_summary()
    assert result is not None
    assert isinstance(result, dict)
    assert "phase" in result
    assert "enablement_level" in result
