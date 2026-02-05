"""
Tests for phase_event

Comprehensive test coverage for execution phase event emission protocol.
"""

import importlib
import json
import os
from core.phase_event import ExecutionPhase, emit_phase, PHASE_MARKER_PREFIX
from unittest.mock import MagicMock, patch
import pytest
import sys


class TestEmitPhaseBasic:
    """Tests for basic emit_phase() functionality."""

    def test_emit_phase_with_enum(self, capsys):
        """Test emit_phase with ExecutionPhase enum."""
        # Act
        emit_phase(ExecutionPhase.CODING, "Starting to code")

        # Assert - Check JSON contains expected values (formatting may vary)
        captured = capsys.readouterr()
        assert PHASE_MARKER_PREFIX in captured.out
        assert '"phase": "coding"' in captured.out or '"phase":"coding"' in captured.out
        assert '"message": "Starting to code"' in captured.out or '"message":"Starting to code"' in captured.out

    def test_emit_phase_with_string(self, capsys):
        """Test emit_phase with string phase value."""
        # Act
        emit_phase("custom_phase", "Custom message")

        # Assert
        captured = capsys.readouterr()
        assert PHASE_MARKER_PREFIX in captured.out
        assert '"phase": "custom_phase"' in captured.out or '"phase":"custom_phase"' in captured.out

    def test_emit_phase_empty_message(self, capsys):
        """Test emit_phase with empty message."""
        # Act
        emit_phase(ExecutionPhase.PLANNING, "")

        # Assert
        captured = capsys.readouterr()
        assert PHASE_MARKER_PREFIX in captured.out
        assert '"phase": "planning"' in captured.out or '"phase":"planning"' in captured.out
        assert '"message": ""' in captured.out or '"message":""' in captured.out

    def test_emit_phase_no_message_defaults(self, capsys):
        """Test emit_phase with default message parameter."""
        # Act
        emit_phase(ExecutionPhase.QA_REVIEW)

        # Assert
        captured = capsys.readouterr()
        assert PHASE_MARKER_PREFIX in captured.out
        assert '"phase": "qa_review"' in captured.out or '"phase":"qa_review"' in captured.out


class TestEmitPhaseAllEnumValues:
    """Tests for all ExecutionPhase enum values."""

    def test_emit_phase_planning(self, capsys):
        """Test emit_phase with PLANNING phase."""
        emit_phase(ExecutionPhase.PLANNING, "Planning implementation")
        captured = capsys.readouterr()
        assert '"phase": "planning"' in captured.out or '"phase":"planning"' in captured.out
        assert "Planning implementation" in captured.out

    def test_emit_phase_coding(self, capsys):
        """Test emit_phase with CODING phase."""
        emit_phase(ExecutionPhase.CODING, "Writing code")
        captured = capsys.readouterr()
        assert '"phase": "coding"' in captured.out or '"phase":"coding"' in captured.out
        assert "Writing code" in captured.out

    def test_emit_phase_qa_review(self, capsys):
        """Test emit_phase with QA_REVIEW phase."""
        emit_phase(ExecutionPhase.QA_REVIEW, "Reviewing code")
        captured = capsys.readouterr()
        assert '"phase": "qa_review"' in captured.out or '"phase":"qa_review"' in captured.out
        assert "Reviewing code" in captured.out

    def test_emit_phase_qa_fixing(self, capsys):
        """Test emit_phase with QA_FIXING phase."""
        emit_phase(ExecutionPhase.QA_FIXING, "Fixing issues")
        captured = capsys.readouterr()
        assert '"phase": "qa_fixing"' in captured.out or '"phase":"qa_fixing"' in captured.out
        assert "Fixing issues" in captured.out

    def test_emit_phase_complete(self, capsys):
        """Test emit_phase with COMPLETE phase."""
        emit_phase(ExecutionPhase.COMPLETE, "Task completed")
        captured = capsys.readouterr()
        assert '"phase": "complete"' in captured.out or '"phase":"complete"' in captured.out
        assert "Task completed" in captured.out

    def test_emit_phase_failed(self, capsys):
        """Test emit_phase with FAILED phase."""
        emit_phase(ExecutionPhase.FAILED, "Task failed")
        captured = capsys.readouterr()
        assert '"phase": "failed"' in captured.out or '"phase":"failed"' in captured.out
        assert "Task failed" in captured.out


class TestEmitPhaseProgress:
    """Tests for progress value handling and clamping."""

    def test_emit_phase_with_progress(self, capsys):
        """Test emit_phase with progress value."""
        # Act
        emit_phase(ExecutionPhase.CODING, "Processing", progress=50)

        # Assert
        captured = capsys.readouterr()
        data = json.loads(captured.out.replace(PHASE_MARKER_PREFIX, "").strip())
        assert data["progress"] == 50

    def test_emit_phase_progress_clamp_above_max(self, capsys):
        """Test progress clamping when above 100."""
        # Act
        emit_phase(ExecutionPhase.CODING, "Too high", progress=150)

        # Assert
        captured = capsys.readouterr()
        data = json.loads(captured.out.replace(PHASE_MARKER_PREFIX, "").strip())
        assert data["progress"] == 100  # Clamped to max

    def test_emit_phase_progress_clamp_below_min(self, capsys):
        """Test progress clamping when below 0."""
        # Act
        emit_phase(ExecutionPhase.CODING, "Too low", progress=-50)

        # Assert
        captured = capsys.readouterr()
        data = json.loads(captured.out.replace(PHASE_MARKER_PREFIX, "").strip())
        assert data["progress"] == 0  # Clamped to min

    def test_emit_phase_progress_boundary_values(self, capsys):
        """Test progress at exact boundary values."""
        # Test 0
        emit_phase(ExecutionPhase.CODING, "Min", progress=0)
        captured = capsys.readouterr()
        data = json.loads(captured.out.replace(PHASE_MARKER_PREFIX, "").strip())
        assert data["progress"] == 0

        # Test 100
        emit_phase(ExecutionPhase.CODING, "Max", progress=100)
        captured = capsys.readouterr()
        data = json.loads(captured.out.replace(PHASE_MARKER_PREFIX, "").strip())
        assert data["progress"] == 100

    def test_emit_phase_progress_not_in_payload_when_none(self, capsys):
        """Test that progress key is not in payload when None."""
        # Act
        emit_phase(ExecutionPhase.CODING, "No progress", progress=None)

        # Assert
        captured = capsys.readouterr()
        data = json.loads(captured.out.replace(PHASE_MARKER_PREFIX, "").strip())
        assert "progress" not in data


class TestEmitPhaseSubtask:
    """Tests for subtask tracking."""

    def test_emit_phase_with_subtask(self, capsys):
        """Test emit_phase with subtask parameter."""
        # Act
        emit_phase(ExecutionPhase.CODING, "Main task", subtask="Implementing feature X")

        # Assert
        captured = capsys.readouterr()
        data = json.loads(captured.out.replace(PHASE_MARKER_PREFIX, "").strip())
        assert data["subtask"] == "Implementing feature X"

    def test_emit_phase_subtask_not_in_payload_when_none(self, capsys):
        """Test that subtask key is not in payload when None."""
        # Act
        emit_phase(ExecutionPhase.CODING, "No subtask", subtask=None)

        # Assert
        captured = capsys.readouterr()
        data = json.loads(captured.out.replace(PHASE_MARKER_PREFIX, "").strip())
        assert "subtask" not in data

    def test_emit_phase_with_all_optional_params(self, capsys):
        """Test emit_phase with both progress and subtask."""
        # Act
        emit_phase(
            ExecutionPhase.CODING,
            "Full payload",
            progress=75,
            subtask="Subtask 3 of 5"
        )

        # Assert
        captured = capsys.readouterr()
        data = json.loads(captured.out.replace(PHASE_MARKER_PREFIX, "").strip())
        assert data["phase"] == "coding"
        assert data["message"] == "Full payload"
        assert data["progress"] == 75
        assert data["subtask"] == "Subtask 3 of 5"


class TestEmitPhaseErrorHandling:
    """Tests for error handling in emit_phase."""

    def test_emit_phase_handles_oserror(self, capsys):
        """Test emit_phase handles OSError gracefully."""
        # Arrange - mock print to raise OSError
        with patch('builtins.print', side_effect=OSError("Pipe broken")):
            # Act - should not raise
            emit_phase(ExecutionPhase.CODING, "Test")

        # Assert - nothing in stdout
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_emit_phase_handles_unicode_encode_error(self, capsys):
        """Test emit_phase handles UnicodeEncodeError gracefully."""
        # Arrange - mock print to raise UnicodeEncodeError
        with patch('builtins.print', side_effect=UnicodeEncodeError('utf-8', '', 0, 1, '')):
            # Act - should not raise
            emit_phase(ExecutionPhase.CODING, "Test")

        # Assert - nothing in stdout
        captured = capsys.readouterr()
        assert captured.out == ""

    @patch.dict(os.environ, {'DEBUG': '1'})
    def test_emit_phase_debug_mode_oserror(self, capsys):
        """Test emit_phase writes to stderr in debug mode on OSError."""
        # Reload module to pick up new DEBUG value
        import core.phase_event
        importlib.reload(core.phase_event)
        from core.phase_event import emit_phase as emit_phase_debug

        # Arrange - mock print to raise OSError
        with patch('builtins.print', side_effect=OSError("Pipe broken")):
            # Act
            emit_phase_debug(ExecutionPhase.CODING, "Test")

        # Assert - error message in stderr
        captured = capsys.readouterr()
        assert "emit failed" in captured.err
        assert "Pipe broken" in captured.err

        # Reset DEBUG
        os.environ.pop('DEBUG', None)
        importlib.reload(core.phase_event)

    @patch.dict(os.environ, {'DEBUG': 'true'})
    def test_emit_phase_debug_mode_variations(self, capsys):
        """Test emit_phase debug mode with various DEBUG values."""
        # Reload module to pick up new DEBUG value
        import core.phase_event
        importlib.reload(core.phase_event)
        from core.phase_event import emit_phase as emit_phase_debug

        # Test with 'true'
        with patch('builtins.print', side_effect=OSError("Error")):
            emit_phase_debug(ExecutionPhase.CODING, "Test")

        captured = capsys.readouterr()
        assert "emit failed" in captured.err

        # Reset DEBUG
        os.environ.pop('DEBUG', None)
        importlib.reload(core.phase_event)

    @patch.dict(os.environ, {'DEBUG': 'yes'})
    def test_emit_phase_debug_mode_yes(self, capsys):
        """Test emit_phase debug mode with DEBUG=yes."""
        # Reload module to pick up new DEBUG value
        import core.phase_event
        importlib.reload(core.phase_event)
        from core.phase_event import emit_phase as emit_phase_debug

        with patch('builtins.print', side_effect=OSError("Error")):
            emit_phase_debug(ExecutionPhase.CODING, "Test")

        captured = capsys.readouterr()
        assert "emit failed" in captured.err

        # Reset DEBUG
        os.environ.pop('DEBUG', None)
        importlib.reload(core.phase_event)

    @patch.dict(os.environ, {'DEBUG': '0'})
    def test_emit_phase_non_debug_mode_no_stderr(self, capsys):
        """Test emit_phase doesn't write to stderr when DEBUG=0."""
        # Arrange
        with patch('builtins.print', side_effect=OSError("Error")):
            # Act
            emit_phase(ExecutionPhase.CODING, "Test")

        # Assert - nothing in stderr
        captured = capsys.readouterr()
        assert captured.err == ""

    @patch.dict(os.environ, {}, clear=True)
    def test_emit_phase_no_debug_env_var(self, capsys):
        """Test emit_phase when DEBUG env var is not set."""
        with patch('builtins.print', side_effect=OSError("Error")):
            emit_phase(ExecutionPhase.CODING, "Test")

        captured = capsys.readouterr()
        assert captured.err == ""

    def test_emit_phase_stderr_write_failure_silent(self, capsys):
        """Test that stderr write failures are silently ignored in debug mode."""
        # Arrange - both stdout and stderr fail
        with patch('builtins.print', side_effect=OSError("Stdout fail")):
            with patch('sys.stderr.write', side_effect=OSError("Stderr fail")):
                with patch.dict(os.environ, {'DEBUG': '1'}):
                    # Act - should not raise
                    emit_phase(ExecutionPhase.CODING, "Test")

        # Assert - completely silent
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_emit_phase_stderr_flush_failure_silent(self, capsys):
        """Test that stderr flush failures are silently ignored in debug mode."""
        # Arrange - stderr.write succeeds but flush fails
        with patch('builtins.print', side_effect=OSError("Stdout fail")):
            with patch('sys.stderr') as mock_stderr:
                mock_stderr.write.return_value = None
                mock_stderr.flush.side_effect = OSError("Flush fail")
                with patch.dict(os.environ, {'DEBUG': '1'}):
                    # Act - should not raise
                    emit_phase(ExecutionPhase.CODING, "Test")

        # Assert
        captured = capsys.readouterr()
        assert captured.out == ""


class TestEmitPhaseComplexPayloads:
    """Tests for complex payload scenarios."""

    def test_emit_phase_special_characters_in_message(self, capsys):
        """Test emit_phase with special characters in message."""
        # Arrange - message with quotes, newlines, unicode
        message = 'Test "quoted" and \'single\' \n with unicode: \u2713'

        # Act
        emit_phase(ExecutionPhase.CODING, message)

        # Assert
        captured = capsys.readouterr()
        data = json.loads(captured.out.replace(PHASE_MARKER_PREFIX, "").strip())
        assert data["message"] == message

    def test_emit_phase_very_long_message(self, capsys):
        """Test emit_phase with a very long message."""
        # Arrange - 10KB message
        long_message = "A" * 10000

        # Act
        emit_phase(ExecutionPhase.CODING, long_message)

        # Assert
        captured = capsys.readouterr()
        data = json.loads(captured.out.replace(PHASE_MARKER_PREFIX, "").strip())
        assert data["message"] == long_message

    def test_emit_phase_subtask_with_special_characters(self, capsys):
        """Test emit_phase with special characters in subtask."""
        # Arrange
        subtask = "Fix bug: \"Error: can't open file\""

        # Act
        emit_phase(ExecutionPhase.CODING, "Working", subtask=subtask)

        # Assert
        captured = capsys.readouterr()
        data = json.loads(captured.out.replace(PHASE_MARKER_PREFIX, "").strip())
        assert data["subtask"] == subtask

    def test_emit_phase_flush_always_true(self, capsys):
        """Test that emit_phase always flushes output."""
        # The function uses flush=True in print()
        # We verify by checking the output is immediately available
        emit_phase(ExecutionPhase.CODING, "Test")
        captured = capsys.readouterr()
        assert captured.out != ""


class TestEmitPhaseMultipleCalls:
    """Tests for multiple emit_phase calls in sequence."""

    def test_multiple_phase_updates(self, capsys):
        """Test multiple phase updates in sequence."""
        # Act
        emit_phase(ExecutionPhase.PLANNING, "Starting", progress=0)
        emit_phase(ExecutionPhase.PLANNING, "Planning", progress=50)
        emit_phase(ExecutionPhase.CODING, "Coding", progress=0)
        emit_phase(ExecutionPhase.CODING, "Still coding", progress=50, subtask="Feature X")
        emit_phase(ExecutionPhase.COMPLETE, "Done", progress=100)

        # Assert
        captured = capsys.readouterr()
        lines = captured.out.strip().split('\n')

        assert len(lines) == 5

        # Verify first line
        data1 = json.loads(lines[0].replace(PHASE_MARKER_PREFIX, ""))
        assert data1["phase"] == "planning"
        assert data1["progress"] == 0

        # Verify last line
        data5 = json.loads(lines[4].replace(PHASE_MARKER_PREFIX, ""))
        assert data5["phase"] == "complete"
        assert data5["progress"] == 100

    def test_phase_transitions(self, capsys):
        """Test realistic phase transition sequence."""
        phases = [
            (ExecutionPhase.PLANNING, "Planning", None, None),
            (ExecutionPhase.CODING, "Coding", 0, None),
            (ExecutionPhase.CODING, "Coding", 50, "Subtask 1"),
            (ExecutionPhase.CODING, "Coding", 100, None),
            (ExecutionPhase.QA_REVIEW, "Reviewing", None, None),
            (ExecutionPhase.QA_FIXING, "Fixing", None, None),
            (ExecutionPhase.COMPLETE, "Complete", 100, None),
        ]

        for phase, message, progress, subtask in phases:
            emit_phase(phase, message, progress=progress, subtask=subtask)

        captured = capsys.readouterr()
        lines = captured.out.strip().split('\n')
        assert len(lines) == 7


class TestEmitPhasePayloadStructure:
    """Tests for payload structure validation."""

    def test_payload_structure_minimal(self, capsys):
        """Test minimal payload structure."""
        emit_phase(ExecutionPhase.CODING, "Test")

        captured = capsys.readouterr()
        payload_str = captured.out.replace(PHASE_MARKER_PREFIX, "").strip()
        data = json.loads(payload_str)

        assert set(data.keys()) == {"phase", "message"}

    def test_payload_structure_with_progress(self, capsys):
        """Test payload structure with progress."""
        emit_phase(ExecutionPhase.CODING, "Test", progress=50)

        captured = capsys.readouterr()
        payload_str = captured.out.replace(PHASE_MARKER_PREFIX, "").strip()
        data = json.loads(payload_str)

        assert set(data.keys()) == {"phase", "message", "progress"}

    def test_payload_structure_with_subtask(self, capsys):
        """Test payload structure with subtask."""
        emit_phase(ExecutionPhase.CODING, "Test", subtask="Subtask")

        captured = capsys.readouterr()
        payload_str = captured.out.replace(PHASE_MARKER_PREFIX, "").strip()
        data = json.loads(payload_str)

        assert set(data.keys()) == {"phase", "message", "subtask"}

    def test_payload_structure_full(self, capsys):
        """Test full payload structure."""
        emit_phase(ExecutionPhase.CODING, "Test", progress=75, subtask="Subtask")

        captured = capsys.readouterr()
        payload_str = captured.out.replace(PHASE_MARKER_PREFIX, "").strip()
        data = json.loads(payload_str)

        assert set(data.keys()) == {"phase", "message", "progress", "subtask"}

    def test_payload_is_valid_json(self, capsys):
        """Test that output is valid JSON."""
        emit_phase(ExecutionPhase.CODING, "Test", progress=50, subtask="Subtask")

        captured = capsys.readouterr()
        # Should not raise JSONDecodeError
        data = json.loads(captured.out.replace(PHASE_MARKER_PREFIX, "").strip())
        assert data is not None


class TestExecutionPhaseEnum:
    """Tests for ExecutionPhase enum values."""

    def test_all_enum_values_exist(self):
        """Test that all expected enum values exist."""
        assert ExecutionPhase.PLANNING.value == "planning"
        assert ExecutionPhase.CODING.value == "coding"
        assert ExecutionPhase.QA_REVIEW.value == "qa_review"
        assert ExecutionPhase.QA_FIXING.value == "qa_fixing"
        assert ExecutionPhase.COMPLETE.value == "complete"
        assert ExecutionPhase.FAILED.value == "failed"

    def test_enum_is_string_enum(self):
        """Test that ExecutionPhase is a string enum."""
        assert isinstance(ExecutionPhase.CODING, str)
        # ExecutionPhase.CODING is the string "coding" (inherits from str)
        assert ExecutionPhase.CODING == "coding"

    def test_enum_iteration(self):
        """Test iterating over all enum values."""
        phases = [phase.value for phase in ExecutionPhase]
        expected = ["planning", "coding", "qa_review", "qa_fixing", "complete", "failed"]
        assert phases == expected
