"""Tests for baseline_capture"""

from merge.file_evolution.baseline_capture import BaselineCapture
from merge.file_evolution.storage import EvolutionStorage
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


def test_BaselineCapture___init__():
    """Test BaselineCapture.__init__"""

    # Arrange
    storage = MagicMock(spec=EvolutionStorage)
    extensions = {".py", ".tsx"}

    # Act
    instance = BaselineCapture(storage=storage, extensions=extensions)

    # Assert
    assert instance is not None
    assert instance.storage == storage
    assert instance.extensions == extensions


def test_BaselineCapture_discover_trackable_files():
    """Test BaselineCapture.discover_trackable_files"""

    # Arrange
    storage = MagicMock(spec=EvolutionStorage)
    storage.project_dir = Path("/tmp/test")
    instance = BaselineCapture(storage=storage)

    # Mock subprocess to return file list
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = "test.py\nmain.ts\nREADME.md\nsetup.sh"

        # Act
        result = instance.discover_trackable_files()

        # Assert
        assert result is not None
        assert isinstance(result, list)
        # Should filter by extension (default includes .py but not .md or .sh)
        assert len(result) >= 1
        assert any(str(f).endswith("test.py") for f in result)


@patch("subprocess.run")
def test_BaselineCapture_get_current_commit(mock_run):
    """Test BaselineCapture.get_current_commit"""

    # Arrange
    storage = MagicMock(spec=EvolutionStorage)
    storage.project_dir = Path("/tmp/test")
    instance = BaselineCapture(storage=storage)
    mock_run.return_value.stdout = "abc123def456"

    # Act
    result = instance.get_current_commit()

    # Assert
    assert result is not None
    assert isinstance(result, str)
    assert result == "abc123def456"


def test_BaselineCapture_capture_baselines():
    """Test BaselineCapture.capture_baselines"""

    # Arrange
    storage = MagicMock(spec=EvolutionStorage)
    storage.project_dir = Path("/tmp/test")
    storage.read_file_content = MagicMock(return_value="test content")
    storage.get_relative_path = MagicMock(return_value="test.py")
    storage.store_baseline_content = MagicMock(return_value="/baseline/test.py")

    task_id = "task_001"
    files = [Path("/tmp/test/test.py")]
    intent = "Test intent"

    instance = BaselineCapture(storage=storage)

    # Act
    result = instance.capture_baselines(task_id, files, intent, {})

    # Assert
    assert result is not None
    assert isinstance(result, dict)
    assert "test.py" in result
    storage.read_file_content.assert_called()
    storage.store_baseline_content.assert_called()


@patch("subprocess.run")
def test_BaselineCapture_capture_baselines_discover_files(mock_run):
    """Test BaselineCapture.capture_baselines with auto-discovery"""

    # Arrange
    storage = MagicMock(spec=EvolutionStorage)
    storage.project_dir = Path("/tmp/test")
    storage.read_file_content = MagicMock(return_value="test content")
    storage.get_relative_path = MagicMock(return_value="test.py")
    storage.store_baseline_content = MagicMock(return_value="/baseline/test.py")

    mock_run.return_value.stdout = "test.py\nmain.ts"

    task_id = "task_001"
    intent = "Test intent"

    instance = BaselineCapture(storage=storage)

    # Act - files=None should trigger discovery
    result = instance.capture_baselines(task_id, None, intent, {})

    # Assert
    assert result is not None
    assert isinstance(result, dict)
    mock_run.assert_called()
