"""Tests for storage"""

from merge.file_evolution.storage import EvolutionStorage
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
import tempfile


def test_EvolutionStorage___init__():
    """Test EvolutionStorage.__init__"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "project"
        storage_dir = Path(tmpdir) / "storage"

        project_dir.mkdir()

        # Act
        instance = EvolutionStorage(project_dir=project_dir, storage_dir=storage_dir)

        # Assert
        assert instance is not None
        assert instance.project_dir == project_dir.resolve()
        assert instance.storage_dir == storage_dir.resolve()


def test_EvolutionStorage_load_evolutions():
    """Test EvolutionStorage.load_evolutions"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "project"
        storage_dir = Path(tmpdir) / "storage"

        project_dir.mkdir()
        instance = EvolutionStorage(project_dir=project_dir, storage_dir=storage_dir)

        # Act
        result = instance.load_evolutions()

        # Assert
        assert result is not None
        assert isinstance(result, dict)


def test_EvolutionStorage_save_evolutions():
    """Test EvolutionStorage.save_evolutions"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "project"
        storage_dir = Path(tmpdir) / "storage"

        project_dir.mkdir()
        instance = EvolutionStorage(project_dir=project_dir, storage_dir=storage_dir)

        evolutions = {}

        # Act
        instance.save_evolutions(evolutions)

        # Assert - should not raise
        assert True


def test_EvolutionStorage_store_baseline_content():
    """Test EvolutionStorage.store_baseline_content"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "project"
        storage_dir = Path(tmpdir) / "storage"

        project_dir.mkdir()
        instance = EvolutionStorage(project_dir=project_dir, storage_dir=storage_dir)

        file_path = "test.py"
        content = "test content"
        task_id = "task_001"

        # Act
        result = instance.store_baseline_content(file_path, content, task_id)

        # Assert
        assert result is not None
        assert isinstance(result, (str, Path))


def test_EvolutionStorage_read_baseline_content():
    """Test EvolutionStorage.read_baseline_content"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "project"
        storage_dir = Path(tmpdir) / "storage"

        project_dir.mkdir()
        instance = EvolutionStorage(project_dir=project_dir, storage_dir=storage_dir)

        # Store baseline first
        snapshot_path = instance.store_baseline_content("test.py", "test content", "task_001")

        # Act
        result = instance.read_baseline_content(snapshot_path)

        # Assert
        assert result == "test content"


def test_EvolutionStorage_read_file_content():
    """Test EvolutionStorage.read_file_content"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "project"
        storage_dir = Path(tmpdir) / "storage"

        project_dir.mkdir()
        test_file = project_dir / "test.py"
        test_file.write_text("test content")

        instance = EvolutionStorage(project_dir=project_dir, storage_dir=storage_dir)

        # Act
        result = instance.read_file_content("test.py")

        # Assert
        assert result == "test content"


def test_EvolutionStorage_get_relative_path():
    """Test EvolutionStorage.get_relative_path"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "project"
        storage_dir = Path(tmpdir) / "storage"

        project_dir.mkdir()
        instance = EvolutionStorage(project_dir=project_dir, storage_dir=storage_dir)

        # Act
        result = instance.get_relative_path(str(project_dir / "src" / "test.py"))

        # Assert
        assert "src" in str(result) or "test.py" in str(result)
