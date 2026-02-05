"""Tests for props_strategy"""

from merge.auto_merger.strategies.props_strategy import PropsStrategy
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


def test_PropsStrategy_execute():
    """Test PropsStrategy.execute"""

    # Arrange
    change = SemanticChange(
        change_type=ChangeType.MODIFY_JSX_PROPS,
        target="App",
        location="function:App",
        line_start=10,
        line_end=10,
        content_after="<App newProp={value} />",
        metadata={"props": [{"name": "newProp", "value": "{value}"}]}
    )

    snapshot = TaskSnapshot(
        task_id="task_001",
        task_intent="Add new prop",
        started_at=datetime.now(),
        semantic_changes=[change]
    )

    conflict = ConflictRegion(
        file_path="App.tsx",
        location="function:App",
        tasks_involved=["task_001"],
        change_types=[ChangeType.MODIFY_JSX_PROPS],
        severity=ConflictSeverity.NONE,
        can_auto_merge=True
    )

    context = MergeContext(
        file_path="App.tsx",
        baseline_content="<App existingProp={value} />",
        task_snapshots=[snapshot],
        conflict=conflict
    )

    instance = PropsStrategy()

    # Act
    result = instance.execute(context)

    # Assert
    assert result is not None
    assert result.decision == MergeDecision.AUTO_MERGED
