"""Tests for task_logger/models.py"""

from datetime import datetime, timezone

import pytest

from task_logger.models import (
    LogEntry,
    LogEntryType,
    LogPhase,
    PhaseLog,
)


class TestLogPhase:
    """Tests for LogPhase enum"""

    def test_log_phase_values(self):
        """Test LogPhase enum values"""
        assert LogPhase.PLANNING.value == "planning"
        assert LogPhase.CODING.value == "coding"
        assert LogPhase.VALIDATION.value == "validation"

    def test_log_phase_is_string_enum(self):
        """Test LogPhase is a string enum"""
        assert isinstance(LogPhase.PLANNING, str)
        # String enums use .value to get the string value
        assert LogPhase.CODING.value == "coding"


class TestLogEntryType:
    """Tests for LogEntryType enum"""

    def test_log_entry_type_values(self):
        """Test LogEntryType enum values"""
        assert LogEntryType.TEXT.value == "text"
        assert LogEntryType.TOOL_START.value == "tool_start"
        assert LogEntryType.TOOL_END.value == "tool_end"
        assert LogEntryType.PHASE_START.value == "phase_start"
        assert LogEntryType.PHASE_END.value == "phase_end"
        assert LogEntryType.ERROR.value == "error"
        assert LogEntryType.SUCCESS.value == "success"
        assert LogEntryType.INFO.value == "info"

    def test_log_entry_type_is_string_enum(self):
        """Test LogEntryType is a string enum"""
        assert isinstance(LogEntryType.TEXT, str)
        # String enums use .value to get the string value
        assert LogEntryType.ERROR.value == "error"


class TestLogEntry:
    """Tests for LogEntry dataclass"""

    def test_log_entry_creation(self):
        """Test creating a LogEntry"""
        entry = LogEntry(
            timestamp="2024-01-01T00:00:00Z",
            type="text",
            content="Test message",
            phase="coding",
        )

        assert entry.timestamp == "2024-01-01T00:00:00Z"
        assert entry.type == "text"
        assert entry.content == "Test message"
        assert entry.phase == "coding"
        assert entry.tool_name is None
        assert entry.tool_input is None
        assert entry.subtask_id is None
        assert entry.session is None
        assert entry.detail is None
        assert entry.subphase is None
        assert entry.collapsed is None

    def test_log_entry_with_all_fields(self):
        """Test creating a LogEntry with all fields"""
        entry = LogEntry(
            timestamp="2024-01-01T00:00:00Z",
            type="tool_start",
            content="[Read] file.py",
            phase="coding",
            tool_name="Read",
            tool_input="file.py",
            subtask_id="subtask-1",
            session=1,
            detail="File content here",
            subphase="FILE READING",
            collapsed=True,
        )

        assert entry.tool_name == "Read"
        assert entry.tool_input == "file.py"
        assert entry.subtask_id == "subtask-1"
        assert entry.session == 1
        assert entry.detail == "File content here"
        assert entry.subphase == "FILE READING"
        assert entry.collapsed is True

    def test_log_entry_to_dict_excludes_none(self):
        """Test LogEntry.to_dict excludes None values"""
        entry = LogEntry(
            timestamp="2024-01-01T00:00:00Z",
            type="text",
            content="Test",
            phase="coding",
        )

        result = entry.to_dict()

        assert "timestamp" in result
        assert "type" in result
        assert "content" in result
        assert "phase" in result
        assert "tool_name" not in result
        assert "tool_input" not in result
        assert "subtask_id" not in result
        assert "session" not in result
        assert "detail" not in result
        assert "subphase" not in result
        assert "collapsed" not in result

    def test_log_entry_to_dict_includes_non_none(self):
        """Test LogEntry.to_dict includes non-None values"""
        entry = LogEntry(
            timestamp="2024-01-01T00:00:00Z",
            type="tool_start",
            content="[Read] file.py",
            phase="coding",
            tool_name="Read",
            tool_input="file.py",
            session=1,
        )

        result = entry.to_dict()

        assert "tool_name" in result
        assert "tool_input" in result
        assert "session" in result
        assert result["tool_name"] == "Read"
        assert result["tool_input"] == "file.py"
        assert result["session"] == 1

    def test_log_entry_with_session_zero(self):
        """Test LogEntry with session=0 (falsy but valid)"""
        entry = LogEntry(
            timestamp="2024-01-01T00:00:00Z",
            type="text",
            content="Test",
            phase="coding",
            session=0,
        )

        result = entry.to_dict()
        assert "session" in result
        assert result["session"] == 0

    def test_log_entry_with_collapsed_false(self):
        """Test LogEntry with collapsed=False (falsy but valid)"""
        entry = LogEntry(
            timestamp="2024-01-01T00:00:00Z",
            type="text",
            content="Test",
            phase="coding",
            collapsed=False,
        )

        result = entry.to_dict()
        assert "collapsed" in result
        assert result["collapsed"] is False


class TestPhaseLog:
    """Tests for PhaseLog dataclass"""

    def test_phase_log_creation_default(self):
        """Test creating PhaseLog with defaults"""
        phase = PhaseLog(phase="coding", status="active")

        assert phase.phase == "coding"
        assert phase.status == "active"
        assert phase.started_at is None
        assert phase.completed_at is None
        assert phase.entries == []

    def test_phase_log_with_all_fields(self):
        """Test creating PhaseLog with all fields"""
        phase = PhaseLog(
            phase="coding",
            status="completed",
            started_at="2024-01-01T00:00:00Z",
            completed_at="2024-01-01T01:00:00Z",
            entries=[
                {"timestamp": "2024-01-01T00:00:00Z", "type": "text", "content": "Test"}
            ],
        )

        assert phase.started_at == "2024-01-01T00:00:00Z"
        assert phase.completed_at == "2024-01-01T01:00:00Z"
        assert len(phase.entries) == 1

    def test_phase_log_entries_initialization(self):
        """Test PhaseLog __post_init__ initializes entries"""
        phase = PhaseLog(phase="coding", status="active")
        assert phase.entries == []

    def test_phase_log_to_dict(self):
        """Test PhaseLog.to_dict returns correct structure"""
        phase = PhaseLog(
            phase="coding",
            status="active",
            started_at="2024-01-01T00:00:00Z",
        )

        result = phase.to_dict()

        assert result["phase"] == "coding"
        assert result["status"] == "active"
        assert result["started_at"] == "2024-01-01T00:00:00Z"
        assert result["completed_at"] is None
        assert result["entries"] == []

    def test_phase_log_statuses(self):
        """Test various PhaseLog status values"""
        statuses = ["pending", "active", "completed", "failed"]

        for status in statuses:
            phase = PhaseLog(phase="coding", status=status)
            assert phase.status == status


class TestLogEntryIntegration:
    """Integration tests for LogEntry with actual usage"""

    def test_create_text_entry(self):
        """Test creating a text log entry"""
        entry = LogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            type=LogEntryType.TEXT.value,
            content="Test message",
            phase=LogPhase.CODING.value,
        )

        result = entry.to_dict()
        assert result["type"] == "text"
        assert result["phase"] == "coding"

    def test_create_tool_entry(self):
        """Test creating a tool log entry"""
        entry = LogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            type=LogEntryType.TOOL_START.value,
            content="[Read] file.py",
            phase=LogPhase.CODING.value,
            tool_name="Read",
            tool_input="file.py",
        )

        result = entry.to_dict()
        assert result["type"] == "tool_start"
        assert result["tool_name"] == "Read"
        assert result["tool_input"] == "file.py"

    def test_create_phase_entry(self):
        """Test creating a phase change entry"""
        entry = LogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            type=LogEntryType.PHASE_START.value,
            content="Starting coding phase",
            phase=LogPhase.CODING.value,
        )

        result = entry.to_dict()
        assert result["type"] == "phase_start"

    def test_create_error_entry(self):
        """Test creating an error entry"""
        entry = LogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            type=LogEntryType.ERROR.value,
            content="Error occurred",
            phase=LogPhase.CODING.value,
        )

        result = entry.to_dict()
        assert result["type"] == "error"

    def test_create_entry_with_detail(self):
        """Test creating entry with expandable detail"""
        entry = LogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            type=LogEntryType.TEXT.value,
            content="Brief summary",
            phase=LogPhase.CODING.value,
            detail="Full detailed content that can be expanded",
            subphase="CONTEXT GATHERING",
            collapsed=True,
        )

        result = entry.to_dict()
        assert result["content"] == "Brief summary"
        assert result["detail"] == "Full detailed content that can be expanded"
        assert result["subphase"] == "CONTEXT GATHERING"
        assert result["collapsed"] is True
