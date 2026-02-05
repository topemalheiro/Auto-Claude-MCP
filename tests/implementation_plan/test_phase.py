"""Tests for phase"""

from implementation_plan.phase import Phase
from implementation_plan.enums import PhaseType, SubtaskStatus
from implementation_plan.subtask import Subtask
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


def test_Phase_chunks():
    """Test Phase.chunks property getter and setter"""

    # Arrange
    subtask1 = Subtask(id="1", description="Task 1")
    subtask2 = Subtask(id="2", description="Task 2")
    instance = Phase(phase=1, name="Test Phase", subtasks=[subtask1])

    # Act - test getter (chunks is alias for subtasks)
    result = instance.chunks

    # Assert
    assert len(result) == 1
    assert result[0].id == "1"

    # Act - test setter
    instance.chunks = [subtask1, subtask2]

    # Assert
    assert len(instance.subtasks) == 2
    assert instance.subtasks[0].id == "1"
    assert instance.subtasks[1].id == "2"


def test_Phase_to_dict():
    """Test Phase.to_dict"""

    # Arrange
    subtask1 = Subtask(id="1", description="Task 1", status=SubtaskStatus.COMPLETED)
    subtask2 = Subtask(id="2", description="Task 2", status=SubtaskStatus.PENDING)
    instance = Phase(
        phase=1,
        name="Test Phase",
        type=PhaseType.INVESTIGATION,
        subtasks=[subtask1, subtask2],
        depends_on=[],
        parallel_safe=True
    )

    # Act
    result = instance.to_dict()

    # Assert
    assert result["phase"] == 1
    assert result["name"] == "Test Phase"
    assert result["type"] == "investigation"
    assert len(result["subtasks"]) == 2
    assert len(result["chunks"]) == 2  # Backwards compatibility
    assert result["parallel_safe"] is True


def test_Phase_from_dict():
    """Test Phase.from_dict"""

    # Arrange
    data = {
        "phase": 2,
        "name": "From Dict Phase",
        "type": "implementation",
        "subtasks": [
            {"id": "1", "description": "Task 1", "status": "pending"}
        ],
        "depends_on": [1],
        "parallel_safe": False
    }

    # Act
    result = Phase.from_dict(data)

    # Assert
    assert result.phase == 2
    assert result.name == "From Dict Phase"
    assert result.type == PhaseType.IMPLEMENTATION
    assert len(result.subtasks) == 1
    assert result.subtasks[0].id == "1"
    assert result.depends_on == [1]
    assert result.parallel_safe is False


def test_Phase_from_dict_with_fallback():
    """Test Phase.from_dict with fallback phase"""

    # Arrange
    data = {
        "name": "Fallback Phase",
        "subtasks": []
    }

    # Act
    result = Phase.from_dict(data, fallback_phase=5)

    # Assert
    assert result.phase == 5
    assert result.name == "Fallback Phase"


def test_Phase_from_dict_with_chunks():
    """Test Phase.from_dict supports 'chunks' key for backwards compatibility"""

    # Arrange
    data = {
        "phase": 1,
        "name": "Chunks Phase",
        "chunks": [  # Using 'chunks' instead of 'subtasks'
            {"id": "1", "description": "Task 1", "status": "pending"}
        ]
    }

    # Act
    result = Phase.from_dict(data)

    # Assert
    assert len(result.subtasks) == 1
    assert result.subtasks[0].id == "1"


def test_Phase_is_complete():
    """Test Phase.is_complete"""

    # Arrange - all completed
    completed_subtasks = [
        Subtask(id="1", description="Task 1", status=SubtaskStatus.COMPLETED),
        Subtask(id="2", description="Task 2", status=SubtaskStatus.COMPLETED),
    ]
    instance = Phase(phase=1, name="Complete Phase", subtasks=completed_subtasks)

    # Act
    result = instance.is_complete()

    # Assert
    assert result is True

    # Arrange - not all completed
    mixed_subtasks = [
        Subtask(id="1", description="Task 1", status=SubtaskStatus.COMPLETED),
        Subtask(id="2", description="Task 2", status=SubtaskStatus.PENDING),
    ]
    instance.subtasks = mixed_subtasks

    # Act
    result = instance.is_complete()

    # Assert
    assert result is False


def test_Phase_get_pending_subtasks():
    """Test Phase.get_pending_subtasks"""

    # Arrange
    subtasks = [
        Subtask(id="1", description="Task 1", status=SubtaskStatus.PENDING),
        Subtask(id="2", description="Task 2", status=SubtaskStatus.COMPLETED),
        Subtask(id="3", description="Task 3", status=SubtaskStatus.PENDING),
        Subtask(id="4", description="Task 4", status=SubtaskStatus.IN_PROGRESS),
    ]
    instance = Phase(phase=1, name="Test Phase", subtasks=subtasks)

    # Act
    result = instance.get_pending_subtasks()

    # Assert
    assert len(result) == 2
    assert result[0].id == "1"
    assert result[1].id == "3"


def test_Phase_get_pending_chunks():
    """Test Phase.get_pending_chunks (backwards compatibility alias)"""

    # Arrange
    subtasks = [
        Subtask(id="1", description="Task 1", status=SubtaskStatus.PENDING),
        Subtask(id="2", description="Task 2", status=SubtaskStatus.COMPLETED),
    ]
    instance = Phase(phase=1, name="Test Phase", subtasks=subtasks)

    # Act
    result = instance.get_pending_chunks()

    # Assert
    assert len(result) == 1
    assert result[0].id == "1"


def test_Phase_get_progress():
    """Test Phase.get_progress"""

    # Arrange
    subtasks = [
        Subtask(id="1", description="Task 1", status=SubtaskStatus.COMPLETED),
        Subtask(id="2", description="Task 2", status=SubtaskStatus.COMPLETED),
        Subtask(id="3", description="Task 3", status=SubtaskStatus.PENDING),
        Subtask(id="4", description="Task 4", status=SubtaskStatus.IN_PROGRESS),
    ]
    instance = Phase(phase=1, name="Test Phase", subtasks=subtasks)

    # Act
    completed, total = instance.get_progress()

    # Assert
    assert completed == 2
    assert total == 4


def test_Phase_get_progress_empty():
    """Test Phase.get_progress with no subtasks"""

    # Arrange
    instance = Phase(phase=1, name="Empty Phase", subtasks=[])

    # Act
    completed, total = instance.get_progress()

    # Assert
    assert completed == 0
    assert total == 0
