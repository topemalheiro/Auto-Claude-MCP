"""Tests for qa_commands"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cli.qa_commands import (
    handle_qa_command,
    handle_qa_status_command,
    handle_review_status_command,
)


def test_handle_qa_status_command(tmp_path, capsys):
    """Test handle_qa_status_command."""
    # Arrange
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()

    # Act
    handle_qa_status_command(spec_dir)

    # Assert
    captured = capsys.readouterr()
    assert "Spec:" in captured.out or "QA" in captured.out


def test_handle_qa_status_command_with_empty_inputs(capsys):
    """Test handle_qa_status_command with empty spec_dir."""
    # Arrange
    spec_dir = Path("/tmp/test")

    # Act
    handle_qa_status_command(spec_dir)

    # Assert
    captured = capsys.readouterr()
    assert "Spec:" in captured.out


def test_handle_review_status_command(tmp_path, capsys):
    """Test handle_review_status_command."""
    # Arrange
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()

    # Act
    handle_review_status_command(spec_dir)

    # Assert
    captured = capsys.readouterr()
    assert "Spec:" in captured.out


def test_handle_review_status_command_with_approval(tmp_path, capsys):
    """Test handle_review_status_command with valid approval."""
    # Arrange
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()

    with patch("cli.qa_commands.ReviewState") as mock_state:
        mock_instance = MagicMock()
        mock_instance.is_approval_valid.return_value = True
        mock_instance.approved = "test_user"
        mock_state.load.return_value = mock_instance

        # Act
        handle_review_status_command(spec_dir)

    # Assert
    captured = capsys.readouterr()
    assert "Spec:" in captured.out


def test_handle_review_status_command_with_empty_inputs(capsys):
    """Test handle_review_status_command with empty spec_dir."""
    # Arrange
    spec_dir = Path("/tmp/test")

    # Act
    handle_review_status_command(spec_dir)

    # Assert
    captured = capsys.readouterr()
    assert "Spec:" in captured.out


def test_handle_qa_command_not_approved(tmp_path, capsys):
    """Test handle_qa_command when QA not needed and not approved."""
    # Arrange
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    (spec_dir / "spec.md").write_text("# Test Spec")

    with patch("cli.qa_commands.validate_environment", return_value=True), \
         patch("cli.qa_commands.should_run_qa", return_value=False), \
         patch("cli.qa_commands.is_qa_approved", return_value=False), \
         patch("cli.qa_commands.count_subtasks", return_value=(2, 5)):
        # Act
        handle_qa_command(project_dir, spec_dir, "sonnet", False)

    # Assert
    captured = capsys.readouterr()
    assert "Build not complete" in captured.out or "subtasks" in captured.out


def test_handle_qa_command_already_approved(tmp_path, capsys):
    """Test handle_qa_command when already approved."""
    # Arrange
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    (spec_dir / "spec.md").write_text("# Test Spec")

    with patch("cli.qa_commands.validate_environment", return_value=True), \
         patch("cli.qa_commands.should_run_qa", return_value=False), \
         patch("cli.qa_commands.is_qa_approved", return_value=True):
        # Act
        handle_qa_command(project_dir, spec_dir, "sonnet", False)

    # Assert
    captured = capsys.readouterr()
    assert "approved" in captured.out.lower()


def test_handle_qa_command_successful_validation(tmp_path, capsys):
    """Test handle_qa_command with successful QA validation."""
    # Arrange
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    (spec_dir / "spec.md").write_text("# Test Spec")

    with patch("cli.qa_commands.validate_environment", return_value=True), \
         patch("cli.qa_commands.should_run_qa", return_value=True), \
         patch("cli.qa_commands.run_qa_validation_loop", return_value=True):
        # Act
        handle_qa_command(project_dir, spec_dir, "sonnet", False)

    # Assert
    captured = capsys.readouterr()
    assert "passed" in captured.out.lower() or "QA" in captured.out


def test_handle_qa_command_validation_failed(tmp_path):
    """Test handle_qa_command with failed QA validation."""
    # Arrange
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    (spec_dir / "spec.md").write_text("# Test Spec")

    with patch("cli.qa_commands.validate_environment", return_value=True), \
         patch("cli.qa_commands.should_run_qa", return_value=True), \
         patch("cli.qa_commands.run_qa_validation_loop", return_value=False):
        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            handle_qa_command(project_dir, spec_dir, "sonnet", False)
        assert exc_info.value.code == 1


def test_handle_qa_command_keyboard_interrupt(tmp_path):
    """Test handle_qa_command handles KeyboardInterrupt."""
    # Arrange
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    (spec_dir / "spec.md").write_text("# Test Spec")

    with patch("cli.qa_commands.validate_environment", return_value=True), \
         patch("cli.qa_commands.should_run_qa", return_value=True), \
         patch("cli.qa_commands.run_qa_validation_loop", side_effect=KeyboardInterrupt()):
        # Act
        handle_qa_command(project_dir, spec_dir, "sonnet", False)

    # Assert - should exit gracefully without raising exception


def test_handle_qa_command_invalid_environment(tmp_path):
    """Test handle_qa_command with invalid environment."""
    # Arrange
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()

    with patch("cli.qa_commands.validate_environment", return_value=False):
        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            handle_qa_command(project_dir, spec_dir, "sonnet", False)
        assert exc_info.value.code == 1


def test_handle_qa_command_with_empty_inputs(tmp_path):
    """Test handle_qa_command with empty model string."""
    # Arrange
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    (spec_dir / "spec.md").write_text("# Test Spec")

    with patch("cli.qa_commands.validate_environment", return_value=True), \
         patch("cli.qa_commands.should_run_qa", return_value=False), \
         patch("cli.qa_commands.is_qa_approved", return_value=True):
        # Act
        handle_qa_command(project_dir, spec_dir, "", False)

    # Assert - should complete without error


def test_handle_qa_command_with_human_feedback(tmp_path, capsys):
    """Test handle_qa_command with human feedback file."""
    # Arrange
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    (spec_dir / "spec.md").write_text("# Test Spec")
    (spec_dir / "QA_FIX_REQUEST.md").write_text("# Fix Request")

    with patch("cli.qa_commands.validate_environment", return_value=True), \
         patch("cli.qa_commands.should_run_qa", return_value=False), \
         patch("cli.qa_commands.run_qa_validation_loop", return_value=True):
        # Act
        handle_qa_command(project_dir, spec_dir, "sonnet", False)

    # Assert
    captured = capsys.readouterr()
    assert "feedback" in captured.out.lower() or "passed" in captured.out.lower()
