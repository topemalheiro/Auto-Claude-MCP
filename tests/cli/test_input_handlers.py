"""Tests for input_handlers"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cli.input_handlers import (
    collect_user_input_interactive,
    read_from_file,
    read_multiline_input,
)


def test_collect_user_input_interactive_type_choice():
    """Test collect_user_input_interactive with type choice."""
    # Arrange
    title = "Test Title"
    subtitle = "Test Subtitle"
    prompt_text = "Enter text:"
    allow_file = True
    allow_paste = True

    with patch("cli.input_handlers.select_menu") as mock_select, \
         patch("cli.input_handlers.read_multiline_input") as mock_read:
        mock_select.return_value = "type"
        mock_read.return_value = "Test input from user"

        # Act
        result = collect_user_input_interactive(title, subtitle, prompt_text, allow_file, allow_paste)

        # Assert
        assert result == "Test input from user"


def test_collect_user_input_interactive_quit_choice():
    """Test collect_user_input_interactive with quit choice."""
    # Arrange
    title = "Test Title"
    subtitle = "Test Subtitle"
    prompt_text = "Enter text:"

    with patch("cli.input_handlers.select_menu") as mock_select:
        mock_select.return_value = "quit"

        # Act
        result = collect_user_input_interactive(title, subtitle, prompt_text)

        # Assert
        assert result is None


def test_collect_user_input_interactive_skip_choice():
    """Test collect_user_input_interactive with skip choice."""
    # Arrange
    title = "Test Title"

    with patch("cli.input_handlers.select_menu") as mock_select:
        mock_select.return_value = "skip"

        # Act
        result = collect_user_input_interactive(title, "", "")

        # Assert
        assert result == ""


def test_collect_user_input_interactive_file_choice():
    """Test collect_user_input_interactive with file choice."""
    # Arrange
    with patch("cli.input_handlers.select_menu") as mock_select, \
         patch("cli.input_handlers.read_from_file") as mock_read:
        mock_select.return_value = "file"
        mock_read.return_value = "Content from file"

        # Act
        result = collect_user_input_interactive("Title", "", "", True, False)

        # Assert
        assert result == "Content from file"


def test_read_from_file_with_valid_file(tmp_path, capsys):
    """Test read_from_file with valid file."""
    # Arrange
    test_file = tmp_path / "test_input.txt"
    test_file.write_text("Test content from file")

    with patch("builtins.input", return_value=str(test_file)):
        # Act
        result = read_from_file()

    # Assert
    captured = capsys.readouterr()
    assert result == "Test content from file"
    assert "Loaded" in captured.out


def test_read_from_file_with_nonexistent_file(capsys):
    """Test read_from_file with non-existent file."""
    # Arrange
    with patch("builtins.input", return_value="/tmp/nonexistent_file.txt"):
        # Act
        result = read_from_file()

    # Assert
    captured = capsys.readouterr()
    assert result is None
    assert "File not found" in captured.out or "error" in captured.out.lower()


def test_read_from_file_with_empty_path(capsys):
    """Test read_from_file with empty path."""
    # Arrange
    with patch("builtins.input", return_value=""):
        # Act
        result = read_from_file()

    # Assert
    captured = capsys.readouterr()
    assert result is None
    assert "No file path" in captured.out


def test_read_from_file_with_empty_file(tmp_path, capsys):
    """Test read_from_file with empty file."""
    # Arrange
    test_file = tmp_path / "empty_file.txt"
    test_file.write_text("")

    with patch("builtins.input", return_value=str(test_file)):
        # Act
        result = read_from_file()

    # Assert
    captured = capsys.readouterr()
    assert result is None
    assert "empty" in captured.out.lower() or "error" in captured.out.lower()


def test_read_from_file_keyboard_interrupt(capsys):
    """Test read_from_file handles KeyboardInterrupt."""
    # Arrange
    with patch("builtins.input", side_effect=KeyboardInterrupt()):
        # Act
        result = read_from_file()

    # Assert
    captured = capsys.readouterr()
    assert result is None
    assert "Cancelled" in captured.out or "warning" in captured.out.lower()


def test_read_multiline_input_with_content(capsys):
    """Test read_multiline_input with content."""
    # Arrange
    prompt_text = "Enter your input:"
    lines = ["Line 1", "Line 2", "Line 3", ""]

    with patch("builtins.input", side_effect=lines):
        # Act
        result = read_multiline_input(prompt_text)

    # Assert
    assert result == "Line 1\nLine 2\nLine 3"


def test_read_multiline_input_empty_input(capsys):
    """Test read_multiline_input with immediate empty line."""
    # Arrange
    prompt_text = "Enter your input:"

    with patch("builtins.input", return_value=""):
        # Act
        result = read_multiline_input(prompt_text)

    # Assert
    assert result == ""


def test_read_multiline_input_keyboard_interrupt(capsys):
    """Test read_multiline_input handles KeyboardInterrupt."""
    # Arrange
    with patch("builtins.input", side_effect=KeyboardInterrupt()):
        # Act
        result = read_multiline_input("Enter text:")

    # Assert
    captured = capsys.readouterr()
    assert result is None
    assert "Cancelled" in captured.out


def test_read_multiline_input_eof_error():
    """Test read_multiline_input handles EOFError."""
    # Arrange
    with patch("builtins.input", side_effect=EOFError()):
        # Act
        result = read_multiline_input("Enter text:")

    # Assert
    assert result == ""


def test_collect_user_input_interactive_with_empty_inputs():
    """Test collect_user_input_interactive with empty strings."""
    # Arrange
    with patch("cli.input_handlers.select_menu", return_value="skip"):
        # Act
        result = collect_user_input_interactive("", "", "")

    # Assert
    assert result == ""


def test_collect_user_input_interactive_cancelled():
    """Test collect_user_input_interactive when user cancels multiline input."""
    # Arrange
    with patch("cli.input_handlers.select_menu", return_value="type"), \
         patch("cli.input_handlers.read_multiline_input", return_value=None):
        # Act
        result = collect_user_input_interactive("Title", "", "")

    # Assert
    assert result is None


def test_read_from_file_with_permission_error(capsys):
    """Test read_from_file with permission error."""
    # Arrange
    with patch("builtins.input", return_value="/root/protected_file.txt"), \
         patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.read_text", side_effect=PermissionError("Access denied")):
        # Act
        result = read_from_file()

    # Assert
    captured = capsys.readouterr()
    assert result is None
    assert "Permission" in captured.out or "error" in captured.out.lower()


def test_read_multiline_input_with_empty_prompt():
    """Test read_multiline_input with empty prompt text."""
    # Arrange
    with patch("builtins.input", return_value=""):
        # Act
        result = read_multiline_input("")

    # Assert
    assert result == ""


def test_read_from_file_exception_handling(capsys):
    """Test read_from_file with general exception."""
    # Arrange
    with patch("builtins.input", return_value="test.txt"), \
         patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.read_text", side_effect=Exception("Unknown error")):
        # Act
        result = read_from_file()

    # Assert
    captured = capsys.readouterr()
    assert result is None
    assert "Error reading file" in captured.out or "error" in captured.out.lower()
