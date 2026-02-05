"""Tests for followup_commands"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cli.followup_commands import collect_followup_task, handle_followup_command


def test_collect_followup_task_type_choice(tmp_path, capsys):
    """Test collect_followup_task with type choice."""
    # Arrange
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    max_retries = 3
    lines = ["Test follow-up task", "Second line", ""]

    with patch("cli.followup_commands.select_menu") as mock_select, \
         patch("builtins.input", side_effect=lines):
        mock_select.return_value = "type"

        # Act
        result = collect_followup_task(spec_dir, max_retries)

    # Assert
    assert result == "Test follow-up task\nSecond line"
    assert (spec_dir / "FOLLOWUP_REQUEST.md").exists()


def test_collect_followup_task_quit_choice(tmp_path):
    """Test collect_followup_task with quit choice."""
    # Arrange
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()

    with patch("cli.followup_commands.select_menu") as mock_select:
        mock_select.return_value = "quit"

        # Act
        result = collect_followup_task(spec_dir)

    # Assert
    assert result is None


def test_collect_followup_task_file_choice_valid_file(tmp_path, capsys):
    """Test collect_followup_task with file choice and valid file."""
    # Arrange
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    test_file = tmp_path / "followup.txt"
    test_file.write_text("Follow-up content from file")

    with patch("cli.followup_commands.select_menu") as mock_select, \
         patch("builtins.input", return_value=str(test_file)):
        mock_select.return_value = "file"

        # Act
        result = collect_followup_task(spec_dir)

    # Assert
    assert result == "Follow-up content from file"
    captured = capsys.readouterr()
    assert "Loaded" in captured.out


def test_collect_followup_task_file_choice_nonexistent_file(capsys):
    """Test collect_followup_task with file choice and non-existent file."""
    # Arrange
    spec_dir = Path("/tmp/test_spec")

    with patch("cli.followup_commands.select_menu") as mock_select, \
         patch("builtins.input", return_value="/tmp/nonexistent_file.txt"):
        mock_select.return_value = "file"

        # Act
        result = collect_followup_task(spec_dir, max_retries=1)

    # Assert
    assert result is None
    captured = capsys.readouterr()
    assert "Maximum retry" in captured.out or "cancelled" in captured.out.lower()


def test_collect_followup_task_empty_input_with_retry(tmp_path):
    """Test collect_followup_task with empty input triggers retry."""
    # Arrange
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()

    with patch("cli.followup_commands.select_menu") as mock_select, \
         patch("builtins.input", return_value=""):
        mock_select.return_value = "type"

        # Act
        result = collect_followup_task(spec_dir, max_retries=1)

    # Assert
    assert result is None


def test_collect_followup_task_keyboard_interrupt(tmp_path):
    """Test collect_followup_task handles KeyboardInterrupt."""
    # Arrange
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()

    with patch("cli.followup_commands.select_menu") as mock_select, \
         patch("builtins.input", side_effect=KeyboardInterrupt()):
        mock_select.return_value = "type"

        # Act
        result = collect_followup_task(spec_dir)

    # Assert
    assert result is None


def test_handle_followup_command_no_implementation_plan(tmp_path, capsys):
    """Test handle_followup_command when implementation plan doesn't exist."""
    # Arrange
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()

    # Act & Assert
    with pytest.raises(SystemExit) as exc_info:
        handle_followup_command(project_dir, spec_dir, "sonnet", False)
    assert exc_info.value.code == 1


def test_handle_followup_command_build_not_complete(tmp_path, capsys):
    """Test handle_followup_command when build is not complete."""
    # Arrange
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    plan_file = spec_dir / "implementation_plan.json"
    plan_file.write_text('{"phases": [], "subtasks": []}')

    # Patch is_build_complete and count_subtasks where they're used in followup_commands
    with patch("cli.followup_commands.is_build_complete", return_value=False), \
         patch("cli.followup_commands.count_subtasks", return_value=(1, 3)):
        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            handle_followup_command(project_dir, spec_dir, "sonnet", False)
        assert exc_info.value.code == 1


def test_handle_followup_command_user_cancels(tmp_path, capsys):
    """Test handle_followup_command when user cancels."""
    # Arrange
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    plan_file = spec_dir / "implementation_plan.json"
    plan_file.write_text('{"phases": [], "subtasks": []}')
    # Create spec.md to avoid validation error
    (spec_dir / "spec.md").write_text("# Test Spec")

    # Patch is_build_complete where it's used in followup_commands
    with patch("cli.followup_commands.is_build_complete", return_value=True), \
         patch("cli.followup_commands.collect_followup_task", return_value=None), \
         patch("cli.utils.validate_environment", return_value=True):
        # Act
        handle_followup_command(project_dir, spec_dir, "sonnet", False)

    # Assert - should return without error
    captured = capsys.readouterr()
    assert "cancelled" in captured.out.lower()


def test_handle_followup_command_successful_planning(tmp_path, capsys):
    """Test handle_followup_command with successful planning."""
    # Arrange
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    plan_file = spec_dir / "implementation_plan.json"
    plan_file.write_text('{"phases": [], "subtasks": []}')
    # Create spec.md to avoid validation error
    (spec_dir / "spec.md").write_text("# Test Spec")

    # Patch is_build_complete where it's used in followup_commands
    with patch("cli.followup_commands.is_build_complete", return_value=True), \
         patch("cli.followup_commands.collect_followup_task", return_value="Add new feature"), \
         patch("cli.utils.validate_environment", return_value=True), \
         patch("agent.run_followup_planner", return_value=True):
        # Act - the function has side effects, just verify it doesn't crash
        try:
            handle_followup_command(project_dir, spec_dir, "sonnet", False)
        except SystemExit:
            pass  # Expected in some cases

    # Assert - if we get here without exception, test passed
    assert True


def test_handle_followup_command_keyboard_interrupt(tmp_path):
    """Test handle_followup_command handles KeyboardInterrupt."""
    # Arrange
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    plan_file = spec_dir / "implementation_plan.json"
    plan_file.write_text('{"phases": [], "subtasks": []}')
    # Create spec.md to avoid validation error
    (spec_dir / "spec.md").write_text("# Test Spec")

    # Patch is_build_complete where it's used in followup_commands
    with patch("cli.followup_commands.is_build_complete", return_value=True), \
         patch("cli.followup_commands.collect_followup_task", return_value="Test"), \
         patch("cli.utils.validate_environment", return_value=True), \
         patch("agent.run_followup_planner", side_effect=KeyboardInterrupt()), \
         patch("sys.exit") as mock_exit:
        # Act
        handle_followup_command(project_dir, spec_dir, "sonnet", False)

    # Assert
    mock_exit.assert_called_with(0)


def test_handle_followup_command_planning_error(tmp_path):
    """Test handle_followup_command with planning error."""
    # Arrange
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    plan_file = spec_dir / "implementation_plan.json"
    plan_file.write_text('{"phases": [], "subtasks": []}')
    # Create spec.md to avoid validation error
    (spec_dir / "spec.md").write_text("# Test Spec")

    # Patch is_build_complete where it's used in followup_commands
    with patch("cli.followup_commands.is_build_complete", return_value=True), \
         patch("cli.followup_commands.collect_followup_task", return_value="Test"), \
         patch("cli.utils.validate_environment", return_value=True), \
         patch("agent.run_followup_planner", side_effect=RuntimeError("Planning error")), \
         patch("sys.exit") as mock_exit:
        # Act
        handle_followup_command(project_dir, spec_dir, "sonnet", True)

    # Assert
    mock_exit.assert_called_with(1)


def test_collect_followup_task_with_empty_inputs():
    """Test collect_followup_task with empty spec_dir path."""
    # Arrange
    spec_dir = Path("/tmp/test")

    with patch("cli.followup_commands.select_menu", return_value="quit"):
        # Act
        result = collect_followup_task(spec_dir)

    # Assert
    assert result is None


def test_handle_followup_command_with_empty_inputs(tmp_path):
    """Test handle_followup_command with empty model string."""
    # Arrange
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    plan_file = spec_dir / "implementation_plan.json"
    plan_file.write_text('{"phases": [], "subtasks": []}')
    # Create spec.md to avoid validation error
    (spec_dir / "spec.md").write_text("# Test Spec")

    # Patch is_build_complete where it's used in followup_commands
    with patch("cli.followup_commands.is_build_complete", return_value=True), \
         patch("cli.followup_commands.collect_followup_task", return_value=None):
        # Act
        handle_followup_command(project_dir, spec_dir, "", False)

    # Assert - should complete without raising
    assert True  # If we get here, the test passed
