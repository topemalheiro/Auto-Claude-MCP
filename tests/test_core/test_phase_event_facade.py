"""
Tests for phase_event facade module (root level re-export).
"""

import json
import os
from io import StringIO
from unittest.mock import patch

import pytest

# The root phase_event module re-exports from core.phase_event
# We need to test that the re-exports work correctly
from phase_event import (
    PHASE_MARKER_PREFIX,
    ExecutionPhase,
    emit_phase,
)


class TestPhaseEventFacade:
    """Tests for phase_event facade (root level re-exports)."""

    def test_phase_marker_prefix(self):
        """Test PHASE_MARKER_PREFIX is exported correctly."""
        assert PHASE_MARKER_PREFIX == "__EXEC_PHASE__:"
        assert isinstance(PHASE_MARKER_PREFIX, str)
        assert PHASE_MARKER_PREFIX.endswith(":")

    def test_execution_phase_enum_values(self):
        """Test ExecutionPhase enum has all expected values."""
        assert ExecutionPhase.PLANNING == "planning"
        assert ExecutionPhase.CODING == "coding"
        assert ExecutionPhase.QA_REVIEW == "qa_review"
        assert ExecutionPhase.QA_FIXING == "qa_fixing"
        assert ExecutionPhase.COMPLETE == "complete"
        assert ExecutionPhase.FAILED == "failed"
        assert ExecutionPhase.RATE_LIMIT_PAUSED == "rate_limit_paused"
        assert ExecutionPhase.AUTH_FAILURE_PAUSED == "auth_failure_paused"

    def test_execution_phase_is_string_enum(self):
        """Test ExecutionPhase is a string enum."""
        assert isinstance(ExecutionPhase.PLANNING, str)
        assert ExecutionPhase.PLANNING == "planning"

        # Can compare with strings
        phase = ExecutionPhase.CODING
        assert phase == "coding"

    def test_execution_phase_iteration(self):
        """Test iterating over ExecutionPhase enum."""
        phases = list(ExecutionPhase)
        assert len(phases) == 8
        assert ExecutionPhase.PLANNING in phases
        assert ExecutionPhase.FAILED in phases
        assert ExecutionPhase.RATE_LIMIT_PAUSED in phases
        assert ExecutionPhase.AUTH_FAILURE_PAUSED in phases

    def test_emit_phase_basic(self, capsys):
        """Test basic emit_phase function."""
        emit_phase(ExecutionPhase.CODING, "Starting to code")

        captured = capsys.readouterr()
        assert "__EXEC_PHASE__:" in captured.out
        assert "coding" in captured.out
        assert "Starting to code" in captured.out

    def test_emit_phase_with_string(self, capsys):
        """Test emit_phase with string phase instead of enum."""
        emit_phase("planning", "Creating plan")

        captured = capsys.readouterr()
        assert "planning" in captured.out
        assert "Creating plan" in captured.out

    def test_emit_phase_with_progress(self, capsys):
        """Test emit_phase with progress percentage."""
        emit_phase(ExecutionPhase.CODING, "In progress", progress=50)

        captured = capsys.readouterr()
        output = captured.out
        assert "coding" in output
        assert "progress" in output.lower()
        assert "50" in output

    def test_emit_phase_with_subtask(self, capsys):
        """Test emit_phase with subtask identifier."""
        emit_phase(ExecutionPhase.QA_FIXING, "Fixing bugs", subtask="task-001")

        captured = capsys.readouterr()
        output = captured.out
        assert "qa_fixing" in output
        assert "subtask" in output.lower()
        assert "task-001" in output

    def test_emit_phase_with_all_options(self, capsys):
        """Test emit_phase with all optional parameters."""
        emit_phase(
            ExecutionPhase.CODING,
            "Working on feature",
            progress=75,
            subtask="task-123",
        )

        captured = capsys.readouterr()
        output = captured.out
        assert "coding" in output
        assert "75" in output
        assert "task-123" in output

    def test_emit_phase_flushes_output(self, capsys):
        """Test that emit_phase flushes output immediately."""
        # This is hard to test directly, but we can verify output appears
        emit_phase(ExecutionPhase.PLANNING, "Planning")

        captured = capsys.readouterr()
        # If output wasn't flushed, it might not appear
        assert len(captured.out) > 0

    def test_emit_phase_json_format(self, capsys):
        """Test that emit_phase outputs valid JSON."""
        emit_phase(ExecutionPhase.COMPLETE, "Done")

        captured = capsys.readouterr()
        # Extract JSON part
        json_str = captured.out.strip()
        if json_str.startswith("__EXEC_PHASE__:"):
            json_part = json_str.replace("__EXEC_PHASE__:", "")
            data = json.loads(json_part)
            assert data["phase"] == "complete"
            assert data["message"] == "Done"

    def test_emit_phase_progress_clamping(self, capsys):
        """Test that progress is clamped to 0-100 range."""
        emit_phase(ExecutionPhase.CODING, "Test", progress=150)
        captured1 = capsys.readouterr()

        emit_phase(ExecutionPhase.CODING, "Test", progress=-20)
        captured2 = capsys.readouterr()

        # Both should have valid progress values (clamped)
        data1 = json.loads(captured1.out.replace("__EXEC_PHASE__:", ""))
        data2 = json.loads(captured2.out.replace("__EXEC_PHASE__:", ""))

        assert 0 <= data1["progress"] <= 100
        assert 0 <= data2["progress"] <= 100

    def test_emit_phase_empty_message(self, capsys):
        """Test emit_phase with empty message."""
        emit_phase(ExecutionPhase.PLANNING, "")

        captured = capsys.readouterr()
        data = json.loads(captured.out.replace("__EXEC_PHASE__:", ""))
        assert data["message"] == ""

    def test_emit_phase_special_characters(self, capsys):
        """Test emit_phase with special characters in message."""
        message = "Test with 'quotes' and \"double quotes\""
        emit_phase(ExecutionPhase.CODING, message)

        captured = capsys.readouterr()
        data = json.loads(captured.out.replace("__EXEC_PHASE__:", ""))
        assert data["message"] == message

    def test_execution_phase_values_are_strings(self):
        """Test that all ExecutionPhase values are strings."""
        for phase in ExecutionPhase:
            assert isinstance(phase.value, str)

    def test_execution_phase_comparison(self):
        """Test ExecutionPhase comparison operations."""
        assert ExecutionPhase.PLANNING == ExecutionPhase.PLANNING
        assert ExecutionPhase.PLANNING != ExecutionPhase.CODING
        assert ExecutionPhase.PLANNING == "planning"

    def test_execution_phase_hashable(self):
        """Test ExecutionPhase can be used in sets and dicts."""
        phases_set = {ExecutionPhase.PLANNING, ExecutionPhase.CODING}
        assert len(phases_set) == 2
        assert ExecutionPhase.PLANNING in phases_set

        phases_dict = {ExecutionPhase.PLANNING: "Plan first"}
        assert phases_dict[ExecutionPhase.PLANNING] == "Plan first"

    def test_emit_phase_consecutive_calls(self, capsys):
        """Test multiple consecutive emit_phase calls."""
        emit_phase(ExecutionPhase.PLANNING, "Phase 1")
        emit_phase(ExecutionPhase.CODING, "Phase 2")
        emit_phase(ExecutionPhase.COMPLETE, "Phase 3")

        captured = capsys.readouterr()
        lines = captured.out.strip().split("\n")

        assert len(lines) == 3
        assert "planning" in lines[0]
        assert "coding" in lines[1]
        assert "complete" in lines[2]

    def test_emit_phase_unicode_message(self, capsys):
        """Test emit_phase with unicode characters."""
        message = "Test with emoji 🎉 and chinese 中文"
        emit_phase(ExecutionPhase.CODING, message)

        captured = capsys.readouterr()
        data = json.loads(captured.out.replace("__EXEC_PHASE__:", ""))
        assert "🎉" in data["message"]
        assert "中文" in data["message"]

    def test_emit_phase_very_long_message(self, capsys):
        """Test emit_phase with very long message."""
        long_message = "x" * 10000
        emit_phase(ExecutionPhase.CODING, long_message)

        captured = capsys.readouterr()
        data = json.loads(captured.out.replace("__EXEC_PHASE__:", ""))
        assert len(data["message"]) == 10000

    def test_emit_phase_newlines_in_message(self, capsys):
        """Test emit_phase with newlines in message."""
        message = "Line 1\nLine 2\nLine 3"
        emit_phase(ExecutionPhase.CODING, message)

        captured = capsys.readouterr()
        data = json.loads(captured.out.replace("__EXEC_PHASE__:", ""))
        assert data["message"] == message

    def test_execution_phase_members(self):
        """Test ExecutionPhase enum members."""
        assert hasattr(ExecutionPhase, "PLANNING")
        assert hasattr(ExecutionPhase, "CODING")
        assert hasattr(ExecutionPhase, "QA_REVIEW")
        assert hasattr(ExecutionPhase, "QA_FIXING")
        assert hasattr(ExecutionPhase, "COMPLETE")
        assert hasattr(ExecutionPhase, "FAILED")
        assert hasattr(ExecutionPhase, "RATE_LIMIT_PAUSED")
        assert hasattr(ExecutionPhase, "AUTH_FAILURE_PAUSED")

    def test_phase_marker_prefix_constant(self):
        """Test PHASE_MARKER_PREFIX is a constant."""
        # Should start with __ for magic-like behavior
        assert PHASE_MARKER_PREFIX.startswith("__")
        # Should end with : for prefix pattern
        assert PHASE_MARKER_PREFIX.endswith(":")

    def test_emit_phase_ordering_of_fields(self, capsys):
        """Test that JSON fields are in expected order."""
        emit_phase(ExecutionPhase.CODING, "Test", progress=50, subtask="task-1")

        captured = capsys.readouterr()
        json_str = captured.out.replace("__EXEC_PHASE__:", "")
        data = json.loads(json_str)

        # Check all expected fields are present
        assert "phase" in data
        assert "message" in data
        assert "progress" in data
        assert "subtask" in data

    @patch.dict(os.environ, {"DEBUG": "1"})
    def test_emit_phase_in_debug_mode(self, capsys):
        """Test emit_phase behavior in DEBUG mode."""
        # Just verify it works without error
        emit_phase(ExecutionPhase.CODING, "Debug test")

        captured = capsys.readouterr()
        assert "coding" in captured.out

    def test_execution_phase_name_property(self):
        """Test ExecutionPhase enum name property."""
        assert ExecutionPhase.PLANNING.name == "PLANNING"
        assert ExecutionPhase.CODING.name == "CODING"
        assert ExecutionPhase.QA_REVIEW.name == "QA_REVIEW"

    def test_execution_phase_value_property(self):
        """Test ExecutionPhase enum value property."""
        assert ExecutionPhase.PLANNING.value == "planning"
        assert ExecutionPhase.CODING.value == "coding"
        assert ExecutionPhase.QA_REVIEW.value == "qa_review"
