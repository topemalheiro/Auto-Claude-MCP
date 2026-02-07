"""
Tests for review.state module.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime

import pytest

from review.state import (
    REVIEW_STATE_FILE,
    ReviewState,
    _compute_file_hash,
    _compute_spec_hash,
    get_review_status_summary,
)


class TestComputeFileHash:
    """Tests for _compute_file_hash helper function."""

    def test_hash_existing_file(self, tmp_path: Path) -> None:
        """Test computing hash of existing file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        result = _compute_file_hash(test_file)
        assert result  # Should return non-empty hash
        assert len(result) == 32  # MD5 hash is 32 hex chars

    def test_hash_nonexistent_file(self, tmp_path: Path) -> None:
        """Test computing hash of nonexistent file."""
        result = _compute_file_hash(tmp_path / "nonexistent.txt")
        assert result == ""

    def test_hash_different_content(self, tmp_path: Path) -> None:
        """Test that different content produces different hashes."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("Content 1")
        file2.write_text("Content 2")

        hash1 = _compute_file_hash(file1)
        hash2 = _compute_file_hash(file2)
        assert hash1 != hash2

    def test_hash_same_content(self, tmp_path: Path) -> None:
        """Test that same content produces same hash."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("Same content")
        file2.write_text("Same content")

        hash1 = _compute_file_hash(file1)
        hash2 = _compute_file_hash(file2)
        assert hash1 == hash2

    def test_hash_unicode_content(self, tmp_path: Path) -> None:
        """Test computing hash of file with unicode content."""
        test_file = tmp_path / "unicode.txt"
        test_file.write_text("Hello 世界 🌍")

        result = _compute_file_hash(test_file)
        assert result
        assert len(result) == 32


class TestComputeSpecHash:
    """Tests for _compute_spec_hash helper function."""

    def test_spec_hash_with_both_files(self, tmp_path: Path) -> None:
        """Test computing hash when both spec.md and implementation_plan.json exist."""
        spec_dir = tmp_path
        (spec_dir / "spec.md").write_text("# Spec")
        (spec_dir / "implementation_plan.json").write_text('{"title": "Test"}')

        result = _compute_spec_hash(spec_dir)
        assert result
        assert len(result) == 32

    def test_spec_hash_with_only_spec(self, tmp_path: Path) -> None:
        """Test computing hash with only spec.md."""
        spec_dir = tmp_path
        (spec_dir / "spec.md").write_text("# Spec")

        result = _compute_spec_hash(spec_dir)
        assert result

    def test_spec_hash_with_only_plan(self, tmp_path: Path) -> None:
        """Test computing hash with only implementation_plan.json."""
        spec_dir = tmp_path
        (spec_dir / "implementation_plan.json").write_text('{}')

        result = _compute_spec_hash(spec_dir)
        assert result

    def test_spec_hash_no_files(self, tmp_path: Path) -> None:
        """Test computing hash with no spec files."""
        result = _compute_spec_hash(tmp_path)
        # When no files exist, hash is computed from empty strings
        # The hash of ":" (empty:empty) is not empty
        # Let's verify it returns some hash value
        assert result != ""  # Actually returns a hash of empty content

    def test_spec_hash_changes_when_files_change(self, tmp_path: Path) -> None:
        """Test that hash changes when files are modified."""
        spec_dir = tmp_path
        (spec_dir / "spec.md").write_text("# Original")
        (spec_dir / "implementation_plan.json").write_text('{}')

        hash1 = _compute_spec_hash(spec_dir)

        # Modify spec.md
        (spec_dir / "spec.md").write_text("# Modified")
        hash2 = _compute_spec_hash(spec_dir)

        assert hash1 != hash2


class TestReviewStateDataclass:
    """Tests for ReviewState dataclass methods."""

    def test_default_values(self) -> None:
        """Test ReviewState has correct default values."""
        state = ReviewState()
        assert state.approved is False
        assert state.approved_by == ""
        assert state.approved_at == ""
        assert state.feedback == []
        assert state.spec_hash == ""
        assert state.review_count == 0

    def test_to_dict(self) -> None:
        """Test converting ReviewState to dictionary."""
        state = ReviewState(
            approved=True,
            approved_by="user",
            approved_at="2024-01-01T00:00:00",
            feedback=["Good work"],
            spec_hash="abc123",
            review_count=1,
        )
        result = state.to_dict()
        assert result["approved"] is True
        assert result["approved_by"] == "user"
        assert result["approved_at"] == "2024-01-01T00:00:00"
        assert result["feedback"] == ["Good work"]
        assert result["spec_hash"] == "abc123"
        assert result["review_count"] == 1

    def test_from_dict(self) -> None:
        """Test creating ReviewState from dictionary."""
        data = {
            "approved": True,
            "approved_by": "auto",
            "approved_at": "2024-01-01T00:00:00",
            "feedback": ["Review comment"],
            "spec_hash": "def456",
            "review_count": 2,
        }
        state = ReviewState.from_dict(data)
        assert state.approved is True
        assert state.approved_by == "auto"
        assert state.approved_at == "2024-01-01T00:00:00"
        assert state.feedback == ["Review comment"]
        assert state.spec_hash == "def456"
        assert state.review_count == 2

    def test_from_dict_with_missing_fields(self) -> None:
        """Test from_dict handles missing fields gracefully."""
        data = {"approved": True}
        state = ReviewState.from_dict(data)
        assert state.approved is True
        assert state.approved_by == ""
        assert state.feedback == []
        assert state.review_count == 0

    def test_from_dict_empty(self) -> None:
        """Test from_dict with empty dict."""
        state = ReviewState.from_dict({})
        assert state.approved is False
        assert state.approved_by == ""
        assert state.feedback == []
        assert state.review_count == 0

    def test_is_approved(self) -> None:
        """Test is_approved method."""
        state = ReviewState(approved=False)
        assert state.is_approved() is False

        state.approved = True
        assert state.is_approved() is True


class TestReviewStatePersistence:
    """Tests for ReviewState save/load functionality."""

    def test_save_creates_file(self, tmp_path: Path) -> None:
        """Test that save creates the state file."""
        state = ReviewState(approved=True, approved_by="user")
        state.save(tmp_path)

        state_file = tmp_path / REVIEW_STATE_FILE
        assert state_file.exists()

    def test_save_content(self, tmp_path: Path) -> None:
        """Test that save writes correct content."""
        state = ReviewState(
            approved=True,
            approved_by="user",
            approved_at="2024-01-01T00:00:00",
            feedback=["Comment"],
            review_count=1,
        )
        state.save(tmp_path)

        state_file = tmp_path / REVIEW_STATE_FILE
        content = json.loads(state_file.read_text())
        assert content["approved"] is True
        assert content["approved_by"] == "user"
        assert content["feedback"] == ["Comment"]

    def test_load_existing_file(self, tmp_path: Path) -> None:
        """Test loading existing state file."""
        # Create a state file
        state_data = {
            "approved": True,
            "approved_by": "auto",
            "approved_at": "2024-01-01T00:00:00",
            "feedback": ["Auto-approved"],
            "spec_hash": "abc123",
            "review_count": 3,
        }
        state_file = tmp_path / REVIEW_STATE_FILE
        state_file.write_text(json.dumps(state_data))

        state = ReviewState.load(tmp_path)
        assert state.approved is True
        assert state.approved_by == "auto"
        assert state.feedback == ["Auto-approved"]
        assert state.review_count == 3

    def test_load_nonexistent_file(self, tmp_path: Path) -> None:
        """Test loading when state file doesn't exist."""
        state = ReviewState.load(tmp_path)
        assert state.approved is False
        assert state.approved_by == ""
        assert state.feedback == []
        assert state.review_count == 0

    def test_load_invalid_json(self, tmp_path: Path) -> None:
        """Test loading invalid JSON returns empty state."""
        state_file = tmp_path / REVIEW_STATE_FILE
        state_file.write_text("invalid json {")

        state = ReviewState.load(tmp_path)
        assert state.approved is False

    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        """Test that save and load preserves state."""
        original = ReviewState(
            approved=True,
            approved_by="craig",
            approved_at="2024-01-15T10:30:00",
            feedback=["First review", "Second review"],
            spec_hash="xyz789",
            review_count=5,
        )
        original.save(tmp_path)

        loaded = ReviewState.load(tmp_path)
        assert loaded.approved == original.approved
        assert loaded.approved_by == original.approved_by
        assert loaded.approved_at == original.approved_at
        assert loaded.feedback == original.feedback
        assert loaded.spec_hash == original.spec_hash
        assert loaded.review_count == original.review_count


class TestReviewStateApproval:
    """Tests for ReviewState approval workflow methods."""

    def test_approve_sets_attributes(self, tmp_path: Path) -> None:
        """Test that approve sets correct attributes."""
        state = ReviewState()
        state.approve(tmp_path, approved_by="user", auto_save=False)

        assert state.approved is True
        assert state.approved_by == "user"
        assert state.approved_at  # Should have timestamp
        assert state.review_count == 1
        assert state.spec_hash  # Should have computed hash

    def test_approve_saves_by_default(self, tmp_path: Path) -> None:
        """Test that approve saves by default."""
        state = ReviewState()
        state.approve(tmp_path, approved_by="user")

        state_file = tmp_path / REVIEW_STATE_FILE
        assert state_file.exists()

    def test_approve_without_save(self, tmp_path: Path) -> None:
        """Test approve with auto_save=False."""
        state = ReviewState()
        state.approve(tmp_path, approved_by="user", auto_save=False)

        state_file = tmp_path / REVIEW_STATE_FILE
        assert not state_file.exists()

    def test_approve_different_users(self, tmp_path: Path) -> None:
        """Test approving with different user types."""
        state1 = ReviewState()
        state1.approve(tmp_path, approved_by="auto", auto_save=False)
        assert state1.approved_by == "auto"

        state2 = ReviewState()
        state2.approve(tmp_path, approved_by="craig", auto_save=False)
        assert state2.approved_by == "craig"

    def test_approve_increments_count(self, tmp_path: Path) -> None:
        """Test that approve increments review count."""
        state = ReviewState(review_count=2)
        state.approve(tmp_path, auto_save=False)
        assert state.review_count == 3

    def test_reject_clears_attributes(self, tmp_path: Path) -> None:
        """Test that reject clears approval."""
        state = ReviewState(
            approved=True,
            approved_by="user",
            approved_at="2024-01-01T00:00:00",
            spec_hash="abc123",
        )
        state.reject(tmp_path, auto_save=False)

        assert state.approved is False
        assert state.approved_by == ""
        assert state.approved_at == ""
        assert state.spec_hash == ""

    def test_reject_increments_count(self, tmp_path: Path) -> None:
        """Test that reject increments review count."""
        state = ReviewState(review_count=1)
        state.reject(tmp_path, auto_save=False)
        assert state.review_count == 2

    def test_reject_saves_by_default(self, tmp_path: Path) -> None:
        """Test that reject saves by default."""
        state = ReviewState()
        state.reject(tmp_path)

        state_file = tmp_path / REVIEW_STATE_FILE
        assert state_file.exists()


class TestReviewStateValidation:
    """Tests for ReviewState approval validation methods."""

    def test_is_approval_valid_when_approved(self, tmp_path: Path) -> None:
        """Test is_approval_valid when approved and hash matches."""
        # Create spec files
        (tmp_path / "spec.md").write_text("# Spec")
        (tmp_path / "implementation_plan.json").write_text('{}')

        state = ReviewState()
        state.approve(tmp_path, auto_save=False)

        assert state.is_approval_valid(tmp_path) is True

    def test_is_approval_valid_when_not_approved(self, tmp_path: Path) -> None:
        """Test is_approval_valid when not approved."""
        state = ReviewState(approved=False)
        assert state.is_approval_valid(tmp_path) is False

    def test_is_approval_valid_when_hash_mismatch(self, tmp_path: Path) -> None:
        """Test is_approval_valid when spec changed after approval."""
        # Create and approve with original files
        (tmp_path / "spec.md").write_text("# Original")
        (tmp_path / "implementation_plan.json").write_text('{}')

        state = ReviewState()
        state.approve(tmp_path, auto_save=False)

        # Modify spec.md
        (tmp_path / "spec.md").write_text("# Modified")

        assert state.is_approval_valid(tmp_path) is False

    def test_is_approval_valid_legacy_no_hash(self, tmp_path: Path) -> None:
        """Test is_approval_valid for legacy approval without hash."""
        state = ReviewState(approved=True, spec_hash="")
        # Legacy approval without hash should be considered valid
        assert state.is_approval_valid(tmp_path) is True


class TestReviewStateFeedback:
    """Tests for ReviewState feedback management."""

    def test_add_feedback(self, tmp_path: Path) -> None:
        """Test adding feedback."""
        state = ReviewState()
        state.add_feedback("Great work!", tmp_path, auto_save=False)

        assert len(state.feedback) == 1
        assert "Great work!" in state.feedback[0]

    def test_add_feedback_includes_timestamp(self, tmp_path: Path) -> None:
        """Test that feedback includes timestamp."""
        state = ReviewState()
        state.add_feedback("Comment", tmp_path, auto_save=False)

        feedback_text = state.feedback[0]
        # Should have timestamp in format [YYYY-MM-DD HH:MM]
        assert "[" in feedback_text
        assert "]" in feedback_text
        assert "Comment" in feedback_text

    def test_add_multiple_feedback(self, tmp_path: Path) -> None:
        """Test adding multiple feedback items."""
        state = ReviewState()
        state.add_feedback("First", tmp_path, auto_save=False)
        state.add_feedback("Second", tmp_path, auto_save=False)
        state.add_feedback("Third", tmp_path, auto_save=False)

        assert len(state.feedback) == 3
        assert "First" in state.feedback[0]
        assert "Second" in state.feedback[1]
        assert "Third" in state.feedback[2]

    def test_add_feedback_saves_by_default(self, tmp_path: Path) -> None:
        """Test that add_feedback saves by default."""
        state = ReviewState()
        state.add_feedback("Comment", tmp_path)

        state_file = tmp_path / REVIEW_STATE_FILE
        assert state_file.exists()

    def test_add_feedback_without_spec_dir_no_save(self, tmp_path: Path) -> None:
        """Test add_feedback with spec_dir=None doesn't error."""
        state = ReviewState()
        # Should not raise error even though auto_save=True
        state.add_feedback("Comment", spec_dir=None, auto_save=True)

        assert len(state.feedback) == 1

    def test_add_feedback_without_save(self, tmp_path: Path) -> None:
        """Test add_feedback with auto_save=False."""
        state = ReviewState()
        state.add_feedback("Comment", tmp_path, auto_save=False)

        state_file = tmp_path / REVIEW_STATE_FILE
        assert not state_file.exists()


class TestReviewStateInvalidate:
    """Tests for ReviewState.invalidate method."""

    def test_invalidate_clears_approval(self, tmp_path: Path) -> None:
        """Test that invalidate clears approval status."""
        state = ReviewState(
            approved=True,
            approved_by="user",
            approved_at="2024-01-01T00:00:00",
            spec_hash="abc123",
        )
        state.invalidate(tmp_path, auto_save=False)

        assert state.approved is False
        assert state.approved_at == ""
        assert state.spec_hash == ""
        # approved_by and feedback are kept as history
        assert state.approved_by == "user"

    def test_invalidate_preserves_feedback(self, tmp_path: Path) -> None:
        """Test that invalidate preserves feedback history."""
        state = ReviewState(
            approved=True,
            feedback=["Review 1", "Review 2"],
        )
        state.invalidate(tmp_path, auto_save=False)

        assert state.feedback == ["Review 1", "Review 2"]

    def test_invalidate_saves_by_default(self, tmp_path: Path) -> None:
        """Test that invalidate saves by default."""
        state = ReviewState(approved=True)
        state.invalidate(tmp_path)

        state_file = tmp_path / REVIEW_STATE_FILE
        assert state_file.exists()


class TestGetReviewStatusSummary:
    """Tests for get_review_status_summary function."""

    def test_summary_for_new_spec(self, tmp_path: Path) -> None:
        """Test summary for spec with no review state."""
        summary = get_review_status_summary(tmp_path)

        assert summary["approved"] is False
        assert summary["valid"] is False
        assert summary["approved_by"] == ""
        assert summary["approved_at"] == ""
        assert summary["review_count"] == 0
        assert summary["feedback_count"] == 0
        assert summary["spec_changed"] is False

    def test_summary_for_approved_spec(self, tmp_path: Path) -> None:
        """Test summary for approved spec."""
        state = ReviewState(approved=True, approved_by="user", review_count=1)
        state.save(tmp_path)

        summary = get_review_status_summary(tmp_path)
        assert summary["approved"] is True
        assert summary["valid"] is True
        assert summary["approved_by"] == "user"
        assert summary["review_count"] == 1

    def test_summary_for_invalidated_approval(self, tmp_path: Path) -> None:
        """Test summary when approval is invalidated."""
        # Create spec files first
        (tmp_path / "spec.md").write_text("# Original")
        (tmp_path / "implementation_plan.json").write_text('{}')

        state = ReviewState()
        state.approve(tmp_path, auto_save=False)  # Computes hash
        state.save(tmp_path)  # Save to persist the state

        # Modify spec to invalidate
        (tmp_path / "spec.md").write_text("# Modified")

        summary = get_review_status_summary(tmp_path)
        # Note: spec_changed is True when spec_hash exists and differs from current hash
        # But the state has approved=True, so the summary reflects that
        assert summary["approved"] is True  # Still marked as approved
        # valid checks is_approval_valid which returns False when hash differs
        assert summary["valid"] is False  # But not valid

    def test_summary_with_feedback(self, tmp_path: Path) -> None:
        """Test summary includes feedback count."""
        state = ReviewState(
            approved=True,
            feedback=["Review 1", "Review 2", "Review 3"],
        )
        state.save(tmp_path)

        summary = get_review_status_summary(tmp_path)
        assert summary["feedback_count"] == 3

    def test_summary_includes_timestamp(self, tmp_path: Path) -> None:
        """Test summary includes approved_at timestamp."""
        state = ReviewState(
            approved=True,
            approved_at="2024-01-15T10:30:00",
        )
        state.save(tmp_path)

        summary = get_review_status_summary(tmp_path)
        assert summary["approved_at"] == "2024-01-15T10:30:00"
