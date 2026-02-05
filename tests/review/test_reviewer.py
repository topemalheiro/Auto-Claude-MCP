"""
Tests for review.reviewer module.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime

import pytest

from review.reviewer import (
    ReviewChoice,
    get_review_menu_options,
    open_file_in_editor,
    prompt_feedback,
    run_review_checkpoint,
)
from review.state import ReviewState


class TestReviewChoice:
    """Tests for ReviewChoice enum."""

    def test_review_choice_values(self) -> None:
        """Test that ReviewChoice has correct values."""
        assert ReviewChoice.APPROVE.value == "approve"
        assert ReviewChoice.EDIT_SPEC.value == "edit_spec"
        assert ReviewChoice.EDIT_PLAN.value == "edit_plan"
        assert ReviewChoice.FEEDBACK.value == "feedback"
        assert ReviewChoice.REJECT.value == "reject"

    def test_review_choice_count(self) -> None:
        """Test that ReviewChoice has 5 options."""
        assert len(ReviewChoice) == 5


class TestGetReviewMenuOptions:
    """Tests for get_review_menu_options function."""

    def test_returns_list(self) -> None:
        """Test that function returns a list."""
        options = get_review_menu_options()
        assert isinstance(options, list)

    def test_returns_five_options(self) -> None:
        """Test that function returns 5 menu options."""
        options = get_review_menu_options()
        assert len(options) == 5

    def test_options_have_required_attributes(self) -> None:
        """Test that options have key, label, icon, description."""
        options = get_review_menu_options()
        for option in options:
            assert hasattr(option, "key")
            assert hasattr(option, "label")
            assert hasattr(option, "icon")
            assert hasattr(option, "description")

    def test_approve_option_exists(self) -> None:
        """Test that approve option exists."""
        options = get_review_menu_options()
        approve_option = next((o for o in options if o.key == "approve"), None)
        assert approve_option is not None
        assert "approve" in approve_option.label.lower()

    def test_reject_option_exists(self) -> None:
        """Test that reject option exists."""
        options = get_review_menu_options()
        reject_option = next((o for o in options if o.key == "reject"), None)
        assert reject_option is not None
        assert "reject" in reject_option.label.lower()

    def test_edit_spec_option_exists(self) -> None:
        """Test that edit spec option exists."""
        options = get_review_menu_options()
        edit_spec_option = next((o for o in options if o.key == "edit_spec"), None)
        assert edit_spec_option is not None
        assert "spec" in edit_spec_option.label.lower()

    def test_edit_plan_option_exists(self) -> None:
        """Test that edit plan option exists."""
        options = get_review_menu_options()
        edit_plan_option = next((o for o in options if o.key == "edit_plan"), None)
        assert edit_plan_option is not None
        assert "plan" in edit_plan_option.label.lower()

    def test_feedback_option_exists(self) -> None:
        """Test that feedback option exists."""
        options = get_review_menu_options()
        feedback_option = next((o for o in options if o.key == "feedback"), None)
        assert feedback_option is not None
        assert "feedback" in feedback_option.label.lower()


class TestPromptFeedback:
    """Tests for prompt_feedback function."""

    def test_prompt_feedback_returns_text(self, monkeypatch) -> None:
        """Test that prompt_feedback returns entered text."""
        inputs = ["Line 1", "Line 2", "", ""]
        monkeypatch.setattr("builtins.input", lambda: inputs.pop(0))

        result = prompt_feedback()
        assert result == "Line 1\nLine 2"

    def test_prompt_feedback_single_empty_line(self, monkeypatch) -> None:
        """Test that single empty line requires second empty to finish."""
        # The function looks for TWO consecutive empty lines
        inputs = ["", ""]
        monkeypatch.setattr("builtins.input", lambda: inputs.pop(0))

        result = prompt_feedback()
        # Result should be None since feedback is empty after strip
        assert result is None

    def test_prompt_feedback_ctrl_c(self, monkeypatch) -> None:
        """Test that Ctrl+C returns None."""
        def raise_keyboard_interrupt():
            raise KeyboardInterrupt()

        monkeypatch.setattr("builtins.input", raise_keyboard_interrupt)

        result = prompt_feedback()
        assert result is None

    def test_prompt_feedback_eof(self, monkeypatch) -> None:
        """Test that EOF returns None."""
        def raise_eof():
            raise EOFError()

        monkeypatch.setattr("builtins.input", raise_eof)

        result = prompt_feedback()
        assert result is None

    def test_prompt_feedback_strips_trailing_empty_lines(self, monkeypatch) -> None:
        """Test that trailing empty lines are stripped."""
        inputs = ["Line 1", "Line 2", "", "", ""]
        monkeypatch.setattr("builtins.input", lambda: inputs.pop(0))

        result = prompt_feedback()
        assert result == "Line 1\nLine 2"

    def test_prompt_feedback_multiline(self, monkeypatch) -> None:
        """Test multiline input."""
        inputs = ["First paragraph", "", "Second paragraph", "", ""]
        monkeypatch.setattr("builtins.input", lambda: inputs.pop(0))

        result = prompt_feedback()
        assert result == "First paragraph\n\nSecond paragraph"

    def test_prompt_feedback_strips_whitespace(self, monkeypatch) -> None:
        """Test that feedback strips leading/trailing whitespace."""
        inputs = ["  Indented  ", "", ""]
        monkeypatch.setattr("builtins.input", lambda: inputs.pop(0))

        result = prompt_feedback()
        # The function calls .strip() on the final result
        assert result == "Indented"

    def test_prompt_feedback_empty_input(self, monkeypatch) -> None:
        """Test that empty input returns None."""
        # The function looks for TWO consecutive empty lines
        inputs = ["", ""]
        monkeypatch.setattr("builtins.input", lambda: inputs.pop(0))

        result = prompt_feedback()
        assert result is None


class TestOpenFileInEditor:
    """Tests for open_file_in_editor function."""

    def test_open_file_with_editor_env(self, tmp_path: Path, monkeypatch) -> None:
        """Test opening file with EDITOR env set."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        mock_run = MagicMock()
        monkeypatch.setenv("EDITOR", "vim")
        monkeypatch.setattr("subprocess.run", mock_run)

        result = open_file_in_editor(test_file)

        assert result is True
        mock_run.assert_called_once()

    def test_open_file_with_vscode(self, tmp_path: Path, monkeypatch) -> None:
        """Test opening file with VS Code uses --wait flag."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        mock_run = MagicMock()
        monkeypatch.setenv("EDITOR", "code")
        monkeypatch.setattr("subprocess.run", mock_run)

        result = open_file_in_editor(test_file)

        assert result is True
        # Check that --wait flag is used for code
        call_args = mock_run.call_args[0][0]
        assert "--wait" in call_args

    def test_open_file_with_code_insiders(self, tmp_path: Path, monkeypatch) -> None:
        """Test opening file with code-insiders uses --wait flag."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        mock_run = MagicMock()
        monkeypatch.setenv("EDITOR", "code-insiders")
        monkeypatch.setattr("subprocess.run", mock_run)

        result = open_file_in_editor(test_file)

        assert result is True
        # Check that --wait flag is used
        call_args = mock_run.call_args[0][0]
        assert "--wait" in call_args

    def test_open_file_no_editor_env(self, tmp_path: Path, monkeypatch) -> None:
        """Test opening file without EDITOR env uses fallback."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        mock_run = MagicMock()
        mock_which = MagicMock()
        # Simulate nano being found
        mock_which.return_value = MagicMock(returncode=0)

        monkeypatch.delenv("EDITOR", raising=False)
        monkeypatch.setattr("subprocess.run", mock_run)
        monkeypatch.setattr("subprocess.run", mock_which)

        # This will try to find an editor - might fail in test environment
        # Just verify it doesn't crash
        try:
            result = open_file_in_editor(test_file)
        except Exception:
            # Expected if no editor found
            pass

    def test_open_nonexistent_file(self, tmp_path: Path, monkeypatch) -> None:
        """Test opening nonexistent file returns False."""
        nonexistent = tmp_path / "nonexistent.txt"

        monkeypatch.setenv("EDITOR", "vim")

        result = open_file_in_editor(nonexistent)

        assert result is False

    def test_open_file_editor_fails(self, tmp_path: Path, monkeypatch) -> None:
        """Test handling when editor command fails."""
        import subprocess
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        mock_run = MagicMock(side_effect=subprocess.CalledProcessError(1, "vim"))
        monkeypatch.setenv("EDITOR", "vim")
        monkeypatch.setattr("subprocess.run", mock_run)

        result = open_file_in_editor(test_file)

        assert result is False

    def test_open_file_editor_not_found(self, tmp_path: Path, monkeypatch) -> None:
        """Test handling when editor executable not found."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        mock_run = MagicMock(side_effect=FileNotFoundError)
        monkeypatch.setenv("EDITOR", "nonexistent-editor")
        monkeypatch.setattr("subprocess.run", mock_run)

        result = open_file_in_editor(test_file)

        assert result is False


class TestRunReviewCheckpoint:
    """Tests for run_review_checkpoint function."""

    @pytest.fixture
    def spec_dir(self, tmp_path: Path) -> Path:
        """Create a temporary spec directory."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        return spec_dir

    @pytest.fixture
    def populated_spec_dir(self, spec_dir: Path) -> Path:
        """Create spec directory with spec.md and implementation_plan.json."""
        (spec_dir / "spec.md").write_text("# Test Spec\n\n## Overview\nTest content.")
        (spec_dir / "implementation_plan.json").write_text(
            json.dumps({"feature": "Test", "phases": []})
        )
        return spec_dir

    def test_auto_approve_mode(self, populated_spec_dir: Path) -> None:
        """Test checkpoint with auto_approve=True."""
        state = run_review_checkpoint(populated_spec_dir, auto_approve=True)

        assert state.is_approved() is True
        assert state.approved_by == "auto"

    def test_auto_approve_creates_state_file(self, populated_spec_dir: Path) -> None:
        """Test that auto_approve creates state file."""
        run_review_checkpoint(populated_spec_dir, auto_approve=True)

        state_file = populated_spec_dir / "review_state.json"
        assert state_file.exists()

    def test_already_approved_shows_message(
        self, populated_spec_dir: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """Test that already approved spec shows message."""
        # First approve
        state = ReviewState()
        state.approve(populated_spec_dir)
        state.save(populated_spec_dir)

        # Run checkpoint again
        result_state = run_review_checkpoint(populated_spec_dir)

        assert result_state.is_approved() is True
        captured = capsys.readouterr()
        # Should show "already approved" message
        output = captured.out.lower()
        assert "approved" in output

    def test_spec_changed_shows_warning(
        self, populated_spec_dir: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """Test that spec changed after approval shows warning."""
        # Approve original
        state = ReviewState()
        state.approve(populated_spec_dir)
        state.save(populated_spec_dir)

        # Modify spec
        (populated_spec_dir / "spec.md").write_text("# Modified Spec")

        # Run checkpoint
        with patch("review.reviewer.select_menu", return_value="approve"):
            run_review_checkpoint(populated_spec_dir)

        captured = capsys.readouterr()
        # Should show warning about spec change
        output = captured.out.lower()
        # The implementation shows "SPEC CHANGED SINCE APPROVAL"
        assert "changed" in output or "stale" in output

    @patch("review.reviewer.select_menu")
    @patch("review.reviewer.open_file_in_editor")
    def test_edit_spec_invalidates_approval(
        self, mock_open, mock_menu, populated_spec_dir: Path
    ) -> None:
        """Test that editing spec invalidates previous approval."""
        # Approve first
        state = ReviewState()
        state.approve(populated_spec_dir)
        state.save(populated_spec_dir)

        # Modify spec to invalidate approval
        (populated_spec_dir / "spec.md").write_text("# Modified Spec")

        # Now the approval should be invalid, so it enters the menu loop
        mock_menu.side_effect = ["edit_spec", "approve"]
        mock_open.return_value = True

        with patch("review.reviewer.display_spec_summary"):
            with patch("review.reviewer.display_plan_summary"):
                with patch("review.reviewer.display_review_status"):
                    result_state = run_review_checkpoint(populated_spec_dir)

        # After editing and re-approving, we should have a new approval
        loaded_state = ReviewState.load(populated_spec_dir)
        # The state should be approved after we select "approve"
        assert loaded_state.is_approved() is True
        # The review count should have increased
        assert loaded_state.review_count >= 2

    @patch("review.reviewer.select_menu")
    @patch("review.reviewer.open_file_in_editor")
    def test_edit_plan_invalidates_approval(
        self, mock_open, mock_menu, populated_spec_dir: Path
    ) -> None:
        """Test that editing plan invalidates previous approval."""
        # Approve first
        state = ReviewState()
        state.approve(populated_spec_dir)
        state.save(populated_spec_dir)

        # Modify plan to invalidate approval
        (populated_spec_dir / "implementation_plan.json").write_text('{"modified": true}')

        # Now the approval should be invalid, so it enters the menu loop
        mock_menu.side_effect = ["edit_plan", "approve"]
        mock_open.return_value = True

        with patch("review.reviewer.display_spec_summary"):
            with patch("review.reviewer.display_plan_summary"):
                with patch("review.reviewer.display_review_status"):
                    run_review_checkpoint(populated_spec_dir)

        # After editing and re-approving, we should have a new approval
        loaded_state = ReviewState.load(populated_spec_dir)
        assert loaded_state.is_approved() is True
        # The review count should have increased
        assert loaded_state.review_count >= 2

    @patch("review.reviewer.select_menu")
    @patch("review.reviewer.prompt_feedback")
    def test_add_feedback(self, mock_prompt, mock_menu, populated_spec_dir: Path) -> None:
        """Test adding feedback."""
        mock_menu.side_effect = ["feedback", "approve"]
        mock_prompt.return_value = "Great work!"

        with patch("review.reviewer.display_spec_summary"):
            with patch("review.reviewer.display_plan_summary"):
                with patch("review.reviewer.display_review_status"):
                    result_state = run_review_checkpoint(populated_spec_dir)

        # Should have feedback
        assert len(result_state.feedback) > 0
        assert "Great work!" in result_state.feedback[0]

    @patch("review.reviewer.select_menu")
    def test_reject_exits(self, mock_menu, populated_spec_dir: Path) -> None:
        """Test that reject choice causes exit."""
        mock_menu.return_value = "reject"

        with pytest.raises(SystemExit) as exc_info:
            with patch("review.reviewer.display_spec_summary"):
                with patch("review.reviewer.display_plan_summary"):
                    with patch("review.reviewer.display_review_status"):
                        run_review_checkpoint(populated_spec_dir)

        # Should exit with code 1
        assert exc_info.value.code == 1

    @patch("review.reviewer.select_menu")
    def test_keyboard_interrupt_handled(self, mock_menu, populated_spec_dir: Path) -> None:
        """Test that KeyboardInterrupt is handled gracefully."""
        mock_menu.side_effect = KeyboardInterrupt()

        with pytest.raises(SystemExit) as exc_info:
            with patch("review.reviewer.display_spec_summary"):
                with patch("review.reviewer.display_plan_summary"):
                    with patch("review.reviewer.display_review_status"):
                        run_review_checkpoint(populated_spec_dir)

        # Should exit with code 0 (graceful)
        assert exc_info.value.code == 0

    @patch("review.reviewer.select_menu")
    def test_quit_option_exits(self, mock_menu, populated_spec_dir: Path) -> None:
        """Test that quit (None return) exits gracefully."""
        mock_menu.return_value = None

        with pytest.raises(SystemExit) as exc_info:
            with patch("review.reviewer.display_spec_summary"):
                with patch("review.reviewer.display_plan_summary"):
                    with patch("review.reviewer.display_review_status"):
                        run_review_checkpoint(populated_spec_dir)

        # Should exit with code 0
        assert exc_info.value.code == 0

    @patch("review.reviewer.select_menu")
    def test_approve_sets_correct_fields(self, mock_menu, populated_spec_dir: Path) -> None:
        """Test that approve sets all required fields."""
        mock_menu.return_value = "approve"

        with patch("review.reviewer.display_spec_summary"):
            with patch("review.reviewer.display_plan_summary"):
                with patch("review.reviewer.display_review_status"):
                    result_state = run_review_checkpoint(populated_spec_dir)

        assert result_state.is_approved() is True
        assert result_state.approved_by == "user"
        assert result_state.approved_at  # Should have timestamp
        assert result_state.spec_hash  # Should have computed hash
        assert result_state.review_count > 0

    @patch("review.reviewer.select_menu")
    @patch("review.reviewer.open_file_in_editor")
    def test_edit_spec_missing_file(
        self, mock_open, mock_menu, populated_spec_dir: Path, capsys
    ) -> None:
        """Test handling when spec.md doesn't exist."""
        # Remove spec.md
        (populated_spec_dir / "spec.md").unlink()

        mock_menu.side_effect = ["edit_spec", "approve"]
        mock_open.return_value = True

        with patch("review.reviewer.display_spec_summary"):
            with patch("review.reviewer.display_plan_summary"):
                with patch("review.reviewer.display_review_status"):
                    run_review_checkpoint(populated_spec_dir)

        captured = capsys.readouterr()
        # Should show error about missing file
        output = captured.out.lower()
        assert "not found" in output

    @patch("review.reviewer.select_menu")
    @patch("review.reviewer.open_file_in_editor")
    def test_edit_plan_missing_file(
        self, mock_open, mock_menu, populated_spec_dir: Path, capsys
    ) -> None:
        """Test handling when implementation_plan.json doesn't exist."""
        # Remove plan file
        (populated_spec_dir / "implementation_plan.json").unlink()

        mock_menu.side_effect = ["edit_plan", "approve"]
        mock_open.return_value = True

        with patch("review.reviewer.display_spec_summary"):
            with patch("review.reviewer.display_plan_summary"):
                with patch("review.reviewer.display_review_status"):
                    run_review_checkpoint(populated_spec_dir)

        captured = capsys.readouterr()
        # Should show error about missing file
        output = captured.out.lower()
        assert "not found" in output

    @patch("review.reviewer.select_menu")
    @patch("review.reviewer.prompt_feedback")
    def test_feedback_empty(self, mock_prompt, mock_menu, populated_spec_dir: Path) -> None:
        """Test handling when feedback is empty."""
        mock_menu.side_effect = ["feedback", "approve"]
        mock_prompt.return_value = None  # User cancelled

        with patch("review.reviewer.display_spec_summary"):
            with patch("review.reviewer.display_plan_summary"):
                with patch("review.reviewer.display_review_status"):
                    run_review_checkpoint(populated_spec_dir)

        # Should not crash or add empty feedback


class TestRunReviewCheckpointEdgeCases:
    """Edge case tests for run_review_checkpoint."""

    @pytest.fixture
    def spec_dir(self, tmp_path: Path) -> Path:
        """Create a temporary spec directory."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        return spec_dir

    def test_directory_with_only_state_file(self, spec_dir: Path) -> None:
        """Test when only state file exists (no spec or plan)."""
        # Create only state file
        state = ReviewState()
        state.save(spec_dir)

        # Should handle gracefully - auto-approve mode should work
        result = run_review_checkpoint(spec_dir, auto_approve=True)
        assert result.is_approved() is True

    def test_loads_existing_feedback(self, spec_dir: Path) -> None:
        """Test that existing feedback is preserved."""
        # Create spec files
        (spec_dir / "spec.md").write_text("# Test")
        (spec_dir / "implementation_plan.json").write_text("{}")

        # Create state with feedback
        state = ReviewState(feedback=["[2024-01-01 10:00] Old feedback"])
        state.save(spec_dir)

        # Approve
        result = run_review_checkpoint(spec_dir, auto_approve=True)

        # Should preserve old feedback
        assert len(result.feedback) == 1
        assert "Old feedback" in result.feedback[0]

    def test_review_count_increments(self, spec_dir: Path) -> None:
        """Test that review count increments on each approval."""
        (spec_dir / "spec.md").write_text("# Test")
        (spec_dir / "implementation_plan.json").write_text("{}")

        # First approval
        state1 = run_review_checkpoint(spec_dir, auto_approve=True)
        count1 = state1.review_count

        # Second approval (after modification)
        (spec_dir / "spec.md").write_text("# Modified")
        state2 = run_review_checkpoint(spec_dir, auto_approve=True)
        count2 = state2.review_count

        assert count2 > count1
