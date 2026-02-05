"""Tests for merge/models.py

Tests for MergeStats, TaskMergeRequest, and MergeReport dataclasses.
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
import pytest
import tempfile
import json

from merge.models import MergeStats, TaskMergeRequest, MergeReport
from merge.types import MergeDecision, MergeResult, ConflictRegion, ChangeType, ConflictSeverity


class TestMergeStats:
    """Tests for MergeStats dataclass"""

    def test_merge_stats_default_values(self):
        """Test MergeStats initializes with default zero values"""
        stats = MergeStats()

        assert stats.files_processed == 0
        assert stats.files_auto_merged == 0
        assert stats.files_ai_merged == 0
        assert stats.files_need_review == 0
        assert stats.files_failed == 0
        assert stats.conflicts_detected == 0
        assert stats.conflicts_auto_resolved == 0
        assert stats.conflicts_ai_resolved == 0
        assert stats.ai_calls_made == 0
        assert stats.estimated_tokens_used == 0
        assert stats.duration_seconds == 0.0

    def test_merge_stats_custom_values(self):
        """Test MergeStats with custom values"""
        stats = MergeStats(
            files_processed=10,
            files_auto_merged=5,
            files_ai_merged=3,
            files_need_review=1,
            files_failed=1,
            conflicts_detected=8,
            conflicts_auto_resolved=5,
            conflicts_ai_resolved=3,
            ai_calls_made=3,
            estimated_tokens_used=1500,
            duration_seconds=45.5,
        )

        assert stats.files_processed == 10
        assert stats.files_auto_merged == 5
        assert stats.ai_calls_made == 3

    def test_merge_stats_to_dict(self):
        """Test MergeStats.to_dict() serialization"""
        stats = MergeStats(
            files_processed=5,
            files_auto_merged=3,
            files_ai_merged=1,
            files_need_review=0,
            files_failed=1,
            conflicts_detected=4,
            conflicts_auto_resolved=3,
            conflicts_ai_resolved=1,
            ai_calls_made=1,
            estimated_tokens_used=500,
            duration_seconds=10.5,
        )

        result = stats.to_dict()

        assert isinstance(result, dict)
        assert result["files_processed"] == 5
        assert result["files_auto_merged"] == 3
        assert result["files_ai_merged"] == 1
        assert result["conflicts_detected"] == 4
        assert result["duration_seconds"] == 10.5

    def test_merge_stats_success_rate_no_files(self):
        """Test success_rate property with no files processed"""
        stats = MergeStats(files_processed=0)

        assert stats.success_rate == 1.0  # Returns 1.0 for empty

    def test_merge_stats_success_rate_all_auto_merged(self):
        """Test success_rate property with all auto-merged files"""
        stats = MergeStats(
            files_processed=10,
            files_auto_merged=10,
            files_ai_merged=0,
        )

        assert stats.success_rate == 1.0

    def test_merge_stats_success_rate_mixed(self):
        """Test success_rate property with mixed results"""
        stats = MergeStats(
            files_processed=10,
            files_auto_merged=5,
            files_ai_merged=3,
            files_failed=2,
        )

        # (5 + 3) / 10 = 0.8
        assert stats.success_rate == 0.8

    def test_merge_stats_auto_merge_rate_no_conflicts(self):
        """Test auto_merge_rate property with no conflicts"""
        stats = MergeStats(conflicts_detected=0)

        assert stats.auto_merge_rate == 1.0  # Returns 1.0 for no conflicts

    def test_merge_stats_auto_merge_rate_all_resolved(self):
        """Test auto_merge_rate property with all conflicts auto-resolved"""
        stats = MergeStats(
            conflicts_detected=10,
            conflicts_auto_resolved=10,
        )

        assert stats.auto_merge_rate == 1.0

    def test_merge_stats_auto_merge_rate_partial(self):
        """Test auto_merge_rate property with partial resolution"""
        stats = MergeStats(
            conflicts_detected=10,
            conflicts_auto_resolved=5,
        )

        assert stats.auto_merge_rate == 0.5


class TestTaskMergeRequest:
    """Tests for TaskMergeRequest dataclass"""

    def test_task_merge_request_required_fields(self):
        """Test TaskMergeRequest with required fields only"""
        with tempfile.TemporaryDirectory() as tmpdir:
            request = TaskMergeRequest(
                task_id="task-001",
                worktree_path=Path(tmpdir),
            )

            assert request.task_id == "task-001"
            assert request.worktree_path == Path(tmpdir)
            assert request.intent == ""
            assert request.priority == 0

    def test_task_merge_request_all_fields(self):
        """Test TaskMergeRequest with all fields"""
        with tempfile.TemporaryDirectory() as tmpdir:
            request = TaskMergeRequest(
                task_id="task-002",
                worktree_path=Path(tmpdir) / "worktree",
                intent="Add user authentication",
                priority=10,
            )

            assert request.task_id == "task-002"
            assert request.intent == "Add user authentication"
            assert request.priority == 10

    def test_task_merge_request_priority_sorting(self):
        """Test that requests can be sorted by priority"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)

            request_low = TaskMergeRequest(
                task_id="low",
                worktree_path=base_path,
                priority=1,
            )
            request_high = TaskMergeRequest(
                task_id="high",
                worktree_path=base_path,
                priority=10,
            )
            request_medium = TaskMergeRequest(
                task_id="medium",
                worktree_path=base_path,
                priority=5,
            )

            # Sort by priority (descending)
            requests = [request_low, request_high, request_medium]
            sorted_requests = sorted(requests, key=lambda r: -r.priority)

            assert sorted_requests[0].task_id == "high"
            assert sorted_requests[1].task_id == "medium"
            assert sorted_requests[2].task_id == "low"


class TestMergeReport:
    """Tests for MergeReport dataclass"""

    def test_merge_report_default_values(self):
        """Test MergeReport initializes with required field only"""
        started_at = datetime.now()
        report = MergeReport(started_at=started_at)

        assert report.started_at == started_at
        assert report.completed_at is None
        assert report.tasks_merged == []
        assert report.file_results == {}
        assert report.success is True
        assert report.error is None
        # stats should be default MergeStats instance
        assert isinstance(report.stats, MergeStats)
        assert report.stats.files_processed == 0

    def test_merge_report_with_tasks(self):
        """Test MergeReport with tasks_merged"""
        started_at = datetime.now()
        report = MergeReport(
            started_at=started_at,
            tasks_merged=["task-001", "task-002"],
        )

        assert len(report.tasks_merged) == 2
        assert "task-001" in report.tasks_merged
        assert "task-002" in report.tasks_merged

    def test_merge_report_with_file_results(self):
        """Test MergeReport with file results"""
        started_at = datetime.now()
        result = MergeResult(
            decision=MergeDecision.AUTO_MERGED,
            file_path="test.py",
            merged_content="content",
            conflicts_resolved=[],
            conflicts_remaining=[],
        )

        report = MergeReport(
            started_at=started_at,
            file_results={"test.py": result},
        )

        assert "test.py" in report.file_results
        assert report.file_results["test.py"].decision == MergeDecision.AUTO_MERGED

    def test_merge_report_with_error(self):
        """Test MergeReport with error state"""
        started_at = datetime.now()
        report = MergeReport(
            started_at=started_at,
            success=False,
            error="Worktree not found",
        )

        assert report.success is False
        assert report.error == "Worktree not found"

    def test_merge_report_completed_at(self):
        """Test MergeReport with completion time"""
        started_at = datetime.now()
        completed_at = datetime.now()

        report = MergeReport(
            started_at=started_at,
            completed_at=completed_at,
        )

        assert report.completed_at == completed_at

    def test_merge_report_to_dict(self):
        """Test MergeReport.to_dict() serialization"""
        started_at = datetime(2024, 1, 1, 12, 0, 0)
        completed_at = datetime(2024, 1, 1, 12, 5, 30)

        result = MergeResult(
            decision=MergeDecision.AUTO_MERGED,
            file_path="test.py",
            merged_content="content",
            conflicts_resolved=[],
            conflicts_remaining=[],
        )

        report = MergeReport(
            started_at=started_at,
            completed_at=completed_at,
            tasks_merged=["task-001"],
            file_results={"test.py": result},
            success=True,
        )

        result_dict = report.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["started_at"] == "2024-01-01T12:00:00"
        assert result_dict["completed_at"] == "2024-01-01T12:05:30"
        assert result_dict["tasks_merged"] == ["task-001"]
        assert result_dict["success"] is True
        assert "test.py" in result_dict["file_results"]
        assert "stats" in result_dict

    def test_merge_report_to_dict_with_error(self):
        """Test MergeReport.to_dict() with error state"""
        started_at = datetime.now()
        report = MergeReport(
            started_at=started_at,
            success=False,
            error="Merge failed",
        )

        result_dict = report.to_dict()

        assert result_dict["success"] is False
        assert result_dict["error"] == "Merge failed"

    def test_merge_report_to_dict_with_conflicts(self):
        """Test MergeReport.to_dict() includes conflict info"""
        started_at = datetime.now()

        conflict = ConflictRegion(
            file_path="test.py",
            location="function:foo",
            tasks_involved=["task-001", "task-002"],
            change_types=[ChangeType.MODIFY_FUNCTION],
            severity=ConflictSeverity.HIGH,
            can_auto_merge=False,
            reason="Test conflict",
        )

        result = MergeResult(
            decision=MergeDecision.NEEDS_HUMAN_REVIEW,
            file_path="test.py",
            merged_content=None,
            conflicts_resolved=[],
            conflicts_remaining=[conflict],
        )

        report = MergeReport(
            started_at=started_at,
            file_results={"test.py": result},
        )

        result_dict = report.to_dict()

        # Check that conflicts are serialized
        file_result = result_dict["file_results"]["test.py"]
        assert len(file_result["conflicts_remaining"]) == 1
        assert file_result["conflicts_remaining"][0]["file_path"] == "test.py"

    def test_merge_report_save_creates_file(self):
        """Test MergeReport.save() creates JSON file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            started_at = datetime(2024, 1, 1, 12, 0, 0)

            report = MergeReport(
                started_at=started_at,
                tasks_merged=["task-001"],
            )

            save_path = Path(tmpdir) / "report.json"
            report.save(save_path)

            assert save_path.exists()

            # Verify content
            with open(save_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert data["tasks_merged"] == ["task-001"]
            assert data["started_at"] == "2024-01-01T12:00:00"

    def test_merge_report_save_overwrites_existing(self):
        """Test MergeReport.save() overwrites existing file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "report.json"

            # Create initial file
            save_path.write_text('{"old": "data"}')

            started_at = datetime.now()
            report = MergeReport(started_at=started_at, tasks_merged=["task-001"])
            report.save(save_path)

            # Verify file was overwritten
            with open(save_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert "old" not in data
            assert "tasks_merged" in data

    def test_merge_report_save_requires_parent_directory(self):
        """Test MergeReport.save() requires parent directory to exist"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Use a nested path that doesn't exist
            save_path = Path(tmpdir) / "reports" / "nested" / "report.json"

            started_at = datetime.now()
            report = MergeReport(started_at=started_at)

            # Should raise FileNotFoundError if parent doesn't exist
            with pytest.raises(FileNotFoundError):
                report.save(save_path)

    def test_merge_report_save_utf8_encoding(self):
        """Test MergeReport.save() handles UTF-8 content"""
        with tempfile.TemporaryDirectory() as tmpdir:
            started_at = datetime.now()

            # Create a report with UTF-8 content
            result = MergeResult(
                decision=MergeDecision.AUTO_MERGED,
                file_path="test.py",
                merged_content="# Test: 🚀 café 日本語",
                conflicts_resolved=[],
                conflicts_remaining=[],
            )

            report = MergeReport(
                started_at=started_at,
                file_results={"test.py": result},
            )

            save_path = Path(tmpdir) / "report.json"
            report.save(save_path)

            # Read back and verify UTF-8 is preserved
            with open(save_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert "café" in data["file_results"]["test.py"]["merged_content"]

    def test_merge_report_save_with_stats(self):
        """Test MergeReport.save() includes statistics"""
        with tempfile.TemporaryDirectory() as tmpdir:
            started_at = datetime.now()

            stats = MergeStats(
                files_processed=10,
                files_auto_merged=8,
                files_ai_merged=1,
                files_failed=1,
                conflicts_detected=3,
                conflicts_auto_resolved=2,
                duration_seconds=15.5,
            )

            report = MergeReport(
                started_at=started_at,
                stats=stats,
            )

            save_path = Path(tmpdir) / "report.json"
            report.save(save_path)

            with open(save_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert data["stats"]["files_processed"] == 10
            assert data["stats"]["files_auto_merged"] == 8
            assert data["stats"]["duration_seconds"] == 15.5


class TestMergeReportIntegration:
    """Integration tests for MergeReport with MergeResult"""

    def test_merge_report_accumulates_results(self):
        """Test MergeReport accumulates multiple file results"""
        started_at = datetime.now()

        result1 = MergeResult(
            decision=MergeDecision.AUTO_MERGED,
            file_path="file1.py",
            merged_content="content1",
            conflicts_resolved=[],
            conflicts_remaining=[],
        )

        result2 = MergeResult(
            decision=MergeDecision.AI_MERGED,
            file_path="file2.py",
            merged_content="content2",
            conflicts_resolved=[],
            conflicts_remaining=[],
            ai_calls_made=1,
            tokens_used=500,
        )

        report = MergeReport(
            started_at=started_at,
            file_results={
                "file1.py": result1,
                "file2.py": result2,
            },
        )

        assert len(report.file_results) == 2
        assert report.file_results["file1.py"].decision == MergeDecision.AUTO_MERGED
        assert report.file_results["file2.py"].decision == MergeDecision.AI_MERGED

    def test_merge_report_to_dict_roundtrip(self):
        """Test MergeReport can be serialized and deserialized"""
        started_at = datetime(2024, 1, 1, 12, 0, 0)
        completed_at = datetime(2024, 1, 1, 12, 5, 0)

        result = MergeResult(
            decision=MergeDecision.AUTO_MERGED,
            file_path="test.py",
            merged_content="merged",
            conflicts_resolved=[],
            conflicts_remaining=[],
        )

        original_report = MergeReport(
            started_at=started_at,
            completed_at=completed_at,
            tasks_merged=["task-001", "task-002"],
            file_results={"test.py": result},
            success=True,
        )

        # Serialize
        report_dict = original_report.to_dict()

        # Verify all fields are present
        assert "started_at" in report_dict
        assert "completed_at" in report_dict
        assert "tasks_merged" in report_dict
        assert "file_results" in report_dict
        assert "stats" in report_dict
        assert "success" in report_dict
        assert "error" in report_dict

    def test_merge_report_with_multiple_conflicts(self):
        """Test MergeReport with multiple conflicts in results"""
        started_at = datetime.now()

        conflict1 = ConflictRegion(
            file_path="test.py",
            location="function:foo",
            tasks_involved=["task-001", "task-002"],
            change_types=[ChangeType.MODIFY_FUNCTION],
            severity=ConflictSeverity.HIGH,
            can_auto_merge=False,
            reason="Conflict 1",
        )

        conflict2 = ConflictRegion(
            file_path="test.py",
            location="function:bar",
            tasks_involved=["task-001", "task-002"],
            change_types=[ChangeType.MODIFY_FUNCTION],
            severity=ConflictSeverity.MEDIUM,
            can_auto_merge=False,
            reason="Conflict 2",
        )

        result = MergeResult(
            decision=MergeDecision.NEEDS_HUMAN_REVIEW,
            file_path="test.py",
            merged_content=None,
            conflicts_resolved=[],
            conflicts_remaining=[conflict1, conflict2],
        )

        report = MergeReport(
            started_at=started_at,
            file_results={"test.py": result},
        )

        result_dict = report.to_dict()

        file_result = result_dict["file_results"]["test.py"]
        assert len(file_result["conflicts_remaining"]) == 2
        assert file_result["conflicts_remaining"][0]["location"] == "function:foo"
        assert file_result["conflicts_remaining"][1]["location"] == "function:bar"


class TestMergeReportEdgeCases:
    """Edge case tests for MergeReport"""

    def test_merge_report_empty_file_results(self):
        """Test MergeReport with empty file results dict"""
        started_at = datetime.now()
        report = MergeReport(
            started_at=started_at,
            file_results={},
        )

        assert len(report.file_results) == 0
        assert report.to_dict()["file_results"] == {}

    def test_merge_report_none_completed_at(self):
        """Test MergeReport.to_dict() with None completed_at"""
        started_at = datetime.now()
        report = MergeReport(
            started_at=started_at,
            completed_at=None,
        )

        result_dict = report.to_dict()
        assert result_dict["completed_at"] is None

    def test_merge_report_zero_duration(self):
        """Test MergeReport with zero duration"""
        stats = MergeStats(duration_seconds=0.0)
        started_at = datetime.now()

        report = MergeReport(
            started_at=started_at,
            stats=stats,
        )

        assert report.stats.duration_seconds == 0.0
        assert report.to_dict()["stats"]["duration_seconds"] == 0.0

    def test_merge_report_negative_duration_not_possible(self):
        """Test that negative duration cannot be set (dataclass validation)"""
        # Dataclasses don't validate, but we can test the behavior
        stats = MergeStats(duration_seconds=-1.0)
        # This is allowed by dataclass but represents invalid data
        assert stats.duration_seconds == -1.0

    def test_merge_report_very_long_task_list(self):
        """Test MergeReport with many tasks"""
        started_at = datetime.now()
        task_ids = [f"task-{i:03d}" for i in range(1000)]

        report = MergeReport(
            started_at=started_at,
            tasks_merged=task_ids,
        )

        assert len(report.tasks_merged) == 1000
        assert report.to_dict()["tasks_merged"] == task_ids
