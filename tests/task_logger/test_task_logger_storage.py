"""Tests for task_logger/storage.py"""

from pathlib import Path
from unittest.mock import patch, MagicMock
import json

import pytest

from task_logger.storage import (
    LogStorage,
    load_task_logs,
    get_active_phase,
)
from task_logger.models import LogEntry, LogPhase


class TestLogStorage:
    """Tests for LogStorage class"""

    def test_init_creates_new_structure(self, tmp_path):
        """Test LogStorage initialization creates new structure"""
        spec_dir = tmp_path / "001-test"
        spec_dir.mkdir(parents=True)

        storage = LogStorage(spec_dir)

        assert storage.spec_dir == spec_dir
        assert storage.log_file == spec_dir / "task_logs.json"
        assert storage._data is not None
        assert "phases" in storage._data
        assert "planning" in storage._data["phases"]
        assert "coding" in storage._data["phases"]
        assert "validation" in storage._data["phases"]

    def test_init_loads_existing_file(self, tmp_path):
        """Test LogStorage loads existing log file"""
        spec_dir = tmp_path / "001-test"
        spec_dir.mkdir(parents=True)

        existing_data = {
            "spec_id": "001-test",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "phases": {
                "planning": {
                    "phase": "planning",
                    "status": "completed",
                    "started_at": "2024-01-01T00:00:00Z",
                    "completed_at": "2024-01-01T01:00:00Z",
                    "entries": [{"timestamp": "2024-01-01T00:00:00Z", "content": "Test entry"}]
                }
            }
        }

        log_file = spec_dir / "task_logs.json"
        log_file.write_text(json.dumps(existing_data), encoding="utf-8")

        storage = LogStorage(spec_dir)

        assert storage._data["spec_id"] == "001-test"
        assert storage._data["phases"]["planning"]["status"] == "completed"

    def test_init_handles_corrupted_file(self, tmp_path):
        """Test LogStorage handles corrupted log file"""
        spec_dir = tmp_path / "001-test"
        spec_dir.mkdir(parents=True)

        log_file = spec_dir / "task_logs.json"
        log_file.write_text("{invalid json", encoding="utf-8")

        storage = LogStorage(spec_dir)

        # Should create new structure
        assert storage._data["spec_id"] == "001-test"
        assert "phases" in storage._data

    def test_save_writes_file(self, tmp_path):
        """Test save writes log file atomically"""
        spec_dir = tmp_path / "001-test"
        spec_dir.mkdir(parents=True)

        storage = LogStorage(spec_dir)
        storage.save()

        log_file = spec_dir / "task_logs.json"
        assert log_file.exists()

        with open(log_file, encoding="utf-8") as f:
            data = json.load(f)

        assert data["spec_id"] == "001-test"

    def test_save_handles_directory_creation(self, tmp_path):
        """Test save creates directory if needed"""
        spec_dir = tmp_path / "new" / "nested" / "001-test"
        # Don't create directory beforehand

        storage = LogStorage(spec_dir)
        storage.save()

        assert spec_dir.exists()
        assert (spec_dir / "task_logs.json").exists()

    def test_add_entry(self, tmp_path):
        """Test add_entry adds log entry to phase"""
        spec_dir = tmp_path / "001-test"
        spec_dir.mkdir(parents=True)

        storage = LogStorage(spec_dir)

        entry = LogEntry(
            timestamp="2024-01-01T00:00:00Z",
            type="text",
            phase="planning",
            content="Test planning entry"
        )

        storage.add_entry(entry)

        # Save should have been called
        assert (spec_dir / "task_logs.json").exists()

        phase_data = storage.get_phase_data("planning")
        assert len(phase_data["entries"]) == 1
        assert phase_data["entries"][0]["content"] == "Test planning entry"

    def test_add_entry_creates_new_phase(self, tmp_path):
        """Test add_entry creates phase if it doesn't exist"""
        spec_dir = tmp_path / "001-test"
        spec_dir.mkdir(parents=True)

        storage = LogStorage(spec_dir)

        entry = LogEntry(
            timestamp="2024-01-01T00:00:00Z",
            type="text",
            phase="custom_phase",
            content="Custom phase entry"
        )

        storage.add_entry(entry)

        phase_data = storage.get_phase_data("custom_phase")
        assert phase_data["phase"] == "custom_phase"
        assert phase_data["status"] == "active"
        assert len(phase_data["entries"]) == 1

    def test_update_phase_status(self, tmp_path):
        """Test update_phase_status updates phase status"""
        spec_dir = tmp_path / "001-test"
        spec_dir.mkdir(parents=True)

        storage = LogStorage(spec_dir)

        storage.update_phase_status("planning", "active")

        phase_data = storage.get_phase_data("planning")
        assert phase_data["status"] == "active"

    def test_update_phase_status_with_completion(self, tmp_path):
        """Test update_phase_status with completion time"""
        spec_dir = tmp_path / "001-test"
        spec_dir.mkdir(parents=True)

        storage = LogStorage(spec_dir)

        completed_at = "2024-01-01T02:00:00Z"
        storage.update_phase_status("planning", "completed", completed_at=completed_at)

        phase_data = storage.get_phase_data("planning")
        assert phase_data["status"] == "completed"
        assert phase_data["completed_at"] == completed_at

    def test_set_phase_started(self, tmp_path):
        """Test set_phase_started sets phase start time"""
        spec_dir = tmp_path / "001-test"
        spec_dir.mkdir(parents=True)

        storage = LogStorage(spec_dir)

        started_at = "2024-01-01T00:00:00Z"
        storage.set_phase_started("planning", started_at)

        phase_data = storage.get_phase_data("planning")
        assert phase_data["started_at"] == started_at

    def test_get_data(self, tmp_path):
        """Test get_data returns all data"""
        spec_dir = tmp_path / "001-test"
        spec_dir.mkdir(parents=True)

        storage = LogStorage(spec_dir)

        data = storage.get_data()

        assert "spec_id" in data
        assert "phases" in data
        assert data["spec_id"] == "001-test"

    def test_get_phase_data(self, tmp_path):
        """Test get_phase_data returns specific phase data"""
        spec_dir = tmp_path / "001-test"
        spec_dir.mkdir(parents=True)

        storage = LogStorage(spec_dir)

        planning_data = storage.get_phase_data("planning")

        assert planning_data["phase"] == "planning"
        assert planning_data["status"] == "pending"

    def test_get_phase_data_nonexistent(self, tmp_path):
        """Test get_phase_data returns empty dict for nonexistent phase"""
        spec_dir = tmp_path / "001-test"
        spec_dir.mkdir(parents=True)

        storage = LogStorage(spec_dir)

        result = storage.get_phase_data("nonexistent")

        assert result == {}

    def test_update_spec_id(self, tmp_path):
        """Test update_spec_id updates spec ID"""
        spec_dir = tmp_path / "001-test"
        spec_dir.mkdir(parents=True)

        storage = LogStorage(spec_dir)

        storage.update_spec_id("002-new-spec")

        assert storage._data["spec_id"] == "002-new-spec"

    def test_save_failure_handling(self, tmp_path):
        """Test save handles failures gracefully"""
        spec_dir = tmp_path / "001-test"
        spec_dir.mkdir(parents=True)

        storage = LogStorage(spec_dir)

        # Mock to cause failure
        with patch('tempfile.mkstemp', side_effect=OSError("Permission denied")):
            with patch('builtins.print') as mock_print:
                storage.save()  # Should not raise exception

                # Should print warning
                mock_print.assert_called()

    def test_timestamp_format(self, tmp_path):
        """Test _timestamp returns valid ISO format"""
        spec_dir = tmp_path / "001-test"
        spec_dir.mkdir(parents=True)

        storage = LogStorage(spec_dir)

        timestamp = storage._timestamp()

        # Should be valid ISO format with timezone
        assert "T" in timestamp
        assert "+" in timestamp or "Z" in timestamp



class TestLoadTaskLogs:
    """Tests for load_task_logs function"""

    def test_load_existing_logs(self, tmp_path):
        """Test load_task_logs loads existing log file"""
        spec_dir = tmp_path / "001-test"
        spec_dir.mkdir(parents=True)

        log_data = {
            "spec_id": "001-test",
            "phases": {}
        }

        log_file = spec_dir / "task_logs.json"
        log_file.write_text(json.dumps(log_data), encoding="utf-8")

        result = load_task_logs(spec_dir)

        assert result is not None
        assert result["spec_id"] == "001-test"

    def test_load_nonexistent_logs(self, tmp_path):
        """Test load_task_logs returns None for nonexistent file"""
        spec_dir = tmp_path / "001-test"
        spec_dir.mkdir(parents=True)

        result = load_task_logs(spec_dir)

        assert result is None

    def test_load_corrupted_logs(self, tmp_path):
        """Test load_task_logs returns None for corrupted file"""
        spec_dir = tmp_path / "001-test"
        spec_dir.mkdir(parents=True)

        log_file = spec_dir / "task_logs.json"
        log_file.write_text("{invalid json", encoding="utf-8")

        result = load_task_logs(spec_dir)

        assert result is None


class TestGetActivePhase:
    """Tests for get_active_phase function"""

    def test_get_active_phase_returns_active(self, tmp_path):
        """Test get_active_phase returns active phase"""
        spec_dir = tmp_path / "001-test"
        spec_dir.mkdir(parents=True)

        log_data = {
            "spec_id": "001-test",
            "phases": {
                "planning": {"status": "completed"},
                "coding": {"status": "active"},
                "validation": {"status": "pending"}
            }
        }

        log_file = spec_dir / "task_logs.json"
        log_file.write_text(json.dumps(log_data), encoding="utf-8")

        result = get_active_phase(spec_dir)

        assert result == "coding"

    def test_get_active_phase_none_when_no_active(self, tmp_path):
        """Test get_active_phase returns None when no active phase"""
        spec_dir = tmp_path / "001-test"
        spec_dir.mkdir(parents=True)

        log_data = {
            "spec_id": "001-test",
            "phases": {
                "planning": {"status": "completed"},
                "coding": {"status": "pending"},
                "validation": {"status": "pending"}
            }
        }

        log_file = spec_dir / "task_logs.json"
        log_file.write_text(json.dumps(log_data), encoding="utf-8")

        result = get_active_phase(spec_dir)

        assert result is None

    def test_get_active_phase_none_when_no_logs(self, tmp_path):
        """Test get_active_phase returns None when no logs exist"""
        spec_dir = tmp_path / "001-test"
        spec_dir.mkdir(parents=True)

        result = get_active_phase(spec_dir)

        assert result is None


class TestLogStorageEdgeCases:
    """Tests for edge cases and error handling in LogStorage"""

    def test_load_handles_unicode_decode_error(self, tmp_path):
        """Test loading file with Unicode decode error creates new structure"""
        spec_dir = tmp_path / "001-test"
        spec_dir.mkdir(parents=True)

        # Write invalid UTF-8
        log_file = spec_dir / "task_logs.json"
        with open(log_file, "wb") as f:
            f.write(b"\xff\xfe Invalid UTF-8")

        storage = LogStorage(spec_dir)

        # Should create new structure
        assert storage._data["spec_id"] == "001-test"
        assert "phases" in storage._data

    def test_add_entry_to_nonexistent_phase(self, tmp_path):
        """Test adding entry to phase that doesn't exist creates it"""
        spec_dir = tmp_path / "001-test"
        spec_dir.mkdir(parents=True)

        storage = LogStorage(spec_dir)

        # Add entry to a new phase
        entry = LogEntry(
            timestamp="2024-01-01T00:00:00Z",
            type="text",
            content="Test",
            phase="new_custom_phase",
        )

        storage.add_entry(entry)

        # Phase should be created
        phase_data = storage.get_phase_data("new_custom_phase")
        assert phase_data["phase"] == "new_custom_phase"
        assert phase_data["status"] == "active"
        assert len(phase_data["entries"]) == 1

    def test_update_phase_status_nonexistent_phase(self, tmp_path):
        """Test updating status of nonexistent phase does nothing"""
        spec_dir = tmp_path / "001-test"
        spec_dir.mkdir(parents=True)

        storage = LogStorage(spec_dir)

        # Should not raise
        storage.update_phase_status("nonexistent", "active")

        # No error should occur
        assert storage.get_phase_data("nonexistent") == {}

    def test_set_phase_started_nonexistent_phase(self, tmp_path):
        """Test setting start time of nonexistent phase does nothing"""
        spec_dir = tmp_path / "001-test"
        spec_dir.mkdir(parents=True)

        storage = LogStorage(spec_dir)

        # Should not raise
        storage.set_phase_started("nonexistent", "2024-01-01T00:00:00Z")

        # No error should occur
        assert storage.get_phase_data("nonexistent") == {}

    def test_save_handles_permission_denied_gracefully(self, tmp_path):
        """Test save handles permission denied gracefully"""
        spec_dir = tmp_path / "001-test"
        spec_dir.mkdir(parents=True)

        storage = LogStorage(spec_dir)

        # Mock to cause failure in directory creation
        with patch('pathlib.Path.mkdir', side_effect=OSError("Permission denied")):
            with patch('builtins.print') as mock_print:
                # Should not raise
                storage.save()

                # Should print warning
                mock_print.assert_called()
