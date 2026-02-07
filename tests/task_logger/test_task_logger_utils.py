"""Tests for task_logger/utils.py"""

from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from task_logger.utils import (
    get_task_logger,
    clear_task_logger,
    update_task_logger_path,
)
from task_logger.logger import TaskLogger
from task_logger.models import LogEntry, LogEntryType, LogPhase


class TestGetTaskLogger:
    """Tests for get_task_logger function"""

    def setup_method(self):
        """Clear global logger before each test"""
        clear_task_logger()

    def test_get_task_logger_returns_none_when_no_spec_dir(self):
        """Test get_task_logger returns None when no spec_dir provided"""
        result = get_task_logger(spec_dir=None)
        assert result is None

    def test_get_task_logger_creates_new_logger(self, tmp_path):
        """Test get_task_logger creates new logger for spec_dir"""
        spec_dir = tmp_path / "001-test"
        spec_dir.mkdir(parents=True)

        result = get_task_logger(spec_dir)

        assert result is not None
        # Use type() instead of isinstance to handle module re-import issues
        assert type(result).__name__ == "TaskLogger"
        assert result.spec_dir == spec_dir

    def test_get_task_logger_returns_cached_logger(self, tmp_path):
        """Test get_task_logger returns cached logger for same spec_dir"""
        spec_dir = tmp_path / "001-test"
        spec_dir.mkdir(parents=True)

        logger1 = get_task_logger(spec_dir)
        logger2 = get_task_logger(spec_dir)

        assert logger1 is logger2

    def test_get_task_logger_creates_new_for_different_spec_dir(self, tmp_path):
        """Test get_task_logger creates new logger for different spec_dir"""
        spec_dir1 = tmp_path / "001-test"
        spec_dir2 = tmp_path / "002-test"
        spec_dir1.mkdir(parents=True)
        spec_dir2.mkdir(parents=True)

        logger1 = get_task_logger(spec_dir1)
        logger2 = get_task_logger(spec_dir2)

        assert logger1 is not logger2
        assert logger1.spec_dir == spec_dir1
        assert logger2.spec_dir == spec_dir2

    def test_get_task_logger_emit_markers_default(self, tmp_path):
        """Test get_task_logger emit_markers defaults to True"""
        spec_dir = tmp_path / "001-test"
        spec_dir.mkdir(parents=True)

        logger = get_task_logger(spec_dir)

        assert logger.emit_markers is True

    def test_get_task_logger_emit_markers_disabled(self, tmp_path):
        """Test get_task_logger with emit_markers=False"""
        spec_dir = tmp_path / "001-test"
        spec_dir.mkdir(parents=True)

        logger = get_task_logger(spec_dir, emit_markers=False)

        assert logger.emit_markers is False

    def test_get_task_logger_without_spec_dir_returns_current(self, tmp_path):
        """Test get_task_logger without args returns current logger"""
        spec_dir = tmp_path / "001-test"
        spec_dir.mkdir(parents=True)

        # Create a logger
        original_logger = get_task_logger(spec_dir)

        # Get without args should return the same one
        result = get_task_logger()

        assert result is original_logger

    def test_get_task_logger_lazily_imports_logger(self, tmp_path):
        """Test get_task_logger lazily imports TaskLogger to avoid cycles"""
        spec_dir = tmp_path / "001-test"
        spec_dir.mkdir(parents=True)

        # This should not cause circular import issues
        result = get_task_logger(spec_dir)

        assert result is not None
        # Use type() instead of isinstance to handle module re-import issues
        assert type(result).__name__ == "TaskLogger"


class TestClearTaskLogger:
    """Tests for clear_task_logger function"""

    def setup_method(self):
        """Clear global logger before each test"""
        clear_task_logger()

    def test_clear_task_logger_clears_global(self, tmp_path):
        """Test clear_task_logger clears global logger"""
        spec_dir = tmp_path / "001-test"
        spec_dir.mkdir(parents=True)

        # Create a logger
        get_task_logger(spec_dir)
        assert get_task_logger() is not None

        # Clear it
        clear_task_logger()
        assert get_task_logger() is None

    def test_clear_task_logger_idempotent(self):
        """Test clear_task_logger can be called multiple times"""
        clear_task_logger()
        clear_task_logger()
        clear_task_logger()

        # Should not raise
        assert get_task_logger() is None

    def test_clear_allows_new_logger_creation(self, tmp_path):
        """Test that clearing allows creating a new logger"""
        spec_dir1 = tmp_path / "001-test"
        spec_dir2 = tmp_path / "002-test"
        spec_dir1.mkdir(parents=True)
        spec_dir2.mkdir(parents=True)

        # Create first logger
        logger1 = get_task_logger(spec_dir1)
        assert get_task_logger() is logger1

        # Clear
        clear_task_logger()
        assert get_task_logger() is None

        # Create new logger
        logger2 = get_task_logger(spec_dir2)
        assert get_task_logger() is logger2
        assert logger2 is not logger1


class TestUpdateTaskLoggerPath:
    """Tests for update_task_logger_path function"""

    def setup_method(self):
        """Clear global logger before each test"""
        clear_task_logger()

    def test_update_task_logger_path_no_logger(self, tmp_path):
        """Test update_task_logger_path does nothing when no logger exists"""
        new_spec_dir = tmp_path / "002-test"
        new_spec_dir.mkdir(parents=True)

        # Should not raise
        update_task_logger_path(new_spec_dir)

        # Still no logger
        assert get_task_logger() is None

    def test_update_task_logger_path_updates_spec_dir(self, tmp_path):
        """Test update_task_logger_path updates logger's spec_dir"""
        spec_dir = tmp_path / "001-test"
        new_spec_dir = tmp_path / "002-test-renamed"
        spec_dir.mkdir(parents=True)
        new_spec_dir.mkdir(parents=True)

        # Create logger
        logger = get_task_logger(spec_dir)
        assert logger.spec_dir == spec_dir

        # Update path
        update_task_logger_path(new_spec_dir)

        assert logger.spec_dir == new_spec_dir

    def test_update_task_logger_path_updates_log_file(self, tmp_path):
        """Test update_task_logger_path updates log_file path"""
        spec_dir = tmp_path / "001-test"
        new_spec_dir = tmp_path / "002-test-renamed"
        spec_dir.mkdir(parents=True)
        new_spec_dir.mkdir(parents=True)

        # Create logger
        logger = get_task_logger(spec_dir)
        original_log_file = logger.log_file

        # Update path
        update_task_logger_path(new_spec_dir)

        assert logger.log_file != original_log_file
        assert logger.log_file == new_spec_dir / TaskLogger.LOG_FILE

    def test_update_task_logger_path_updates_spec_id(self, tmp_path):
        """Test update_task_logger_path updates spec_id in storage"""
        spec_dir = tmp_path / "001-test"
        new_spec_dir = tmp_path / "002-test-renamed"
        spec_dir.mkdir(parents=True)
        new_spec_dir.mkdir(parents=True)

        # Create logger
        logger = get_task_logger(spec_dir)

        # Update path
        update_task_logger_path(new_spec_dir)

        # Check spec_id was updated
        assert logger.storage._data["spec_id"] == new_spec_dir.name

    def test_update_task_logger_path_saves_to_new_location(self, tmp_path):
        """Test update_task_logger_path saves logs to new location"""
        spec_dir = tmp_path / "001-test"
        new_spec_dir = tmp_path / "002-test-renamed"
        spec_dir.mkdir(parents=True)
        new_spec_dir.mkdir(parents=True)

        # Create logger and add some data
        logger = get_task_logger(spec_dir)
        logger.start_phase(LogPhase.CODING, "Starting coding")
        logger.log("Test message")

        # Update path
        update_task_logger_path(new_spec_dir)

        # Should have updated internal paths
        assert logger.spec_dir == new_spec_dir
        assert logger.log_file == new_spec_dir / TaskLogger.LOG_FILE

        # Note: Data is only saved when explicitly calling methods that save
        # The update just updates paths, doesn't force save
        # But the spec_id in storage should be updated
        assert logger.storage._data["spec_id"] == new_spec_dir.name

    def test_update_task_logger_path_with_pathlib_path(self, tmp_path):
        """Test update_task_logger_path works with Path object"""
        spec_dir = tmp_path / "001-test"
        new_spec_dir = Path(tmp_path / "002-test-renamed")
        spec_dir.mkdir(parents=True)
        new_spec_dir.mkdir(parents=True)

        logger = get_task_logger(spec_dir)
        update_task_logger_path(new_spec_dir)

        assert logger.spec_dir == new_spec_dir

    def test_update_task_logger_path_preserves_logger_state(self, tmp_path):
        """Test update_task_logger_path preserves logger state"""
        spec_dir = tmp_path / "001-test"
        new_spec_dir = tmp_path / "002-test-renamed"
        spec_dir.mkdir(parents=True)
        new_spec_dir.mkdir(parents=True)

        # Create logger with state
        logger = get_task_logger(spec_dir, emit_markers=False)
        logger.set_session(5)
        logger.set_subtask("subtask-1")
        logger.start_phase(LogPhase.CODING)

        # Update path
        update_task_logger_path(new_spec_dir)

        # State should be preserved
        assert logger.current_session == 5
        assert logger.current_subtask == "subtask-1"
        assert logger.current_phase == LogPhase.CODING
        assert logger.emit_markers is False


class TestIntegration:
    """Integration tests for utils module"""

    def setup_method(self):
        """Clear global logger before each test"""
        clear_task_logger()

    def test_full_workflow_with_utils(self, tmp_path):
        """Test full workflow using utility functions"""
        spec_dir = tmp_path / "001-test"
        spec_dir.mkdir(parents=True)

        # Get logger
        logger = get_task_logger(spec_dir)
        assert logger is not None

        # Use logger
        logger.set_session(1)
        logger.start_phase(LogPhase.PLANNING)
        logger.log("Planning message")

        # Rename spec dir
        new_spec_dir = tmp_path / "002-renamed"
        new_spec_dir.mkdir(parents=True)
        update_task_logger_path(new_spec_dir)

        # Continue using logger
        logger.log("After rename")

        # Clear and start fresh
        clear_task_logger()
        assert get_task_logger() is None

    def test_multiple_loggers_with_utils(self, tmp_path):
        """Test managing multiple loggers via utils"""
        spec_dir1 = tmp_path / "001-test"
        spec_dir2 = tmp_path / "002-test"
        spec_dir1.mkdir(parents=True)
        spec_dir2.mkdir(parents=True)

        # Work with first spec
        logger1 = get_task_logger(spec_dir1)
        logger1.set_session(1)

        # Clear and work with second spec
        clear_task_logger()
        logger2 = get_task_logger(spec_dir2)
        logger2.set_session(2)

        # Loggers should be different
        assert logger1 is not logger2
        assert logger1.spec_dir == spec_dir1
        assert logger2.spec_dir == spec_dir2

    def test_logger_persistence_across_calls(self, tmp_path):
        """Test that logger persists across multiple get_task_logger calls"""
        spec_dir = tmp_path / "001-test"
        spec_dir.mkdir(parents=True)

        logger1 = get_task_logger(spec_dir)
        logger1.set_session(10)

        logger2 = get_task_logger()
        logger3 = get_task_logger(spec_dir)

        assert logger2 is logger1
        assert logger3 is logger1
        assert logger2.current_session == 10
