"""Tests for task_logger/main.py"""

from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# Test that the task_logger module can be imported
# and that it re-exports all expected APIs


class TestTaskLoggerMainExports:
    """Tests for task_logger.main module exports"""

    def test_main_import_from_task_logger(self):
        """Test importing from task_logger.main"""
        # This test verifies the module can be imported
        # and re-exports from the task_logger package
        from task_logger import main

        # The main module should exist and be importable
        assert main is not None

    def test_main_reexports_logphase(self):
        """Test main module re-exports LogPhase"""
        from task_logger.main import LogPhase

        assert LogPhase is not None
        assert LogPhase.CODING.value == "coding"

    def test_main_reexports_logentrytype(self):
        """Test main module re-exports LogEntryType"""
        from task_logger.main import LogEntryType

        assert LogEntryType is not None
        assert LogEntryType.TEXT.value == "text"

    def test_main_reexports_logentry(self):
        """Test main module re-exports LogEntry"""
        from task_logger.main import LogEntry

        assert LogEntry is not None

    def test_main_reexports_phaselog(self):
        """Test main module re-exports PhaseLog"""
        from task_logger.main import PhaseLog

        assert PhaseLog is not None

    def test_main_reexports_tasklogger(self):
        """Test main module re-exports TaskLogger"""
        from task_logger.main import TaskLogger

        assert TaskLogger is not None

    def test_main_reexports_streaminglogcapture(self):
        """Test main module re-exports StreamingLogCapture"""
        from task_logger.main import StreamingLogCapture

        assert StreamingLogCapture is not None

    def test_main_reexports_get_task_logger(self):
        """Test main module re-exports get_task_logger"""
        from task_logger.main import get_task_logger

        assert get_task_logger is not None

    def test_main_reexports_clear_task_logger(self):
        """Test main module re-exports clear_task_logger"""
        from task_logger.main import clear_task_logger

        assert clear_task_logger is not None

    def test_main_reexports_update_task_logger_path(self):
        """Test main module re-exports update_task_logger_path"""
        from task_logger.main import update_task_logger_path

        assert update_task_logger_path is not None

    def test_main_reexports_load_task_logs(self):
        """Test main module re-exports load_task_logs"""
        from task_logger.main import load_task_logs

        assert load_task_logs is not None

    def test_main_reexports_get_active_phase(self):
        """Test main module re-exports get_active_phase"""
        from task_logger.main import get_active_phase

        assert get_active_phase is not None

    def test_main_all_list(self):
        """Test main module __all__ list contains all exports"""
        from task_logger import main

        expected_exports = [
            "LogPhase",
            "LogEntryType",
            "LogEntry",
            "PhaseLog",
            "TaskLogger",
            "load_task_logs",
            "get_active_phase",
            "get_task_logger",
            "clear_task_logger",
            "update_task_logger_path",
            "StreamingLogCapture",
        ]

        assert hasattr(main, "__all__")
        for export in expected_exports:
            assert export in main.__all__


class TestTaskLoggerMainBackwardsCompatibility:
    """Tests for backwards compatibility of main module"""

    def test_can_use_tasklogger_from_main(self, tmp_path):
        """Test using TaskLogger imported from main"""
        from task_logger.main import TaskLogger

        spec_dir = tmp_path / "001-test"
        spec_dir.mkdir(parents=True)

        logger = TaskLogger(spec_dir, emit_markers=False)

        assert logger.spec_dir == spec_dir

    def test_can_use_get_task_logger_from_main(self, tmp_path):
        """Test using get_task_logger imported from main"""
        from task_logger.main import get_task_logger, clear_task_logger

        # Clear any existing logger
        clear_task_logger()

        spec_dir = tmp_path / "001-test"
        spec_dir.mkdir(parents=True)

        logger = get_task_logger(spec_dir, emit_markers=False)

        assert logger is not None

    def test_can_use_storage_functions_from_main(self, tmp_path):
        """Test using storage functions imported from main"""
        from task_logger.main import load_task_logs, get_active_phase
        import json

        spec_dir = tmp_path / "001-test"
        spec_dir.mkdir(parents=True)

        # Create a log file
        log_data = {
            "spec_id": "001-test",
            "phases": {
                "coding": {"status": "active"},
            },
        }
        log_file = spec_dir / "task_logs.json"
        log_file.write_text(json.dumps(log_data), encoding="utf-8")

        # Load logs
        logs = load_task_logs(spec_dir)
        assert logs is not None
        assert logs["spec_id"] == "001-test"

        # Get active phase
        active = get_active_phase(spec_dir)
        assert active == "coding"
