"""Tests for append_strategy"""

from merge.auto_merger.strategies.append_strategy import (
    AppendFunctionsStrategy,
    AppendMethodsStrategy,
    AppendStatementsStrategy,
)
from merge.auto_merger.context import MergeContext
from merge.types import (
    ChangeType,
    ConflictRegion,
    ConflictSeverity,
    MergeDecision,
    SemanticChange,
    TaskSnapshot,
)
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


def test_AppendFunctionsStrategy_execute():
    """Test AppendFunctionsStrategy.execute"""

    # Arrange
    change = SemanticChange(
        change_type=ChangeType.ADD_FUNCTION,
        target="newFunction",
        location="file_top",
        line_start=10,
        line_end=15,
        content_after="def newFunction():\n    pass"
    )

    snapshot = TaskSnapshot(
        task_id="task_001",
        task_intent="Add new function",
        started_at=datetime.now(),
        semantic_changes=[change]
    )

    conflict = ConflictRegion(
        file_path="test.py",
        location="file_top",
        tasks_involved=["task_001"],
        change_types=[ChangeType.ADD_FUNCTION],
        severity=ConflictSeverity.NONE,
        can_auto_merge=True
    )

    context = MergeContext(
        file_path="test.py",
        baseline_content="def existing():\n    pass",
        task_snapshots=[snapshot],
        conflict=conflict
    )

    instance = AppendFunctionsStrategy()

    # Act
    result = instance.execute(context)

    # Assert
    assert result is not None
    assert result.decision == MergeDecision.AUTO_MERGED
    assert "def newFunction()" in result.merged_content


def test_AppendMethodsStrategy_execute():
    """Test AppendMethodsStrategy.execute"""

    # Arrange
    change = SemanticChange(
        change_type=ChangeType.ADD_METHOD,
        target="MyClass.newMethod",
        location="class:MyClass",
        line_start=10,
        line_end=15,
        content_after="    def newMethod(self):\n        pass"
    )

    snapshot = TaskSnapshot(
        task_id="task_001",
        task_intent="Add new method",
        started_at=datetime.now(),
        semantic_changes=[change]
    )

    conflict = ConflictRegion(
        file_path="test.py",
        location="class:MyClass",
        tasks_involved=["task_001"],
        change_types=[ChangeType.ADD_METHOD],
        severity=ConflictSeverity.NONE,
        can_auto_merge=True
    )

    context = MergeContext(
        file_path="test.py",
        baseline_content="class MyClass:\n    def existing(self):\n        pass",
        task_snapshots=[snapshot],
        conflict=conflict
    )

    instance = AppendMethodsStrategy()

    # Act
    result = instance.execute(context)

    # Assert
    assert result is not None
    assert result.decision == MergeDecision.AUTO_MERGED


def test_AppendStatementsStrategy_execute():
    """Test AppendStatementsStrategy.execute"""

    # Arrange
    change = SemanticChange(
        change_type=ChangeType.ADD_VARIABLE,
        target="MY_VAR",
        location="file_top",
        line_start=5,
        line_end=5,
        content_after="MY_VAR = 42"
    )

    snapshot = TaskSnapshot(
        task_id="task_001",
        task_intent="Add variable",
        started_at=datetime.now(),
        semantic_changes=[change]
    )

    conflict = ConflictRegion(
        file_path="test.py",
        location="file_top",
        tasks_involved=["task_001"],
        change_types=[ChangeType.ADD_VARIABLE],
        severity=ConflictSeverity.NONE,
        can_auto_merge=True
    )

    context = MergeContext(
        file_path="test.py",
        baseline_content="def existing():\n    pass",
        task_snapshots=[snapshot],
        conflict=conflict
    )

    instance = AppendStatementsStrategy()

    # Act
    result = instance.execute(context)

    # Assert
    assert result is not None
    assert result.decision == MergeDecision.AUTO_MERGED
    assert "MY_VAR = 42" in result.merged_content
