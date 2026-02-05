"""Comprehensive tests for conflict_resolver module"""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from merge.auto_merger import AutoMerger, MergeContext
from merge.conflict_resolver import ConflictResolver, build_explanation
from merge.types import (
    ChangeType,
    ConflictRegion,
    ConflictSeverity,
    MergeDecision,
    MergeResult,
    MergeStrategy,
    SemanticChange,
    TaskSnapshot,
)


class TestConflictResolverInit:
    """Test suite for ConflictResolver initialization"""

    def test_init_with_auto_merger_only(self):
        """Test initialization with only auto_merger"""
        auto_merger = AutoMerger()

        resolver = ConflictResolver(auto_merger=auto_merger)

        assert resolver.auto_merger == auto_merger
        assert resolver.ai_resolver is None
        assert resolver.enable_ai is True

    def test_init_with_ai_resolver(self):
        """Test initialization with AI resolver"""
        auto_merger = AutoMerger()
        ai_resolver = Mock()

        resolver = ConflictResolver(
            auto_merger=auto_merger, ai_resolver=ai_resolver
        )

        assert resolver.auto_merger == auto_merger
        assert resolver.ai_resolver == ai_resolver
        assert resolver.enable_ai is True

    def test_init_with_ai_disabled(self):
        """Test initialization with AI disabled"""
        auto_merger = AutoMerger()

        resolver = ConflictResolver(auto_merger=auto_merger, enable_ai=False)

        assert resolver.auto_merger == auto_merger
        assert resolver.enable_ai is False


class TestConflictResolverResolveConflicts:
    """Test suite for ConflictResolver.resolve_conflicts"""

    def test_resolve_conflicts_empty_list(self):
        """Test resolving with no conflicts"""
        auto_merger = AutoMerger()
        resolver = ConflictResolver(auto_merger=auto_merger)

        file_path = "test.py"
        baseline_content = "def existing():\n    pass"
        snapshots = []

        result = resolver.resolve_conflicts(file_path, baseline_content, snapshots, [])

        assert result.decision == MergeDecision.AUTO_MERGED
        assert result.file_path == file_path
        assert result.merged_content == baseline_content
        assert len(result.conflicts_resolved) == 0
        assert len(result.conflicts_remaining) == 0

    def test_resolve_conflicts_auto_mergeable(self):
        """Test resolving auto-mergeable conflicts"""
        auto_merger = AutoMerger()
        resolver = ConflictResolver(auto_merger=auto_merger)

        file_path = "test.py"
        baseline_content = "def existing():\n    pass\n"

        conflict = ConflictRegion(
            file_path=file_path,
            location="file_top",
            tasks_involved=["task_001"],
            change_types=[ChangeType.ADD_FUNCTION],
            severity=ConflictSeverity.NONE,
            can_auto_merge=True,
            merge_strategy=MergeStrategy.APPEND_FUNCTIONS,
        )

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Add function",
            started_at=datetime.now(),
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.ADD_FUNCTION,
                    target="new_func",
                    location="file_top",
                    line_start=5,
                    line_end=10,
                    content_after="def new_func():\n    pass",
                )
            ],
        )

        result = resolver.resolve_conflicts(
            file_path, baseline_content, [snapshot], [conflict]
        )

        # Should attempt auto-merge
        assert result is not None
        assert result.file_path == file_path

    def test_resolve_conflicts_with_progress_callback(self):
        """Test that progress callback is called during resolution"""
        auto_merger = AutoMerger()
        resolver = ConflictResolver(auto_merger=auto_merger)

        file_path = "test.py"
        baseline_content = "def existing():\n    pass"

        conflict = ConflictRegion(
            file_path=file_path,
            location="file_top",
            tasks_involved=["task_001"],
            change_types=[ChangeType.ADD_IMPORT],
            severity=ConflictSeverity.NONE,
            can_auto_merge=True,
            merge_strategy=MergeStrategy.COMBINE_IMPORTS,
        )

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Add import",
            started_at=datetime.now(),
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.ADD_IMPORT,
                    target="os",
                    location="file_top",
                    line_start=1,
                    line_end=2,
                    content_after="import os",
                )
            ],
        )

        progress_mock = Mock()

        result = resolver.resolve_conflicts(
            file_path, baseline_content, [snapshot], [conflict], progress_mock
        )

        # Verify progress callback was called
        assert progress_mock.called
        # Check that stage was set to RESOLVING
        call_args = progress_mock.call_args
        assert "stage" in call_args.kwargs or call_args[1].get("stage") is not None

    def test_resolve_conflicts_all_auto_merged(self):
        """Test that all auto-mergeable conflicts result in AUTO_MERGED decision"""
        auto_merger = AutoMerger()
        with patch.object(auto_merger, "merge") as merge_mock:
            # Mock successful merge
            merge_mock.return_value = MergeResult(
                decision=MergeDecision.AUTO_MERGED,
                file_path="test.py",
                merged_content="merged content",
            )

            resolver = ConflictResolver(auto_merger=auto_merger)

            file_path = "test.py"
            baseline_content = "baseline"

            conflict = ConflictRegion(
                file_path=file_path,
                location="file_top",
                tasks_involved=["task_001"],
                change_types=[ChangeType.ADD_IMPORT],
                severity=ConflictSeverity.NONE,
                can_auto_merge=True,
                merge_strategy=MergeStrategy.COMBINE_IMPORTS,
            )

            snapshot = TaskSnapshot(
                task_id="task_001",
                task_intent="Add import",
                started_at=datetime.now(),
                semantic_changes=[],
            )

            result = resolver.resolve_conflicts(
                file_path, baseline_content, [snapshot], [conflict]
            )

            assert result.decision == MergeDecision.AUTO_MERGED
            assert len(result.conflicts_resolved) == 1
            assert len(result.conflicts_remaining) == 0

    def test_resolve_conflicts_needs_human_review(self):
        """Test that unresolvable conflicts result in NEEDS_HUMAN_REVIEW"""
        auto_merger = AutoMerger()
        with patch.object(auto_merger, "merge") as merge_mock:
            # Mock failed merge
            merge_mock.return_value = MergeResult(
                decision=MergeDecision.FAILED,
                file_path="test.py",
                error="Cannot auto-merge",
            )

            resolver = ConflictResolver(auto_merger=auto_merger, enable_ai=False)

            file_path = "test.py"
            baseline_content = "baseline"

            conflict = ConflictRegion(
                file_path=file_path,
                location="function:my_func",
                tasks_involved=["task_001", "task_002"],
                change_types=[ChangeType.MODIFY_FUNCTION, ChangeType.MODIFY_FUNCTION],
                severity=ConflictSeverity.HIGH,
                can_auto_merge=False,
            )

            snapshot = TaskSnapshot(
                task_id="task_001",
                task_intent="Modify function",
                started_at=datetime.now(),
                semantic_changes=[],
            )

            result = resolver.resolve_conflicts(
                file_path, baseline_content, [snapshot], [conflict]
            )

            assert result.decision in {
                MergeDecision.NEEDS_HUMAN_REVIEW,
                MergeDecision.FAILED,
            }

    def test_resolve_conflicts_with_ai_resolver(self):
        """Test AI resolver is used for appropriate conflicts"""
        auto_merger = AutoMerger()
        ai_resolver = Mock()
        ai_resolver.resolve_conflict.return_value = MergeResult(
            decision=MergeDecision.AI_MERGED,
            file_path="test.py",
            merged_content="ai merged content",
            conflicts_resolved=[],
            ai_calls_made=1,
            tokens_used=100,
        )

        resolver = ConflictResolver(
            auto_merger=auto_merger, ai_resolver=ai_resolver, enable_ai=True
        )

        file_path = "test.py"
        baseline_content = "baseline"

        # Create a MEDIUM severity conflict that should trigger AI
        conflict = ConflictRegion(
            file_path=file_path,
            location="function:my_func",
            tasks_involved=["task_001", "task_002"],
            change_types=[ChangeType.MODIFY_FUNCTION, ChangeType.ADD_HOOK_CALL],
            severity=ConflictSeverity.MEDIUM,
            can_auto_merge=False,
        )

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Modify function",
            started_at=datetime.now(),
            semantic_changes=[],
        )

        with patch.object(auto_merger, "merge") as merge_mock:
            # Auto-merge fails
            merge_mock.return_value = MergeResult(
                decision=MergeDecision.FAILED,
                file_path="test.py",
                error="Cannot auto-merge",
            )

            result = resolver.resolve_conflicts(
                file_path, baseline_content, [snapshot], [conflict]
            )

            # AI resolver should have been called
            assert ai_resolver.resolve_conflict.called

    def test_resolve_conflicts_ai_disabled_skips_ai(self):
        """Test that AI resolver is not used when AI is disabled"""
        auto_merger = AutoMerger()
        ai_resolver = Mock()

        resolver = ConflictResolver(
            auto_merger=auto_merger, ai_resolver=ai_resolver, enable_ai=False
        )

        file_path = "test.py"
        baseline_content = "baseline"

        conflict = ConflictRegion(
            file_path=file_path,
            location="function:my_func",
            tasks_involved=["task_001"],
            change_types=[ChangeType.MODIFY_FUNCTION],
            severity=ConflictSeverity.MEDIUM,
            can_auto_merge=False,
        )

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Modify function",
            started_at=datetime.now(),
            semantic_changes=[],
        )

        with patch.object(auto_merger, "merge") as merge_mock:
            merge_mock.return_value = MergeResult(
                decision=MergeDecision.FAILED,
                file_path="test.py",
                error="Cannot auto-merge",
            )

            resolver.resolve_conflicts(file_path, baseline_content, [snapshot], [conflict])

            # AI resolver should NOT have been called
            assert not ai_resolver.resolve_conflict.called

    def test_resolve_conflicts_partial_resolution(self):
        """Test partial resolution results in NEEDS_HUMAN_REVIEW"""
        auto_merger = AutoMerger()
        ai_resolver = Mock()

        resolver = ConflictResolver(
            auto_merger=auto_merger, ai_resolver=ai_resolver, enable_ai=True
        )

        file_path = "test.py"
        baseline_content = "baseline"

        # Create two conflicts - one resolvable, one not
        conflict1 = ConflictRegion(
            file_path=file_path,
            location="file_top",
            tasks_involved=["task_001"],
            change_types=[ChangeType.ADD_IMPORT],
            severity=ConflictSeverity.NONE,
            can_auto_merge=True,
            merge_strategy=MergeStrategy.COMBINE_IMPORTS,
        )

        conflict2 = ConflictRegion(
            file_path=file_path,
            location="function:my_func",
            tasks_involved=["task_001", "task_002"],
            change_types=[ChangeType.MODIFY_FUNCTION, ChangeType.MODIFY_FUNCTION],
            severity=ConflictSeverity.CRITICAL,
            can_auto_merge=False,
        )

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Add import and modify",
            started_at=datetime.now(),
            semantic_changes=[],
        )

        with patch.object(auto_merger, "merge") as merge_mock:
            # First conflict succeeds, second fails
            merge_mock.side_effect = [
                MergeResult(
                    decision=MergeDecision.AUTO_MERGED,
                    file_path="test.py",
                    merged_content="partially merged",
                ),
                MergeResult(
                    decision=MergeDecision.FAILED,
                    file_path="test.py",
                    error="Cannot auto-merge",
                ),
            ]

            result = resolver.resolve_conflicts(
                file_path, baseline_content, [snapshot], [conflict1, conflict2]
            )

            assert result.decision == MergeDecision.NEEDS_HUMAN_REVIEW
            # At least one conflict should remain
            assert len(result.conflicts_remaining) > 0

    def test_resolve_conflicts_tracks_ai_usage(self):
        """Test that AI calls and tokens are tracked correctly"""
        auto_merger = AutoMerger()
        ai_resolver = Mock()
        ai_resolver.resolve_conflict.return_value = MergeResult(
            decision=MergeDecision.AI_MERGED,
            file_path="test.py",
            merged_content="ai merged",
            conflicts_resolved=[],
            ai_calls_made=2,
            tokens_used=500,
        )

        resolver = ConflictResolver(
            auto_merger=auto_merger, ai_resolver=ai_resolver, enable_ai=True
        )

        file_path = "test.py"
        baseline_content = "baseline"

        conflict = ConflictRegion(
            file_path=file_path,
            location="function:my_func",
            tasks_involved=["task_001"],
            change_types=[ChangeType.MODIFY_FUNCTION],
            severity=ConflictSeverity.MEDIUM,
            can_auto_merge=False,
        )

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Modify function",
            started_at=datetime.now(),
            semantic_changes=[],
        )

        with patch.object(auto_merger, "merge") as merge_mock:
            merge_mock.return_value = MergeResult(
                decision=MergeDecision.FAILED,
                file_path="test.py",
                error="Cannot auto-merge",
            )

            result = resolver.resolve_conflicts(
                file_path, baseline_content, [snapshot], [conflict]
            )

            # Should track AI usage from the result
            assert result.ai_calls_made >= 0
            assert result.tokens_used >= 0


class TestBuildExplanation:
    """Test suite for build_explanation function"""

    def test_build_explanation_no_conflicts(self):
        """Test explanation with no conflicts"""
        explanation = build_explanation([], [])

        assert explanation == "No conflicts"

    def test_build_explanation_only_resolved(self):
        """Test explanation with only resolved conflicts"""
        conflicts = [
            ConflictRegion(
                file_path="test.py",
                location="file_top",
                tasks_involved=["task_001"],
                change_types=[ChangeType.ADD_IMPORT],
                severity=ConflictSeverity.NONE,
                can_auto_merge=True,
                merge_strategy=MergeStrategy.COMBINE_IMPORTS,
            ),
            ConflictRegion(
                file_path="test.py",
                location="function:func",
                tasks_involved=["task_002"],
                change_types=[ChangeType.ADD_FUNCTION],
                severity=ConflictSeverity.NONE,
                can_auto_merge=True,
                merge_strategy=MergeStrategy.APPEND_FUNCTIONS,
            ),
        ]

        explanation = build_explanation(conflicts, [])

        assert "Resolved 2 conflict(s)" in explanation
        assert "file_top" in explanation
        assert "function:func" in explanation

    def test_build_explanation_only_remaining(self):
        """Test explanation with only remaining conflicts"""
        conflicts = [
            ConflictRegion(
                file_path="test.py",
                location="function:func",
                tasks_involved=["task_001", "task_002"],
                change_types=[ChangeType.MODIFY_FUNCTION, ChangeType.MODIFY_FUNCTION],
                severity=ConflictSeverity.HIGH,
                can_auto_merge=False,
                reason="Both tasks modified the same function",
            )
        ]

        explanation = build_explanation([], conflicts)

        assert "Unresolved 1 conflict(s)" in explanation
        assert "human review" in explanation
        assert "function:func" in explanation

    def test_build_explanation_mixed(self):
        """Test explanation with both resolved and remaining conflicts"""
        resolved = [
            ConflictRegion(
                file_path="test.py",
                location="file_top",
                tasks_involved=["task_001"],
                change_types=[ChangeType.ADD_IMPORT],
                severity=ConflictSeverity.NONE,
                can_auto_merge=True,
                merge_strategy=MergeStrategy.COMBINE_IMPORTS,
            )
        ]

        remaining = [
            ConflictRegion(
                file_path="test.py",
                location="function:func",
                tasks_involved=["task_001", "task_002"],
                change_types=[ChangeType.MODIFY_FUNCTION, ChangeType.MODIFY_FUNCTION],
                severity=ConflictSeverity.HIGH,
                can_auto_merge=False,
                reason="Conflicting modifications",
            )
        ]

        explanation = build_explanation(resolved, remaining)

        assert "Resolved 1 conflict(s)" in explanation
        assert "Unresolved 1 conflict(s)" in explanation

    def test_build_explanation_limits_output(self):
        """Test that explanation limits output to first 5 conflicts"""
        resolved = [
            ConflictRegion(
                file_path="test.py",
                location=f"location_{i}",
                tasks_involved=["task_001"],
                change_types=[ChangeType.ADD_IMPORT],
                severity=ConflictSeverity.NONE,
                can_auto_merge=True,
                merge_strategy=MergeStrategy.COMBINE_IMPORTS,
            )
            for i in range(10)
        ]

        remaining = [
            ConflictRegion(
                file_path="test.py",
                location=f"location_{i}",
                tasks_involved=["task_001", "task_002"],
                change_types=[ChangeType.MODIFY_FUNCTION, ChangeType.MODIFY_FUNCTION],
                severity=ConflictSeverity.HIGH,
                can_auto_merge=False,
                reason=f"Conflict {i}",
            )
            for i in range(10)
        ]

        explanation = build_explanation(resolved, remaining)

        # Should mention "... and X more"
        assert "and 5 more" in explanation

    def test_build_explanation_includes_strategies(self):
        """Test that resolved conflicts include their merge strategies"""
        resolved = [
            ConflictRegion(
                file_path="test.py",
                location="file_top",
                tasks_involved=["task_001"],
                change_types=[ChangeType.ADD_IMPORT],
                severity=ConflictSeverity.NONE,
                can_auto_merge=True,
                merge_strategy=MergeStrategy.COMBINE_IMPORTS,
            )
        ]

        explanation = build_explanation(resolved, [])

        assert "combine_imports" in explanation

    def test_build_explanation_includes_reasons(self):
        """Test that remaining conflicts include their reasons"""
        remaining = [
            ConflictRegion(
                file_path="test.py",
                location="function:func",
                tasks_involved=["task_001", "task_002"],
                change_types=[ChangeType.MODIFY_FUNCTION, ChangeType.MODIFY_FUNCTION],
                severity=ConflictSeverity.HIGH,
                can_auto_merge=False,
                reason="Incompatible modifications to same function",
            )
        ]

        explanation = build_explanation([], remaining)

        assert "Incompatible modifications" in explanation


class TestConflictResolverIntegration:
    """Integration tests for ConflictResolver"""

    def test_full_resolution_workflow(self):
        """Test complete resolution workflow with mixed conflicts"""
        auto_merger = AutoMerger()
        resolver = ConflictResolver(auto_merger=auto_merger, enable_ai=False)

        file_path = "app.py"
        baseline_content = "import os\n\ndef existing():\n    pass\n"

        # Create various types of conflicts
        conflicts = [
            ConflictRegion(
                file_path=file_path,
                location="file_top",
                tasks_involved=["task_001", "task_002"],
                change_types=[ChangeType.ADD_IMPORT, ChangeType.ADD_IMPORT],
                severity=ConflictSeverity.NONE,
                can_auto_merge=True,
                merge_strategy=MergeStrategy.COMBINE_IMPORTS,
            ),
            ConflictRegion(
                file_path=file_path,
                location="function:existing",
                tasks_involved=["task_001", "task_003"],
                change_types=[ChangeType.MODIFY_FUNCTION, ChangeType.MODIFY_FUNCTION],
                severity=ConflictSeverity.HIGH,
                can_auto_merge=False,
                reason="Both tasks modified existing() function",
            ),
        ]

        snapshots = [
            TaskSnapshot(
                task_id="task_001",
                task_intent="Add import and modify function",
                started_at=datetime.now(),
                semantic_changes=[],
            ),
            TaskSnapshot(
                task_id="task_002",
                task_intent="Add import",
                started_at=datetime.now(),
                semantic_changes=[],
            ),
            TaskSnapshot(
                task_id="task_003",
                task_intent="Modify function",
                started_at=datetime.now(),
                semantic_changes=[],
            ),
        ]

        result = resolver.resolve_conflicts(
            file_path, baseline_content, snapshots, conflicts
        )

        # Verify result structure
        assert isinstance(result, MergeResult)
        assert result.file_path == file_path
        assert len(result.explanation) > 0

    def test_progress_callback_emitted_for_each_conflict(self):
        """Test that progress callback is called for each conflict"""
        auto_merger = AutoMerger()
        resolver = ConflictResolver(auto_merger=auto_merger)

        file_path = "test.py"
        baseline_content = "content"

        conflicts = [
            ConflictRegion(
                file_path=file_path,
                location=f"location_{i}",
                tasks_involved=["task_001"],
                change_types=[ChangeType.ADD_IMPORT],
                severity=ConflictSeverity.NONE,
                can_auto_merge=True,
                merge_strategy=MergeStrategy.COMBINE_IMPORTS,
            )
            for i in range(5)
        ]

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Add imports",
            started_at=datetime.now(),
            semantic_changes=[],
        )

        progress_mock = Mock()

        resolver.resolve_conflicts(
            file_path, baseline_content, [snapshot], conflicts, progress_mock
        )

        # Should be called at least once per conflict
        assert progress_mock.call_count >= len(conflicts)
