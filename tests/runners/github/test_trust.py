"""Tests for trust"""

from runners.github.trust import AccuracyMetrics, TrustLevel, TrustManager, TrustState
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
import tempfile
import json


def test_TrustLevel_can_perform():
    """Test TrustLevel.can_perform"""
    # Arrange & Act & Assert
    assert TrustLevel.L0_REVIEW_ONLY.can_perform("comment") is True
    assert TrustLevel.L0_REVIEW_ONLY.can_perform("label") is False
    assert TrustLevel.L1_LABEL.can_perform("label") is True
    assert TrustLevel.L1_LABEL.can_perform("close_duplicate") is False
    assert TrustLevel.L2_CLOSE.can_perform("close_duplicate") is True
    assert TrustLevel.L2_CLOSE.can_perform("merge_trivial") is False
    assert TrustLevel.L3_MERGE_TRIVIAL.can_perform("merge_trivial") is True
    assert TrustLevel.L3_MERGE_TRIVIAL.can_perform("auto_fix") is False
    assert TrustLevel.L4_FULL_AUTO.can_perform("auto_fix") is True
    assert TrustLevel.L4_FULL_AUTO.can_perform("merge") is True


def test_AccuracyMetrics_record_action():
    """Test AccuracyMetrics.record_action"""
    # Arrange
    instance = AccuracyMetrics()

    # Act
    instance.record_action("review", correct=True, overridden=False)
    instance.record_action("label", correct=True, overridden=False)
    instance.record_action("label", correct=False, overridden=True)

    # Assert
    assert instance.total_actions == 3
    assert instance.correct_actions == 2
    assert instance.overridden_actions == 1
    assert instance.review_total == 1
    assert instance.review_correct == 1
    assert instance.label_total == 2
    assert instance.label_correct == 1


def test_AccuracyMetrics_to_dict():
    """Test AccuracyMetrics.to_dict"""
    # Arrange
    instance = AccuracyMetrics()
    instance.record_action("review", correct=True, overridden=False)

    # Act
    result = instance.to_dict()

    # Assert
    assert result["total_actions"] == 1
    assert result["correct_actions"] == 1
    assert result["review_total"] == 1
    assert result["review_correct"] == 1


def test_AccuracyMetrics_from_dict():
    """Test AccuracyMetrics.from_dict"""
    # Arrange
    data = {
        "total_actions": 10,
        "correct_actions": 9,
        "overridden_actions": 1,
        "review_total": 5,
        "review_correct": 4,
    }

    # Act
    result = AccuracyMetrics.from_dict(data)

    # Assert
    assert result.total_actions == 10
    assert result.correct_actions == 9
    assert result.review_total == 5
    assert result.review_correct == 4


def test_TrustState_can_perform():
    """Test TrustState.can_perform"""
    # Arrange
    instance = TrustState(repo="owner/repo")

    # Act & Assert
    assert instance.can_perform("comment") is True
    assert instance.can_perform("label") is False

    # Upgrade to L1
    instance.upgrade_level(TrustLevel.L1_LABEL)
    assert instance.can_perform("label") is True
    assert instance.can_perform("close_duplicate") is False


def test_TrustState_get_progress_to_next_level():
    """Test TrustState.get_progress_to_next_level"""
    # Arrange
    instance = TrustState(repo="owner/repo")

    # Act
    result = instance.get_progress_to_next_level()

    # Assert
    assert result["next_level"] == TrustLevel.L1_LABEL.value
    assert result["at_max"] is False
    assert "actions" in result
    assert "accuracy" in result
    assert "days" in result

    # Test max level
    instance.upgrade_level(TrustLevel.L4_FULL_AUTO)
    result = instance.get_progress_to_next_level()
    assert result["at_max"] is True
    assert result["next_level"] is None


def test_TrustState_check_upgrade():
    """Test TrustState.check_upgrade"""
    # Arrange
    instance = TrustState(repo="owner/repo")

    # Act - no actions yet
    result = instance.check_upgrade()
    assert result is None

    # Add enough actions and accuracy to qualify for L1
    for _ in range(20):
        instance.metrics.record_action("review", correct=True, overridden=False)

    # Act - still not enough days
    result = instance.check_upgrade()
    assert result is None

    # Manually set first action to be old enough
    from datetime import datetime, timezone, timedelta
    old_time = (datetime.now(timezone.utc) - timedelta(days=4)).isoformat()
    instance.metrics.first_action_at = old_time

    # Act - should qualify now
    result = instance.check_upgrade()
    assert result == TrustLevel.L1_LABEL


def test_TrustState_upgrade_level():
    """Test TrustState.upgrade_level"""
    # Arrange
    instance = TrustState(repo="owner/repo")

    # Act
    instance.upgrade_level(TrustLevel.L1_LABEL, reason="test")

    # Assert
    assert instance.current_level == TrustLevel.L1_LABEL
    assert instance.last_level_change is not None
    assert len(instance.level_history) == 1
    assert instance.level_history[0]["to_level"] == TrustLevel.L1_LABEL.value
    assert instance.level_history[0]["reason"] == "test"


def test_TrustState_downgrade_level():
    """Test TrustState.downgrade_level"""
    # Arrange
    instance = TrustState(repo="owner/repo", current_level=TrustLevel.L2_CLOSE)

    # Act
    instance.downgrade_level(reason="test")

    # Assert
    assert instance.current_level == TrustLevel.L1_LABEL
    assert len(instance.level_history) == 1
    assert instance.level_history[0]["to_level"] == TrustLevel.L1_LABEL.value


def test_TrustState_set_manual_override():
    """Test TrustState.set_manual_override"""
    # Arrange
    instance = TrustState(repo="owner/repo")

    # Act
    instance.set_manual_override(TrustLevel.L3_MERGE_TRIVIAL)

    # Assert
    assert instance.manual_override == TrustLevel.L3_MERGE_TRIVIAL
    assert instance.effective_level == TrustLevel.L3_MERGE_TRIVIAL
    assert len(instance.level_history) == 1


def test_TrustState_to_dict():
    """Test TrustState.to_dict"""
    # Arrange
    instance = TrustState(repo="owner/repo", current_level=TrustLevel.L2_CLOSE)

    # Act
    result = instance.to_dict()

    # Assert
    assert result["repo"] == "owner/repo"
    assert result["current_level"] == TrustLevel.L2_CLOSE.value
    assert "metrics" in result
    assert result["manual_override"] is None


def test_TrustState_from_dict():
    """Test TrustState.from_dict"""
    # Arrange
    data = {
        "repo": "owner/repo",
        "current_level": TrustLevel.L2_CLOSE.value,
        "metrics": {"total_actions": 10, "correct_actions": 9},
        "manual_override": None,
        "last_level_change": None,
        "level_history": [],
    }

    # Act
    result = TrustState.from_dict(data)

    # Assert
    assert result.repo == "owner/repo"
    assert result.current_level == TrustLevel.L2_CLOSE
    assert result.metrics.total_actions == 10


def test_TrustManager___init__():
    """Test TrustManager.__init__"""
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = Path(tmpdir)

        # Act
        instance = TrustManager(state_dir)

        # Assert
        assert instance.state_dir == state_dir
        assert instance.trust_dir == state_dir / "trust"
        assert instance.trust_dir.exists()


def test_TrustManager_get_state():
    """Test TrustManager.get_state"""
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = Path(tmpdir)
        instance = TrustManager(state_dir)

        # Act
        result = instance.get_state("owner/repo")

        # Assert
        assert result.repo == "owner/repo"
        assert result.current_level == TrustLevel.L0_REVIEW_ONLY

        # Should be cached
        assert "owner/repo" in instance._states


def test_TrustManager_save_state():
    """Test TrustManager.save_state"""
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = Path(tmpdir)
        instance = TrustManager(state_dir)
        state = instance.get_state("owner/repo")
        state.upgrade_level(TrustLevel.L1_LABEL)

        # Act
        instance.save_state("owner/repo")

        # Assert
        state_file = instance._get_state_file("owner/repo")
        assert state_file.exists()

        with open(state_file) as f:
            data = json.load(f)
        assert data["current_level"] == TrustLevel.L1_LABEL.value


def test_TrustManager_get_trust_level():
    """Test TrustManager.get_trust_level"""
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = Path(tmpdir)
        instance = TrustManager(state_dir)

        # Act
        result = instance.get_trust_level("owner/repo")

        # Assert
        assert result == TrustLevel.L0_REVIEW_ONLY


def test_TrustManager_can_perform():
    """Test TrustManager.can_perform"""
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = Path(tmpdir)
        instance = TrustManager(state_dir)

        # Act & Assert
        assert instance.can_perform("owner/repo", "comment") is True
        assert instance.can_perform("owner/repo", "label") is False


def test_TrustManager_record_action():
    """Test TrustManager.record_action"""
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = Path(tmpdir)
        instance = TrustManager(state_dir)

        # Act
        instance.record_action("owner/repo", "review", correct=True, overridden=False)

        # Assert
        state = instance.get_state("owner/repo")
        assert state.metrics.total_actions == 1
        assert state.metrics.correct_actions == 1
        assert instance._get_state_file("owner/repo").exists()


def test_TrustManager_check_and_upgrade():
    """Test TrustManager.check_and_upgrade"""
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = Path(tmpdir)
        instance = TrustManager(state_dir)
        state = instance.get_state("owner/repo")

        # Add enough metrics for upgrade
        for _ in range(20):
            state.metrics.record_action("review", correct=True, overridden=False)

        from datetime import datetime, timezone, timedelta
        old_time = (datetime.now(timezone.utc) - timedelta(days=4)).isoformat()
        state.metrics.first_action_at = old_time

        # Act
        result = instance.check_and_upgrade("owner/repo")

        # Assert
        assert result is True
        assert instance.get_trust_level("owner/repo") == TrustLevel.L1_LABEL


def test_TrustManager_set_manual_level():
    """Test TrustManager.set_manual_level"""
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = Path(tmpdir)
        instance = TrustManager(state_dir)

        # Act
        instance.set_manual_level("owner/repo", TrustLevel.L3_MERGE_TRIVIAL)

        # Assert
        state = instance.get_state("owner/repo")
        assert state.manual_override == TrustLevel.L3_MERGE_TRIVIAL
        assert instance.get_trust_level("owner/repo") == TrustLevel.L3_MERGE_TRIVIAL


def test_TrustManager_clear_manual_override():
    """Test TrustManager.clear_manual_override"""
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = Path(tmpdir)
        instance = TrustManager(state_dir)
        instance.set_manual_level("owner/repo", TrustLevel.L3_MERGE_TRIVIAL)

        # Act
        instance.clear_manual_override("owner/repo")

        # Assert
        state = instance.get_state("owner/repo")
        assert state.manual_override is None


def test_TrustManager_get_progress():
    """Test TrustManager.get_progress"""
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = Path(tmpdir)
        instance = TrustManager(state_dir)

        # Act
        result = instance.get_progress("owner/repo")

        # Assert
        assert result["current_level"] == TrustLevel.L0_REVIEW_ONLY.value
        assert "progress_to_next" in result
        assert result["is_manual_override"] is False


def test_TrustManager_get_all_states():
    """Test TrustManager.get_all_states"""
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = Path(tmpdir)
        instance = TrustManager(state_dir)
        instance.save_state("owner/repo1")
        instance.save_state("owner/repo2")

        # Act
        result = instance.get_all_states()

        # Assert
        assert len(result) == 2
        repos = {s.repo for s in result}
        assert repos == {"owner/repo1", "owner/repo2"}


def test_TrustManager_get_summary():
    """Test TrustManager.get_summary"""
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = Path(tmpdir)
        instance = TrustManager(state_dir)
        instance.save_state("owner/repo1")
        instance.save_state("owner/repo2")

        # Act
        result = instance.get_summary()

        # Assert
        assert result["total_repos"] == 2
        assert "by_level" in result
        assert "total_actions" in result
