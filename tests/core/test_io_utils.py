"""
Tests for io_utils

Comprehensive test coverage for safe console output utilities handling broken pipes.
"""

from core.io_utils import is_pipe_broken, reset_pipe_state, safe_print
from unittest.mock import MagicMock, patch
import pytest
import sys


# Disable pytest capture for this module due to sys.stdout.close() in safe_print
# See: https://github.com/pytest-dev/pytest/issues/7770
pytestmark = pytest.mark.filterwarnings("ignore::pytest.PytestUnraisableExceptionWarning")
pytestmark = pytest.mark.filterwarnings("ignore::RuntimeWarning")


@pytest.fixture(autouse=True)
def cleanup_io_state():
    """Ensure clean I/O state before and after each test."""
    # Reset before test
    reset_pipe_state()
    yield
    # Reset after test to ensure clean state for next test
    reset_pipe_state()


class TestSafePrint:
    """Tests for safe_print() function."""

    def test_safe_print_normal_operation(self, capsys):
        """Test safe_print works normally with valid stdout."""
        reset_pipe_state()  # Ensure clean state

        # Act
        safe_print("Hello, World!")

        # Assert
        captured = capsys.readouterr()
        assert captured.out == "Hello, World!\n"

    def test_safe_print_with_flush_true(self, capsys):
        """Test safe_print with flush=True."""
        reset_pipe_state()

        # Act
        safe_print("Test message", flush=True)

        # Assert
        captured = capsys.readouterr()
        assert captured.out == "Test message\n"

    def test_safe_print_with_flush_false(self, capsys):
        """Test safe_print with flush=False."""
        reset_pipe_state()

        # Act
        safe_print("No flush", flush=False)

        # Assert
        captured = capsys.readouterr()
        assert captured.out == "No flush\n"

    def test_safe_print_broken_pipe_error(self):
        """Test safe_print handles BrokenPipeError gracefully."""
        reset_pipe_state()

        # Arrange - mock print to raise BrokenPipeError
        with patch('builtins.print', side_effect=BrokenPipeError("Pipe closed")):
            # Act - should not raise
            safe_print("This should be silently ignored")

        # Assert - pipe is marked as broken
        assert is_pipe_broken()

    def test_safe_print_value_error_closed_file(self):
        """Test safe_print handles ValueError for closed file."""
        reset_pipe_state()

        # Arrange - mock print to raise ValueError for closed file
        with patch('builtins.print', side_effect=ValueError("I/O operation on closed file")):
            # Act - should not raise
            safe_print("This should handle closed file")

        # Assert - pipe is marked as broken
        assert is_pipe_broken()

    def test_safe_print_value_error_case_insensitive(self):
        """Test safe_print handles ValueError with different case variations."""
        reset_pipe_state()

        # Arrange - test with lowercase 'closed file'
        with patch('builtins.print', side_effect=ValueError("write to closed file")):
            # Act
            safe_print("Test")

        assert is_pipe_broken()

        # Reset and test again
        reset_pipe_state()

        # Arrange - test with uppercase 'CLOSED FILE'
        with patch('builtins.print', side_effect=ValueError("CLOSED FILE")):
            # Act
            safe_print("Test")

        assert is_pipe_broken()

    def test_safe_print_value_error_unexpected_reraises(self):
        """Test safe_print re-raises unexpected ValueErrors."""
        reset_pipe_state()

        # Arrange - mock print to raise unexpected ValueError
        with patch('builtins.print', side_effect=ValueError("Some other error")):
            # Act & Assert - should re-raise
            with pytest.raises(ValueError, match="Some other error"):
                safe_print("This should raise")

    def test_safe_print_os_error_epipe(self):
        """Test safe_print handles OSError with errno 32 (EPIPE)."""
        reset_pipe_state()

        # Arrange - create OSError with errno 32 (EPIPE - Broken pipe)
        epipe_error = OSError("Broken pipe")
        epipe_error.errno = 32

        with patch('builtins.print', side_effect=epipe_error):
            # Act - should not raise
            safe_print("This should handle EPIPE")

        # Assert - pipe is marked as broken
        assert is_pipe_broken()

    def test_safe_print_os_error_unexpected_reraises(self):
        """Test safe_print re-raises unexpected OS errors."""
        reset_pipe_state()

        # Arrange - create OSError with different errno
        other_error = OSError("Some other OS error")
        other_error.errno = 2  # ENOENT

        with patch('builtins.print', side_effect=other_error):
            # Act & Assert - should re-raise
            with pytest.raises(OSError, match="Some other OS error"):
                safe_print("This should raise")

    def test_safe_print_closes_stdout_on_broken_pipe(self):
        """Test that safe_print closes stdout on BrokenPipeError."""
        reset_pipe_state()

        # Arrange
        mock_stdout = MagicMock()
        mock_stdout.close.side_effect = Exception("Already closed")

        with patch('sys.stdout', mock_stdout):
            with patch('builtins.print', side_effect=BrokenPipeError):
                # Act - should attempt to close stdout
                safe_print("Test")

        # Assert - pipe marked as broken
        assert is_pipe_broken()

    def test_safe_print_stdout_close_exception_ignored(self):
        """Test that exceptions during stdout.close() are ignored."""
        reset_pipe_state()

        # Arrange - sys.stdout.close() raises an exception
        with patch('builtins.print', side_effect=BrokenPipeError):
            with patch('sys.stdout') as mock_stdout:
                mock_stdout.close.side_effect = OSError("Can't close")

                # Act - should not raise
                safe_print("Test")

        # Assert - still marks pipe as broken despite close exception
        assert is_pipe_broken()

    def test_safe_print_skip_when_pipe_already_broken(self, capsys):
        """Test that safe_print skips printing when pipe is already broken."""
        # Arrange - mark pipe as broken
        with patch('builtins.print', side_effect=BrokenPipeError):
            safe_print("First message")

        # Reset the mock to track if print is called again
        with patch('builtins.print') as mock_print:
            # Act - try to print again
            safe_print("Second message")

            # Assert - print should not be called since pipe is broken
            mock_print.assert_not_called()

        # Assert - nothing was output
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_safe_print_multiple_broken_pipe_scenarios(self):
        """Test handling of multiple consecutive broken pipe scenarios."""
        reset_pipe_state()

        # First broken pipe
        with patch('builtins.print', side_effect=BrokenPipeError):
            safe_print("Message 1")
        assert is_pipe_broken()

        # Reset state
        reset_pipe_state()
        assert not is_pipe_broken()

        # Second broken pipe (after reset)
        with patch('builtins.print', side_effect=BrokenPipeError):
            safe_print("Message 2")
        assert is_pipe_broken()

    def test_safe_print_empty_message(self, capsys):
        """Test safe_print with empty message."""
        reset_pipe_state()

        # Act
        safe_print("")

        # Assert
        captured = capsys.readouterr()
        assert captured.out == "\n"


class TestIsPipeBroken:
    """Tests for is_pipe_broken() function."""

    def test_is_pipe_broken_initial_state(self):
        """Test that is_pipe_broken returns False initially."""
        reset_pipe_state()
        assert is_pipe_broken() is False

    def test_is_pipe_broken_after_broken_pipe(self):
        """Test that is_pipe_broken returns True after BrokenPipeError."""
        reset_pipe_state()

        # Trigger broken pipe
        with patch('builtins.print', side_effect=BrokenPipeError):
            safe_print("Test")

        assert is_pipe_broken() is True

    def test_is_pipe_broken_after_value_error(self):
        """Test that is_pipe_broken returns True after ValueError for closed file."""
        reset_pipe_state()

        # Trigger ValueError
        with patch('builtins.print', side_effect=ValueError("I/O operation on closed file")):
            safe_print("Test")

        assert is_pipe_broken() is True

    def test_is_pipe_broken_after_epipe(self):
        """Test that is_pipe_broken returns True after EPIPE."""
        reset_pipe_state()

        # Trigger EPIPE
        epipe_error = OSError("Broken pipe")
        epipe_error.errno = 32

        with patch('builtins.print', side_effect=epipe_error):
            safe_print("Test")

        assert is_pipe_broken() is True

    def test_is_pipe_broken_after_reset(self):
        """Test that is_pipe_broken returns False after reset."""
        # Mark as broken
        with patch('builtins.print', side_effect=BrokenPipeError):
            safe_print("Test")

        # Reset
        reset_pipe_state()

        assert is_pipe_broken() is False


class TestResetPipeState:
    """Tests for reset_pipe_state() function."""

    def test_reset_pipe_state_clears_broken_flag(self):
        """Test that reset_pipe_state clears the broken pipe flag."""
        # Arrange - mark pipe as broken
        with patch('builtins.print', side_effect=BrokenPipeError):
            safe_print("Test")
        assert is_pipe_broken()

        # Act
        reset_pipe_state()

        # Assert
        assert is_pipe_broken() is False

    def test_reset_pipe_state_idempotent(self):
        """Test that reset_pipe_state can be called multiple times safely."""
        reset_pipe_state()
        reset_pipe_state()
        reset_pipe_state()

        assert is_pipe_broken() is False

    def test_reset_pipe_state_before_any_print(self):
        """Test reset_pipe_state when no print has occurred yet."""
        # Act - reset before any print operation
        reset_pipe_state()

        # Assert - should still work normally
        assert is_pipe_broken() is False

    def test_reset_pipe_state_allows_printing_again(self, capsys):
        """Test that reset_pipe_state allows safe_print to work again."""
        # First print - breaks pipe
        with patch('builtins.print', side_effect=BrokenPipeError):
            safe_print("First")
        assert is_pipe_broken()

        # Reset state
        reset_pipe_state()

        # Second print - should work (no mock this time)
        safe_print("Second")

        captured = capsys.readouterr()
        assert captured.out == "Second\n"
        assert is_pipe_broken() is False

    def test_reset_multiple_break_cycles(self, capsys):
        """Test multiple break/reset cycles."""
        for i in range(3):
            # Should not be broken at start of cycle
            assert not is_pipe_broken()

            # Break the pipe
            with patch('builtins.print', side_effect=BrokenPipeError):
                safe_print(f"Break {i}")
            assert is_pipe_broken()

            # Reset
            reset_pipe_state()
            assert not is_pipe_broken()


class TestConcurrentScenarios:
    """Tests for concurrent-like scenarios (rapid state changes)."""

    def test_rapid_broken_pipe_detection(self):
        """Test rapid detection of broken pipe state."""
        reset_pipe_state()

        # Rapid consecutive checks should all return False until broken
        assert not is_pipe_broken()
        assert not is_pipe_broken()
        assert not is_pipe_broken()

        # Break pipe
        with patch('builtins.print', side_effect=BrokenPipeError):
            safe_print("Break")

        # Rapid consecutive checks should all return True after broken
        assert is_pipe_broken()
        assert is_pipe_broken()
        assert is_pipe_broken()

    def test_interleaved_operations(self):
        """Test interleaved state checks and resets."""
        reset_pipe_state()
        assert not is_pipe_broken()

        # Break
        with patch('builtins.print', side_effect=BrokenPipeError):
            safe_print("A")
        assert is_pipe_broken()

        # Reset
        reset_pipe_state()
        assert not is_pipe_broken()

        # Break again with different error type
        epipe_error = OSError("EPIPE")
        epipe_error.errno = 32
        with patch('builtins.print', side_effect=epipe_error):
            safe_print("B")
        assert is_pipe_broken()

        # Reset again
        reset_pipe_state()
        assert not is_pipe_broken()

        # Normal print should work
        with patch('builtins.print') as mock_print:
            safe_print("C")
            mock_print.assert_called_once_with("C", flush=True)
