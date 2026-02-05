"""Comprehensive tests for merge/ai_resolver/resolver.py"""

from merge.ai_resolver.resolver import AIResolver
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


class TestAIResolverInit:
    """Tests for AIResolver initialization"""

    def test_init_with_ai_function(self):
        """Test initialization with AI function"""
        ai_call_fn = MagicMock(return_value="response")
        instance = AIResolver(ai_call_fn=ai_call_fn)

        assert instance.ai_call_fn == ai_call_fn
        assert instance._call_count == 0
        assert instance._total_tokens == 0

    def test_init_without_ai_function(self):
        """Test initialization without AI function"""
        instance = AIResolver()

        assert instance.ai_call_fn is None
        assert instance._call_count == 0

    def test_init_custom_max_tokens(self):
        """Test initialization with custom max tokens"""
        instance = AIResolver(max_context_tokens=10000)

        assert instance.max_context_tokens == 10000

    def test_stats_property(self):
        """Test stats property returns correct dict"""
        instance = AIResolver()
        instance._call_count = 5
        instance._total_tokens = 2500

        stats = instance.stats

        assert stats["calls_made"] == 5
        assert stats["estimated_tokens_used"] == 2500


class TestSetAIFunction:
    """Tests for set_ai_function method"""

    def test_set_ai_function_updates_function(self):
        """Test that set_ai_function updates the AI function"""
        ai_fn1 = MagicMock(return_value="response1")
        ai_fn2 = MagicMock(return_value="response2")

        instance = AIResolver(ai_call_fn=ai_fn1)
        assert instance.ai_call_fn == ai_fn1

        instance.set_ai_function(ai_fn2)
        assert instance.ai_call_fn == ai_fn2


class TestResetStats:
    """Tests for reset_stats method"""

    def test_reset_stats_clears_counters(self):
        """Test that reset_stats clears all counters"""
        instance = AIResolver()
        instance._call_count = 10
        instance._total_tokens = 5000

        instance.reset_stats()

        assert instance._call_count == 0
        assert instance._total_tokens == 0


class TestBuildContext:
    """Tests for build_context method"""

    def test_build_context_basic(self):
        """Test basic context building"""
        conflict = ConflictRegion(
            file_path="test.py",
            location="function:foo",
            tasks_involved=["task_001"],
            change_types=[ChangeType.MODIFY_FUNCTION],
            severity=ConflictSeverity.MEDIUM,
            can_auto_merge=False,
            reason="Test conflict"
        )

        baseline = "def foo(): pass"

        change = SemanticChange(
            change_type=ChangeType.MODIFY_FUNCTION,
            target="foo",
            location="function:foo",
            line_start=1,
            line_end=1,
            content_after="def foo(): return 1"
        )

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Modify foo",
            started_at=datetime.now(),
            semantic_changes=[change]
        )

        instance = AIResolver()
        context = instance.build_context(conflict, baseline, [snapshot])

        assert context.file_path == "test.py"
        assert context.location == "function:foo"
        assert context.baseline_code == baseline
        assert len(context.task_changes) == 1
        assert context.task_changes[0][0] == "task_001"

    def test_build_context_filters_relevant_changes(self):
        """Test that only relevant changes are included"""
        conflict = ConflictRegion(
            file_path="test.py",
            location="function:foo",
            tasks_involved=["task_001"],
            change_types=[ChangeType.MODIFY_FUNCTION],
            severity=ConflictSeverity.MEDIUM,
            can_auto_merge=False,
            reason="Test"
        )

        change1 = SemanticChange(
            change_type=ChangeType.MODIFY_FUNCTION,
            target="foo",
            location="function:foo",  # Same location
            line_start=1,
            line_end=1,
            content_after="new"
        )

        change2 = SemanticChange(
            change_type=ChangeType.ADD_IMPORT,
            target="os",
            location="file",  # Different location
            line_start=1,
            line_end=1,
            content_after="import os"
        )

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Test",
            started_at=datetime.now(),
            semantic_changes=[change1, change2]
        )

        instance = AIResolver()
        context = instance.build_context(conflict, "", [snapshot])

        # Only change1 should be included (same location)
        assert len(context.task_changes[0][2]) == 1

    def test_build_context_includes_language(self):
        """Test that language is inferred from file extension"""
        conflict = ConflictRegion(
            file_path="test.tsx",
            location="component:App",
            tasks_involved=["task_001"],
            change_types=[ChangeType.MODIFY_FUNCTION],
            severity=ConflictSeverity.LOW,
            can_auto_merge=False,
            reason="Test"
        )

        instance = AIResolver()
        context = instance.build_context(conflict, "", [])

        # Language should be "tsx" for .tsx files
        assert context.language == "tsx"

    def test_build_context_no_intent(self):
        """Test context when task has no intent"""
        conflict = ConflictRegion(
            file_path="test.py",
            location="function:foo",
            tasks_involved=["task_001"],
            change_types=[ChangeType.MODIFY_FUNCTION],
            severity=ConflictSeverity.LOW,
            can_auto_merge=False,
            reason="Test"
        )

        # Create a semantic change for this task
        change = SemanticChange(
            change_type=ChangeType.MODIFY_FUNCTION,
            target="foo",
            location="function:foo",
            line_start=1,
            line_end=1,
            content_after="new"
        )

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="",  # Empty string instead of None
            started_at=datetime.now(),
            semantic_changes=[change]
        )

        instance = AIResolver()
        context = instance.build_context(conflict, "", [snapshot])

        # Should use "No intent specified" when intent is empty
        assert "No intent specified" in context.task_changes[0][1]


class TestResolveConflict:
    """Tests for resolve_conflict method"""

    def test_resolve_conflict_no_ai_function(self):
        """Test resolve_conflict when no AI function is set"""
        conflict = ConflictRegion(
            file_path="test.py",
            location="function:foo",
            tasks_involved=["task_001"],
            change_types=[ChangeType.MODIFY_FUNCTION],
            severity=ConflictSeverity.MEDIUM,
            can_auto_merge=False,
            reason="Test"
        )

        instance = AIResolver(ai_call_fn=None)
        result = instance.resolve_conflict(conflict, "", [])

        assert result.decision == MergeDecision.NEEDS_HUMAN_REVIEW
        assert "No AI function configured" in result.explanation

    def test_resolve_conflict_context_too_large(self):
        """Test resolve_conflict when context exceeds token limit"""
        conflict = ConflictRegion(
            file_path="test.py",
            location="function:foo",
            tasks_involved=["task_001"],
            change_types=[ChangeType.MODIFY_FUNCTION],
            severity=ConflictSeverity.MEDIUM,
            can_auto_merge=False,
            reason="Test"
        )

        ai_call_fn = MagicMock(return_value="response")
        instance = AIResolver(ai_call_fn=ai_call_fn, max_context_tokens=100)

        # Mock a context with high token estimate
        with patch.object(instance, 'build_context') as mock_build:
            mock_ctx = MagicMock()
            mock_ctx.estimated_tokens = 1000  # Exceeds max
            mock_build.return_value = mock_ctx

            result = instance.resolve_conflict(conflict, "", [])

            assert result.decision == MergeDecision.NEEDS_HUMAN_REVIEW
            assert "Context too large" in result.explanation

    def test_resolve_conflict_success(self):
        """Test successful conflict resolution"""
        conflict = ConflictRegion(
            file_path="test.py",
            location="function:foo",
            tasks_involved=["task_001"],
            change_types=[ChangeType.MODIFY_FUNCTION],
            severity=ConflictSeverity.MEDIUM,
            can_auto_merge=False,
            reason="Test"
        )

        ai_response = "```python\ndef merged():\n    pass\n```"
        ai_call_fn = MagicMock(return_value=ai_response)

        instance = AIResolver(ai_call_fn=ai_call_fn)
        result = instance.resolve_conflict(conflict, "", [])

        assert result.decision == MergeDecision.AI_MERGED
        assert "def merged():" in result.merged_content
        assert result.ai_calls_made == 1

    def test_resolve_conflict_cannot_parse_response(self):
        """Test when AI response cannot be parsed"""
        conflict = ConflictRegion(
            file_path="test.py",
            location="function:foo",
            tasks_involved=["task_001"],
            change_types=[ChangeType.MODIFY_FUNCTION],
            severity=ConflictSeverity.MEDIUM,
            can_auto_merge=False,
            reason="Test"
        )

        ai_call_fn = MagicMock(return_value="No code block here")
        instance = AIResolver(ai_call_fn=ai_call_fn)

        result = instance.resolve_conflict(conflict, "", [])

        assert result.decision == MergeDecision.NEEDS_HUMAN_REVIEW
        assert "Could not parse AI" in result.explanation

    def test_resolve_conflict_ai_call_fails(self):
        """Test when AI call raises exception"""
        conflict = ConflictRegion(
            file_path="test.py",
            location="function:foo",
            tasks_involved=["task_001"],
            change_types=[ChangeType.MODIFY_FUNCTION],
            severity=ConflictSeverity.MEDIUM,
            can_auto_merge=False,
            reason="Test"
        )

        ai_call_fn = MagicMock(side_effect=Exception("API error"))
        instance = AIResolver(ai_call_fn=ai_call_fn)

        result = instance.resolve_conflict(conflict, "", [])

        assert result.decision == MergeDecision.FAILED
        assert "API error" in result.error


class TestResolveMultipleConflicts:
    """Tests for resolve_multiple_conflicts method"""

    def test_resolve_multiple_individual(self):
        """Test resolving multiple conflicts individually (batch=False)"""
        conflicts = [
            ConflictRegion(
                file_path="test.py",
                location=f"function:func{i}",
                tasks_involved=["task_001"],
                change_types=[ChangeType.MODIFY_FUNCTION],
                severity=ConflictSeverity.LOW,
                can_auto_merge=False,
                reason=f"Conflict {i}"
            )
            for i in range(3)
        ]

        baseline_codes = {f"function:func{i}": f"def func{i}(): pass" for i in range(3)}

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Test",
            started_at=datetime.now(),
            semantic_changes=[]
        )

        ai_call_fn = MagicMock(return_value="```python\ndef merged(): pass\n```")
        instance = AIResolver(ai_call_fn=ai_call_fn)

        results = instance.resolve_multiple_conflicts(
            conflicts, baseline_codes, [snapshot], batch=False
        )

        assert len(results) == 3
        assert all(r.decision in {MergeDecision.AI_MERGED, MergeDecision.NEEDS_HUMAN_REVIEW}
                   for r in results)

    def test_resolve_multiple_batch_same_file(self):
        """Test batch resolving conflicts in same file"""
        conflicts = [
            ConflictRegion(
                file_path="test.py",
                location=f"function:func{i}",
                tasks_involved=["task_001"],
                change_types=[ChangeType.MODIFY_FUNCTION],
                severity=ConflictSeverity.LOW,
                can_auto_merge=False,
                reason=f"Conflict {i}"
            )
            for i in range(3)
        ]

        baseline_codes = {f"function:func{i}": f"def func{i}(): pass" for i in range(3)}

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Test",
            started_at=datetime.now(),
            semantic_changes=[]
        )

        # Mock batch response
        ai_response = """## Location: function:func0
```python
def func0(): pass
```

## Location: function:func1
```python
def func1(): pass
```

## Location: function:func2
```python
def func2(): pass
```"""

        ai_call_fn = MagicMock(return_value=ai_response)
        instance = AIResolver(ai_call_fn=ai_call_fn)

        results = instance.resolve_multiple_conflicts(
            conflicts, baseline_codes, [snapshot], batch=True
        )

        # With batch, should get 1 result for the file
        assert len(results) >= 1

    def test_resolve_multiple_batch_different_files(self):
        """Test batch resolving conflicts in different files"""
        conflicts = [
            ConflictRegion(
                file_path=f"file{i}.py",
                location="function:foo",
                tasks_involved=["task_001"],
                change_types=[ChangeType.MODIFY_FUNCTION],
                severity=ConflictSeverity.LOW,
                can_auto_merge=False,
                reason="Test"
            )
            for i in range(2)
        ]

        baseline_codes = {"function:foo": "def foo(): pass"}

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Test",
            started_at=datetime.now(),
            semantic_changes=[]
        )

        ai_call_fn = MagicMock(return_value="```python\ndef foo(): pass\n```")
        instance = AIResolver(ai_call_fn=ai_call_fn)

        results = instance.resolve_multiple_conflicts(
            conflicts, baseline_codes, [snapshot], batch=True
        )

        # Each file should be resolved separately
        assert len(results) == 2

    def test_resolve_multiple_empty_list(self):
        """Test resolving empty conflict list"""
        instance = AIResolver()

        results = instance.resolve_multiple_conflicts([], {}, [], batch=True)

        assert len(results) == 0


class TestResolveFileBatch:
    """Tests for _resolve_file_batch method"""

    def test_resolve_file_batch_no_ai_function(self):
        """Test batch resolve without AI function"""
        conflicts = [
            ConflictRegion(
                file_path="test.py",
                location="function:foo",
                tasks_involved=["task_001"],
                change_types=[ChangeType.MODIFY_FUNCTION],
                severity=ConflictSeverity.LOW,
                can_auto_merge=False,
                reason="Test"
            )
        ]

        instance = AIResolver(ai_call_fn=None)
        result = instance._resolve_file_batch("test.py", conflicts, {}, [])

        assert result.decision == MergeDecision.NEEDS_HUMAN_REVIEW
        assert "No AI function configured" in result.explanation

    def test_resolve_file_batch_token_limit_fallback(self):
        """Test batch resolve falls back to individual when token limit exceeded"""
        conflicts = [
            ConflictRegion(
                file_path="test.py",
                location=f"function:func{i}",
                tasks_involved=["task_001"],
                change_types=[ChangeType.MODIFY_FUNCTION],
                severity=ConflictSeverity.LOW,
                can_auto_merge=False,
                reason="Test"
            )
            for i in range(3)
        ]

        baseline_codes = {f"function:func{i}": f"def func{i}(): pass" for i in range(3)}

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Test",
            started_at=datetime.now(),
            semantic_changes=[]
        )

        ai_call_fn = MagicMock(return_value="```python\ndef merged(): pass\n```")
        instance = AIResolver(ai_call_fn=ai_call_fn, max_context_tokens=10)

        # Mock build_context to return high token estimate
        with patch.object(instance, 'build_context') as mock_build:
            mock_ctx = MagicMock()
            mock_ctx.estimated_tokens = 1000  # Exceeds limit
            mock_build.return_value = mock_ctx

            result = instance._resolve_file_batch("test.py", conflicts, baseline_codes, [snapshot])

            # Should fall back and still produce result
            assert result is not None

    def test_resolve_file_batch_success(self):
        """Test successful batch resolution"""
        conflicts = [
            ConflictRegion(
                file_path="test.py",
                location="function:foo",
                tasks_involved=["task_001"],
                change_types=[ChangeType.MODIFY_FUNCTION],
                severity=ConflictSeverity.LOW,
                can_auto_merge=False,
                reason="Test"
            )
        ]

        baseline_codes = {"function:foo": "def foo(): pass"}

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Test",
            started_at=datetime.now(),
            semantic_changes=[]
        )

        ai_response = """## Location: function:foo
```python
def merged(): pass
```"""

        ai_call_fn = MagicMock(return_value=ai_response)
        instance = AIResolver(ai_call_fn=ai_call_fn)

        result = instance._resolve_file_batch("test.py", conflicts, baseline_codes, [snapshot])

        assert result.decision == MergeDecision.AI_MERGED
        assert len(result.conflicts_resolved) == 1

    def test_resolve_file_batch_partial_resolution(self):
        """Test batch where some conflicts remain unresolved"""
        conflicts = [
            ConflictRegion(
                file_path="test.py",
                location=f"function:func{i}",
                tasks_involved=["task_001"],
                change_types=[ChangeType.MODIFY_FUNCTION],
                severity=ConflictSeverity.LOW,
                can_auto_merge=False,
                reason="Test"
            )
            for i in range(2)
        ]

        baseline_codes = {f"function:func{i}": f"def func{i}(): pass" for i in range(2)}

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Test",
            started_at=datetime.now(),
            semantic_changes=[]
        )

        # Response only resolves first conflict
        ai_response = """## Location: function:func0
```python
def func0(): pass
```"""

        ai_call_fn = MagicMock(return_value=ai_response)
        instance = AIResolver(ai_call_fn=ai_call_fn)

        result = instance._resolve_file_batch("test.py", conflicts, baseline_codes, [snapshot])

        # Should have one resolved and one remaining
        assert result.decision == MergeDecision.NEEDS_HUMAN_REVIEW
        assert len(result.conflicts_resolved) > 0
        assert len(result.conflicts_remaining) > 0


class TestCanResolve:
    """Tests for can_resolve method"""

    def test_can_resolve_with_ai_required(self):
        """Test can_resolve returns True for AI_REQUIRED with AI function"""
        conflict = ConflictRegion(
            file_path="test.py",
            location="function:foo",
            tasks_involved=["task_001"],
            change_types=[ChangeType.MODIFY_FUNCTION],
            severity=ConflictSeverity.MEDIUM,
            can_auto_merge=False,
            merge_strategy=MergeStrategy.AI_REQUIRED,
            reason="Test"
        )

        ai_call_fn = MagicMock()
        instance = AIResolver(ai_call_fn=ai_call_fn)

        result = instance.can_resolve(conflict)

        assert result is True

    def test_can_resolve_no_ai_function(self):
        """Test can_resolve returns False without AI function"""
        conflict = ConflictRegion(
            file_path="test.py",
            location="function:foo",
            tasks_involved=["task_001"],
            change_types=[ChangeType.MODIFY_FUNCTION],
            severity=ConflictSeverity.MEDIUM,
            can_auto_merge=False,
            merge_strategy=MergeStrategy.AI_REQUIRED,
            reason="Test"
        )

        instance = AIResolver(ai_call_fn=None)

        result = instance.can_resolve(conflict)

        assert result is False

    def test_can_resolve_low_severity(self):
        """Test can_resolve returns False for LOW severity"""
        conflict = ConflictRegion(
            file_path="test.py",
            location="function:foo",
            tasks_involved=["task_001"],
            change_types=[ChangeType.MODIFY_FUNCTION],
            severity=ConflictSeverity.LOW,
            can_auto_merge=False,
            merge_strategy=MergeStrategy.AI_REQUIRED,
            reason="Test"
        )

        instance = AIResolver(ai_call_fn=MagicMock())

        result = instance.can_resolve(conflict)

        assert result is False

    def test_can_resolve_none_merge_strategy(self):
        """Test can_resolve with None merge_strategy"""
        conflict = ConflictRegion(
            file_path="test.py",
            location="function:foo",
            tasks_involved=["task_001"],
            change_types=[ChangeType.MODIFY_FUNCTION],
            severity=ConflictSeverity.HIGH,
            can_auto_merge=False,
            merge_strategy=None,
            reason="Test"
        )

        instance = AIResolver(ai_call_fn=MagicMock())

        result = instance.can_resolve(conflict)

        assert result is True

    def test_can_resolve_auto_merge_strategy(self):
        """Test can_resolve returns False for non-AI strategies"""
        conflict = ConflictRegion(
            file_path="test.py",
            location="function:foo",
            tasks_involved=["task_001"],
            change_types=[ChangeType.MODIFY_FUNCTION],
            severity=ConflictSeverity.MEDIUM,
            can_auto_merge=True,
            merge_strategy=MergeStrategy.COMBINE_IMPORTS,  # A specific strategy, not AI_REQUIRED
            reason="Can auto merge"
        )

        instance = AIResolver(ai_call_fn=MagicMock())

        result = instance.can_resolve(conflict)

        # Should return False since merge_strategy is not AI_REQUIRED or None
        assert result is False
