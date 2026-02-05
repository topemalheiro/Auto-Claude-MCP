"""Tests for hooks_strategy"""

from merge.auto_merger.strategies.hooks_strategy import HooksStrategy, HooksThenWrapStrategy
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


def test_HooksStrategy_execute():
    """Test HooksStrategy.execute"""

    # Arrange
    change = SemanticChange(
        change_type=ChangeType.ADD_HOOK_CALL,
        target="useEffect",
        location="function:App",
        line_start=5,
        line_end=5,
        content_after="    useEffect(() => {}, [])"
    )

    snapshot = TaskSnapshot(
        task_id="task_001",
        task_intent="Add useEffect hook",
        started_at=datetime.now(),
        semantic_changes=[change]
    )

    conflict = ConflictRegion(
        file_path="App.tsx",
        location="function:App",
        tasks_involved=["task_001"],
        change_types=[ChangeType.ADD_HOOK_CALL],
        severity=ConflictSeverity.NONE,
        can_auto_merge=True
    )

    context = MergeContext(
        file_path="App.tsx",
        baseline_content="function App() {\n    return <div>Hello</div>\n}",
        task_snapshots=[snapshot],
        conflict=conflict
    )

    instance = HooksStrategy()

    # Act
    result = instance.execute(context)

    # Assert
    assert result is not None
    assert result.decision == MergeDecision.AUTO_MERGED


def test_HooksThenWrapStrategy_execute():
    """Test HooksThenWrapStrategy.execute"""

    # Arrange
    hook_change = SemanticChange(
        change_type=ChangeType.ADD_HOOK_CALL,
        target="useAuth",
        location="function:App",
        line_start=5,
        line_end=5,
        content_after="    const { user } = useAuth()"
    )

    jsx_change = SemanticChange(
        change_type=ChangeType.WRAP_JSX,
        target="App",
        location="function:App",
        line_start=10,
        line_end=10,
        content_after='<AuthProvider>\n    return <div>Hello</div>\n</AuthProvider>'
    )

    snapshot = TaskSnapshot(
        task_id="task_001",
        task_intent="Add auth wrapper",
        started_at=datetime.now(),
        semantic_changes=[hook_change, jsx_change]
    )

    conflict = ConflictRegion(
        file_path="App.tsx",
        location="function:App",
        tasks_involved=["task_001"],
        change_types=[ChangeType.ADD_HOOK_CALL, ChangeType.WRAP_JSX],
        severity=ConflictSeverity.NONE,
        can_auto_merge=True
    )

    context = MergeContext(
        file_path="App.tsx",
        baseline_content="function App() {\n    return <div>Hello</div>\n}",
        task_snapshots=[snapshot],
        conflict=conflict
    )

    instance = HooksThenWrapStrategy()

    # Act
    result = instance.execute(context)

    # Assert
    assert result is not None
    assert result.decision == MergeDecision.AUTO_MERGED
