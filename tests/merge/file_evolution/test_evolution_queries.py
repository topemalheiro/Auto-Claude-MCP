"""Tests for evolution_queries"""

from merge.file_evolution.evolution_queries import EvolutionQueries
from merge.file_evolution.storage import EvolutionStorage
from merge.types import FileEvolution, TaskSnapshot, SemanticChange, ChangeType
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock
import pytest


def test_EvolutionQueries___init__():
    """Test EvolutionQueries.__init__"""

    # Arrange
    storage = MagicMock(spec=EvolutionStorage)

    # Act
    instance = EvolutionQueries(storage=storage)

    # Assert
    assert instance is not None
    assert instance.storage == storage


def test_EvolutionQueries_get_file_evolution():
    """Test EvolutionQueries.get_file_evolution"""

    # Arrange
    storage = MagicMock(spec=EvolutionStorage)
    storage.get_relative_path = MagicMock(return_value="test.py")
    instance = EvolutionQueries(storage=storage)

    file_path = "test.py"
    evolutions = {}

    # Act
    result = instance.get_file_evolution(file_path, evolutions)

    # Assert
    assert result is None  # No evolutions exist yet


def test_EvolutionQueries_get_baseline_content():
    """Test EvolutionQueries.get_baseline_content"""

    # Arrange
    storage = MagicMock(spec=EvolutionStorage)
    storage.get_relative_path = MagicMock(return_value="test.py")
    storage.read_baseline_content = MagicMock(return_value="baseline content")

    instance = EvolutionQueries(storage=storage)

    file_path = "test.py"
    evolutions = {}

    # Act
    result = instance.get_baseline_content(file_path, evolutions)

    # Assert
    # Should return None since no evolution exists
    assert result is None


def test_EvolutionQueries_get_task_modifications():
    """Test EvolutionQueries.get_task_modifications"""

    # Arrange
    storage = MagicMock(spec=EvolutionStorage)

    instance = EvolutionQueries(storage=storage)

    # Create a FileEvolution with a task snapshot that has modifications
    snapshot = TaskSnapshot(
        task_id="task_001",
        task_intent="Test task",
        started_at=datetime.now(),
        content_hash_before="hash1",
        content_hash_after="hash2",
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
    result = instance.get_task_modifications(task_id, evolutions)

    # Assert
    assert result is not None
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0][0] == "test.py"


def test_EvolutionQueries_get_files_modified_by_tasks():
    """Test EvolutionQueries.get_files_modified_by_tasks"""

    # Arrange
    storage = MagicMock(spec=EvolutionStorage)

    instance = EvolutionQueries(storage=storage)

    # Create FileEvolutions with task snapshots
    snapshot1 = TaskSnapshot(
        task_id="task_001",
        task_intent="Test task 1",
        started_at=datetime.now(),
        content_hash_before="hash1",
        content_hash_after="hash2",  # Different hash to indicate modification
    )
    snapshot2 = TaskSnapshot(
        task_id="task_002",
        task_intent="Test task 2",
        started_at=datetime.now(),
        content_hash_before="hash1",
        content_hash_after="hash3",  # Different hash to indicate modification
    )
    evolution = FileEvolution(
        file_path="test.py",
        baseline_commit="abc123",
        baseline_captured_at=datetime.now(),
        baseline_content_hash="hash1",
        baseline_snapshot_path="/baseline/test.py",
        task_snapshots=[snapshot1, snapshot2],
    )

    task_ids = ["task_001", "task_002"]
    evolutions = {"test.py": evolution}

    # Act
    result = instance.get_files_modified_by_tasks(task_ids, evolutions)

    # Assert
    assert result is not None
    assert isinstance(result, dict)
    assert "test.py" in result
    assert len(result["test.py"]) == 2


def test_EvolutionQueries_get_conflicting_files():
    """Test EvolutionQueries.get_conflicting_files"""

    # Arrange
    storage = MagicMock(spec=EvolutionStorage)

    instance = EvolutionQueries(storage=storage)

    # Create FileEvolution with multiple task snapshots (potential conflict)
    snapshot1 = TaskSnapshot(
        task_id="task_001",
        task_intent="Test task 1",
        started_at=datetime.now(),
        content_hash_before="hash1",
        content_hash_after="hash2",  # Different hash to indicate modification
    )
    snapshot2 = TaskSnapshot(
        task_id="task_002",
        task_intent="Test task 2",
        started_at=datetime.now(),
        content_hash_before="hash1",
        content_hash_after="hash3",  # Different hash to indicate modification
    )
    evolution = FileEvolution(
        file_path="test.py",
        baseline_commit="abc123",
        baseline_captured_at=datetime.now(),
        baseline_content_hash="hash1",
        baseline_snapshot_path="/baseline/test.py",
        task_snapshots=[snapshot1, snapshot2],
    )

    task_ids = ["task_001", "task_002"]
    evolutions = {"test.py": evolution}

    # Act
    result = instance.get_conflicting_files(task_ids, evolutions)

    # Assert
    assert result is not None
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0] == "test.py"


def test_EvolutionQueries_get_active_tasks():
    """Test EvolutionQueries.get_active_tasks"""

    # Arrange
    storage = MagicMock(spec=EvolutionStorage)

    instance = EvolutionQueries(storage=storage)

    # Create FileEvolution with active and completed tasks
    active_snapshot = TaskSnapshot(
        task_id="task_001",
        task_intent="Active task",
        started_at=datetime.now(),
        content_hash_before="hash1",
        completed_at=None,  # Active
    )
    completed_snapshot = TaskSnapshot(
        task_id="task_002",
        task_intent="Completed task",
        started_at=datetime.now(),
        content_hash_before="hash1",
        completed_at=datetime.now(),  # Completed
    )
    evolution = FileEvolution(
        file_path="test.py",
        baseline_commit="abc123",
        baseline_captured_at=datetime.now(),
        baseline_content_hash="hash1",
        baseline_snapshot_path="/baseline/test.py",
        task_snapshots=[active_snapshot, completed_snapshot],
    )

    evolutions = {"test.py": evolution}

    # Act
    result = instance.get_active_tasks(evolutions)

    # Assert
    assert result is not None
    assert isinstance(result, set)
    assert "task_001" in result
    assert "task_002" not in result


def test_EvolutionQueries_get_evolution_summary():
    """Test EvolutionQueries.get_evolution_summary"""

    # Arrange
    storage = MagicMock(spec=EvolutionStorage)

    instance = EvolutionQueries(storage=storage)

    snapshot = TaskSnapshot(
        task_id="task_001",
        task_intent="Test task",
        started_at=datetime.now(),
        content_hash_before="hash1",
        semantic_changes=[
            SemanticChange(
                change_type=ChangeType.ADD_FUNCTION,
                target="test_func",
                location="test.py:10",
                line_start=10,
                line_end=15,
            )
        ],
    )
    evolution = FileEvolution(
        file_path="test.py",
        baseline_commit="abc123",
        baseline_captured_at=datetime.now(),
        baseline_content_hash="hash1",
        baseline_snapshot_path="/baseline/test.py",
        task_snapshots=[snapshot],
    )

    evolutions = {"test.py": evolution}

    # Act
    result = instance.get_evolution_summary(evolutions)

    # Assert
    assert result is not None
    assert isinstance(result, dict)
    assert result["total_files_tracked"] == 1
    assert result["total_tasks"] == 1
    assert result["files_with_potential_conflicts"] == 0
    assert result["active_tasks"] == 1


def test_EvolutionQueries_export_for_merge():
    """Test EvolutionQueries.export_for_merge"""

    # Arrange
    storage = MagicMock(spec=EvolutionStorage)
    storage.get_relative_path = MagicMock(return_value="test.py")
    storage.read_baseline_content = MagicMock(return_value="baseline content")

    instance = EvolutionQueries(storage=storage)

    snapshot = TaskSnapshot(
        task_id="task_001",
        task_intent="Test task",
        started_at=datetime.now(),
        content_hash_before="hash1",
    )
    evolution = FileEvolution(
        file_path="test.py",
        baseline_commit="abc123",
        baseline_captured_at=datetime.now(),
        baseline_content_hash="hash1",
        baseline_snapshot_path="/baseline/test.py",
        task_snapshots=[snapshot],
    )

    file_path = "test.py"
    evolutions = {"test.py": evolution}

    # Act
    result = instance.export_for_merge(file_path, evolutions)

    # Assert
    assert result is not None
    assert result["file_path"] == "test.py"
    assert result["baseline_content"] == "baseline content"
    assert len(result["tasks"]) == 1


def test_EvolutionQueries_cleanup_task():
    """Test EvolutionQueries.cleanup_task"""

    # Arrange
    storage = MagicMock(spec=EvolutionStorage)
    storage.baselines_dir = Path("/tmp/baselines")

    instance = EvolutionQueries(storage=storage)

    snapshot = TaskSnapshot(
        task_id="task_001",
        task_intent="Test task",
        started_at=datetime.now(),
        content_hash_before="hash1",
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
    result = instance.cleanup_task(task_id, evolutions, remove_baselines=False)

    # Assert
    assert result is not None
    assert isinstance(result, dict)
    # After cleanup, the evolution should be empty (no snapshots)
    assert "test.py" not in result or len(result.get("test.py", {}).task_snapshots) == 0
