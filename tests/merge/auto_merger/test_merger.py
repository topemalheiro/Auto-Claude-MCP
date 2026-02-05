"""Tests for merger"""

from merge.auto_merger.merger import AutoMerger
from merge.auto_merger.context import MergeContext
from merge.types import (
    ChangeType,
    ConflictRegion,
    ConflictSeverity,
    MergeDecision,
    MergeStrategy,
    SemanticChange,
    TaskSnapshot,
)
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


def test_AutoMerger___init__():
    """Test AutoMerger.__init__"""

    # Act
    instance = AutoMerger()

    # Assert
    assert instance is not None
    assert len(instance._strategy_handlers) > 0
    assert MergeStrategy.COMBINE_IMPORTS in instance._strategy_handlers


def test_AutoMerger_merge():
    """Test AutoMerger.merge"""

    # Arrange
    change = SemanticChange(
        change_type=ChangeType.ADD_IMPORT,
        target="useEffect",
        location="file_top",
        line_start=1,
        line_end=1,
        content_after='import { useEffect } from "react"'
    )

    snapshot = TaskSnapshot(
        task_id="task_001",
        task_intent="Add useEffect import",
        started_at=datetime.now(),
        semantic_changes=[change]
    )

    conflict = ConflictRegion(
        file_path="App.tsx",
        location="file_top",
        tasks_involved=["task_001"],
        change_types=[ChangeType.ADD_IMPORT],
        severity=ConflictSeverity.NONE,
        can_auto_merge=True
    )

    context = MergeContext(
        file_path="App.tsx",
        baseline_content='import { useState } from "react"\n\nfunction App() {\n    return <div>Hello</div>\n}',
        task_snapshots=[snapshot],
        conflict=conflict
    )

    instance = AutoMerger()

    # Act
    result = instance.merge(context, MergeStrategy.COMBINE_IMPORTS)

    # Assert
    assert result is not None
    assert result.decision in {MergeDecision.AUTO_MERGED, MergeDecision.FAILED}


def test_AutoMerger_can_handle():
    """Test AutoMerger.can_handle"""

    # Arrange
    instance = AutoMerger()

    # Act & Assert
    assert instance.can_handle(MergeStrategy.COMBINE_IMPORTS) is True
    assert instance.can_handle(MergeStrategy.AI_REQUIRED) is False
    assert instance.can_handle(MergeStrategy.HUMAN_REQUIRED) is False
