"""Tests for serialization"""

from context.serialization import load_context, save_context, serialize_context
from context.models import TaskContext
from pathlib import Path
import pytest


def test_serialize_context():
    """Test serialize_context"""

    # Arrange
    context = TaskContext(
        task_description="Add authentication to API",
        scoped_services=["api"],
        files_to_modify=[{"path": "api/auth.py", "relevance_score": 8}],
        files_to_reference=[{"path": "api/utils.py", "relevance_score": 3}],
        patterns_discovered={"auth_pattern": "def authenticate()"},
        service_contexts={"api": {"source": "generated", "language": "python"}},
        graph_hints=["Previous work: Added login form"]
    )

    # Act
    result = serialize_context(context)

    # Assert
    assert isinstance(result, dict)
    assert result["task_description"] == "Add authentication to API"
    assert result["scoped_services"] == ["api"]
    assert "files_to_modify" in result
    assert "patterns" in result
    assert result["graph_hints"] == ["Previous work: Added login form"]


def test_save_context(tmp_path):
    """Test save_context"""

    # Arrange
    context = TaskContext(
        task_description="Test task",
        scoped_services=["web"],
        files_to_modify=[],
        files_to_reference=[],
        patterns_discovered={},
        service_contexts={},
        graph_hints=[]
    )
    output_file = tmp_path / "context.json"

    # Act
    save_context(context, output_file)

    # Assert
    assert output_file.exists()
    import json
    with open(output_file) as f:
        data = json.load(f)
    assert data["task_description"] == "Test task"


def test_load_context(tmp_path):
    """Test load_context"""

    # Arrange
    input_file = tmp_path / "test_context.json"
    import json
    test_data = {
        "task_description": "Load test",
        "scoped_services": ["api"],
        "files_to_modify": [],
        "files_to_reference": [],
        "patterns": {},
        "service_contexts": {},
        "graph_hints": []
    }
    input_file.write_text(json.dumps(test_data))

    # Act
    result = load_context(input_file)

    # Assert
    assert isinstance(result, dict)
    assert result["task_description"] == "Load test"
    assert result["scoped_services"] == ["api"]
