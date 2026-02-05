"""Tests for main"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cli.main import main, parse_args


def test_parse_args_with_defaults():
    """Test parse_args with default arguments."""
    # Arrange - mock sys.argv with empty args
    with patch("sys.argv", ["run.py"]):
        # Act
        result = parse_args()

    # Assert
    assert result is not None
    assert result.spec is None
    assert result.list is False
    assert result.verbose is False
    assert result.max_iterations is None


def test_parse_args_with_spec():
    """Test parse_args with --spec argument."""
    # Arrange
    with patch("sys.argv", ["run.py", "--spec", "001"]):
        # Act
        result = parse_args()

    # Assert
    assert result.spec == "001"


def test_parse_args_with_list():
    """Test parse_args with --list argument."""
    # Arrange
    with patch("sys.argv", ["run.py", "--list"]):
        # Act
        result = parse_args()

    # Assert
    assert result.list is True


def test_parse_args_with_multiple_options():
    """Test parse_args with multiple options."""
    # Arrange
    with patch("sys.argv", ["run.py", "--spec", "001", "--verbose", "--isolated"]):
        # Act
        result = parse_args()

    # Assert
    assert result.spec == "001"
    assert result.verbose is True
    assert result.isolated is True


def test_parse_args_with_invalid_option():
    """Test parse_args with invalid option raises SystemExit."""
    # Arrange
    with patch("sys.argv", ["run.py", "--invalid-option"]):
        # Act & Assert
        with pytest.raises(SystemExit):
            parse_args()


def test_main_with_list_command(capsys):
    """Test main with --list command."""
    # Arrange
    with patch("sys.argv", ["run.py", "--list"]), \
         patch("cli.main.print_specs_list"):
        # Act & Assert - should not raise exception
        try:
            main()
        except SystemExit as e:
            # SystemExit(0) or (130) for KeyboardInterrupt is acceptable
            assert e.code in (0, 130)


def test_main_with_missing_spec(capsys):
    """Test main exits when --spec is not provided."""
    # Arrange
    with patch("sys.argv", ["run.py"]):
        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1


def test_main_with_spec_not_found(capsys):
    """Test main exits when spec is not found."""
    # Arrange
    with patch("sys.argv", ["run.py", "--spec", "999-nonexistent"]), \
         patch("cli.main.find_spec", return_value=None):
        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1


def test_main_keyboard_interrupt():
    """Test main handles KeyboardInterrupt."""
    # Arrange
    with patch("sys.argv", ["run.py", "--list"]), \
         patch("cli.main.print_specs_list", side_effect=KeyboardInterrupt()):
        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 130


def test_main_unexpected_error():
    """Test main handles unexpected errors."""
    # Arrange
    with patch("sys.argv", ["run.py", "--list"]), \
         patch("cli.main.print_specs_list", side_effect=RuntimeError("Test error")):
        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1


def test_parse_args_with_qa_options():
    """Test parse_args with QA-related options."""
    # Arrange
    with patch("sys.argv", ["run.py", "--spec", "001", "--qa", "--skip-qa"]):
        # Act
        result = parse_args()

    # Assert
    assert result.qa is True
    assert result.skip_qa is True


def test_parse_args_with_workspace_options():
    """Test parse_args with workspace-related options."""
    # Arrange
    with patch("sys.argv", ["run.py", "--spec", "001", "--merge", "--no-commit"]):
        # Act
        result = parse_args()

    # Assert
    assert result.merge is True
    assert result.no_commit is True


def test_parse_args_with_pr_options():
    """Test parse_args with PR-related options."""
    # Arrange
    with patch("sys.argv", ["run.py", "--spec", "001", "--create-pr", "--pr-draft", "--pr-title", "Test PR"]):
        # Act
        result = parse_args()

    # Assert
    assert result.create_pr is True
    assert result.pr_draft is True
    assert result.pr_title == "Test PR"


def test_parse_args_with_batch_options():
    """Test parse_args with batch-related options."""
    # Arrange
    with patch("sys.argv", ["run.py", "--batch-create", "batch.json"]):
        # Act
        result = parse_args()

    # Assert
    assert result.batch_create == "batch.json"


def test_parse_args_empty_inputs():
    """Test parse_args with no arguments (same as defaults)."""
    # Arrange
    with patch("sys.argv", ["run.py"]):
        # Act
        result = parse_args()

    # Assert
    assert result is not None
    assert result.spec is None


def test_main_with_empty_inputs():
    """Test main with no arguments should show error."""
    # Arrange
    with patch("sys.argv", ["run.py"]):
        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
