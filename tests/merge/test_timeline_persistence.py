"""Tests for timeline_persistence"""

from merge.timeline_persistence import TimelinePersistence
from merge.timeline_models import FileTimeline, MainBranchEvent
from pathlib import Path
from datetime import datetime
import pytest
import tempfile


def test_TimelinePersistence___init__():
    """Test TimelinePersistence.__init__"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir)

        # Act
        instance = TimelinePersistence(storage_path)

        # Assert
        assert instance is not None
        assert instance.storage_path == storage_path.resolve()
        assert instance.timelines_dir.exists()


def test_TimelinePersistence_load_all_timelines():
    """Test TimelinePersistence.load_all_timelines"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir)
        instance = TimelinePersistence(storage_path)

        # Act
        result = instance.load_all_timelines()

        # Assert
        assert result is not None
        assert isinstance(result, dict)
        assert len(result) == 0  # No timelines saved yet


def test_TimelinePersistence_save_timeline():
    """Test TimelinePersistence.save_timeline"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir)
        instance = TimelinePersistence(storage_path)

        file_path = "test.py"
        timeline = FileTimeline(file_path=file_path)

        # Act
        instance.save_timeline(file_path, timeline)

        # Assert - should not raise
        assert True


def test_TimelinePersistence_update_index():
    """Test TimelinePersistence.update_index"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir)
        instance = TimelinePersistence(storage_path)

        file_paths = ["test.py", "main.ts"]

        # Act
        instance.update_index(file_paths)

        # Assert - should not raise
        assert True
