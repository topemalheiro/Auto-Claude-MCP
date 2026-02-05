"""Tests for context"""

from merge.ai_resolver.context import ConflictContext
from merge.types import ChangeType, SemanticChange
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


def test_ConflictContext_to_prompt_context():
    """Test ConflictContext.to_prompt_context"""

    # Arrange
    change = SemanticChange(
        change_type=ChangeType.ADD_FUNCTION,
        target="newFunction",
        location="file_top",
        line_start=10,
        line_end=15,
        content_after="def newFunction():\n    pass"
    )

    instance = ConflictContext(
        file_path="src/test.py",
        location="file_top",
        baseline_code="def existing():\n    pass",
        task_changes=[("task_001", "Add new function", [change])],
        conflict_description="Tasks made conflicting changes",
        language="python"
    )

    # Act
    result = instance.to_prompt_context()

    # Assert
    assert result is not None
    assert "src/test.py" in result
    assert "file_top" in result
    assert "task_001" in result
    assert "Add new function" in result
