"""Tests for bot_detection"""

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from runners.github.bot_detection import (
    BotDetectionState,
    BotDetector,
)


def test_BotDetectionState_to_dict():
    """Test BotDetectionState.to_dict"""

    # Arrange
    state = BotDetectionState(
        reviewed_commits={1: ["abc123", "def456"]},
        last_review_times={1: "2024-01-01T00:00:00"},
        in_progress_reviews={2: "2024-01-01T01:00:00"},
    )

    # Act
    result = state.to_dict()

    # Assert
    assert result["reviewed_commits"] == {1: ["abc123", "def456"]}
    assert result["last_review_times"] == {1: "2024-01-01T00:00:00"}
    assert result["in_progress_reviews"] == {2: "2024-01-01T01:00:00"}


def test_BotDetectionState_from_dict():
    """Test BotDetectionState.from_dict"""

    # Arrange
    data = {
        "reviewed_commits": {1: ["abc123"], 2: ["def456"]},
        "last_review_times": {1: "2024-01-01T00:00:00"},
        "in_progress_reviews": {2: "2024-01-01T01:00:00"},
    }

    # Act
    result = BotDetectionState.from_dict(data)

    # Assert
    assert result.reviewed_commits == {1: ["abc123"], 2: ["def456"]}
    assert result.last_review_times == {1: "2024-01-01T00:00:00"}
    assert result.in_progress_reviews == {2: "2024-01-01T01:00:00"}


def test_BotDetectionState_from_dict_empty():
    """Test BotDetectionState.from_dict with empty data"""

    # Arrange
    data = {}

    # Act
    result = BotDetectionState.from_dict(data)

    # Assert
    assert result.reviewed_commits == {}
    assert result.last_review_times == {}
    assert result.in_progress_reviews == {}


def test_BotDetectionState_save(tmp_path):
    """Test BotDetectionState.save"""

    # Arrange
    state_dir = tmp_path / "state"
    state = BotDetectionState(
        reviewed_commits={1: ["abc123"]},
    )

    # Act
    state.save(state_dir)

    # Assert
    state_file = state_dir / "bot_detection_state.json"
    assert state_file.exists()


def test_BotDetectionState_load(tmp_path):
    """Test BotDetectionState.load"""

    # Arrange
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    state = BotDetectionState(
        reviewed_commits={1: ["abc123"]},
    )
    state.save(state_dir)

    # Act
    result = BotDetectionState.load(state_dir)

    # Assert
    assert result.reviewed_commits == {"1": ["abc123"]}


def test_BotDetectionState_load_no_file(tmp_path):
    """Test BotDetectionState.load when file doesn't exist"""

    # Arrange
    state_dir = tmp_path / "nonexistent_state"

    # Act
    result = BotDetectionState.load(state_dir)

    # Assert
    assert isinstance(result, BotDetectionState)
    assert result.reviewed_commits == {}


def test_BotDetector___init__(tmp_path):
    """Test BotDetector.__init__"""

    # Arrange & Act
    state_dir = tmp_path / "state"
    detector = BotDetector(
        state_dir=state_dir,
        bot_token="test-token",
        review_own_prs=False,
    )

    # Assert
    assert detector.state_dir == state_dir
    assert detector.bot_token == "test-token"
    assert detector.review_own_prs is False
    assert isinstance(detector.state, BotDetectionState)


def test_BotDetector___init__without_token(tmp_path):
    """Test BotDetector.__init__ without bot token"""

    # Arrange & Act
    state_dir = tmp_path / "state"
    detector = BotDetector(
        state_dir=state_dir,
        bot_token=None,
        review_own_prs=True,
    )

    # Assert
    assert detector.bot_token is None
    assert detector.bot_username is None
    assert detector.review_own_prs is True


def test_BotDetector_is_bot_pr(tmp_path):
    """Test BotDetector.is_bot_pr"""

    # Arrange
    state_dir = tmp_path / "state"
    detector = BotDetector(
        state_dir=state_dir,
        bot_token="test-token",
    )
    detector.bot_username = "my-bot"

    pr_data = {"author": {"login": "my-bot"}}

    # Act
    result = detector.is_bot_pr(pr_data)

    # Assert
    assert result is True


def test_BotDetector_is_bot_pr_not_bot(tmp_path):
    """Test BotDetector.is_bot_pr with human PR"""

    # Arrange
    state_dir = tmp_path / "state"
    detector = BotDetector(
        state_dir=state_dir,
        bot_token="test-token",
    )
    detector.bot_username = "my-bot"

    pr_data = {"author": {"login": "human-user"}}

    # Act
    result = detector.is_bot_pr(pr_data)

    # Assert
    assert result is False


def test_BotDetector_is_bot_pr_no_username(tmp_path):
    """Test BotDetector.is_bot_pr without bot username"""

    # Arrange
    state_dir = tmp_path / "state"
    detector = BotDetector(
        state_dir=state_dir,
        bot_token=None,
    )

    pr_data = {"author": {"login": "some-user"}}

    # Act
    result = detector.is_bot_pr(pr_data)

    # Assert
    assert result is False


def test_BotDetector_is_bot_commit(tmp_path):
    """Test BotDetector.is_bot_commit"""

    # Arrange
    state_dir = tmp_path / "state"
    detector = BotDetector(
        state_dir=state_dir,
        bot_token="test-token",
    )
    detector.bot_username = "my-bot"

    commit_data = {"author": {"login": "my-bot"}}

    # Act
    result = detector.is_bot_commit(commit_data)

    # Assert
    assert result is True


def test_BotDetector_is_bot_commit_committer(tmp_path):
    """Test BotDetector.is_bot_commit with bot as committer"""

    # Arrange
    state_dir = tmp_path / "state"
    detector = BotDetector(
        state_dir=state_dir,
        bot_token="test-token",
    )
    detector.bot_username = "my-bot"

    commit_data = {"committer": {"login": "my-bot"}}

    # Act
    result = detector.is_bot_commit(commit_data)

    # Assert
    assert result is True


def test_BotDetector_is_bot_commit_human(tmp_path):
    """Test BotDetector.is_bot_commit with human commit"""

    # Arrange
    state_dir = tmp_path / "state"
    detector = BotDetector(
        state_dir=state_dir,
        bot_token="test-token",
    )
    detector.bot_username = "my-bot"

    commit_data = {"author": {"login": "human-user"}}

    # Act
    result = detector.is_bot_commit(commit_data)

    # Assert
    assert result is False


def test_BotDetector_get_last_commit_sha():
    """Test BotDetector.get_last_commit_sha"""

    # Arrange
    state_dir = Path("/tmp")
    detector = BotDetector(state_dir=state_dir)
    commits = [
        {"oid": "abc123"},
        {"oid": "def456"},
        {"oid": "ghi789"},
    ]

    # Act
    result = detector.get_last_commit_sha(commits)

    # Assert
    assert result == "ghi789"


def test_BotDetector_get_last_commit_sha_empty():
    """Test BotDetector.get_last_commit_sha with empty list"""

    # Arrange
    state_dir = Path("/tmp")
    detector = BotDetector(state_dir=state_dir)
    commits = []

    # Act
    result = detector.get_last_commit_sha(commits)

    # Assert
    assert result is None


def test_BotDetector_get_last_commit_sha_with_sha_field():
    """Test BotDetector.get_last_commit_sha with sha field"""

    # Arrange
    state_dir = Path("/tmp")
    detector = BotDetector(state_dir=state_dir)
    commits = [
        {"sha": "abc123"},
    ]

    # Act
    result = detector.get_last_commit_sha(commits)

    # Assert
    assert result == "abc123"


def test_BotDetector_is_within_cooling_off_active(tmp_path):
    """Test BotDetector.is_within_cooling_off when active"""

    # Arrange
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    detector = BotDetector(state_dir=state_dir)

    # Set last review time to 30 seconds ago
    recent_time = (datetime.now() - timedelta(seconds=30)).isoformat()
    detector.state.last_review_times["1"] = recent_time

    # Act
    is_cooling, reason = detector.is_within_cooling_off(1)

    # Assert
    assert is_cooling is True
    assert "Cooling off period active" in reason


def test_BotDetector_is_within_cooling_off_expired(tmp_path):
    """Test BotDetector.is_within_cooling_off when expired"""

    # Arrange
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    detector = BotDetector(state_dir=state_dir)

    # Set last review time to 5 minutes ago
    old_time = (datetime.now() - timedelta(minutes=5)).isoformat()
    detector.state.last_review_times["1"] = old_time

    # Act
    is_cooling, reason = detector.is_within_cooling_off(1)

    # Assert
    assert is_cooling is False
    assert reason == ""


def test_BotDetector_is_within_cooling_off_no_review(tmp_path):
    """Test BotDetector.is_within_cooling_off with no prior review"""

    # Arrange
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    detector = BotDetector(state_dir=state_dir)

    # Act
    is_cooling, reason = detector.is_within_cooling_off(1)

    # Assert
    assert is_cooling is False
    assert reason == ""


def test_BotDetector_has_reviewed_commit_true(tmp_path):
    """Test BotDetector.has_reviewed_commit when reviewed"""

    # Arrange
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    detector = BotDetector(state_dir=state_dir)

    detector.state.reviewed_commits["1"] = ["abc123", "def456"]

    # Act
    result = detector.has_reviewed_commit(1, "abc123")

    # Assert
    assert result is True


def test_BotDetector_has_reviewed_commit_false(tmp_path):
    """Test BotDetector.has_reviewed_commit when not reviewed"""

    # Arrange
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    detector = BotDetector(state_dir=state_dir)

    detector.state.reviewed_commits["1"] = ["abc123"]

    # Act
    result = detector.has_reviewed_commit(1, "def456")

    # Assert
    assert result is False


def test_BotDetector_has_reviewed_commit_no_pr(tmp_path):
    """Test BotDetector.has_reviewed_commit with no prior reviews"""

    # Arrange
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    detector = BotDetector(state_dir=state_dir)

    # Act
    result = detector.has_reviewed_commit(1, "abc123")

    # Assert
    assert result is False


def test_BotDetector_is_review_in_progress_true(tmp_path):
    """Test BotDetector.is_review_in_progress when in progress"""

    # Arrange
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    detector = BotDetector(state_dir=state_dir)

    # Set in-progress to 1 minute ago
    start_time = (datetime.now() - timedelta(minutes=1)).isoformat()
    detector.state.in_progress_reviews["1"] = start_time

    # Act
    is_in_progress, reason = detector.is_review_in_progress(1)

    # Assert
    assert is_in_progress is True
    assert "Review already in progress" in reason


def test_BotDetector_is_review_in_progress_false(tmp_path):
    """Test BotDetector.is_review_in_progress when not in progress"""

    # Arrange
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    detector = BotDetector(state_dir=state_dir)

    # Act
    is_in_progress, reason = detector.is_review_in_progress(1)

    # Assert
    assert is_in_progress is False
    assert reason == ""


def test_BotDetector_is_review_in_progress_stale(tmp_path):
    """Test BotDetector.is_review_in_progress with stale review"""

    # Arrange
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    detector = BotDetector(state_dir=state_dir)

    # Set in-progress to 60 minutes ago (past timeout)
    start_time = (datetime.now() - timedelta(minutes=60)).isoformat()
    detector.state.in_progress_reviews["1"] = start_time

    # Act
    is_in_progress, reason = detector.is_review_in_progress(1)

    # Assert
    assert is_in_progress is False
    assert reason == ""
    # State should be cleared
    assert "1" not in detector.state.in_progress_reviews


def test_BotDetector_mark_review_started(tmp_path):
    """Test BotDetector.mark_review_started"""

    # Arrange
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    detector = BotDetector(state_dir=state_dir)

    # Act
    detector.mark_review_started(1)

    # Assert
    assert "1" in detector.state.in_progress_reviews
    # Verify time is recent (within last minute)
    start_time = datetime.fromisoformat(detector.state.in_progress_reviews["1"])
    assert datetime.now() - start_time < timedelta(minutes=1)


def test_BotDetector_mark_review_finished(tmp_path):
    """Test BotDetector.mark_review_finished"""

    # Arrange
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    detector = BotDetector(state_dir=state_dir)
    detector.state.in_progress_reviews["1"] = "2024-01-01T00:00:00"

    # Act
    detector.mark_review_finished(1, success=True)

    # Assert
    assert "1" not in detector.state.in_progress_reviews


def test_BotDetector_mark_reviewed(tmp_path):
    """Test BotDetector.mark_reviewed"""

    # Arrange
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    detector = BotDetector(state_dir=state_dir)

    # Act
    detector.mark_reviewed(1, "abc123")

    # Assert
    assert "1" in detector.state.reviewed_commits
    assert "abc123" in detector.state.reviewed_commits["1"]
    assert "1" in detector.state.last_review_times
    # Verify time is recent
    last_review = datetime.fromisoformat(detector.state.last_review_times["1"])
    assert datetime.now() - last_review < timedelta(minutes=1)
    # In-progress should be cleared
    assert "1" not in detector.state.in_progress_reviews


def test_BotDetector_clear_pr_state(tmp_path):
    """Test BotDetector.clear_pr_state"""

    # Arrange
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    detector = BotDetector(state_dir=state_dir)
    detector.state.reviewed_commits["1"] = ["abc123"]
    detector.state.last_review_times["1"] = "2024-01-01T00:00:00"
    detector.state.in_progress_reviews["1"] = "2024-01-01T01:00:00"

    # Act
    detector.clear_pr_state(1)

    # Assert
    assert "1" not in detector.state.reviewed_commits
    assert "1" not in detector.state.last_review_times
    assert "1" not in detector.state.in_progress_reviews


def test_BotDetector_get_stats(tmp_path):
    """Test BotDetector.get_stats"""

    # Arrange
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    detector = BotDetector(state_dir=state_dir)
    detector.state.reviewed_commits[1] = ["abc123", "def456"]
    detector.state.reviewed_commits[2] = ["ghi789"]
    detector.state.last_review_times[1] = "2024-01-01T00:00:00"
    detector.state.in_progress_reviews[3] = "2024-01-01T01:00:00"

    # Act
    stats = detector.get_stats()

    # Assert
    assert stats["total_prs_tracked"] == 2
    assert stats["total_reviews_performed"] == 3
    assert stats["in_progress_reviews"] == 1
    assert stats["cooling_off_minutes"] == 1


def test_BotDetector_cleanup_stale_prs(tmp_path):
    """Test BotDetector.cleanup_stale_prs"""

    # Arrange
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    detector = BotDetector(state_dir=state_dir)

    # Add some old reviews (more than a day old)
    old_time = (datetime.now() - timedelta(days=2)).isoformat()
    detector.state.last_review_times["1"] = old_time

    # Add recent review
    recent_time = (datetime.now() - timedelta(minutes=5)).isoformat()
    detector.state.last_review_times["2"] = recent_time

    # Act
    count = detector.cleanup_stale_prs(max_age_days=1)

    # Assert
    # Old review should be removed
    assert "1" not in detector.state.last_review_times
    # Recent review should remain
    assert "2" in detector.state.last_review_times
    assert count >= 1


def test_BotDetector_should_skip_pr_review_bot_pr(tmp_path):
    """Test BotDetector.should_skip_pr_review with bot PR"""

    # Arrange
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    detector = BotDetector(
        state_dir=state_dir,
        bot_token="test-token",
        review_own_prs=False,
    )
    detector.bot_username = "my-bot"

    pr_data = {"author": {"login": "my-bot"}}
    commits = []

    # Act
    should_skip, reason = detector.should_skip_pr_review(1, pr_data, commits)

    # Assert
    assert should_skip is True
    assert "bot" in reason.lower()


def test_BotDetector_should_skip_pr_review_reviewed_commit(tmp_path):
    """Test BotDetector.should_skip_pr_review with reviewed commit"""

    # Arrange
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    detector = BotDetector(
        state_dir=state_dir,
        bot_token=None,
    )

    pr_data = {"author": {"login": "human-user"}}
    commits = [{"oid": "abc123"}]

    # Mark commit as reviewed
    detector.state.reviewed_commits["1"] = ["abc123"]

    # Act
    should_skip, reason = detector.should_skip_pr_review(1, pr_data, commits)

    # Assert
    assert should_skip is True
    assert "already reviewed" in reason.lower()


def test_BotDetector_should_skip_pr_review_cooling_off(tmp_path):
    """Test BotDetector.should_skip_pr_review in cooling off"""

    # Arrange
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    detector = BotDetector(
        state_dir=state_dir,
        bot_token=None,
    )

    pr_data = {"author": {"login": "human-user"}}
    commits = [{"oid": "def456"}]

    # Set recent review time
    recent_time = (datetime.now() - timedelta(seconds=30)).isoformat()
    detector.state.last_review_times["1"] = recent_time

    # Act
    should_skip, reason = detector.should_skip_pr_review(1, pr_data, commits)

    # Assert
    assert should_skip is True
    assert "cooling" in reason.lower()


def test_BotDetector_should_skip_pr_review_in_progress(tmp_path):
    """Test BotDetector.should_skip_pr_review with in-progress review"""

    # Arrange
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    detector = BotDetector(
        state_dir=state_dir,
        bot_token=None,
    )

    pr_data = {"author": {"login": "human-user"}}
    commits = [{"oid": "def456"}]

    # Set in-progress review
    start_time = (datetime.now() - timedelta(minutes=1)).isoformat()
    detector.state.in_progress_reviews["1"] = start_time

    # Act
    should_skip, reason = detector.should_skip_pr_review(1, pr_data, commits)

    # Assert
    assert should_skip is True
    assert "in progress" in reason.lower()


def test_BotDetector_should_skip_pr_review_no_skip(tmp_path):
    """Test BotDetector.should_skip_pr_review when should not skip"""

    # Arrange
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    detector = BotDetector(
        state_dir=state_dir,
        bot_token=None,
    )

    pr_data = {"author": {"login": "human-user"}}
    commits = [{"oid": "abc123"}]

    # Act
    should_skip, reason = detector.should_skip_pr_review(1, pr_data, commits)

    # Assert
    assert should_skip is False
    assert reason == ""
