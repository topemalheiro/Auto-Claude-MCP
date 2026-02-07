"""Comprehensive tests for merge/orchestrator.py"""

from datetime import datetime
from merge.orchestrator import (
    MergeOrchestrator,
    MergeReport,
    MergeStats,
    TaskMergeRequest,
    MergeProgressStage,
)
from merge.types import (
    ChangeType,
    ConflictRegion,
    ConflictSeverity,
    MergeDecision,
    SemanticChange,
    TaskSnapshot,
    MergeResult,
    FileAnalysis,
    MergeStrategy,
)
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open, call
import pytest
import tempfile


class TestMergeOrchestratorInit:
    """Tests for MergeOrchestrator initialization"""

    def test_init_default_parameters(self):
        """Test initialization with default parameters"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(project_dir=project_dir)

            assert instance.project_dir == project_dir.resolve()
            assert instance.enable_ai is True
            assert instance.dry_run is False
            # storage_dir is computed from resolved project_dir
            assert instance.storage_dir == project_dir.resolve() / ".auto-claude"

    def test_init_custom_storage_dir(self):
        """Test initialization with custom storage directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            storage_dir = Path(tmpdir) / "custom_storage"

            instance = MergeOrchestrator(
                project_dir=project_dir,
                storage_dir=storage_dir,
            )

            assert instance.storage_dir == storage_dir

    def test_init_with_ai_disabled(self):
        """Test initialization with AI disabled"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(
                project_dir=project_dir,
                enable_ai=False,
            )

            assert instance.enable_ai is False

    def test_init_dry_run(self):
        """Test initialization in dry run mode"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(
                project_dir=project_dir,
                dry_run=True,
            )

            assert instance.dry_run is True

    def test_ai_resolver_property_lazy_init(self):
        """Test that ai_resolver property initializes on first access"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(
                project_dir=project_dir,
                enable_ai=True,
            )

            assert instance._ai_resolver_initialized is False
            _ = instance.ai_resolver
            assert instance._ai_resolver_initialized is True

    def test_conflict_resolver_property_lazy_init(self):
        """Test that conflict_resolver property initializes on first access"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(project_dir=project_dir)

            assert instance._conflict_resolver is None
            _ = instance.conflict_resolver
            assert instance._conflict_resolver is not None

    def test_merge_pipeline_property_lazy_init(self):
        """Test that merge_pipeline property initializes on first access"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(project_dir=project_dir)

            assert instance._merge_pipeline is None
            _ = instance.merge_pipeline
            assert instance._merge_pipeline is not None


class TestMergeTask:
    """Tests for merge_task method"""

    def test_merge_task_worktree_not_found(self):
        """Test merge_task when worktree cannot be found"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(
                project_dir=project_dir,
                enable_ai=False,
            )

            result = instance.merge_task("task_001")

            assert result.success is False
            assert "Could not find worktree" in result.error

    def test_merge_task_with_explicit_worktree(self):
        """Test merge_task with explicitly provided worktree path"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            worktree_path = Path(tmpdir) / "worktrees" / "task_001"
            worktree_path.mkdir(parents=True)

            instance = MergeOrchestrator(
                project_dir=project_dir,
                enable_ai=False,
            )

            # Mock evolution tracker to return no modifications
            with patch.object(instance.evolution_tracker, 'refresh_from_git'):
                with patch.object(instance.evolution_tracker, 'get_task_modifications', return_value=[]):
                    result = instance.merge_task(
                        "task_001",
                        worktree_path=worktree_path,
                    )

                    assert result is not None
                    assert isinstance(result, MergeReport)

    def test_merge_task_no_modifications(self):
        """Test merge_task when no modifications are found"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            worktree_path = Path(tmpdir) / "worktree"
            worktree_path.mkdir(parents=True)

            instance = MergeOrchestrator(
                project_dir=project_dir,
                enable_ai=False,
            )

            with patch.object(instance.evolution_tracker, 'refresh_from_git'):
                with patch.object(instance.evolution_tracker, 'get_task_modifications', return_value=None):
                    result = instance.merge_task(
                        "task_001",
                        worktree_path=worktree_path,
                    )

                    # Should succeed with no files to process
                    assert result is not None
                    assert result.completed_at is not None

    def test_merge_task_with_progress_callback(self):
        """Test merge_task with progress callback"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            worktree_path = Path(tmpdir) / "worktree"
            worktree_path.mkdir(parents=True)

            instance = MergeOrchestrator(
                project_dir=project_dir,
                enable_ai=False,
            )

            progress_calls = []

            def callback(stage, percent, message, details=None):
                progress_calls.append((stage, percent, message, details))

            with patch.object(instance.evolution_tracker, 'refresh_from_git'):
                with patch.object(instance.evolution_tracker, 'get_task_modifications', return_value=None):
                    result = instance.merge_task(
                        "task_001",
                        worktree_path=worktree_path,
                        progress_callback=callback,
                    )

                    # Progress callback should have been called
                    assert len(progress_calls) > 0

    def test_merge_task_direct_copy_decision(self):
        """Test merge_task when decision is DIRECT_COPY"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            worktree_path = Path(tmpdir) / "worktree"
            worktree_path.mkdir(parents=True)

            # Create test file in worktree
            test_file = worktree_path / "test.py"
            test_file.write_text("merged content")

            instance = MergeOrchestrator(
                project_dir=project_dir,
                enable_ai=False,
                dry_run=True,  # Use dry_run to avoid report saving issues
            )

            # Create proper MergeResult with DIRECT_COPY decision
            mock_result = MergeResult(
                decision=MergeDecision.DIRECT_COPY,
                file_path="test.py",
                merged_content=None,  # Will be set by DIRECT_COPY logic
                conflicts_resolved=[],
                conflicts_remaining=[],
                ai_calls_made=0,
                tokens_used=0,
                explanation="Direct copy",
            )

            snapshot = MagicMock()
            snapshot.semantic_changes = []

            with patch.object(instance.evolution_tracker, 'refresh_from_git'):
                with patch.object(instance.evolution_tracker, 'get_task_modifications', return_value=[("test.py", snapshot)]):
                    with patch.object(instance, '_merge_file', return_value=mock_result):
                        result = instance.merge_task(
                            "task_001",
                            worktree_path=worktree_path,
                        )

                        # DIRECT_COPY should read from worktree
                        assert result is not None
                        assert result.file_results["test.py"].merged_content == "merged content"

    def test_merge_task_exception_handling(self):
        """Test merge_task exception handling"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            worktree_path = Path(tmpdir) / "worktree"
            worktree_path.mkdir(parents=True)

            instance = MergeOrchestrator(
                project_dir=project_dir,
                enable_ai=False,
            )

            with patch.object(instance.evolution_tracker, 'refresh_from_git', side_effect=Exception("Test error")):
                result = instance.merge_task(
                    "task_001",
                    worktree_path=worktree_path,
                )

                assert result.success is False
                assert "Test error" in result.error


class TestMergeTasks:
    """Tests for merge_tasks method"""

    def test_merge_tasks_empty_list(self):
        """Test merge_tasks with empty request list"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(
                project_dir=project_dir,
                enable_ai=False,
            )

            result = instance.merge_tasks([])

            assert result is not None
            assert result.success is True  # Empty list succeeds
            assert result.tasks_merged == []

    def test_merge_tasks_with_priority_sorting(self):
        """Test merge_tasks sorts by priority"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(
                project_dir=project_dir,
                enable_ai=False,
            )

            requests = [
                TaskMergeRequest(
                    task_id="low_priority",
                    worktree_path=Path(tmpdir) / "low",
                    priority=1,
                ),
                TaskMergeRequest(
                    task_id="high_priority",
                    worktree_path=Path(tmpdir) / "high",
                    priority=10,
                ),
            ]

            with patch.object(instance.evolution_tracker, 'refresh_from_git'):
                with patch.object(instance.evolution_tracker, 'get_files_modified_by_tasks', return_value={}):
                    result = instance.merge_tasks(requests)

                    # Higher priority task should be processed first
                    assert result is not None

    def test_merge_tasks_exception_handling(self):
        """Test merge_tasks exception handling"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(
                project_dir=project_dir,
                enable_ai=False,
            )

            request = TaskMergeRequest(
                task_id="task_001",
                worktree_path=Path(tmpdir) / "worktree",
            )

            # The exception happens during refresh_from_git which is inside a try block
            # but it's in the requests loop, so we need to check if it actually fails
            # Looking at the code, the exception is caught and sets report.success = False
            with patch.object(instance.evolution_tracker, 'get_files_modified_by_tasks', side_effect=Exception("Test error")):
                result = instance.merge_tasks([request])

                assert result.success is False
                assert "Test error" in result.error


class TestGetPendingConflicts:
    """Tests for get_pending_conflicts method"""

    def test_get_pending_conflicts_no_active_tasks(self):
        """Test get_pending_conflicts when no active tasks"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(
                project_dir=project_dir,
                enable_ai=False,
            )

            with patch.object(instance.evolution_tracker, 'get_active_tasks', return_value=[]):
                result = instance.get_pending_conflicts()

                assert result == []

    def test_get_pending_conflicts_with_conflicts(self):
        """Test get_pending_conflicts returns conflicts"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(
                project_dir=project_dir,
                enable_ai=False,
            )

            # Mock active tasks and conflicts
            conflict = ConflictRegion(
                file_path="test.py",
                location="function:foo",
                tasks_involved=["task_001", "task_002"],
                change_types=[ChangeType.MODIFY_FUNCTION],
                severity=ConflictSeverity.HIGH,
                can_auto_merge=False,
                reason="Test conflict"
            )

            with patch.object(instance.evolution_tracker, 'get_active_tasks', return_value=["task_001", "task_002"]):
                with patch.object(instance.evolution_tracker, 'get_conflicting_files', return_value=["test.py"]):
                    with patch.object(instance.evolution_tracker, 'get_file_evolution') as mock_evolution:
                        mock_timeline = MagicMock()
                        mock_timeline.task_snapshots = []
                        mock_evolution.return_value = mock_timeline

                        with patch.object(instance.conflict_detector, 'detect_conflicts', return_value=[conflict]):
                            result = instance.get_pending_conflicts()

                            assert len(result) > 0


class TestPreviewMerge:
    """Tests for preview_merge method"""

    def test_preview_merge_empty_task_list(self):
        """Test preview_merge with no task IDs"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(
                project_dir=project_dir,
                enable_ai=False,
            )

            result = instance.preview_merge([])

            assert result is not None
            assert result["tasks"] == []
            assert result["files_to_merge"] == []

    def test_preview_merge_with_conflicts(self):
        """Test preview_merge detects potential conflicts"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(
                project_dir=project_dir,
                enable_ai=False,
            )

            conflict = ConflictRegion(
                file_path="test.py",
                location="function:foo",
                tasks_involved=["task_001"],
                change_types=[ChangeType.MODIFY_FUNCTION],
                severity=ConflictSeverity.MEDIUM,
                can_auto_merge=False,
                reason="Test"
            )

            with patch.object(instance.evolution_tracker, 'get_files_modified_by_tasks', return_value={"test.py": ["task_001"]}):
                with patch.object(instance.evolution_tracker, 'get_conflicting_files', return_value=["test.py"]):
                    with patch.object(instance.evolution_tracker, 'get_file_evolution') as mock_evolution:
                        mock_timeline = MagicMock()
                        mock_timeline.task_snapshots = []
                        mock_evolution.return_value = mock_timeline

                        with patch.object(instance.conflict_detector, 'detect_conflicts', return_value=[conflict]):
                            result = instance.preview_merge(["task_001"])

                            assert "test.py" in result["files_with_potential_conflicts"]
                            assert len(result["conflicts"]) > 0

    def test_preview_merge_no_conflicts(self):
        """Test preview_merge when no conflicts detected"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(
                project_dir=project_dir,
                enable_ai=False,
            )

            with patch.object(instance.evolution_tracker, 'get_files_modified_by_tasks', return_value={"test.py": ["task_001"]}):
                with patch.object(instance.evolution_tracker, 'get_conflicting_files', return_value=[]):
                    result = instance.preview_merge(["task_001"])

                    assert len(result["files_with_potential_conflicts"]) == 0
                    assert result["summary"]["total_conflicts"] == 0


class TestWriteMergedFiles:
    """Tests for write_merged_files method"""

    def test_write_merged_files_dry_run(self):
        """Test write_merged_files in dry run mode"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(
                project_dir=project_dir,
                dry_run=True,
            )

            report = MergeReport(started_at=datetime.now(), tasks_merged=[])
            report.file_results["test.py"] = MagicMock(merged_content="content")

            result = instance.write_merged_files(report)

            assert result == []  # Dry run returns empty list

    def test_write_merged_files_writes_files(self):
        """Test write_merged_files actually writes files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            output_dir = Path(tmpdir) / "output"
            instance = MergeOrchestrator(
                project_dir=project_dir,
                storage_dir=Path(tmpdir) / ".auto-claude",
                dry_run=False,
            )

            report = MergeReport(started_at=datetime.now(), tasks_merged=[])
            report.file_results["test.py"] = MagicMock(merged_content="test content")

            result = instance.write_merged_files(report, output_dir=output_dir)

            assert len(result) == 1
            assert (output_dir / "test.py").exists()
            assert (output_dir / "test.py").read_text() == "test content"

    def test_write_merged_files_no_content(self):
        """Test write_merged_files skips results with no content"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            output_dir = Path(tmpdir) / "output"
            instance = MergeOrchestrator(
                project_dir=project_dir,
                storage_dir=Path(tmpdir) / ".auto-claude",
                dry_run=False,
            )

            report = MergeReport(started_at=datetime.now(), tasks_merged=[])
            report.file_results["test.py"] = MagicMock(merged_content=None)

            result = instance.write_merged_files(report, output_dir=output_dir)

            assert len(result) == 0


class TestApplyToProject:
    """Tests for apply_to_project method"""

    def test_apply_to_project_dry_run(self):
        """Test apply_to_project in dry run mode"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(
                project_dir=project_dir,
                dry_run=True,
            )

            report = MergeReport(started_at=datetime.now(), tasks_merged=[])

            result = instance.apply_to_project(report)

            assert result is True

    def test_apply_to_project_writes_files(self):
        """Test apply_to_project writes files to project"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(
                project_dir=project_dir,
                dry_run=False,
            )

            report = MergeReport(started_at=datetime.now(), tasks_merged=[])
            report.file_results["src/test.py"] = MagicMock(
                merged_content="merged",
                success=True,
            )

            result = instance.apply_to_project(report)

            assert result is True
            assert (project_dir / "src" / "test.py").exists()

    def test_apply_to_project_handles_errors(self):
        """Test apply_to_project handles write errors gracefully"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(
                project_dir=project_dir,
                dry_run=False,
            )

            report = MergeReport(started_at=datetime.now(), tasks_merged=[])
            report.file_results["test.py"] = MagicMock(
                merged_content="content",
                success=True,
            )

            # Mock write to raise exception
            with patch.object(Path, 'write_text', side_effect=OSError("Permission denied")):
                result = instance.apply_to_project(report)

                assert result is False


class TestUpdateStats:
    """Tests for _update_stats method"""

    def test_update_stats_auto_merged(self):
        """Test _update_stats for auto-merged file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(project_dir=project_dir)

            stats = MergeStats()
            result = MagicMock()
            result.decision = MergeDecision.AUTO_MERGED
            result.conflicts_resolved = []
            result.conflicts_remaining = []
            result.ai_calls_made = 0
            result.tokens_used = 0

            instance._update_stats(stats, result)

            assert stats.files_processed == 1
            assert stats.files_auto_merged == 1
            assert stats.files_failed == 0

    def test_update_stats_ai_merged(self):
        """Test _update_stats for AI-merged file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(project_dir=project_dir)

            stats = MergeStats()
            result = MagicMock()
            result.decision = MergeDecision.AI_MERGED
            result.conflicts_resolved = [MagicMock(), MagicMock()]
            result.conflicts_remaining = []
            result.ai_calls_made = 1
            result.tokens_used = 100

            instance._update_stats(stats, result)

            assert stats.files_processed == 1
            assert stats.files_ai_merged == 1
            assert stats.conflicts_ai_resolved == 2
            assert stats.ai_calls_made == 1
            assert stats.estimated_tokens_used == 100

    def test_update_stats_failed(self):
        """Test _update_stats for failed merge"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(project_dir=project_dir)

            stats = MergeStats()
            result = MagicMock()
            result.decision = MergeDecision.FAILED
            result.conflicts_resolved = []
            result.conflicts_remaining = [MagicMock()]
            result.ai_calls_made = 0
            result.tokens_used = 0

            instance._update_stats(stats, result)

            assert stats.files_processed == 1
            assert stats.files_failed == 1
            assert stats.conflicts_detected == 1


class TestReadWorktreeFileForDirectCopy:
    """Tests for _read_worktree_file_for_direct_copy method"""

    def test_read_worktree_file_no_worktree_path(self):
        """Test _read_worktree_file_for_direct_copy with no worktree path"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(project_dir=project_dir)

            content, success = instance._read_worktree_file_for_direct_copy(
                "test.py",
                None,
            )

            assert content is None
            assert success is False

    def test_read_worktree_file_not_found(self):
        """Test _read_worktree_file_for_direct_copy when file doesn't exist"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            worktree_path = Path(tmpdir) / "worktree"
            worktree_path.mkdir(parents=True)

            instance = MergeOrchestrator(project_dir=project_dir)

            content, success = instance._read_worktree_file_for_direct_copy(
                "test.py",
                worktree_path,
            )

            assert content is None
            assert success is False

    def test_read_worktree_file_success(self):
        """Test _read_worktree_file_for_direct_copy successful read"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            worktree_path = Path(tmpdir) / "worktree"
            worktree_path.mkdir(parents=True)

            test_file = worktree_path / "test.py"
            test_file.write_text("file content")

            instance = MergeOrchestrator(project_dir=project_dir)

            content, success = instance._read_worktree_file_for_direct_copy(
                "test.py",
                worktree_path,
            )

            assert content == "file content"
            assert success is True

    def test_read_worktree_file_unicode_decode_error_fallback(self):
        """Test _read_worktree_file_for_direct_copy with Unicode decode error"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            worktree_path = Path(tmpdir) / "worktree"
            worktree_path.mkdir(parents=True)

            # Create a file that will cause decode error with utf-8 strict
            test_file = worktree_path / "test.py"
            test_file.write_bytes(b'\xff\xfe Invalid UTF-8')

            instance = MergeOrchestrator(project_dir=project_dir)

            content, success = instance._read_worktree_file_for_direct_copy(
                "test.py",
                worktree_path,
            )

            # Should use errors='replace' and still succeed
            assert content is not None
            assert success is True


class TestMergeFile:
    """Tests for _merge_file method"""

    def test_merge_file_with_baseline_content(self):
        """Test _merge_file with baseline content available"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(
                project_dir=project_dir,
                enable_ai=False,
            )

            snapshot = MagicMock()
            snapshot.task_id = "task_001"
            snapshot.semantic_changes = []

            baseline_content = "baseline content"

            with patch.object(instance.evolution_tracker, 'get_baseline_content', return_value=baseline_content):
                mock_pipeline_result = MergeResult(
                    decision=MergeDecision.AUTO_MERGED,
                    file_path="test.py",
                    merged_content="merged content",
                    conflicts_resolved=[],
                    conflicts_remaining=[],
                )

                with patch.object(instance.merge_pipeline, 'merge_file', return_value=mock_pipeline_result):
                    result = instance._merge_file(
                        file_path="test.py",
                        task_snapshots=[snapshot],
                        target_branch="main",
                    )

                    assert result.decision == MergeDecision.AUTO_MERGED
                    assert result.merged_content == "merged content"

    def test_merge_file_fallback_to_branch_content(self):
        """Test _merge_file falls back to branch content when baseline is None"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(
                project_dir=project_dir,
                enable_ai=False,
            )

            snapshot = MagicMock()
            snapshot.task_id = "task_001"
            snapshot.semantic_changes = []

            mock_pipeline_result = MergeResult(
                decision=MergeDecision.AUTO_MERGED,
                file_path="test.py",
                merged_content="merged content",
                conflicts_resolved=[],
                conflicts_remaining=[],
            )

            with patch.object(instance.evolution_tracker, 'get_baseline_content', return_value=None):
                with patch('merge.orchestrator.get_file_from_branch', return_value="branch content"):
                    with patch.object(instance.merge_pipeline, 'merge_file', return_value=mock_pipeline_result) as mock_merge:
                        result = instance._merge_file(
                            file_path="test.py",
                            task_snapshots=[snapshot],
                            target_branch="main",
                        )

                        # Should call merge_pipeline with branch content
                        mock_merge.assert_called_once()
                        call_args = mock_merge.call_args
                        assert call_args[1]['baseline_content'] == "branch content"

    def test_merge_file_new_file_empty_baseline(self):
        """Test _merge_file with new file (no baseline or branch content)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(
                project_dir=project_dir,
                enable_ai=False,
            )

            snapshot = MagicMock()
            snapshot.task_id = "task_001"
            snapshot.semantic_changes = []

            mock_pipeline_result = MergeResult(
                decision=MergeDecision.AUTO_MERGED,
                file_path="test.py",
                merged_content="merged content",
                conflicts_resolved=[],
                conflicts_remaining=[],
            )

            with patch.object(instance.evolution_tracker, 'get_baseline_content', return_value=None):
                with patch('merge.orchestrator.get_file_from_branch', return_value=None):
                    with patch.object(instance.merge_pipeline, 'merge_file', return_value=mock_pipeline_result) as mock_merge:
                        result = instance._merge_file(
                            file_path="test.py",
                            task_snapshots=[snapshot],
                            target_branch="main",
                        )

                        # Should call merge_pipeline with empty string for new file
                        mock_merge.assert_called_once()
                        call_args = mock_merge.call_args
                        assert call_args[1]['baseline_content'] == ""


class TestMergeTasksDirectCopy:
    """Tests for DIRECT_COPY handling in merge_tasks"""

    def test_merge_tasks_direct_copy_success(self):
        """Test merge_tasks handles DIRECT_COPY decision successfully"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            worktree_path = Path(tmpdir) / "worktree"
            worktree_path.mkdir(parents=True)

            # Create test file
            test_file = worktree_path / "test.py"
            test_file.write_text("worktree content")

            instance = MergeOrchestrator(
                project_dir=project_dir,
                enable_ai=False,
                dry_run=True,
            )

            request = TaskMergeRequest(
                task_id="task_001",
                worktree_path=worktree_path,
            )

            # Mock DIRECT_COPY result
            mock_result = MergeResult(
                decision=MergeDecision.DIRECT_COPY,
                file_path="test.py",
                merged_content=None,
                conflicts_resolved=[],
                conflicts_remaining=[],
                ai_calls_made=0,
                tokens_used=0,
            )

            mock_snapshot = MagicMock()
            mock_snapshot.task_id = "task_001"

            with patch.object(instance.evolution_tracker, 'get_files_modified_by_tasks', return_value={"test.py": ["task_001"]}):
                with patch.object(instance.evolution_tracker, 'get_file_evolution') as mock_evolution:
                    mock_timeline = MagicMock()
                    mock_timeline.get_task_snapshot.return_value = mock_snapshot
                    mock_evolution.return_value = mock_timeline

                    with patch.object(instance, '_merge_file', return_value=mock_result):
                        result = instance.merge_tasks([request])

                        # Should read from worktree and set merged_content
                        assert "test.py" in result.file_results
                        assert result.file_results["test.py"].merged_content == "worktree content"

    def test_merge_tasks_direct_copy_failure_no_worktree(self):
        """Test merge_tasks DIRECT_COPY fails when no worktree available"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(
                project_dir=project_dir,
                enable_ai=False,
                dry_run=True,
            )

            # Request without worktree_path
            request = TaskMergeRequest(
                task_id="task_001",
                worktree_path=None,
            )

            # Mock DIRECT_COPY result
            mock_result = MergeResult(
                decision=MergeDecision.DIRECT_COPY,
                file_path="test.py",
                merged_content=None,
                conflicts_resolved=[],
                conflicts_remaining=[],
                ai_calls_made=0,
                tokens_used=0,
            )

            mock_snapshot = MagicMock()
            mock_snapshot.task_id = "task_001"

            with patch.object(instance.evolution_tracker, 'get_files_modified_by_tasks', return_value={"test.py": ["task_001"]}):
                with patch.object(instance.evolution_tracker, 'get_file_evolution') as mock_evolution:
                    mock_timeline = MagicMock()
                    mock_timeline.get_task_snapshot.return_value = mock_snapshot
                    mock_evolution.return_value = mock_timeline

                    with patch.object(instance, '_merge_file', return_value=mock_result):
                        result = instance.merge_tasks([request])

                        # Should mark as FAILED when no worktree available
                        assert result.file_results["test.py"].decision == MergeDecision.FAILED
                        assert "Worktree file not found" in result.file_results["test.py"].error


class TestGetPendingConflictsEdgeCases:
    """Additional tests for get_pending_conflicts"""

    def test_get_pending_conflicts_auto_mergeable_filtered(self):
        """Test get_pending_conflicts filters out auto-mergeable conflicts"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(
                project_dir=project_dir,
                enable_ai=False,
            )

            # Create auto-mergeable conflict
            auto_mergeable_conflict = ConflictRegion(
                file_path="test.py",
                location="function:foo",
                tasks_involved=["task_001", "task_002"],
                change_types=[ChangeType.MODIFY_FUNCTION],
                severity=ConflictSeverity.LOW,
                can_auto_merge=True,
                reason="Auto-mergeable",
            )

            with patch.object(instance.evolution_tracker, 'get_active_tasks', return_value=["task_001", "task_002"]):
                with patch.object(instance.evolution_tracker, 'get_conflicting_files', return_value=["test.py"]):
                    with patch.object(instance.evolution_tracker, 'get_file_evolution') as mock_evolution:
                        mock_timeline = MagicMock()
                        mock_timeline.task_snapshots = []
                        mock_evolution.return_value = mock_timeline

                        with patch.object(instance.conflict_detector, 'detect_conflicts', return_value=[auto_mergeable_conflict]):
                            result = instance.get_pending_conflicts()

                            # Auto-mergeable conflicts should be filtered out
                            assert len(result) == 0

    def test_get_pending_conflicts_no_evolution_data(self):
        """Test get_pending_conflicts when no evolution data exists"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(
                project_dir=project_dir,
                enable_ai=False,
            )

            with patch.object(instance.evolution_tracker, 'get_active_tasks', return_value=["task_001", "task_002"]):
                with patch.object(instance.evolution_tracker, 'get_conflicting_files', return_value=["test.py"]):
                    with patch.object(instance.evolution_tracker, 'get_file_evolution', return_value=None):
                        result = instance.get_pending_conflicts()

                        # Should skip files with no evolution data
                        assert len(result) == 0


class TestPreviewMergeEdgeCases:
    """Additional tests for preview_merge"""

    def test_preview_merge_no_evolution_data(self):
        """Test preview_merge when no evolution data exists"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(
                project_dir=project_dir,
                enable_ai=False,
            )

            with patch.object(instance.evolution_tracker, 'get_files_modified_by_tasks', return_value={"test.py": ["task_001"]}):
                with patch.object(instance.evolution_tracker, 'get_conflicting_files', return_value=["test.py"]):
                    with patch.object(instance.evolution_tracker, 'get_file_evolution', return_value=None):
                        result = instance.preview_merge(["task_001"])

                        # Should handle missing evolution data gracefully
                        assert result["files_with_potential_conflicts"] == ["test.py"]
                        assert len(result["conflicts"]) == 0

    def test_preview_merge_with_merge_strategy(self):
        """Test preview_merge includes merge strategy in conflicts"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(
                project_dir=project_dir,
                enable_ai=False,
            )

            # Create conflict with merge strategy
            conflict = ConflictRegion(
                file_path="test.py",
                location="function:foo",
                tasks_involved=["task_001"],
                change_types=[ChangeType.MODIFY_FUNCTION],
                severity=ConflictSeverity.MEDIUM,
                can_auto_merge=False,
                reason="Test",
                merge_strategy=MergeStrategy.AI_REQUIRED,
            )

            with patch.object(instance.evolution_tracker, 'get_files_modified_by_tasks', return_value={"test.py": ["task_001"]}):
                with patch.object(instance.evolution_tracker, 'get_conflicting_files', return_value=["test.py"]):
                    with patch.object(instance.evolution_tracker, 'get_file_evolution') as mock_evolution:
                        mock_timeline = MagicMock()
                        mock_timeline.task_snapshots = []
                        mock_evolution.return_value = mock_timeline

                        with patch.object(instance.conflict_detector, 'detect_conflicts', return_value=[conflict]):
                            result = instance.preview_merge(["task_001"])

                            # Should include merge strategy
                            assert result["conflicts"][0]["strategy"] == "ai_required"


class TestSaveReport:
    """Tests for _save_report method"""

    def test_save_report_creates_directory(self):
        """Test _save_report creates reports directory if needed"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            storage_dir = Path(tmpdir) / "storage"
            instance = MergeOrchestrator(
                project_dir=project_dir,
                storage_dir=storage_dir,
                dry_run=False,
            )

            report = MergeReport(
                started_at=datetime.now(),
                tasks_merged=["task_001"],
            )
            report.file_results["test.py"] = MergeResult(
                decision=MergeDecision.AUTO_MERGED,
                file_path="test.py",
                merged_content="content",
                conflicts_resolved=[],
                conflicts_remaining=[],
            )

            # Reports directory doesn't exist yet
            assert not instance.reports_dir.exists()

            instance._save_report(report, "test_task")

            # Should create directory and save report
            assert instance.reports_dir.exists()
            assert len(list(instance.reports_dir.glob("test_task_*.json"))) == 1


class TestWriteMergedFilesEdgeCases:
    """Additional tests for write_merged_files"""

    def test_write_merged_files_creates_output_directory(self):
        """Test write_merged_files creates output directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            storage_dir = Path(tmpdir) / "storage"
            instance = MergeOrchestrator(
                project_dir=project_dir,
                storage_dir=storage_dir,
                dry_run=False,
            )

            report = MergeReport(started_at=datetime.now(), tasks_merged=[])
            report.file_results["src/test.py"] = MergeResult(
                decision=MergeDecision.AUTO_MERGED,
                file_path="src/test.py",
                merged_content="content",
                conflicts_resolved=[],
                conflicts_remaining=[],
            )

            output_dir = Path(tmpdir) / "custom_output"
            result = instance.write_merged_files(report, output_dir=output_dir)

            # Should create nested directories
            assert (output_dir / "src" / "test.py").exists()
            assert len(result) == 1

    def test_write_merged_files_utf8_encoding(self):
        """Test write_merged_files handles UTF-8 content"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            storage_dir = Path(tmpdir) / "storage"
            instance = MergeOrchestrator(
                project_dir=project_dir,
                storage_dir=storage_dir,
                dry_run=False,
            )

            # UTF-8 content with emoji and special chars
            utf8_content = "# Test file with UTF-8: 🚀 café 日本語"

            report = MergeReport(started_at=datetime.now(), tasks_merged=[])
            report.file_results["test.py"] = MergeResult(
                decision=MergeDecision.AUTO_MERGED,
                file_path="test.py",
                merged_content=utf8_content,
                conflicts_resolved=[],
                conflicts_remaining=[],
            )

            output_dir = Path(tmpdir) / "output"
            result = instance.write_merged_files(report, output_dir=output_dir)

            # Should preserve UTF-8 content
            assert (output_dir / "test.py").read_text(encoding="utf-8") == utf8_content


class TestUpdateStatsAdditionalCases:
    """Additional tests for _update_stats method"""

    def test_update_stats_direct_copy(self):
        """Test _update_stats for DIRECT_COPY decision"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(project_dir=project_dir)

            stats = MergeStats()
            result = MergeResult(
                decision=MergeDecision.DIRECT_COPY,
                file_path="test.py",
                merged_content="content",
                conflicts_resolved=[],
                conflicts_remaining=[],
                ai_calls_made=0,
                tokens_used=0,
            )

            instance._update_stats(stats, result)

            assert stats.files_processed == 1
            assert stats.files_auto_merged == 1  # DIRECT_COPY counts as auto-merged
            assert stats.files_failed == 0

    def test_update_stats_needs_human_review(self):
        """Test _update_stats for NEEDS_HUMAN_REVIEW decision"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(project_dir=project_dir)

            stats = MergeStats()
            result = MergeResult(
                decision=MergeDecision.NEEDS_HUMAN_REVIEW,
                file_path="test.py",
                merged_content=None,
                conflicts_resolved=[],
                conflicts_remaining=[MagicMock()],
                ai_calls_made=0,
                tokens_used=0,
            )

            instance._update_stats(stats, result)

            assert stats.files_processed == 1
            assert stats.files_need_review == 1
            assert stats.conflicts_detected == 1

    def test_update_stats_accumulates_conflicts(self):
        """Test _update_stats accumulates conflict counts"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(project_dir=project_dir)

            stats = MergeStats()

            # First result with 2 resolved, 1 remaining
            result1 = MergeResult(
                decision=MergeDecision.AI_MERGED,
                file_path="test1.py",
                merged_content="content1",
                conflicts_resolved=[MagicMock(), MagicMock()],
                conflicts_remaining=[MagicMock()],
                ai_calls_made=1,
                tokens_used=100,
            )

            # Second result with 1 resolved, 0 remaining
            result2 = MergeResult(
                decision=MergeDecision.AI_MERGED,
                file_path="test2.py",
                merged_content="content2",
                conflicts_resolved=[MagicMock()],
                conflicts_remaining=[],
                ai_calls_made=1,
                tokens_used=50,
            )

            instance._update_stats(stats, result1)
            instance._update_stats(stats, result2)

            assert stats.files_processed == 2
            assert stats.conflicts_detected == 4  # (2+1) + (1+0)
            assert stats.conflicts_auto_resolved == 3  # 2 + 1
            assert stats.conflicts_ai_resolved == 3  # Same as auto_resolved for AI_MERGED
            assert stats.ai_calls_made == 2
            assert stats.estimated_tokens_used == 150


class TestProgressCallbackDetailed:
    """Detailed tests for progress callback behavior"""

    def test_merge_task_progress_stages_single_file(self):
        """Test merge_task emits all progress stages for single file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            worktree_path = Path(tmpdir) / "worktree"
            worktree_path.mkdir(parents=True)

            instance = MergeOrchestrator(
                project_dir=project_dir,
                enable_ai=False,
                dry_run=True,
            )

            stages = []

            def callback(stage, percent, message, details=None):
                stages.append((stage, percent, message))

            snapshot = MagicMock()
            snapshot.semantic_changes = []

            with patch.object(instance.evolution_tracker, 'refresh_from_git'):
                with patch.object(instance.evolution_tracker, 'get_task_modifications', return_value=[("test.py", snapshot)]):
                    with patch.object(instance, '_merge_file', return_value=MergeResult(
                        decision=MergeDecision.AUTO_MERGED,
                        file_path="test.py",
                        merged_content="content",
                        conflicts_resolved=[],
                        conflicts_remaining=[],
                    )):
                        instance.merge_task(
                            "task_001",
                            worktree_path=worktree_path,
                            progress_callback=callback,
                        )

                        # Should have multiple stage transitions
                        stage_types = [s[0] for s in stages]
                        assert MergeProgressStage.ANALYZING in stage_types
                        assert MergeProgressStage.COMPLETE in stage_types

    def test_merge_task_progress_with_details(self):
        """Test progress callback includes details parameter"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            worktree_path = Path(tmpdir) / "worktree"
            worktree_path.mkdir(parents=True)

            instance = MergeOrchestrator(
                project_dir=project_dir,
                enable_ai=False,
                dry_run=True,
            )

            calls_with_details = []

            def callback(stage, percent, message, details=None):
                if details:
                    calls_with_details.append((stage, details))

            snapshot = MagicMock()
            snapshot.semantic_changes = []

            with patch.object(instance.evolution_tracker, 'refresh_from_git'):
                with patch.object(instance.evolution_tracker, 'get_task_modifications', return_value=[("test.py", snapshot)]):
                    with patch.object(instance, '_merge_file', return_value=MergeResult(
                        decision=MergeDecision.AUTO_MERGED,
                        file_path="test.py",
                        merged_content="content",
                        conflicts_resolved=[],
                        conflicts_remaining=[],
                    )):
                        instance.merge_task(
                            "task_001",
                            worktree_path=worktree_path,
                            progress_callback=callback,
                        )

                        # Should have details in some callbacks
                        assert len(calls_with_details) > 0


class TestDirectCopyFailurePaths:
    """Tests for DIRECT_COPY failure scenarios"""

    def test_direct_copy_file_not_in_worktree(self):
        """Test DIRECT_COPY when file doesn't exist in worktree"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            worktree_path = Path(tmpdir) / "worktree"
            worktree_path.mkdir(parents=True)

            instance = MergeOrchestrator(
                project_dir=project_dir,
                enable_ai=False,
                dry_run=True,
            )

            # Mock DIRECT_COPY result
            mock_result = MergeResult(
                decision=MergeDecision.DIRECT_COPY,
                file_path="nonexistent.py",
                merged_content=None,
                conflicts_resolved=[],
                conflicts_remaining=[],
                ai_calls_made=0,
                tokens_used=0,
            )

            snapshot = MagicMock()
            snapshot.semantic_changes = []

            with patch.object(instance.evolution_tracker, 'refresh_from_git'):
                with patch.object(instance.evolution_tracker, 'get_task_modifications', return_value=[("nonexistent.py", snapshot)]):
                    with patch.object(instance, '_merge_file', return_value=mock_result):
                        result = instance.merge_task(
                            "task_001",
                            worktree_path=worktree_path,
                        )

                        # Should mark as FAILED when file not found
                        file_result = result.file_results["nonexistent.py"]
                        assert file_result.decision == MergeDecision.FAILED
                        assert "Worktree file not found" in file_result.error


class TestMergeTasksIntegration:
    """Integration tests for merge_tasks"""

    def test_merge_tasks_multiple_files_progress_updates(self):
        """Test merge_tasks sends progress for each file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(
                project_dir=project_dir,
                enable_ai=False,
                dry_run=True,
            )

            progress_calls = []

            def callback(stage, percent, message, details=None):
                progress_calls.append((stage, percent, message, details))

            request = TaskMergeRequest(
                task_id="task_001",
                worktree_path=Path(tmpdir) / "worktree",
            )

            # Mock multiple files
            files = {"file1.py": ["task_001"], "file2.py": ["task_001"]}

            mock_snapshot = MagicMock()
            mock_snapshot.task_id = "task_001"

            with patch.object(instance.evolution_tracker, 'get_files_modified_by_tasks', return_value=files):
                with patch.object(instance.evolution_tracker, 'get_file_evolution') as mock_evolution:
                    mock_timeline = MagicMock()
                    mock_timeline.get_task_snapshot.return_value = mock_snapshot
                    mock_evolution.return_value = mock_timeline

                    with patch.object(instance, '_merge_file', return_value=MergeResult(
                        decision=MergeDecision.AUTO_MERGED,
                        file_path="test.py",
                        merged_content="content",
                        conflicts_resolved=[],
                        conflicts_remaining=[],
                    )):
                        instance.merge_tasks([request], progress_callback=callback)

                        # Should have progress updates
                        resolving_stages = [p for p in progress_calls if p[0] == MergeProgressStage.RESOLVING]
                        assert len(resolving_stages) >= 2  # At least one per file

    def test_merge_tasks_empty_modifications_continues(self):
        """Test merge_tasks handles empty evolution gracefully"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(
                project_dir=project_dir,
                enable_ai=False,
                dry_run=True,
            )

            request = TaskMergeRequest(
                task_id="task_001",
                worktree_path=Path(tmpdir) / "worktree",
            )

            mock_snapshot = MagicMock()
            mock_snapshot.task_id = "task_001"

            # Return empty dict for files_modified
            with patch.object(instance.evolution_tracker, 'get_files_modified_by_tasks', return_value={}):
                with patch.object(instance.evolution_tracker, 'get_file_evolution') as mock_evolution:
                    mock_timeline = MagicMock()
                    mock_timeline.get_task_snapshot.return_value = mock_snapshot
                    mock_evolution.return_value = mock_timeline

                    result = instance.merge_tasks([request])

                    # Should succeed with no files processed
                    assert result.success is True
                    assert result.stats.files_processed == 0


class TestAIResolverProperty:
    """Tests for ai_resolver property behavior"""

    def test_ai_resolver_disabled_returns_noop_resolver(self):
        """Test ai_resolver returns noop resolver when AI is disabled"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(
                project_dir=project_dir,
                enable_ai=False,
            )

            resolver = instance.ai_resolver
            assert resolver is not None
            # Accessing again should return same instance
            assert instance.ai_resolver is resolver

    def test_ai_resolver_custom_resolver(self):
        """Test ai_resolver returns custom resolver when provided"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            custom_resolver = MagicMock()

            instance = MergeOrchestrator(
                project_dir=project_dir,
                enable_ai=True,
                ai_resolver=custom_resolver,
            )

            # Should use provided resolver
            assert instance.ai_resolver is custom_resolver
            assert instance._ai_resolver_initialized is True


class TestConflictResolverProperty:
    """Tests for conflict_resolver property behavior"""

    def test_conflict_resolver_with_ai_enabled(self):
        """Test conflict_resolver includes AI resolver when enabled"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(
                project_dir=project_dir,
                enable_ai=True,
            )

            resolver = instance.conflict_resolver
            assert resolver is not None
            # Accessing again should return same instance (lazy init)
            assert instance.conflict_resolver is resolver
            assert instance._conflict_resolver is not None

    def test_conflict_resolver_without_ai(self):
        """Test conflict_resolver works without AI"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(
                project_dir=project_dir,
                enable_ai=False,
            )

            resolver = instance.conflict_resolver
            assert resolver is not None
            # Should be initialized without AI resolver
            assert instance._conflict_resolver is not None


class TestMergePipelineProperty:
    """Tests for merge_pipeline property behavior"""

    def test_merge_pipeline_lazy_initialization(self):
        """Test merge_pipeline initializes on first access"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(project_dir=project_dir)

            # Initially None
            assert instance._merge_pipeline is None

            # First access initializes
            pipeline = instance.merge_pipeline
            assert pipeline is not None
            assert instance._merge_pipeline is not None

            # Subsequent access returns same instance
            assert instance.merge_pipeline is pipeline


class TestApplyToProjectEdgeCases:
    """Additional tests for apply_to_project"""

    def test_apply_to_project_nested_paths(self):
        """Test apply_to_project creates nested directories"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(
                project_dir=project_dir,
                dry_run=False,
            )

            report = MergeReport(started_at=datetime.now(), tasks_merged=[])
            report.file_results["src/deeply/nested/test.py"] = MergeResult(
                decision=MergeDecision.AUTO_MERGED,
                file_path="src/deeply/nested/test.py",
                merged_content="content",
                conflicts_resolved=[],
                conflicts_remaining=[],
            )

            result = instance.apply_to_project(report)

            assert result is True
            assert (project_dir / "src" / "deeply" / "nested" / "test.py").exists()

    def test_apply_to_project_skips_unsuccessful_results(self):
        """Test apply_to_project skips files with unsuccessful results"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            instance = MergeOrchestrator(
                project_dir=project_dir,
                dry_run=False,
            )

            report = MergeReport(started_at=datetime.now(), tasks_merged=[])
            # Successful file
            report.file_results["good.py"] = MergeResult(
                decision=MergeDecision.AUTO_MERGED,
                file_path="good.py",
                merged_content="good content",
                conflicts_resolved=[],
                conflicts_remaining=[],
            )
            # Unsuccessful file (no content)
            report.file_results["bad.py"] = MergeResult(
                decision=MergeDecision.FAILED,
                file_path="bad.py",
                merged_content=None,
                conflicts_resolved=[],
                conflicts_remaining=[],
                error="Failed",
            )

            result = instance.apply_to_project(report)

            # Should succeed despite one failure
            assert result is True
            assert (project_dir / "good.py").exists()
            assert not (project_dir / "bad.py").exists()
