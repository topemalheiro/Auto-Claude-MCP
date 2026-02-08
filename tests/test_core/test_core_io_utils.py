"""
Tests for core.io_utils module
===============================

Comprehensive tests for safe I/O utilities including:
- safe_print with BrokenPipeError handling
- Pipe state tracking (is_pipe_broken, reset_pipe_state)
- OSError handling for EPIPE errors
- ValueError handling for closed file errors
"""

import logging
from unittest.mock import patch

import pytest

from core.io_utils import safe_print, is_pipe_broken, reset_pipe_state


# ============================================================================
# Pipe state management for tests
# ============================================================================


@pytest.fixture(autouse=True)
def reset_io_utils_state():
    """Reset pipe broken state before and after each test."""
    reset_pipe_state()
    yield
    # Only reset if module state allows
    try:
        reset_pipe_state()
    except Exception:
        pass  # Module state may be broken, ignore (no-op)


# ============================================================================
# safe_print tests
# ============================================================================


class TestSafePrint:
    """Tests for safe_print function."""

    def test_safe_print_normal_operation(self, capsys):
        """Test safe_print works normally when pipe is healthy."""
        safe_print("Hello, world!")
        captured = capsys.readouterr()
        assert captured.out == "Hello, world!\n"

    def test_safe_print_with_flush_false(self, capsys):
        """Test safe_print with flush=False."""
        safe_print("No flush", flush=False)
        captured = capsys.readouterr()
        assert captured.out == "No flush\n"

    def test_safe_print_multiline(self, capsys):
        """Test safe_print with multiline message."""
        safe_print("Line 1\nLine 2\nLine 3")
        captured = capsys.readouterr()
        assert "Line 1" in captured.out
        assert "Line 2" in captured.out
        assert "Line 3" in captured.out

    def test_safe_print_empty_string(self, capsys):
        """Test safe_print with empty string."""
        safe_print("")
        captured = capsys.readouterr()
        assert captured.out == "\n"

    def test_safe_print_unicode(self, capsys):
        """Test safe_print with Unicode characters."""
        safe_print("Hello 世界 🌍")
        captured = capsys.readouterr()
        assert "Hello 世界 🌍\n" == captured.out

    def test_safe_print_special_characters(self, capsys):
        """Test safe_print with special characters."""
        safe_print("Tab:\t")
        captured = capsys.readouterr()
        assert "Tab:" in captured.out

    def test_safe_print_skips_after_broken_flag(self, capsys):
        """Test safe_print skips printing when pipe is marked broken."""
        # Simulate broken pipe state by setting the module-level flag
        import core.io_utils
        core.io_utils._pipe_broken = True

        safe_print("This should be skipped")
        captured = capsys.readouterr()
        # Nothing should be printed
        assert captured.out == ""

    def test_safe_print_value_error_closed_file(self, caplog):
        """Test safe_print handles ValueError for closed file."""
        with patch("builtins.print", side_effect=ValueError("I/O operation on closed file")):
            with caplog.at_level(logging.DEBUG):
                safe_print("This should not raise")
                assert is_pipe_broken() is True

        # Check log message
        assert any("output stream" in record.message.lower() for record in caplog.records)

    def test_safe_print_value_error_other(self):
        """Test safe_print re-raises unexpected ValueError."""
        with patch("builtins.print", side_effect=ValueError("Some other error")):
            with pytest.raises(ValueError, match="Some other error"):
                safe_print("This should raise")

    def test_safe_print_os_error_epipe(self, caplog):
        """Test safe_print handles OSError with EPIPE errno."""
        # Create an OSError with errno 32 (EPIPE on some systems)
        epipe_error = OSError(32, "Broken pipe")
        with patch("builtins.print", side_effect=epipe_error):
            with caplog.at_level(logging.DEBUG):
                safe_print("This should not raise")
                assert is_pipe_broken() is True

    def test_safe_print_os_error_other(self):
        """Test safe_print re-raises unexpected OSError."""
        other_error = OSError(2, "No such file or directory")
        with patch("builtins.print", side_effect=other_error):
            with pytest.raises(OSError):
                safe_print("This should raise")

    def test_safe_print_stdout_close_failure(self, caplog):
        """Test safe_print handles stdout.close() failures gracefully."""
        def failing_print(*args, **kwargs):
            raise BrokenPipeError

        with patch("builtins.print", side_effect=failing_print):
            with patch("sys.stdout.close", side_effect=OSError("Close failed")):
                with caplog.at_level(logging.DEBUG):
                    safe_print("Test")
                    # Should not raise despite close() failure
                    assert is_pipe_broken() is True


# ============================================================================
# is_pipe_broken tests
# ============================================================================


class TestIsPipeBroken:
    """Tests for is_pipe_broken function."""

    def test_is_pipe_broken_initially_false(self):
        """Test is_pipe_broken returns False initially."""
        assert is_pipe_broken() is False

    def test_is_pipe_broken_after_setting_flag(self):
        """Test is_pipe_broken returns True when flag is set."""
        import core.io_utils
        core.io_utils._pipe_broken = True
        assert is_pipe_broken() is True

    def test_is_pipe_broken_after_reset(self):
        """Test is_pipe_broken returns False after reset."""
        import core.io_utils
        core.io_utils._pipe_broken = True
        reset_pipe_state()
        assert is_pipe_broken() is False


# ============================================================================
# reset_pipe_state tests
# ============================================================================


class TestResetPipeState:
    """Tests for reset_pipe_state function."""

    def test_reset_pipe_state_when_broken(self):
        """Test reset_pipe_state resets broken pipe flag."""
        import core.io_utils
        core.io_utils._pipe_broken = True
        assert is_pipe_broken() is True

        reset_pipe_state()
        assert is_pipe_broken() is False

    def test_reset_pipe_state_when_healthy(self):
        """Test reset_pipe_state when pipe is already healthy."""
        assert is_pipe_broken() is False
        reset_pipe_state()
        assert is_pipe_broken() is False

    def test_reset_pipe_state_idempotent(self):
        """Test reset_pipe_state can be called multiple times."""
        reset_pipe_state()
        reset_pipe_state()
        reset_pipe_state()
        assert is_pipe_broken() is False


# ============================================================================
# Integration tests
# ============================================================================


class TestSafePrintIntegration:
    """Integration tests for safe_print with various scenarios."""

    def test_multiple_safe_prints(self, capsys):
        """Test multiple prints work correctly."""
        reset_pipe_state()

        safe_print("First")
        safe_print("Second")
        safe_print("Third")

        captured = capsys.readouterr()
        assert "First\n" in captured.out
        assert "Second\n" in captured.out
        assert "Third\n" in captured.out

    def test_safe_print_large_message(self, capsys):
        """Test safe_print with a large message."""
        large_message = "A" * 10000
        safe_print(large_message)

        captured = capsys.readouterr()
        assert len(captured.out) == len(large_message) + 1  # +1 for newline

    def test_safe_print_none_value(self, capsys):
        """Test safe_print with None value (should convert to string)."""
        safe_print(None)
        captured = capsys.readouterr()
        assert "None\n" == captured.out
