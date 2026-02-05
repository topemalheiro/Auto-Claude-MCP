"""Comprehensive tests for merge_pipeline module"""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from merge.auto_merger import AutoMerger
from merge.conflict_detector import ConflictDetector
from merge.conflict_resolver import ConflictResolver
from merge.merge_pipeline import MergePipeline
from merge.types import (
    ChangeType,
    ConflictRegion,
    ConflictSeverity,
    FileAnalysis,
    MergeDecision,
    MergeResult,
    MergeStrategy,
    SemanticChange,
    TaskSnapshot,
)
from merge.progress import MergeProgressStage


class TestMergePipelineInit:
    """Test suite for MergePipeline initialization"""

    def test_init_with_required_dependencies(self):
        """Test initialization with conflict detector and resolver"""
        conflict_detector = ConflictDetector()
        auto_merger = AutoMerger()
        conflict_resolver = ConflictResolver(auto_merger=auto_merger)

        pipeline = MergePipeline(
            conflict_detector=conflict_detector, conflict_resolver=conflict_resolver
        )

        assert pipeline.conflict_detector == conflict_detector
        assert pipeline.conflict_resolver == conflict_resolver

    def test_init_stores_dependencies(self):
        """Test that dependencies are properly stored"""
        detector = ConflictDetector()
        auto_merger = AutoMerger()
        resolver = ConflictResolver(auto_merger=auto_merger)

        pipeline = MergePipeline(
            conflict_detector=detector, conflict_resolver=resolver
        )

        assert hasattr(pipeline, "conflict_detector")
        assert hasattr(pipeline, "conflict_resolver")
        assert pipeline.conflict_detector is detector
        assert pipeline.conflict_resolver is resolver


class TestMergePipelineMergeFile:
    """Test suite for MergePipeline.merge_file"""

    def test_merge_file_single_task_no_changes(self):
        """Test merging with single task and no semantic changes"""
        detector = ConflictDetector()
        auto_merger = AutoMerger()
        resolver = ConflictResolver(auto_merger=auto_merger)

        pipeline = MergePipeline(
            conflict_detector=detector, conflict_resolver=resolver
        )

        file_path = "test.py"
        baseline_content = "def existing():\n    pass\n"

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="No semantic changes",
            started_at=datetime.now(),
            semantic_changes=[],
        )

        result = pipeline.merge_file(file_path, baseline_content, [snapshot])

        assert result is not None
        assert result.file_path == file_path
        # Should be AUTO_MERGED since there are no changes
        assert result.decision == MergeDecision.AUTO_MERGED

    def test_merge_file_single_task_with_changes(self):
        """Test merging with single task with semantic changes"""
        detector = ConflictDetector()
        auto_merger = AutoMerger()
        resolver = ConflictResolver(auto_merger=auto_merger)

        pipeline = MergePipeline(
            conflict_detector=detector, conflict_resolver=resolver
        )

        file_path = "test.py"
        baseline_content = "def existing():\n    pass\n"

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

        result = pipeline.merge_file(file_path, baseline_content, [snapshot])

        assert result is not None
        assert result.file_path == file_path
        assert result.decision == MergeDecision.AUTO_MERGED
        assert "new_func" in result.merged_content or "def new_func" in str(
            result.merged_content
        )

    def test_merge_file_direct_copy_for_unsupported_changes(self):
        """Test that DIRECT_COPY is used for files with modifications but no semantic changes"""
        detector = ConflictDetector()
        auto_merger = AutoMerger()
        resolver = ConflictResolver(auto_merger=auto_merger)

        pipeline = MergePipeline(
            conflict_detector=detector, conflict_resolver=resolver
        )

        file_path = "test.py"
        baseline_content = "def existing():\n    pass\n"

        # Create a snapshot that has modifications but no semantic changes
        # (e.g., function body modifications that regex_analyzer couldn't detect)
        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Modify function body",
            started_at=datetime.now(),
            semantic_changes=[],  # No semantic changes detected
            content_hash_before="abc123",
            content_hash_after="def456",  # Different hash = modifications
        )

        result = pipeline.merge_file(file_path, baseline_content, [snapshot])

        assert result is not None
        assert result.file_path == file_path
        # Should return DIRECT_COPY when file has modifications but no semantic changes
        assert result.decision == MergeDecision.DIRECT_COPY
        assert result.merged_content is None  # Caller must read from worktree

    def test_merge_file_multiple_tasks_no_conflicts(self):
        """Test merging multiple tasks with no conflicts"""
        detector = ConflictDetector()
        auto_merger = AutoMerger()
        resolver = ConflictResolver(auto_merger=auto_merger)

        pipeline = MergePipeline(
            conflict_detector=detector, conflict_resolver=resolver
        )

        file_path = "test.py"
        baseline_content = "def existing():\n    pass\n"

        snapshot1 = TaskSnapshot(
            task_id="task_001",
            task_intent="Add os import",
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

        snapshot2 = TaskSnapshot(
            task_id="task_002",
            task_intent="Add sys import",
            started_at=datetime.now(),
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.ADD_IMPORT,
                    target="sys",
                    location="file_top",
                    line_start=2,
                    line_end=3,
                    content_after="import sys",
                )
            ],
        )

        result = pipeline.merge_file(
            file_path, baseline_content, [snapshot1, snapshot2]
        )

        assert result is not None
        assert result.file_path == file_path
        # Different imports should be auto-mergeable
        assert result.decision in {MergeDecision.AUTO_MERGED}

    def test_merge_file_with_conflicts(self):
        """Test merging when conflicts are detected"""
        detector = ConflictDetector()
        auto_merger = AutoMerger()
        resolver = ConflictResolver(auto_merger=auto_merger)

        pipeline = MergePipeline(
            conflict_detector=detector, conflict_resolver=resolver
        )

        file_path = "test.py"
        baseline_content = "def existing():\n    pass\n"

        # Create conflicting changes
        snapshot1 = TaskSnapshot(
            task_id="task_001",
            task_intent="Modify function",
            started_at=datetime.now(),
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.MODIFY_FUNCTION,
                    target="existing",
                    location="function:existing",
                    line_start=1,
                    line_end=2,
                    content_before="def existing():\n    pass",
                    content_after="def existing():\n    return True",
                )
            ],
        )

        snapshot2 = TaskSnapshot(
            task_id="task_002",
            task_intent="Modify function differently",
            started_at=datetime.now(),
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.MODIFY_FUNCTION,
                    target="existing",
                    location="function:existing",
                    line_start=1,
                    line_end=2,
                    content_before="def existing():\n    pass",
                    content_after="def existing():\n    return False",
                )
            ],
        )

        result = pipeline.merge_file(
            file_path, baseline_content, [snapshot1, snapshot2]
        )

        assert result is not None
        assert result.file_path == file_path

    def test_merge_file_with_progress_callback(self):
        """Test that progress callback is invoked"""
        detector = ConflictDetector()
        auto_merger = AutoMerger()
        resolver = ConflictResolver(auto_merger=auto_merger)

        pipeline = MergePipeline(
            conflict_detector=detector, conflict_resolver=resolver
        )

        file_path = "test.py"
        baseline_content = "def existing():\n    pass\n"

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

        progress_mock = Mock()

        result = pipeline.merge_file(
            file_path, baseline_content, [snapshot], progress_callback=progress_mock
        )

        # Progress callback should have been called
        assert progress_mock.called

    def test_merge_file_empty_snapshots(self):
        """Test merging with empty snapshots list"""
        detector = ConflictDetector()
        auto_merger = AutoMerger()
        resolver = ConflictResolver(auto_merger=auto_merger)

        pipeline = MergePipeline(
            conflict_detector=detector, conflict_resolver=resolver
        )

        file_path = "test.py"
        baseline_content = "def existing():\n    pass\n"

        result = pipeline.merge_file(file_path, baseline_content, [])

        assert result is not None
        assert result.file_path == file_path

    def test_merge_file_propagates_explanation(self):
        """Test that explanations are properly propagated"""
        detector = ConflictDetector()
        auto_merger = AutoMerger()
        resolver = ConflictResolver(auto_merger=auto_merger)

        pipeline = MergePipeline(
            conflict_detector=detector, conflict_resolver=resolver
        )

        file_path = "test.py"
        baseline_content = "def existing():\n    pass\n"

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

        result = pipeline.merge_file(file_path, baseline_content, [snapshot])

        assert result is not None
        assert isinstance(result.explanation, str)
        assert len(result.explanation) > 0


class TestMergePipelineBuildTaskAnalyses:
    """Test suite for MergePipeline._build_task_analyses"""

    def test_build_task_anyses_basic(self):
        """Test building task analyses from snapshots"""
        detector = ConflictDetector()
        auto_merger = AutoMerger()
        resolver = ConflictResolver(auto_merger=auto_merger)

        pipeline = MergePipeline(
            conflict_detector=detector, conflict_resolver=resolver
        )

        file_path = "test.py"

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

        analyses = pipeline._build_task_analyses(file_path, [snapshot])

        assert "task_001" in analyses
        assert isinstance(analyses["task_001"], FileAnalysis)
        assert analyses["task_001"].file_path == file_path
        assert len(analyses["task_001"].changes) == 1

    def test_build_task_anyses_multiple_tasks(self):
        """Test building analyses for multiple tasks"""
        detector = ConflictDetector()
        auto_merger = AutoMerger()
        resolver = ConflictResolver(auto_merger=auto_merger)

        pipeline = MergePipeline(
            conflict_detector=detector, conflict_resolver=resolver
        )

        file_path = "test.py"

        snapshot1 = TaskSnapshot(
            task_id="task_001",
            task_intent="Add function",
            started_at=datetime.now(),
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.ADD_FUNCTION,
                    target="func1",
                    location="file_top",
                    line_start=5,
                    line_end=10,
                    content_after="def func1():\n    pass",
                )
            ],
        )

        snapshot2 = TaskSnapshot(
            task_id="task_002",
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

        analyses = pipeline._build_task_analyses(file_path, [snapshot1, snapshot2])

        assert "task_001" in analyses
        assert "task_002" in analyses
        assert len(analyses) == 2

    def test_build_task_anyses_populates_summary_fields(self):
        """Test that summary fields are properly populated"""
        detector = ConflictDetector()
        auto_merger = AutoMerger()
        resolver = ConflictResolver(auto_merger=auto_merger)

        pipeline = MergePipeline(
            conflict_detector=detector, conflict_resolver=resolver
        )

        file_path = "test.py"

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Multiple changes",
            started_at=datetime.now(),
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.ADD_FUNCTION,
                    target="new_func",
                    location="file_top",
                    line_start=5,
                    line_end=10,
                    content_after="def new_func():\n    pass",
                ),
                SemanticChange(
                    change_type=ChangeType.MODIFY_FUNCTION,
                    target="existing",
                    location="function:existing",
                    line_start=1,
                    line_end=5,
                    content_before="def existing():\n    pass",
                    content_after="def existing():\n    return True",
                ),
                SemanticChange(
                    change_type=ChangeType.ADD_IMPORT,
                    target="os",
                    location="file_top",
                    line_start=1,
                    line_end=2,
                    content_after="import os",
                ),
            ],
        )

        analyses = pipeline._build_task_analyses(file_path, [snapshot])

        analysis = analyses["task_001"]

        # Check summary fields
        assert "new_func" in analysis.functions_added
        assert "existing" in analysis.functions_modified
        assert "os" in analysis.imports_added
        assert analysis.total_lines_changed > 0

    def test_build_task_anyses_with_no_changes(self):
        """Test building analyses with snapshots that have no semantic changes"""
        detector = ConflictDetector()
        auto_merger = AutoMerger()
        resolver = ConflictResolver(auto_merger=auto_merger)

        pipeline = MergePipeline(
            conflict_detector=detector, conflict_resolver=resolver
        )

        file_path = "test.py"

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="No changes",
            started_at=datetime.now(),
            semantic_changes=[],
        )

        analyses = pipeline._build_task_analyses(file_path, [snapshot])

        assert "task_001" in analyses
        assert len(analyses["task_001"].changes) == 0


class TestMergePipelineIntegration:
    """Integration tests for MergePipeline"""

    def test_full_pipeline_single_task(self):
        """Test complete pipeline with single task"""
        detector = ConflictDetector()
        auto_merger = AutoMerger()
        resolver = ConflictResolver(auto_merger=auto_merger)

        pipeline = MergePipeline(
            conflict_detector=detector, conflict_resolver=resolver
        )

        file_path = "app.py"
        baseline_content = "import json\n\ndef existing():\n    pass\n"

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Enhance file",
            started_at=datetime.now(),
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.ADD_IMPORT,
                    target="os",
                    location="file_top",
                    line_start=2,
                    line_end=3,
                    content_after="import os",
                ),
                SemanticChange(
                    change_type=ChangeType.ADD_FUNCTION,
                    target="new_func",
                    location="file_top",
                    line_start=5,
                    line_end=10,
                    content_after="def new_func():\n    pass",
                ),
            ],
        )

        result = pipeline.merge_file(file_path, baseline_content, [snapshot])

        # Verify result
        assert result.success
        assert result.decision == MergeDecision.AUTO_MERGED
        assert result.file_path == file_path
        assert result.merged_content is not None
        assert len(result.explanation) > 0

    def test_full_pipeline_multiple_tasks_compatible(self):
        """Test complete pipeline with multiple compatible tasks"""
        detector = ConflictDetector()
        auto_merger = AutoMerger()
        resolver = ConflictResolver(auto_merger=auto_merger)

        pipeline = MergePipeline(
            conflict_detector=detector, conflict_resolver=resolver
        )

        file_path = "app.py"
        baseline_content = "def existing():\n    pass\n"

        snapshot1 = TaskSnapshot(
            task_id="task_001",
            task_intent="Add os import",
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

        snapshot2 = TaskSnapshot(
            task_id="task_002",
            task_intent="Add sys import",
            started_at=datetime.now(),
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.ADD_IMPORT,
                    target="sys",
                    location="file_top",
                    line_start=2,
                    line_end=3,
                    content_after="import sys",
                )
            ],
        )

        result = pipeline.merge_file(
            file_path, baseline_content, [snapshot1, snapshot2]
        )

        # Verify result
        assert result is not None
        assert result.file_path == file_path
        # Different imports should be compatible

    def test_full_pipeline_with_progress_tracking(self):
        """Test pipeline with progress callback tracking all stages"""
        detector = ConflictDetector()
        auto_merger = AutoMerger()
        resolver = ConflictResolver(auto_merger=auto_merger)

        pipeline = MergePipeline(
            conflict_detector=detector, conflict_resolver=resolver
        )

        file_path = "app.py"
        baseline_content = "def existing():\n    pass\n"

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

        progress_calls = []

        def track_progress(stage, percent, message, details=None):
            progress_calls.append(
                {"stage": stage, "percent": percent, "message": message, "details": details}
            )

        result = pipeline.merge_file(
            file_path, baseline_content, [snapshot], progress_callback=track_progress
        )

        # Verify progress was tracked
        assert len(progress_calls) > 0

        # Check that stages are valid
        for call in progress_calls:
            assert isinstance(call["stage"], MergeProgressStage)
            assert 0 <= call["percent"] <= 100

    def test_pipeline_handles_empty_file(self):
        """Test pipeline with empty baseline file"""
        detector = ConflictDetector()
        auto_merger = AutoMerger()
        resolver = ConflictResolver(auto_merger=auto_merger)

        pipeline = MergePipeline(
            conflict_detector=detector, conflict_resolver=resolver
        )

        file_path = "new_file.py"
        baseline_content = ""

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Create file",
            started_at=datetime.now(),
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.ADD_FUNCTION,
                    target="first_func",
                    location="file_top",
                    line_start=1,
                    line_end=5,
                    content_after="def first_func():\n    pass",
                )
            ],
        )

        result = pipeline.merge_file(file_path, baseline_content, [snapshot])

        assert result is not None
        assert result.file_path == file_path

    def test_pipeline_result_properties(self):
        """Test MergeResult properties"""
        detector = ConflictDetector()
        auto_merger = AutoMerger()
        resolver = ConflictResolver(auto_merger=auto_merger)

        pipeline = MergePipeline(
            conflict_detector=detector, conflict_resolver=resolver
        )

        file_path = "test.py"
        baseline_content = "def existing():\n    pass\n"

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

        result = pipeline.merge_file(file_path, baseline_content, [snapshot])

        # Check MergeResult properties
        assert hasattr(result, "decision")
        assert hasattr(result, "file_path")
        assert hasattr(result, "merged_content")
        assert hasattr(result, "conflicts_resolved")
        assert hasattr(result, "conflicts_remaining")
        assert hasattr(result, "explanation")

        # Check success property
        if result.decision in {
            MergeDecision.AUTO_MERGED,
            MergeDecision.AI_MERGED,
            MergeDecision.DIRECT_COPY,
        }:
            assert result.success is True

    def test_pipeline_with_various_change_types(self):
        """Test pipeline handles various change types"""
        detector = ConflictDetector()
        auto_merger = AutoMerger()
        resolver = ConflictResolver(auto_merger=auto_merger)

        pipeline = MergePipeline(
            conflict_detector=detector, conflict_resolver=resolver
        )

        file_path = "test.py"
        baseline_content = "import json\n\nclass MyClass:\n    pass\n"

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Various changes",
            started_at=datetime.now(),
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.ADD_IMPORT,
                    target="os",
                    location="file_top",
                    line_start=2,
                    line_end=3,
                    content_after="import os",
                ),
                SemanticChange(
                    change_type=ChangeType.ADD_METHOD,
                    target="MyClass",
                    location="class:MyClass",
                    line_start=5,
                    line_end=7,
                    content_after="    def new_method(self):\n        pass",
                ),
            ],
        )

        result = pipeline.merge_file(file_path, baseline_content, [snapshot])

        assert result is not None
        assert result.file_path == file_path

    def test_pipeline_coordinates_detector_and_resolver(self):
        """Test that pipeline properly coordinates detector and resolver"""
        detector = ConflictDetector()
        auto_merger = AutoMerger()
        resolver = ConflictResolver(auto_merger=auto_merger)

        pipeline = MergePipeline(
            conflict_detector=detector, conflict_resolver=resolver
        )

        file_path = "test.py"
        baseline_content = "def existing():\n    pass\n"

        # Create multiple tasks that might conflict
        snapshot1 = TaskSnapshot(
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

        snapshot2 = TaskSnapshot(
            task_id="task_002",
            task_intent="Add different import",
            started_at=datetime.now(),
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.ADD_IMPORT,
                    target="sys",
                    location="file_top",
                    line_start=2,
                    line_end=3,
                    content_after="import sys",
                )
            ],
        )

        # Detector should be called
        with patch.object(detector, "detect_conflicts", wraps=detector.detect_conflicts) as detect_spy:
            result = pipeline.merge_file(
                file_path, baseline_content, [snapshot1, snapshot2]
            )

            # Detector should have been called for multiple tasks
            assert detect_spy.called
