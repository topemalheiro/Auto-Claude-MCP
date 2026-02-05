"""Tests for ordering_strategy"""

from merge.auto_merger.strategies.ordering_strategy import OrderByDependencyStrategy, OrderByTimeStrategy
from merge.auto_merger.context import MergeContext
from merge.types import (
    ChangeType,
    ConflictRegion,
    ConflictSeverity,
    MergeDecision,
    SemanticChange,
    TaskSnapshot,
)
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


def test_OrderByDependencyStrategy_execute():
    """Test OrderByDependencyStrategy.execute"""

    # Arrange
    change1 = SemanticChange(
        change_type=ChangeType.ADD_FUNCTION,
        target="helperFunction",
        location="file_top",
        line_start=5,
        line_end=10,
        content_after="function helperFunction() { }"
    )

    change2 = SemanticChange(
        change_type=ChangeType.ADD_FUNCTION,
        target="mainFunction",
        location="file_top",
        line_start=15,
        line_end=20,
        content_after="function mainFunction() { helperFunction(); }"
    )

    snapshot = TaskSnapshot(
        task_id="task_001",
        task_intent="Add functions",
        started_at=datetime.now(),
        semantic_changes=[change1, change2]
    )

    conflict = ConflictRegion(
        file_path="test.js",
        location="file_top",
        tasks_involved=["task_001"],
        change_types=[ChangeType.ADD_FUNCTION],
        severity=ConflictSeverity.NONE,
        can_auto_merge=True
    )

    context = MergeContext(
        file_path="test.js",
        baseline_content="// Existing code\n",
        task_snapshots=[snapshot],
        conflict=conflict
    )

    instance = OrderByDependencyStrategy()

    # Act
    result = instance.execute(context)

    # Assert
    assert result is not None
    assert result.decision == MergeDecision.AUTO_MERGED


def test_OrderByTimeStrategy_execute():
    """Test OrderByTimeStrategy.execute"""

    # Arrange
    change = SemanticChange(
        change_type=ChangeType.ADD_VARIABLE,
        target="MY_VAR",
        location="file_top",
        line_start=5,
        line_end=5,
        content_after="const MY_VAR = 42"
    )

    snapshot = TaskSnapshot(
        task_id="task_001",
        task_intent="Add variable",
        started_at=datetime.now() - timedelta(seconds=10),
        semantic_changes=[change]
    )

    conflict = ConflictRegion(
        file_path="test.js",
        location="file_top",
        tasks_involved=["task_001"],
        change_types=[ChangeType.ADD_VARIABLE],
        severity=ConflictSeverity.NONE,
        can_auto_merge=True
    )

    context = MergeContext(
        file_path="test.js",
        baseline_content="// Existing code\n",
        task_snapshots=[snapshot],
        conflict=conflict
    )

    instance = OrderByTimeStrategy()

    # Act
    result = instance.execute(context)

    # Assert
    assert result is not None
    assert result.decision == MergeDecision.AUTO_MERGED
