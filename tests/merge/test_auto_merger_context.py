"""
Comprehensive tests for auto_merger.context module
"""

from datetime import datetime
from merge.auto_merger.context import MergeContext
from merge.types import ChangeType, ConflictRegion, ConflictSeverity, SemanticChange, TaskSnapshot
import pytest


class TestMergeContext:
    """Test MergeContext dataclass"""

    def test_merge_context_creation(self):
        """Test creating a MergeContext with all required fields"""
        file_path = "src/components/App.tsx"
        baseline_content = "function App() {\n  return <div>Hello</div>;\n}"

        task_snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Add user authentication",
            started_at=datetime.now(),
        )

        conflict = ConflictRegion(
            file_path=file_path,
            location="function:App",
            tasks_involved=["task_001", "task_002"],
            change_types=[ChangeType.ADD_HOOK_CALL, ChangeType.WRAP_JSX],
            severity=ConflictSeverity.LOW,
            can_auto_merge=True,
            reason="Both tasks added hooks to same function",
        )

        context = MergeContext(
            file_path=file_path,
            baseline_content=baseline_content,
            task_snapshots=[task_snapshot],
            conflict=conflict,
        )

        assert context.file_path == file_path
        assert context.baseline_content == baseline_content
        assert len(context.task_snapshots) == 1
        assert context.task_snapshots[0].task_id == "task_001"
        assert context.conflict == conflict

    def test_merge_context_with_multiple_snapshots(self):
        """Test MergeContext with multiple task snapshots"""
        now = datetime.now()

        snapshot1 = TaskSnapshot(
            task_id="task_001",
            task_intent="Add auth hook",
            started_at=now,
        )

        snapshot2 = TaskSnapshot(
            task_id="task_002",
            task_intent="Add loading state",
            started_at=now,
        )

        snapshot3 = TaskSnapshot(
            task_id="task_003",
            task_intent="Add error handling",
            started_at=now,
        )

        conflict = ConflictRegion(
            file_path="App.tsx",
            location="function:App",
            tasks_involved=["task_001", "task_002", "task_003"],
            change_types=[ChangeType.ADD_HOOK_CALL],
            severity=ConflictSeverity.MEDIUM,
            can_auto_merge=True,
        )

        context = MergeContext(
            file_path="App.tsx",
            baseline_content="old content",
            task_snapshots=[snapshot1, snapshot2, snapshot3],
            conflict=conflict,
        )

        assert len(context.task_snapshots) == 3
        assert context.task_snapshots[0].task_id == "task_001"
        assert context.task_snapshots[1].task_id == "task_002"
        assert context.task_snapshots[2].task_id == "task_003"

    def test_merge_context_with_empty_baseline(self):
        """Test MergeContext with empty baseline content (new file)"""
        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Create new component",
            started_at=datetime.now(),
        )

        conflict = ConflictRegion(
            file_path="NewComponent.tsx",
            location="file_top",
            tasks_involved=["task_001"],
            change_types=[ChangeType.ADD_FUNCTION],
            severity=ConflictSeverity.NONE,
            can_auto_merge=True,
        )

        context = MergeContext(
            file_path="NewComponent.tsx",
            baseline_content="",
            task_snapshots=[snapshot],
            conflict=conflict,
        )

        assert context.baseline_content == ""

    def test_merge_context_with_snapshots_containing_semantic_changes(self):
        """Test MergeContext where snapshots contain semantic changes"""
        now = datetime.now()

        change1 = SemanticChange(
            change_type=ChangeType.ADD_HOOK_CALL,
            target="useAuth",
            location="function:App",
            line_start=2,
            line_end=2,
            content_after="const { user } = useAuth();",
        )

        change2 = SemanticChange(
            change_type=ChangeType.ADD_IMPORT,
            target="useAuth",
            location="file_top",
            line_start=1,
            line_end=1,
            content_after="import { useAuth } from './hooks';",
        )

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Add authentication",
            started_at=now,
            semantic_changes=[change1, change2],
        )

        conflict = ConflictRegion(
            file_path="App.tsx",
            location="function:App",
            tasks_involved=["task_001"],
            change_types=[ChangeType.ADD_HOOK_CALL],
            severity=ConflictSeverity.NONE,
            can_auto_merge=True,
        )

        context = MergeContext(
            file_path="App.tsx",
            baseline_content="function App() {\n  return <div/>;\n}",
            task_snapshots=[snapshot],
            conflict=conflict,
        )

        assert len(context.task_snapshots[0].semantic_changes) == 2
        assert context.task_snapshots[0].semantic_changes[0].target == "useAuth"
        assert context.task_snapshots[0].semantic_changes[1].change_type == ChangeType.ADD_IMPORT

    def test_merge_context_with_conflict_with_merge_strategy(self):
        """Test MergeContext where conflict includes merge strategy"""
        from merge.types import MergeStrategy

        conflict = ConflictRegion(
            file_path="App.tsx",
            location="function:App",
            tasks_involved=["task_001", "task_002"],
            change_types=[ChangeType.ADD_HOOK_CALL, ChangeType.ADD_VARIABLE],
            severity=ConflictSeverity.LOW,
            can_auto_merge=True,
            merge_strategy=MergeStrategy.HOOKS_FIRST,
            reason="Both tasks added hooks to same function",
        )

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Add feature",
            started_at=datetime.now(),
        )

        context = MergeContext(
            file_path="App.tsx",
            baseline_content="content",
            task_snapshots=[snapshot],
            conflict=conflict,
        )

        assert context.conflict.merge_strategy == MergeStrategy.HOOKS_FIRST
        assert context.conflict.reason == "Both tasks added hooks to same function"

    def test_merge_context_with_various_severity_levels(self):
        """Test MergeContext with different conflict severity levels"""
        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Test task",
            started_at=datetime.now(),
        )

        severities = [
            ConflictSeverity.NONE,
            ConflictSeverity.LOW,
            ConflictSeverity.MEDIUM,
            ConflictSeverity.HIGH,
            ConflictSeverity.CRITICAL,
        ]

        for severity in severities:
            conflict = ConflictRegion(
                file_path="test.py",
                location="file_top",
                tasks_involved=["task_001"],
                change_types=[ChangeType.ADD_IMPORT],
                severity=severity,
                can_auto_merge=severity in [ConflictSeverity.NONE, ConflictSeverity.LOW],
            )

            context = MergeContext(
                file_path="test.py",
                baseline_content="content",
                task_snapshots=[snapshot],
                conflict=conflict,
            )

            assert context.conflict.severity == severity

    def test_merge_context_with_snapshots_with_content_hashes(self):
        """Test MergeContext where snapshots have content hashes"""
        now = datetime.now()

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Modify file",
            started_at=now,
            content_hash_before="abc123def456",
            content_hash_after="def789ghi012",
        )

        conflict = ConflictRegion(
            file_path="test.ts",
            location="file_top",
            tasks_involved=["task_001"],
            change_types=[ChangeType.MODIFY_FUNCTION],
            severity=ConflictSeverity.MEDIUM,
            can_auto_merge=False,
        )

        context = MergeContext(
            file_path="test.ts",
            baseline_content="baseline content",
            task_snapshots=[snapshot],
            conflict=conflict,
        )

        assert context.task_snapshots[0].content_hash_before == "abc123def456"
        assert context.task_snapshots[0].content_hash_after == "def789ghi012"

    def test_merge_context_with_complex_baseline_content(self):
        """Test MergeContext with complex baseline content"""
        complex_content = """
import React from 'react';
import { useState } from 'react';

interface Props {
    name: string;
}

function App({ name }: Props) {
    const [count, setCount] = useState(0);
    return (
        <div>
            <h1>Hello {name}</h1>
            <p>Count: {count}</p>
        </div>
    );
}

export default App;
"""

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Add feature",
            started_at=datetime.now(),
        )

        conflict = ConflictRegion(
            file_path="App.tsx",
            location="function:App",
            tasks_involved=["task_001"],
            change_types=[ChangeType.ADD_HOOK_CALL],
            severity=ConflictSeverity.NONE,
            can_auto_merge=True,
        )

        context = MergeContext(
            file_path="App.tsx",
            baseline_content=complex_content,
            task_snapshots=[snapshot],
            conflict=conflict,
        )

        assert len(context.baseline_content) > 0
        assert "import React" in context.baseline_content
        assert "function App" in context.baseline_content

    def test_merge_context_with_raw_diff_in_snapshot(self):
        """Test MergeContext where snapshot includes raw diff"""
        now = datetime.now()

        raw_diff = """@@ -1,3 +1,4 @@
 import React;
+import { useAuth } from './hooks';

 function App() {
"""

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Add auth import",
            started_at=now,
            raw_diff=raw_diff,
        )

        conflict = ConflictRegion(
            file_path="App.tsx",
            location="file_top",
            tasks_involved=["task_001"],
            change_types=[ChangeType.ADD_IMPORT],
            severity=ConflictSeverity.NONE,
            can_auto_merge=True,
        )

        context = MergeContext(
            file_path="App.tsx",
            baseline_content="import React;\n\nfunction App() {}",
            task_snapshots=[snapshot],
            conflict=conflict,
        )

        assert context.task_snapshots[0].raw_diff == raw_diff
        assert "@@ -1,3" in context.task_snapshots[0].raw_diff

    def test_merge_context_multiline_baseline_content(self):
        """Test MergeContext with multiline baseline content"""
        baseline = "line1\nline2\nline3\nline4\nline5"

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Test",
            started_at=datetime.now(),
        )

        conflict = ConflictRegion(
            file_path="test.py",
            location="file_top",
            tasks_involved=["task_001"],
            change_types=[ChangeType.ADD_IMPORT],
            severity=ConflictSeverity.NONE,
            can_auto_merge=True,
        )

        context = MergeContext(
            file_path="test.py",
            baseline_content=baseline,
            task_snapshots=[snapshot],
            conflict=conflict,
        )

        lines = context.baseline_content.split("\n")
        assert len(lines) == 5
        assert lines[0] == "line1"
        assert lines[4] == "line5"

    def test_merge_context_with_special_characters_in_paths(self):
        """Test MergeContext with special characters in file paths"""
        special_paths = [
            "src/components/My Component.tsx",
            "src/components/My-Component.tsx",
            "src/components/My_Component.tsx",
            "src/components/my.component.tsx",
        ]

        for file_path in special_paths:
            snapshot = TaskSnapshot(
                task_id="task_001",
                task_intent="Test",
                started_at=datetime.now(),
            )

            conflict = ConflictRegion(
                file_path=file_path,
                location="file_top",
                tasks_involved=["task_001"],
                change_types=[ChangeType.ADD_IMPORT],
                severity=ConflictSeverity.NONE,
                can_auto_merge=True,
            )

            context = MergeContext(
                file_path=file_path,
                baseline_content="content",
                task_snapshots=[snapshot],
                conflict=conflict,
            )

            assert context.file_path == file_path

    def test_merge_context_with_completed_timestamp(self):
        """Test MergeContext with snapshots that have completed_at timestamps"""
        from datetime import timedelta
        now = datetime.now()
        completed = now + timedelta(minutes=5)

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Test task",
            started_at=now,
            completed_at=completed,
        )

        conflict = ConflictRegion(
            file_path="test.py",
            location="file_top",
            tasks_involved=["task_001"],
            change_types=[ChangeType.ADD_FUNCTION],
            severity=ConflictSeverity.NONE,
            can_auto_merge=True,
        )

        context = MergeContext(
            file_path="test.py",
            baseline_content="content",
            task_snapshots=[snapshot],
            conflict=conflict,
        )

        assert context.task_snapshots[0].completed_at is not None
        assert context.task_snapshots[0].completed_at > context.task_snapshots[0].started_at

    def test_merge_context_with_metadata_in_semantic_changes(self):
        """Test MergeContext where semantic changes include metadata"""
        now = datetime.now()

        change = SemanticChange(
            change_type=ChangeType.ADD_HOOK_CALL,
            target="useAuth",
            location="function:App",
            line_start=2,
            line_end=2,
            content_after="const { user } = useAuth();",
            metadata={"dependency": "useAuth must be called within component", "async": False},
        )

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Add auth",
            started_at=now,
            semantic_changes=[change],
        )

        conflict = ConflictRegion(
            file_path="App.tsx",
            location="function:App",
            tasks_involved=["task_001"],
            change_types=[ChangeType.ADD_HOOK_CALL],
            severity=ConflictSeverity.NONE,
            can_auto_merge=True,
        )

        context = MergeContext(
            file_path="App.tsx",
            baseline_content="content",
            task_snapshots=[snapshot],
            conflict=conflict,
        )

        assert "dependency" in context.task_snapshots[0].semantic_changes[0].metadata
        assert context.task_snapshots[0].semantic_changes[0].metadata["async"] is False

    def test_merge_context_empty_task_snapshots_list(self):
        """Test MergeContext with empty task snapshots list"""
        conflict = ConflictRegion(
            file_path="test.py",
            location="file_top",
            tasks_involved=[],
            change_types=[],
            severity=ConflictSeverity.NONE,
            can_auto_merge=True,
        )

        context = MergeContext(
            file_path="test.py",
            baseline_content="content",
            task_snapshots=[],
            conflict=conflict,
        )

        assert len(context.task_snapshots) == 0

    def test_merge_context_with_unicode_content(self):
        """Test MergeContext with unicode content"""
        unicode_content = "def hello():\n    print('Hello, 世界! 🌍')\n    return 'Привет'"

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Add unicode",
            started_at=datetime.now(),
        )

        conflict = ConflictRegion(
            file_path="test.py",
            location="file_top",
            tasks_involved=["task_001"],
            change_types=[ChangeType.ADD_FUNCTION],
            severity=ConflictSeverity.NONE,
            can_auto_merge=True,
        )

        context = MergeContext(
            file_path="test.py",
            baseline_content=unicode_content,
            task_snapshots=[snapshot],
            conflict=conflict,
        )

        assert "世界" in context.baseline_content
        assert "🌍" in context.baseline_content
        assert "Привет" in context.baseline_content
