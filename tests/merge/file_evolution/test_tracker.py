"""Tests for tracker"""

from merge.file_evolution.tracker import FileEvolutionTracker
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock, patch
import pytest
import tempfile


def test_FileEvolutionTracker___init__():
    """Test FileEvolutionTracker.__init__"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        # Act
        instance = FileEvolutionTracker(project_dir=project_dir)

        # Assert
        assert instance is not None


@patch("subprocess.run")
def test_FileEvolutionTracker_capture_baselines(mock_run):
    """Test FileEvolutionTracker.capture_baselines"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        # Create a test file
        (project_dir / "test.py").write_text("test content")

        mock_run.return_value.stdout = "test.py\n"
        instance = FileEvolutionTracker(project_dir=project_dir)

        task_id = "task_001"

        # Act
        result = instance.capture_baselines(task_id, files=["test.py"], intent="Test")

        # Assert
        assert result is not None
        assert isinstance(result, dict)


def test_FileEvolutionTracker_record_modification():
    """Test FileEvolutionTracker.record_modification"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        # Create the test file
        (project_dir / "test.py").write_text("test content")
        instance = FileEvolutionTracker(project_dir=project_dir)

        # First capture a baseline
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = "test.py\n"
            instance.capture_baselines("task_001", files=["test.py"], intent="Test")

        task_id = "task_001"
        file_path = "test.py"
        old_content = "test content"
        new_content = "new content"

        # Act
        result = instance.record_modification(task_id, file_path, old_content, new_content)

        # Assert
        assert result is not None


def test_FileEvolutionTracker_get_file_evolution():
    """Test FileEvolutionTracker.get_file_evolution"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        instance = FileEvolutionTracker(project_dir=project_dir)

        file_path = "test.py"

        # Act
        result = instance.get_file_evolution(file_path)

        # Assert
        # No evolution exists yet
        assert result is None


def test_FileEvolutionTracker_get_baseline_content():
    """Test FileEvolutionTracker.get_baseline_content"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        instance = FileEvolutionTracker(project_dir=project_dir)

        file_path = "test.py"

        # Act
        result = instance.get_baseline_content(file_path)

        # Assert
        assert result is None  # No baseline captured


def test_FileEvolutionTracker_get_task_modifications():
    """Test FileEvolutionTracker.get_task_modifications"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        instance = FileEvolutionTracker(project_dir=project_dir)

        task_id = "task_001"

        # Act
        result = instance.get_task_modifications(task_id)

        # Assert
        assert result is not None
        assert isinstance(result, list)


def test_FileEvolutionTracker_get_files_modified_by_tasks():
    """Test FileEvolutionTracker.get_files_modified_by_tasks"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        instance = FileEvolutionTracker(project_dir=project_dir)

        task_ids = ["task_001", "task_002"]

        # Act
        result = instance.get_files_modified_by_tasks(task_ids)

        # Assert
        assert result is not None
        assert isinstance(result, dict)


def test_FileEvolutionTracker_get_conflicting_files():
    """Test FileEvolutionTracker.get_conflicting_files"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        instance = FileEvolutionTracker(project_dir=project_dir)

        task_ids = ["task_001", "task_002"]

        # Act
        result = instance.get_conflicting_files(task_ids)

        # Assert
        assert result is not None
        assert isinstance(result, list)


def test_FileEvolutionTracker_mark_task_completed():
    """Test FileEvolutionTracker.mark_task_completed"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        instance = FileEvolutionTracker(project_dir=project_dir)

        task_id = "task_001"

        # Act
        instance.mark_task_completed(task_id)

        # Assert - should not raise
        assert True


def test_FileEvolutionTracker_cleanup_task():
    """Test FileEvolutionTracker.cleanup_task"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        instance = FileEvolutionTracker(project_dir=project_dir)

        task_id = "task_001"

        # Act
        instance.cleanup_task(task_id)

        # Assert - should not raise
        assert True


def test_FileEvolutionTracker_get_active_tasks():
    """Test FileEvolutionTracker.get_active_tasks"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        instance = FileEvolutionTracker(project_dir=project_dir)

        # Act
        result = instance.get_active_tasks()

        # Assert
        assert result is not None
        assert isinstance(result, set)


def test_FileEvolutionTracker_get_evolution_summary():
    """Test FileEvolutionTracker.get_evolution_summary"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        instance = FileEvolutionTracker(project_dir=project_dir)

        # Act
        result = instance.get_evolution_summary()

        # Assert
        assert result is not None
        assert isinstance(result, dict)


def test_FileEvolutionTracker_export_for_merge():
    """Test FileEvolutionTracker.export_for_merge"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        instance = FileEvolutionTracker(project_dir=project_dir)

        file_path = "test.py"

        # Act
        result = instance.export_for_merge(file_path)

        # Assert
        # No evolution exists yet
        assert result is None


@patch("subprocess.run")
def test_FileEvolutionTracker_refresh_from_git(mock_run):
    """Test FileEvolutionTracker.refresh_from_git"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        instance = FileEvolutionTracker(project_dir=project_dir)

        # Create a generator function for mock results
        def mock_subprocess_calls(*args, **kwargs):
            """Generator that yields results for each subprocess.run call"""
            # Call 1: merge-base
            if "merge-base" in args[0]:
                return MagicMock(stdout="abc123\n", returncode=0, stderr="")
            # Call 2: diff --name-only
            elif "--name-only" in args[0]:
                return MagicMock(stdout="test.py\n", returncode=0, stderr="")
            # Call 3: git diff for file
            elif "diff" in args[0] and "--name-only" not in args[0]:
                return MagicMock(stdout="diff", returncode=0, stderr="")
            # Call 4: git show for old content
            elif "show" in args[0]:
                return MagicMock(stdout="old", returncode=0, stderr="")
            return MagicMock(stdout="", returncode=0, stderr="")

        mock_run.side_effect = mock_subprocess_calls

        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "read_text", return_value="new"):
                task_id = "task_001"
                worktree_path = Path("/tmp/test")

                # Act
                instance.refresh_from_git(task_id, worktree_path)

                # Assert - should not raise
                assert True
