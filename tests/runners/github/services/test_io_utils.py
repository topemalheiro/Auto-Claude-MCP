"""
Tests for I/O Utilities
========================

Tests for runners.github.services.io_utils - Re-exports from core.io_utils
"""

import pytest

from runners.github.services.io_utils import (
    is_pipe_broken,
    reset_pipe_state,
    safe_print,
)


class TestSafePrint:
    """Tests for safe_print function."""

    def test_safe_print_normal_message(self, capsys):
        """Test safe_print with normal message."""
        # Arrange
        message = "Test message"

        # Act
        safe_print(message)

        # Assert
        captured = capsys.readouterr()
        assert message in captured.out
        assert is_pipe_broken() is False

    def test_safe_print_with_flush_false(self, capsys):
        """Test safe_print with flush=False."""
        # Arrange
        message = "Test without flush"

        # Act
        safe_print(message, flush=False)

        # Assert
        captured = capsys.readouterr()
        assert message in captured.out

    def test_safe_print_empty_string(self, capsys):
        """Test safe_print with empty string."""
        # Act & Assert - should not raise
        safe_print("")
        captured = capsys.readouterr()
        assert captured.out == "\n"  # print adds newline

    def test_safe_print_multiple_messages(self, capsys):
        """Test safe_print with multiple messages."""
        # Act
        safe_print("Line 1")
        safe_print("Line 2")
        safe_print("Line 3")

        # Assert
        captured = capsys.readouterr()
        assert "Line 1" in captured.out
        assert "Line 2" in captured.out
        assert "Line 3" in captured.out


class TestIsPipeBroken:
    """Tests for is_pipe_broken function."""

    def test_is_pipe_broken_initial_state(self):
        """Test is_pipe_broken initial state is False."""
        # Reset state first to ensure clean test
        reset_pipe_state()

        # Act & Assert
        assert is_pipe_broken() is False

    def test_is_pipe_broken_after_reset(self):
        """Test is_pipe_broken returns False after reset."""
        # Arrange
        safe_print("test")  # Ensure some activity
        reset_pipe_state()

        # Act & Assert
        assert is_pipe_broken() is False


class TestResetPipeState:
    """Tests for reset_pipe_state function."""

    def test_reset_pipe_state_clears_broken_flag(self):
        """Test reset_pipe_state clears the broken flag."""
        # Arrange - We can't actually break the pipe in tests,
        # but we can verify the function exists and works
        safe_print("test")

        # Act - Should not raise
        reset_pipe_state()

        # Assert
        assert is_pipe_broken() is False

    def test_reset_pipe_state_multiple_calls(self):
        """Test multiple calls to reset_pipe_state."""
        # Act & Assert - Should not raise
        reset_pipe_state()
        reset_pipe_state()
        reset_pipe_state()
        assert is_pipe_broken() is False


class TestModuleExports:
    """Tests for module exports."""

    def test_safe_print_is_callable(self):
        """Test safe_print is exported and callable."""
        assert callable(safe_print)

    def test_is_pipe_broken_is_callable(self):
        """Test is_pipe_broken is exported and callable."""
        assert callable(is_pipe_broken)

    def test_reset_pipe_state_is_callable(self):
        """Test reset_pipe_state is exported and callable."""
        assert callable(reset_pipe_state)

    def test_module_exports_all_expected_functions(self):
        """Test module exports all expected functions."""
        from runners.github.services import io_utils

        expected_exports = ["safe_print", "is_pipe_broken", "reset_pipe_state"]

        for export in expected_exports:
            assert hasattr(io_utils, export)
            assert callable(getattr(io_utils, export))

    def test___all___contains_expected_exports(self):
        """Test __all__ contains expected exports."""
        from runners.github.services.io_utils import __all__

        expected = ["safe_print", "is_pipe_broken", "reset_pipe_state"]
        assert set(__all__) == set(expected)
