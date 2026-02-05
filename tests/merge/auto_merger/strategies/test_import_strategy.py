"""Tests for import_strategy"""

from merge.auto_merger.strategies.import_strategy import ImportStrategy
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


def test_ImportStrategy_execute():
    """Test ImportStrategy.execute"""

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

    instance = ImportStrategy()

    # Act
    result = instance.execute(context)

    # Assert
    assert result is not None
    assert result.decision == MergeDecision.AUTO_MERGED
    assert "useEffect" in result.merged_content
