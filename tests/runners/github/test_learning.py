"""Tests for learning"""

from runners.github.learning import (
    AccuracyStats,
    AuthorResponse,
    LearningPattern,
    LearningTracker,
    OutcomeType,
    PredictionType,
    ReviewOutcome,
)
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import tempfile
from datetime import datetime, timedelta, timezone


def test_ReviewOutcome_to_dict():
    """Test ReviewOutcome.to_dict"""

    # Arrange
    instance = ReviewOutcome(
        review_id="review-123",
        repo="owner/repo",
        pr_number=456,
        prediction=PredictionType.REVIEW_REQUEST_CHANGES,
        findings_count=5,
        high_severity_count=2,
        file_types=["py", "ts"],
        categories=["security", "bug"],
    )

    # Act
    result = instance.to_dict()

    # Assert
    assert result is not None
    assert result["review_id"] == "review-123"
    assert result["repo"] == "owner/repo"
    assert result["pr_number"] == 456
    assert result["prediction"] == "review_request_changes"
    assert result["findings_count"] == 5
    assert result["high_severity_count"] == 2
    assert result["file_types"] == ["py", "ts"]


def test_ReviewOutcome_from_dict():
    """Test ReviewOutcome.from_dict"""

    # Arrange
    data = {
        "review_id": "review-123",
        "repo": "owner/repo",
        "pr_number": 456,
        "prediction": "review_approve",
        "findings_count": 3,
        "high_severity_count": 1,
        "created_at": "2024-01-01T00:00:00Z",
        "actual_outcome": "merged",
        "time_to_outcome": 3600.0,
        "author_response": "accepted",
        "outcome_recorded_at": "2024-01-01T01:00:00Z",
        "file_types": ["py"],
        "categories": ["bug"],
    }

    # Act
    result = ReviewOutcome.from_dict(data)

    # Assert
    assert result.review_id == "review-123"
    assert result.repo == "owner/repo"
    assert result.pr_number == 456
    assert result.prediction == PredictionType.REVIEW_APPROVE
    assert result.actual_outcome == OutcomeType.MERGED
    assert result.time_to_outcome == timedelta(seconds=3600.0)


def test_AccuracyStats_to_dict():
    """Test AccuracyStats.to_dict"""

    # Arrange
    instance = AccuracyStats(
        total_predictions=100,
        correct_predictions=80,
        incorrect_predictions=15,
        pending_outcomes=5,
        by_type={"review_approve": {"total": 50, "correct": 45, "incorrect": 5}},
        avg_time_to_merge=timedelta(seconds=3600),
    )

    # Act
    result = instance.to_dict()

    # Assert
    assert result is not None
    assert result["total_predictions"] == 100
    assert result["correct_predictions"] == 80
    # accuracy = correct / (correct + incorrect) = 80 / 95 = 0.842
    assert abs(result["accuracy"] - 0.842) < 0.01
    assert abs(result["completion_rate"] - 0.95) < 0.01


def test_LearningPattern_to_dict():
    """Test LearningPattern.to_dict"""

    # Arrange
    instance = LearningPattern(
        pattern_id="file_type_py",
        pattern_type="file_type_accuracy",
        context={"file_type": "py"},
        sample_size=100,
        accuracy=0.85,
        confidence=0.9,
    )

    # Act
    result = instance.to_dict()

    # Assert
    assert result is not None
    assert result["pattern_id"] == "file_type_py"
    assert result["pattern_type"] == "file_type_accuracy"
    assert result["context"]["file_type"] == "py"
    assert result["sample_size"] == 100
    assert result["accuracy"] == 0.85


def test_LearningTracker___init__():
    """Test LearningTracker.__init__"""

    # Arrange & Act
    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = Path(tmpdir)
        instance = LearningTracker(state_dir)

    # Assert
    assert instance is not None
    assert instance.state_dir == state_dir
    # The learning_dir is created inside __init__
    # assert instance.learning_dir.exists()


def test_LearningTracker_record_prediction():
    """Test LearningTracker.record_prediction"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        instance = LearningTracker(state_dir=Path(tmpdir))

        # Act
        result = instance.record_prediction(
            repo="owner/repo",
            review_id="review-123",
            prediction=PredictionType.REVIEW_REQUEST_CHANGES,
            pr_number=456,
            findings_count=5,
            high_severity_count=2,
            file_types=["py", "ts"],
            change_size="medium",
            categories=["security", "bug"],
        )

    # Assert
    assert result is not None
    assert result.review_id == "review-123"
    assert result.repo == "owner/repo"
    assert result.prediction == PredictionType.REVIEW_REQUEST_CHANGES


def test_LearningTracker_record_outcome():
    """Test LearningTracker.record_outcome"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        instance = LearningTracker(state_dir=Path(tmpdir))
        # First record a prediction
        instance.record_prediction(
            repo="owner/repo",
            review_id="review-123",
            prediction=PredictionType.REVIEW_REQUEST_CHANGES,
            pr_number=456,
        )

        # Act
        result = instance.record_outcome(
            repo="owner/repo",
            review_id="review-123",
            outcome=OutcomeType.MODIFIED,
            time_to_outcome=timedelta(hours=2),
            author_response=AuthorResponse.ACCEPTED,
        )

    # Assert
    assert result is not None
    assert result.actual_outcome == OutcomeType.MODIFIED
    assert result.time_to_outcome == timedelta(hours=2)


def test_LearningTracker_get_pending_outcomes():
    """Test LearningTracker.get_pending_outcomes"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        instance = LearningTracker(state_dir=Path(tmpdir))
        # Record a prediction without outcome
        instance.record_prediction(
            repo="owner/repo",
            review_id="review-123",
            prediction=PredictionType.REVIEW_REQUEST_CHANGES,
        )

        # Act
        result = instance.get_pending_outcomes(repo="owner/repo")

    # Assert
    assert result is not None
    assert len(result) == 1
    assert result[0].review_id == "review-123"


def test_LearningTracker_get_accuracy():
    """Test LearningTracker.get_accuracy"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        instance = LearningTracker(state_dir=Path(tmpdir))
        # Record predictions with outcomes
        instance.record_prediction(
            repo="owner/repo",
            review_id="review-1",
            prediction=PredictionType.REVIEW_APPROVE,
        )
        instance.record_outcome(
            repo="owner/repo",
            review_id="review-1",
            outcome=OutcomeType.MERGED,
        )
        instance.record_prediction(
            repo="owner/repo",
            review_id="review-2",
            prediction=PredictionType.REVIEW_REQUEST_CHANGES,
        )
        instance.record_outcome(
            repo="owner/repo",
            review_id="review-2",
            outcome=OutcomeType.MODIFIED,
        )

        # Act
        result = instance.get_accuracy(repo="owner/repo")

    # Assert
    assert result is not None
    assert result.total_predictions == 2
    assert result.correct_predictions == 2
    assert result.accuracy == 1.0


def test_LearningTracker_get_recent_outcomes():
    """Test LearningTracker.get_recent_outcomes"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        instance = LearningTracker(state_dir=Path(tmpdir))
        # Record multiple outcomes
        instance.record_prediction(
            repo="owner/repo",
            review_id="review-1",
            prediction=PredictionType.REVIEW_APPROVE,
        )
        instance.record_outcome(
            repo="owner/repo",
            review_id="review-1",
            outcome=OutcomeType.MERGED,
        )
        instance.record_prediction(
            repo="owner/repo",
            review_id="review-2",
            prediction=PredictionType.REVIEW_APPROVE,
        )
        instance.record_outcome(
            repo="owner/repo",
            review_id="review-2",
            outcome=OutcomeType.CLOSED,
        )

        # Act
        result = instance.get_recent_outcomes(repo="owner/repo", limit=10)

    # Assert
    assert result is not None
    assert len(result) == 2


def test_LearningTracker_detect_patterns():
    """Test LearningTracker.detect_patterns"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        instance = LearningTracker(state_dir=Path(tmpdir))
        # Record enough outcomes to detect patterns
        for i in range(25):
            instance.record_prediction(
                repo="owner/repo",
                review_id=f"review-{i}",
                prediction=PredictionType.REVIEW_APPROVE,
                file_types=["py"],
                categories=["bug"],
            )
            outcome = OutcomeType.MERGED if i < 20 else OutcomeType.CLOSED
            instance.record_outcome(
                repo="owner/repo",
                review_id=f"review-{i}",
                outcome=outcome,
            )

        # Act
        result = instance.detect_patterns(min_sample_size=20)

    # Assert
    assert result is not None
    assert isinstance(result, list)


def test_LearningTracker_get_dashboard_data():
    """Test LearningTracker.get_dashboard_data"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        instance = LearningTracker(state_dir=Path(tmpdir))
        # Record some data
        instance.record_prediction(
            repo="owner/repo",
            review_id="review-1",
            prediction=PredictionType.REVIEW_APPROVE,
        )
        instance.record_outcome(
            repo="owner/repo",
            review_id="review-1",
            outcome=OutcomeType.MERGED,
        )

        # Act
        result = instance.get_dashboard_data(repo="owner/repo")

    # Assert
    assert result is not None
    assert "all_time" in result
    assert "last_week" in result
    assert "last_month" in result
    assert "patterns" in result
    assert "recent_outcomes" in result
    assert "pending_count" in result


def test_LearningTracker_check_pr_status():
    """Test LearningTracker.check_pr_status"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        instance = LearningTracker(state_dir=Path(tmpdir))
        gh_provider = MagicMock()

        # Act
        result = instance.check_pr_status(repo="owner/repo", gh_provider=gh_provider)

    # Assert
    # The stub implementation returns 0
    assert result == 0
