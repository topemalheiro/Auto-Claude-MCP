"""Tests for statusline"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ui.status import BuildState, BuildStatus, StatusManager
from ui.statusline import find_project_root, format_compact, format_full, format_json, main


def test_find_project_root():
    """Test find_project_root"""

    # Arrange - current directory should have .auto-claude-status or similar
    # Since we're in a test tree, the function should at least return cwd

    # Act
    result = find_project_root()

    # Assert
    assert result is not None
    assert isinstance(result, Path)


def test_format_compact():
    """Test format_compact"""

    # Arrange - create a status with active build
    status = BuildStatus(
        active=True,
        spec="001-feature",
        state=BuildState.BUILDING,
        subtasks_completed=3,
        subtasks_total=12,
        phase_current="Setup",
        workers_active=1,
        workers_max=1,
    )

    # Act
    result = format_compact(status)

    # Assert
    assert result is not None
    assert "3/12" in result
    assert "25%" in result  # 3/12 = 25%


def test_format_compact_inactive():
    """Test format_compact with inactive status"""

    # Arrange
    status = BuildStatus(active=False)

    # Act
    result = format_compact(status)

    # Assert
    assert result == ""


def test_format_compact_with_parallel_workers():
    """Test format_compact with parallel workers"""

    # Arrange
    status = BuildStatus(
        active=True,
        spec="001-feature",
        state=BuildState.BUILDING,
        subtasks_completed=5,
        subtasks_total=10,
        phase_current="Implementation",
        workers_active=3,
        workers_max=5,
    )

    # Act
    result = format_compact(status)

    # Assert
    assert result is not None
    assert "5/10" in result
    assert "50%" in result  # 5/10 = 50%
    # Workers should be shown when max > 1
    assert "3" in result or "W" in result  # Either worker icon or count


def test_format_full():
    """Test format_full"""

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
        workers_max=5,
        session_number=1,
    )

    # Act
    result = format_full(status)

    # Assert
    assert result is not None
    assert "001-feature" in result
    assert "building" in result
    assert "5/10" in result
    assert "Implementation" in result
    assert "3/5" in result  # workers


def test_format_full_inactive():
    """Test format_full with inactive status"""

    # Arrange
    status = BuildStatus(active=False)

    # Act
    result = format_full(status)

    # Assert
    assert result == "No active build"


def test_format_json():
    """Test format_json"""

    # Arrange
    status = BuildStatus(
        active=True,
        spec="001-feature",
        state=BuildState.BUILDING,
        subtasks_completed=5,
        subtasks_total=10,
    )

    # Act
    result = format_json(status)

    # Assert
    assert result is not None
    # Should be valid JSON
    parsed = json.loads(result)
    assert parsed["active"] is True
    assert parsed["spec"] == "001-feature"
    assert parsed["state"] == "building"


@patch("sys.argv", ["statusline.py", "--format", "compact", "--project-dir", "/tmp/test"])
def test_main_with_args():
    """Test main with command line arguments"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        manager = StatusManager(project_dir)
        manager.set_active("001-test", BuildState.BUILDING)

        # Patch sys.argv to use the temp directory
        with patch("sys.argv", ["statusline.py", "--format", "compact", "--project-dir", str(project_dir)]):
            # Act
            # Should not raise
            main()


@patch("sys.argv", ["statusline.py", "--format", "json"])
def test_main_json_format():
    """Test main with JSON format"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        manager = StatusManager(project_dir)
        manager.set_active("001-test", BuildState.BUILDING)

        with patch("sys.argv", ["statusline.py", "--format", "json", "--project-dir", str(project_dir)]):
            # Act & Assert - should not raise
            main()


@patch("sys.argv", ["statusline.py", "--spec", "001-test"])
def test_main_with_spec_filter():
    """Test main with spec filter"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        manager = StatusManager(project_dir)
        manager.set_active("001-test", BuildState.BUILDING)

        with patch("sys.argv", ["statusline.py", "--spec", "001-test", "--project-dir", str(project_dir)]):
            # Act - should not raise when spec matches
            main()


@patch("sys.argv", ["statusline.py", "--spec", "001-other"])
def test_main_with_spec_mismatch():
    """Test main with spec that doesn't match"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        manager = StatusManager(project_dir)
        manager.set_active("001-test", BuildState.BUILDING)

        with patch("sys.argv", ["statusline.py", "--spec", "001-other", "--project-dir", str(project_dir)]):
            # Act - should not raise, just return empty
            main()


def test_format_compact_complete_state():
    """Test format_compact with COMPLETE state"""

    # Arrange
    status = BuildStatus(
        active=True,
        spec="001-feature",
        state=BuildState.COMPLETE,
        subtasks_completed=10,
        subtasks_total=10,
    )

    # Act
    result = format_compact(status)

    # Assert
    assert result is not None
    # Should have success icon or "OK"


def test_format_compact_error_state():
    """Test format_compact with ERROR state"""

    # Arrange
    status = BuildStatus(
        active=True,
        spec="001-feature",
        state=BuildState.ERROR,
        subtasks_completed=5,
        subtasks_total=10,
        subtasks_failed=2,
    )

    # Act
    result = format_compact(status)

    # Assert
    assert result is not None
    # Should have error icon or "ERR"


def test_format_compact_paused_state():
    """Test format_compact with PAUSED state"""

    # Arrange
    status = BuildStatus(
        active=True,
        spec="001-feature",
        state=BuildState.PAUSED,
        subtasks_completed=5,
        subtasks_total=10,
    )

    # Act
    result = format_compact(status)

    # Assert
    assert result is not None
    # Should have pause icon or "||"
