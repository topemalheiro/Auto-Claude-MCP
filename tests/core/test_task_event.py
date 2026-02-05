"""Tests for task_event"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.task_event import TaskEventContext, TaskEventEmitter, load_task_event_context


def test_load_task_event_context_no_metadata():
    """Test load_task_event_context without metadata file"""
    # Arrange
    spec_dir = Path("/tmp/nonexistent_spec_dir")

    # Act
    result = load_task_event_context(spec_dir)

    # Assert
    assert result is not None
    assert isinstance(result, TaskEventContext)
    assert result.task_id == spec_dir.name
    assert result.spec_id == spec_dir.name
    assert result.project_id == ""
    assert result.sequence_start == 0


def test_load_task_event_context_with_metadata(tmp_path):
    """Test load_task_event_context with metadata file"""
    # Arrange
    import json

    spec_dir = tmp_path / "spec_001"
    spec_dir.mkdir()

    metadata = {
        "taskId": "task-123",
        "specId": "spec-456",
        "projectId": "proj-789",
    }
    (spec_dir / "task_metadata.json").write_text(json.dumps(metadata))

    # Act
    result = load_task_event_context(spec_dir)

    # Assert
    assert result.task_id == "task-123"
    assert result.spec_id == "spec-456"
    assert result.project_id == "proj-789"


def test_load_task_event_context_with_last_event(tmp_path):
    """Test load_task_event_context loads last sequence"""
    # Arrange
    import json

    spec_dir = tmp_path / "spec_002"
    spec_dir.mkdir()

    plan = {
        "phases": [],
        "lastEvent": {"sequence": 5},
    }
    (spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

    # Act
    result = load_task_event_context(spec_dir)

    # Assert
    assert result.sequence_start == 6  # last sequence + 1


def test_TaskEventEmitter_init():
    """Test TaskEventEmitter.__init__"""
    # Arrange
    context = TaskEventContext(
        task_id="task-123",
        spec_id="spec-456",
        project_id="proj-789",
        sequence_start=10,
    )

    # Act
    emitter = TaskEventEmitter(context)

    # Assert
    assert emitter._context == context
    assert emitter._sequence == 10


def test_TaskEventEmitter_from_spec_dir(tmp_path):
    """Test TaskEventEmitter.from_spec_dir class method"""
    # Arrange
    spec_dir = tmp_path / "spec_003"
    spec_dir.mkdir()

    # Act
    emitter = TaskEventEmitter.from_spec_dir(spec_dir)

    # Assert
    assert isinstance(emitter, TaskEventEmitter)
    assert emitter._context.task_id == spec_dir.name
    assert emitter._sequence == 0


def test_TaskEventEmitter_emit(capsys):
    """Test TaskEventEmitter.emit"""
    # Arrange
    context = TaskEventContext(
        task_id="task-123",
        spec_id="spec-456",
        project_id="proj-789",
        sequence_start=0,
    )
    emitter = TaskEventEmitter(context)

    # Act
    emitter.emit("test_event", {"data": "value"})

    # Assert
    captured = capsys.readouterr()
    assert "__TASK_EVENT__:" in captured.out
    assert "test_event" in captured.out
    assert "task-123" in captured.out
    assert emitter._sequence == 1  # Sequence incremented


def test_TaskEventEmitter_emit_without_payload(capsys):
    """Test TaskEventEmitter.emit without payload"""
    # Arrange
    context = TaskEventContext(
        task_id="task-123",
        spec_id="spec-456",
        project_id="proj-789",
        sequence_start=5,
    )
    emitter = TaskEventEmitter(context)

    # Act
    emitter.emit("simple_event")

    # Assert
    captured = capsys.readouterr()
    assert "__TASK_EVENT__:" in captured.out
    assert "simple_event" in captured.out
    assert emitter._sequence == 6


def test_TaskEventEmitter_emit_increments_sequence(capsys):
    """Test TaskEventEmitter.emit increments sequence"""
    # Arrange
    context = TaskEventContext(
        task_id="task-123",
        spec_id="spec-456",
        project_id="proj-789",
        sequence_start=0,
    )
    emitter = TaskEventEmitter(context)

    # Act - emit multiple events
    emitter.emit("event_1")
    emitter.emit("event_2")
    emitter.emit("event_3")

    # Assert
    assert emitter._sequence == 3
    captured = capsys.readouterr()
    assert captured.out.count("__TASK_EVENT__:") == 3


def test_TaskEventContext_dataclass():
    """Test TaskEventContext dataclass"""
    # Arrange & Act
    context = TaskEventContext(
        task_id="task-1",
        spec_id="spec-1",
        project_id="proj-1",
        sequence_start=100,
    )

    # Assert
    assert context.task_id == "task-1"
    assert context.spec_id == "spec-1"
    assert context.project_id == "proj-1"
    assert context.sequence_start == 100
