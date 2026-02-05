"""Tests for modification_tracker"""

from merge.file_evolution.modification_tracker import ModificationTracker
from merge.file_evolution.storage import EvolutionStorage
from merge.types import FileEvolution, TaskSnapshot
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock, patch
import pytest


def test_ModificationTracker___init__():
    """Test ModificationTracker.__init__"""

    # Arrange
    storage = MagicMock(spec=EvolutionStorage)

    # Act
    instance = ModificationTracker(storage=storage)

    # Assert
    assert instance is not None
    assert instance.storage == storage


def test_ModificationTracker_record_modification():
    """Test ModificationTracker.record_modification"""

    # Arrange
    storage = MagicMock(spec=EvolutionStorage)
    storage.get_relative_path = MagicMock(return_value="test.py")
    instance = ModificationTracker(storage=storage)

    # Create an evolution entry for the file
    evolution = FileEvolution(
        file_path="test.py",
        baseline_commit="abc123",
        baseline_captured_at=datetime.now(),
        baseline_content_hash="hash1",
        baseline_snapshot_path="/baseline/test.py",
        task_snapshots=[],
    )

    task_id = "task_001"
    file_path = "test.py"
    old_content = "old content"
    new_content = "new content"
    evolutions = {"test.py": evolution}

    # Act
    result = instance.record_modification(
        task_id, file_path, old_content, new_content, evolutions
    )

    # Assert
    assert result is not None
    assert result.task_id == task_id
    assert result.content_hash_after != result.content_hash_before


def test_ModificationTracker_record_modification_not_tracked():
    """Test ModificationTracker.record_modification with untracked file"""

    # Arrange
    storage = MagicMock(spec=EvolutionStorage)
    storage.get_relative_path = MagicMock(return_value="test.py")
    instance = ModificationTracker(storage=storage)

    task_id = "task_001"
    file_path = "test.py"
    old_content = "old content"
    new_content = "new content"
    evolutions = {}  # No evolution entry

    # Act
    result = instance.record_modification(
        task_id, file_path, old_content, new_content, evolutions
    )

    # Assert
    assert result is None  # File not tracked


@patch("subprocess.run")
def test_ModificationTracker_refresh_from_git(mock_run):
    """Test ModificationTracker.refresh_from_git"""

    # Arrange
    storage = MagicMock(spec=EvolutionStorage)
    storage.project_dir = Path("/tmp/test")
    storage.get_relative_path = MagicMock(side_effect=lambda x: x)
    instance = ModificationTracker(storage=storage)

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
            return MagicMock(stdout="diff content", returncode=0, stderr="")
        # Call 4: git show for old content
        elif "show" in args[0]:
            return MagicMock(stdout="old content", returncode=0, stderr="")
        return MagicMock(stdout="", returncode=0, stderr="")

    mock_run.side_effect = mock_subprocess_calls

    # Create a test file
    with patch.object(Path, "exists", return_value=True):
        with patch.object(Path, "read_text", return_value="new content"):
            task_id = "task_001"
            worktree_path = Path("/tmp/test")
            evolutions = {}

            # Act
            instance.refresh_from_git(task_id, worktree_path, evolutions)

            # Assert - should not raise and should create evolution entry
            assert "test.py" in evolutions


def test_ModificationTracker_mark_task_completed():
    """Test ModificationTracker.mark_task_completed"""

    # Arrange
    storage = MagicMock(spec=EvolutionStorage)
    instance = ModificationTracker(storage=storage)

    # Create a snapshot without completion time
    snapshot = TaskSnapshot(
        task_id="task_001",
        task_intent="Test task",
        started_at=datetime.now(),
        completed_at=None,
    )
    evolution = FileEvolution(
        file_path="test.py",
        baseline_commit="abc123",
        baseline_captured_at=datetime.now(),
        baseline_content_hash="hash1",
        baseline_snapshot_path="/baseline/test.py",
        task_snapshots=[snapshot],
    )

    task_id = "task_001"
    evolutions = {"test.py": evolution}

    # Act
    instance.mark_task_completed(task_id, evolutions)

    # Assert - snapshot should now have completed_at
    assert snapshot.completed_at is not None
