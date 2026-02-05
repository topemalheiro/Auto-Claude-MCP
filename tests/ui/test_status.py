"""Tests for status"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from ui.status import BuildState, BuildStatus, StatusManager


def test_BuildStatus_to_dict():
    """Test BuildStatus.to_dict"""

    # Arrange
    status = BuildStatus(
        active=True,
        spec="001-feature",
        state=BuildState.BUILDING,
        subtasks_completed=5,
        subtasks_total=10,
        subtasks_in_progress=2,
        subtasks_failed=1,
        phase_current="Implementation",
        phase_id=2,
        phase_total=5,
        workers_active=3,
        workers_max=4,
        session_number=1,
        session_started="2024-01-01T12:00:00",
        last_update="2024-01-01T12:05:00",
    )

    # Act
    result = status.to_dict()

    # Assert
    assert result is not None
    assert result["active"] is True
    assert result["spec"] == "001-feature"
    assert result["state"] == "building"
    assert result["subtasks"]["completed"] == 5
    assert result["subtasks"]["total"] == 10
    assert result["subtasks"]["in_progress"] == 2
    assert result["subtasks"]["failed"] == 1
    assert result["phase"]["current"] == "Implementation"
    assert result["phase"]["id"] == 2
    assert result["phase"]["total"] == 5
    assert result["workers"]["active"] == 3
    assert result["workers"]["max"] == 4
    assert result["session"]["number"] == 1
    assert result["session"]["started_at"] == "2024-01-01T12:00:00"


def test_BuildStatus_from_dict():
    """Test BuildStatus.from_dict"""

    # Arrange
    data = {
        "active": True,
        "spec": "001-feature",
        "state": "building",
        "subtasks": {
            "completed": 5,
            "total": 10,
            "in_progress": 2,
            "failed": 1,
        },
        "phase": {
            "current": "Implementation",
            "id": 2,
            "total": 5,
        },
        "workers": {
            "active": 3,
            "max": 4,
        },
        "session": {
            "number": 1,
            "started_at": "2024-01-01T12:00:00",
        },
        "last_update": "2024-01-01T12:05:00",
    }

    # Act
    result = BuildStatus.from_dict(data)

    # Assert
    assert result is not None
    assert result.active is True
    assert result.spec == "001-feature"
    assert result.state == BuildState.BUILDING
    assert result.subtasks_completed == 5
    assert result.subtasks_total == 10
    assert result.subtasks_in_progress == 2
    assert result.subtasks_failed == 1
    assert result.phase_current == "Implementation"
    assert result.phase_id == 2
    assert result.phase_total == 5
    assert result.workers_active == 3
    assert result.workers_max == 4
    assert result.session_number == 1
    assert result.session_started == "2024-01-01T12:00:00"


def test_BuildStatus_from_dict_default_values():
    """Test BuildStatus.from_dict with default values"""

    # Arrange
    data = {}

    # Act
    result = BuildStatus.from_dict(data)

    # Assert
    assert result is not None
    assert result.active is False
    assert result.spec == ""
    assert result.state == BuildState.IDLE
    assert result.subtasks_completed == 0
    assert result.subtasks_total == 0
    assert result.subtasks_in_progress == 0
    assert result.subtasks_failed == 0
    assert result.phase_current == ""
    assert result.phase_id == 0
    assert result.phase_total == 0
    assert result.workers_active == 0
    assert result.workers_max == 1
    assert result.session_number == 0
    assert result.session_started == ""


def test_StatusManager___init__():
    """Test StatusManager.__init__"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        # Act
        manager = StatusManager(project_dir)

        # Assert
        assert manager.project_dir == project_dir
        assert manager.status_file == project_dir / ".auto-claude-status"
        assert manager._status == BuildStatus()
        assert manager._write_pending is False
        assert manager._write_timer is None


def test_StatusManager_read_no_file():
    """Test StatusManager.read when file doesn't exist"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        manager = StatusManager(project_dir)

        # Act
        result = manager.read()

        # Assert
        assert result.active is False
        assert result.spec == ""


def test_StatusManager_read_with_file():
    """Test StatusManager.read with existing file"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        manager = StatusManager(project_dir)

        # Write a status file
        import json

        status_data = {
            "active": True,
            "spec": "001-test",
            "state": "building",
            "subtasks": {"completed": 1, "total": 5, "in_progress": 0, "failed": 0},
            "phase": {"current": "Planning", "id": 1, "total": 3},
            "workers": {"active": 1, "max": 1},
            "session": {"number": 1, "started_at": "2024-01-01T00:00:00"},
            "last_update": "2024-01-01T00:00:00",
        }
        with open(manager.status_file, "w") as f:
            json.dump(status_data, f)

        # Act
        result = manager.read()

        # Assert
        assert result.active is True
        assert result.spec == "001-test"
        assert result.state == BuildState.BUILDING


def test_StatusManager_write():
    """Test StatusManager.write"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        manager = StatusManager(project_dir)
        status = BuildStatus(active=True, spec="001-test", state=BuildState.BUILDING)

        # Act
        manager.write(status, immediate=True)

        # Assert
        assert manager.status_file.exists()
        result = manager.read()
        assert result.active is True
        assert result.spec == "001-test"


def test_StatusManager_flush():
    """Test StatusManager.flush"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        manager = StatusManager(project_dir)
        status = BuildStatus(active=True, spec="001-test", state=BuildState.BUILDING)

        # Write without immediate to schedule a debounced write
        manager.write(status, immediate=False)

        # Act
        manager.flush()

        # Assert
        assert manager.status_file.exists()
        # After flush, no write should be pending
        assert manager._write_pending is False
        assert manager._write_timer is None


def test_StatusManager_update():
    """Test StatusManager.update"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        manager = StatusManager(project_dir)

        # Act
        manager.update(active=True, spec="001-test", subtasks_completed=5)

        # Flush to ensure write is complete
        manager.flush()

        # Assert
        result = manager.read()
        assert result.active is True
        assert result.spec == "001-test"
        assert result.subtasks_completed == 5


def test_StatusManager_set_active():
    """Test StatusManager.set_active"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        manager = StatusManager(project_dir)

        # Act
        manager.set_active("001-test", BuildState.BUILDING)

        # Assert
        result = manager.read()
        assert result.active is True
        assert result.spec == "001-test"
        assert result.state == BuildState.BUILDING
        assert result.session_started != ""  # Should be set to current time


def test_StatusManager_set_inactive():
    """Test StatusManager.set_inactive"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        manager = StatusManager(project_dir)
        manager.set_active("001-test", BuildState.BUILDING)

        # Act
        manager.set_inactive()

        # Assert
        result = manager.read()
        assert result.active is False
        assert result.state == BuildState.IDLE


def test_StatusManager_update_subtasks():
    """Test StatusManager.update_subtasks"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        manager = StatusManager(project_dir)

        # Act
        manager.update_subtasks(completed=5, total=10, in_progress=2, failed=1)
        manager.flush()

        # Assert
        result = manager.read()
        assert result.subtasks_completed == 5
        assert result.subtasks_total == 10
        assert result.subtasks_in_progress == 2
        assert result.subtasks_failed == 1


def test_StatusManager_update_subtasks_partial():
    """Test StatusManager.update_subtasks with partial updates"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        manager = StatusManager(project_dir)
        manager.update_subtasks(completed=5, total=10)
        manager.flush()

        # Act - update only completed
        manager.update_subtasks(completed=7)
        manager.flush()

        # Assert
        result = manager.read()
        assert result.subtasks_completed == 7
        assert result.subtasks_total == 10  # Should remain unchanged
        assert result.subtasks_in_progress == 0
        assert result.subtasks_failed == 0


def test_StatusManager_update_phase():
    """Test StatusManager.update_phase"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        manager = StatusManager(project_dir)

        # Act
        manager.update_phase("Implementation", 2, 5)
        manager.flush()

        # Assert
        result = manager.read()
        assert result.phase_current == "Implementation"
        assert result.phase_id == 2
        assert result.phase_total == 5


def test_StatusManager_update_workers():
    """Test StatusManager.update_workers"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        manager = StatusManager(project_dir)

        # Act
        manager.update_workers(3, 5)
        manager.flush()

        # Assert
        result = manager.read()
        assert result.workers_active == 3
        assert result.workers_max == 5


def test_StatusManager_update_workers_partial():
    """Test StatusManager.update_workers without max_workers"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        manager = StatusManager(project_dir)
        manager.update_workers(2, 4)
        manager.flush()

        # Act - update only active count
        manager.update_workers(3)
        manager.flush()

        # Assert
        result = manager.read()
        assert result.workers_active == 3
        assert result.workers_max == 4  # Should remain unchanged


def test_StatusManager_update_session():
    """Test StatusManager.update_session"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        manager = StatusManager(project_dir)

        # Act
        manager.update_session(5)
        manager.flush()

        # Assert
        result = manager.read()
        assert result.session_number == 5


def test_StatusManager_clear():
    """Test StatusManager.clear"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        manager = StatusManager(project_dir)
        manager.write(BuildStatus(active=True), immediate=True)

        # Verify file exists
        assert manager.status_file.exists()

        # Act
        manager.clear()

        # Assert
        assert not manager.status_file.exists()
        assert manager._write_pending is False
        assert manager._write_timer is None


def test_StatusManager_clear_no_file():
    """Test StatusManager.clear when file doesn't exist"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        manager = StatusManager(project_dir)

        # Act - should not raise
        manager.clear()

        # Assert
        assert not manager.status_file.exists()
