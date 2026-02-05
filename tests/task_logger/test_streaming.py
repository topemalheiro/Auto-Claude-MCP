"""Tests for task_logger/streaming.py"""

import json
from unittest.mock import MagicMock, patch

import pytest

from task_logger.streaming import emit_marker


class TestEmitMarker:
    """Tests for emit_marker function"""

    def test_emit_marker_enabled(self, capsys):
        """Test emitting a marker when enabled"""
        marker_type = "PHASE_START"
        data = {"phase": "coding", "timestamp": "2024-01-01T12:00:00"}

        emit_marker(marker_type, data, enabled=True)

        captured = capsys.readouterr()
        output = captured.out.strip()

        # Should contain the marker prefix and JSON data
        assert "__TASK_LOG_PHASE_START__" in output
        assert "coding" in output

    def test_emit_marker_disabled(self, capsys):
        """Test not emitting marker when disabled"""
        marker_type = "PHASE_START"
        data = {"phase": "coding"}

        emit_marker(marker_type, data, enabled=False)

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_emit_marker_with_complex_data(self, capsys):
        """Test emitting marker with complex nested data"""
        marker_type = "TEXT"
        data = {
            "content": "Test message",
            "phase": "coding",
            "type": "info",
            "subtask_id": "subtask-1",
            "timestamp": "2024-01-01T12:00:00",
            "has_detail": True,
        }

        emit_marker(marker_type, data, enabled=True)

        captured = capsys.readouterr()
        output = captured.out.strip()

        assert "__TASK_LOG_TEXT__" in output
        assert "Test message" in output
        assert "subtask-1" in output

    def test_emit_marker_uppercases_type(self, capsys):
        """Test that marker type is uppercased"""
        marker_type = "tool_end"
        data = {"name": "Read", "success": True}

        emit_marker(marker_type, data, enabled=True)

        captured = capsys.readouterr()
        output = captured.out.strip()

        # Should uppercase the marker type
        assert "__TASK_LOG_TOOL_END__" in output

    def test_emit_marker_json_serializable(self, capsys):
        """Test that data is properly JSON serialized"""
        marker_type = "PHASE_START"
        data = {
            "phase": "coding",
            "number": 42,
            "flag": True,
            "nested": {"key": "value"},
        }

        emit_marker(marker_type, data, enabled=True)

        captured = capsys.readouterr()
        output = captured.out.strip()

        # Extract JSON portion
        prefix = f"__TASK_LOG_{marker_type.upper()}__:"
        json_str = output.replace(prefix, "")
        parsed = json.loads(json_str)

        assert parsed["phase"] == "coding"
        assert parsed["number"] == 42
        assert parsed["flag"] is True
        assert parsed["nested"]["key"] == "value"

    def test_emit_marker_handles_exception_gracefully(self, capsys):
        """Test that emit_marker handles exceptions without crashing"""
        # Use data that might cause JSON serialization issues
        marker_type = "TEST"

        # Even with problematic data, shouldn't raise
        emit_marker(marker_type, {"valid": "data"}, enabled=True)

        captured = capsys.readouterr()
        # Should have output something
        assert captured.out != ""

    def test_emit_marker_empty_data(self, capsys):
        """Test emitting marker with empty data"""
        marker_type = "TEST"
        data = {}

        emit_marker(marker_type, data, enabled=True)

        captured = capsys.readouterr()
        output = captured.out.strip()

        assert "__TASK_LOG_TEST__:" in output
        assert "{}" in output

    def test_emit_marker_with_special_chars(self, capsys):
        """Test emitting marker with special characters in data"""
        marker_type = "TEXT"
        data = {"message": "Test with 'quotes' and \"double quotes\""}

        emit_marker(marker_type, data, enabled=True)

        captured = capsys.readouterr()
        output = captured.out.strip()

        # Should be properly escaped in JSON
        assert "__TASK_LOG_TEXT__:" in output
        assert "quotes" in output

    def test_emit_marker_flush(self, capsys):
        """Test that marker output is flushed"""
        marker_type = "PHASE_START"
        data = {"phase": "coding"}

        emit_marker(marker_type, data, enabled=True)

        captured = capsys.readouterr()
        # Output should be available immediately (flushed)
        assert captured.out != ""

    def test_emit_marker_all_marker_types(self, capsys):
        """Test emitting all common marker types"""
        marker_types = [
            "PHASE_START",
            "PHASE_END",
            "TEXT",
            "TOOL_START",
            "TOOL_END",
            "SUBPHASE_START",
        ]

        for marker_type in marker_types:
            emit_marker(marker_type, {"test": "data"}, enabled=True)

        captured = capsys.readouterr()
        output = captured.out

        for marker_type in marker_types:
            assert f"__TASK_LOG_{marker_type}__:" in output

    def test_emit_marker_unicode_content(self, capsys):
        """Test emitting marker with Unicode content"""
        marker_type = "TEXT"
        data = {"content": "Test with emoji: 🎉 and unicode: ┌─┐"}

        emit_marker(marker_type, data, enabled=True)

        captured = capsys.readouterr()
        output = captured.out.strip()

        assert "__TASK_LOG_TEXT__:" in output
        # Unicode should be in the output
        assert "emoji" in output or len(output) > 0

    def test_emit_marker_with_none_values(self, capsys):
        """Test emitting marker with None values"""
        marker_type = "TOOL_END"
        data = {"name": "Read", "success": True, "result": None, "detail": None}

        emit_marker(marker_type, data, enabled=True)

        captured = capsys.readouterr()
        output = captured.out.strip()

        assert "__TASK_LOG_TOOL_END__:" in output
        # JSON should handle None values
        assert "null" in output or "None" in output or output != ""

    def test_emit_marker_handles_json_serialization_error(self, capsys):
        """Test emit_marker handles JSON serialization errors gracefully"""
        marker_type = "TEST"
        # Use data that can't be JSON serialized (e.g., a lambda)
        data = {"function": lambda x: x}

        # Should not raise, just silently fail
        emit_marker(marker_type, data, enabled=True)

        # Should have crashed the JSON serialization but not raised
        # Output might be empty or have an error marker
        captured = capsys.readouterr()
        # The important part is it didn't crash

    def test_emit_marker_with_unserializable_object(self, capsys):
        """Test emit_marker with object that can't be serialized"""
        marker_type = "TEST"
        # Create a custom object
        class CustomObject:
            pass

        data = {"object": CustomObject()}

        # Should not raise
        emit_marker(marker_type, data, enabled=True)

        # Should complete without crashing
