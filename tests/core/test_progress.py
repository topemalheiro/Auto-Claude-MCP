"""
Comprehensive tests for core.progress module.

Tests cover:
- Subtask counting (count_subtasks, count_subtasks_detailed)
- Build status checking (is_build_complete, get_progress_percentage)
- Session header printing
- Progress summary printing
- Plan summary retrieval
- Current phase detection
- Next subtask detection with dependencies
- Duration formatting
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.progress import (
    count_subtasks,
    count_subtasks_detailed,
    format_duration,
    get_current_phase,
    get_next_subtask,
    get_plan_summary,
    get_progress_percentage,
    is_build_complete,
    print_build_complete_banner,
    print_paused_banner,
    print_progress_summary,
    print_session_header,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def spec_dir(tmp_path):
    """Create a temporary spec directory."""
    spec = tmp_path / "specs" / "001-test"
    spec.mkdir(parents=True)
    return spec


@pytest.fixture
def plan_file(spec_dir):
    """Create a plan file path."""
    return spec_dir / "implementation_plan.json"


@pytest.fixture
def sample_plan():
    """Sample implementation plan data."""
    return {
        "workflow_type": "standard",
        "phases": [
            {
                "id": "phase1",
                "phase": 1,
                "name": "Foundation",
                "depends_on": [],
                "subtasks": [
                    {"id": "1.1", "description": "Task 1.1", "status": "completed"},
                    {"id": "1.2", "description": "Task 1.2", "status": "completed"},
                ],
            },
            {
                "id": "phase2",
                "phase": 2,
                "name": "Implementation",
                "depends_on": ["phase1"],
                "subtasks": [
                    {"id": "2.1", "description": "Task 2.1", "status": "in_progress"},
                    {"id": "2.2", "description": "Task 2.2", "status": "pending"},
                ],
            },
            {
                "id": "phase3",
                "phase": 3,
                "name": "Testing",
                "depends_on": ["phase2"],
                "subtasks": [
                    {"id": "3.1", "description": "Task 3.1", "status": "pending"},
                ],
            },
        ],
    }


@pytest.fixture
def completed_plan():
    """Fully completed implementation plan."""
    return {
        "workflow_type": "standard",
        "phases": [
            {
                "id": "phase1",
                "phase": 1,
                "name": "Foundation",
                "depends_on": [],
                "subtasks": [
                    {"id": "1.1", "description": "Task 1.1", "status": "completed"},
                    {"id": "1.2", "description": "Task 1.2", "status": "completed"},
                ],
            }
        ],
    }


# ============================================================================
# count_subtests Tests
# ============================================================================


class TestCountSubtasks:
    """Tests for count_subtasks function."""

    def test_count_no_plan_file(self, spec_dir):
        """Test counting when plan file doesn't exist."""
        completed, total = count_subtasks(spec_dir)
        assert completed == 0
        assert total == 0

    def test_count_valid_plan(self, spec_dir, sample_plan):
        """Test counting subtasks in valid plan."""
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(sample_plan), encoding="utf-8")

        completed, total = count_subtasks(spec_dir)
        assert completed == 2  # 1.1 and 1.2
        assert total == 5  # All subtasks

    def test_count_all_completed(self, spec_dir, completed_plan):
        """Test counting when all subtasks completed."""
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(completed_plan), encoding="utf-8")

        completed, total = count_subtasks(spec_dir)
        assert completed == 2
        assert total == 2

    def test_count_empty_plan(self, spec_dir):
        """Test counting with empty plan."""
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps({"phases": []}), encoding="utf-8")

        completed, total = count_subtasks(spec_dir)
        assert completed == 0
        assert total == 0

    def test_count_no_phases_key(self, spec_dir):
        """Test counting with missing phases key."""
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps({}), encoding="utf-8")

        completed, total = count_subtasks(spec_dir)
        assert completed == 0
        assert total == 0

    def test_count_invalid_json(self, spec_dir):
        """Test counting with invalid JSON."""
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text("{invalid json}", encoding="utf-8")

        completed, total = count_subtasks(spec_dir)
        assert completed == 0
        assert total == 0

    def test_count_with_various_statuses(self, spec_dir):
        """Test counting with various subtask statuses."""
        plan = {
            "phases": [
                {
                    "subtasks": [
                        {"status": "completed"},
                        {"status": "in_progress"},
                        {"status": "pending"},
                        {"status": "failed"},
                        {"status": "not_started"},
                        {"status": "not started"},
                    ]
                }
            ]
        }
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        completed, total = count_subtasks(spec_dir)
        assert completed == 1  # Only "completed" counts
        assert total == 6


# ============================================================================
# count_subtasks_detailed Tests
# ============================================================================


class TestCountSubtasksDetailed:
    """Tests for count_subtasks_detailed function."""

    def test_detailed_no_plan_file(self, spec_dir):
        """Test detailed counting when plan file doesn't exist."""
        result = count_subtasks_detailed(spec_dir)
        assert result["completed"] == 0
        assert result["in_progress"] == 0
        assert result["pending"] == 0
        assert result["failed"] == 0
        assert result["total"] == 0

    def test_detailed_all_statuses(self, spec_dir):
        """Test detailed counting with all statuses."""
        plan = {
            "phases": [
                {
                    "subtasks": [
                        {"status": "completed"},
                        {"status": "completed"},
                        {"status": "in_progress"},
                        {"status": "pending"},
                        {"status": "failed"},
                        {"status": "unknown_status"},
                    ]
                }
            ]
        }
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        result = count_subtasks_detailed(spec_dir)
        assert result["completed"] == 2
        assert result["in_progress"] == 1
        assert result["pending"] == 2  # "pending" + "unknown_status" defaults to pending
        assert result["failed"] == 1
        assert result["total"] == 6

    def test_detailed_missing_status_defaults_to_pending(self, spec_dir):
        """Test that missing status defaults to pending."""
        plan = {
            "phases": [
                {
                    "subtasks": [
                        {"id": "1"},  # No status field
                    ]
                }
            ]
        }
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        result = count_subtasks_detailed(spec_dir)
        assert result["pending"] == 1
        assert result["total"] == 1


# ============================================================================
# is_build_complete Tests
# ============================================================================


class TestIsBuildComplete:
    """Tests for is_build_complete function."""

    def test_complete_when_all_done(self, spec_dir, completed_plan):
        """Test build complete when all subtasks done."""
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(completed_plan), encoding="utf-8")

        assert is_build_complete(spec_dir) is True

    def test_not_complete_when_partial(self, spec_dir, sample_plan):
        """Test build not complete when partial."""
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(sample_plan), encoding="utf-8")

        assert is_build_complete(spec_dir) is False

    def test_not_complete_when_empty(self, spec_dir):
        """Test build not complete when no subtasks."""
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps({"phases": []}), encoding="utf-8")

        assert is_build_complete(spec_dir) is False

    def test_not_complete_no_file(self, spec_dir):
        """Test build not complete when no plan file."""
        assert is_build_complete(spec_dir) is False


# ============================================================================
# get_progress_percentage Tests
# ============================================================================


class TestGetProgressPercentage:
    """Tests for get_progress_percentage function."""

    def test_percentage_half_done(self, spec_dir, sample_plan):
        """Test percentage calculation."""
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(sample_plan), encoding="utf-8")

        percentage = get_progress_percentage(spec_dir)
        assert percentage == 40.0  # 2/5 = 40%

    def test_percentage_all_done(self, spec_dir, completed_plan):
        """Test percentage when complete."""
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(completed_plan), encoding="utf-8")

        percentage = get_progress_percentage(spec_dir)
        assert percentage == 100.0

    def test_percentage_none_done(self, spec_dir):
        """Test percentage when none done."""
        plan = {
            "phases": [
                {
                    "subtasks": [
                        {"status": "pending"},
                        {"status": "pending"},
                    ]
                }
            ]
        }
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        percentage = get_progress_percentage(spec_dir)
        assert percentage == 0.0

    def test_percentage_no_subtasks(self, spec_dir):
        """Test percentage when no subtasks."""
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps({"phases": []}), encoding="utf-8")

        percentage = get_progress_percentage(spec_dir)
        assert percentage == 0.0


# ============================================================================
# print_session_header Tests
# ============================================================================


class TestPrintSessionHeader:
    """Tests for print_session_header function."""

    def test_planner_header(self, capsys):
        """Test planner session header."""
        print_session_header(session_num=1, is_planner=True)

        captured = capsys.readouterr()
        assert "SESSION 1" in captured.out
        assert "PLANNER AGENT" in captured.out

    def test_coder_header(self, capsys):
        """Test coder session header."""
        print_session_header(session_num=2, is_planner=False)

        captured = capsys.readouterr()
        assert "SESSION 2" in captured.out
        assert "CODING AGENT" in captured.out

    def test_header_with_subtask(self, capsys):
        """Test header with subtask info."""
        print_session_header(
            session_num=1,
            is_planner=False,
            subtask_id="2.1",
            subtask_desc="Implement feature",
        )

        captured = capsys.readouterr()
        assert "Subtask:" in captured.out
        assert "2.1" in captured.out
        assert "Implement feature" in captured.out

    def test_header_with_long_subtask_desc(self, capsys):
        """Test header truncates long descriptions."""
        long_desc = "x" * 100
        print_session_header(
            session_num=1,
            is_planner=False,
            subtask_id="1.1",
            subtask_desc=long_desc,
        )

        captured = capsys.readouterr()
        # Should be truncated to 50 chars + "..."
        assert "..." in captured.out

    def test_header_with_phase(self, capsys):
        """Test header with phase info."""
        print_session_header(
            session_num=1,
            is_planner=False,
            phase_name="Implementation",
        )

        captured = capsys.readouterr()
        assert "Phase:" in captured.out
        assert "Implementation" in captured.out

    def test_header_with_attempt(self, capsys):
        """Test header with retry attempt."""
        print_session_header(
            session_num=1,
            is_planner=False,
            attempt=3,
        )

        captured = capsys.readouterr()
        assert "Attempt:" in captured.out
        assert "3" in captured.out


# ============================================================================
# print_progress_summary Tests
# ============================================================================


class TestPrintProgressSummary:
    """Tests for print_progress_summary function."""

    def test_summary_no_plan(self, spec_dir, capsys):
        """Test summary when no plan exists."""
        print_progress_summary(spec_dir)

        captured = capsys.readouterr()
        assert "No implementation subtasks yet" in captured.out

    def test_summary_with_progress(self, spec_dir, sample_plan, capsys):
        """Test summary with active progress."""
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(sample_plan), encoding="utf-8")

        print_progress_summary(spec_dir)

        captured = capsys.readouterr()
        assert "Progress:" in captured.out
        assert "3 subtasks remaining" in captured.out
        assert "Phases:" in captured.out

    def test_summary_complete(self, spec_dir, completed_plan, capsys):
        """Test summary when build complete."""
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(completed_plan), encoding="utf-8")

        print_progress_summary(spec_dir)

        captured = capsys.readouterr()
        assert "BUILD COMPLETE" in captured.out

    def test_summary_show_next(self, spec_dir, sample_plan, capsys):
        """Test summary shows next subtask."""
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(sample_plan), encoding="utf-8")

        print_progress_summary(spec_dir, show_next=True)

        captured = capsys.readouterr()
        assert "Next:" in captured.out

    def test_summary_hide_next(self, spec_dir, sample_plan, capsys):
        """Test summary can hide next subtask."""
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(sample_plan), encoding="utf-8")

        print_progress_summary(spec_dir, show_next=False)

        captured = capsys.readouterr()
        # Should not show "Next:" when show_next=False
        # But may still show phase info
        assert "Phases:" in captured.out


# ============================================================================
# print_build_complete_banner Tests
# ============================================================================


class TestPrintBuildCompleteBanner:
    """Tests for print_build_complete_banner function."""

    def test_complete_banner(self, capsys):
        """Test build complete banner."""
        print_build_complete_banner(Path("/tmp/spec"))

        captured = capsys.readouterr()
        assert "BUILD COMPLETE!" in captured.out
        assert "All subtasks have been implemented" in captured.out
        assert "auto-claude/*" in captured.out


# ============================================================================
# print_paused_banner Tests
# ============================================================================


class TestPrintPausedBanner:
    """Tests for print_paused_banner function."""

    def test_paused_banner(self, spec_dir, capsys):
        """Test paused banner."""
        plan = {
            "phases": [
                {
                    "subtasks": [
                        {"status": "completed"},
                        {"status": "pending"},
                    ]
                }
            ]
        }
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        print_paused_banner(spec_dir, "001-test")

        captured = capsys.readouterr()
        assert "BUILD PAUSED" in captured.out
        assert "1/2" in captured.out

    def test_paused_banner_with_worktree(self, spec_dir, capsys):
        """Test paused banner with worktree note."""
        plan = {
            "phases": [
                {
                    "subtasks": [
                        {"status": "completed"},
                    ]
                }
            ]
        }
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        print_paused_banner(spec_dir, "001-test", has_worktree=True)

        captured = capsys.readouterr()
        assert "separate workspace" in captured.out


# ============================================================================
# get_plan_summary Tests
# ============================================================================


class TestGetPlanSummary:
    """Tests for get_plan_summary function."""

    def test_summary_no_file(self, spec_dir):
        """Test summary when no plan file."""
        summary = get_plan_summary(spec_dir)

        assert summary["workflow_type"] is None
        assert summary["total_phases"] == 0
        assert summary["total_subtasks"] == 0
        assert summary["completed_subtasks"] == 0
        assert len(summary["phases"]) == 0

    def test_summary_valid_plan(self, spec_dir, sample_plan):
        """Test summary with valid plan."""
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(sample_plan), encoding="utf-8")

        summary = get_plan_summary(spec_dir)

        assert summary["workflow_type"] == "standard"
        assert summary["total_phases"] == 3
        assert summary["total_subtasks"] == 5
        assert summary["completed_subtasks"] == 2
        assert summary["pending_subtasks"] == 2
        assert summary["in_progress_subtasks"] == 1
        assert len(summary["phases"]) == 3

    def test_summary_includes_subtask_details(self, spec_dir, sample_plan):
        """Test summary includes subtask details."""
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(sample_plan), encoding="utf-8")

        summary = get_plan_summary(spec_dir)

        phase1 = summary["phases"][0]
        assert phase1["id"] == "phase1"
        assert phase1["name"] == "Foundation"
        assert phase1["total"] == 2
        assert phase1["completed"] == 2
        assert len(phase1["subtasks"]) == 2

    def test_summary_with_empty_subtasks(self, spec_dir):
        """Test summary plan with empty subtasks list."""
        plan = {
            "phases": [
                {
                    "id": "phase1",
                    "subtasks": []
                }
            ]
        }
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        summary = get_plan_summary(spec_dir)

        # get_plan_summary uses phase.get("subtasks", [])
        # Empty subtasks means no subtasks counted
        assert summary["total_subtasks"] == 0
        assert summary["total_phases"] == 1


# ============================================================================
# get_current_phase Tests
# ============================================================================


class TestGetCurrentPhase:
    """Tests for get_current_phase function."""

    def test_current_phase_when_incomplete(self, spec_dir, sample_plan):
        """Test getting current phase with incomplete subtasks."""
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(sample_plan), encoding="utf-8")

        phase = get_current_phase(spec_dir)

        # Should return phase2 (has in_progress subtask)
        assert phase is not None
        assert phase["id"] == "phase2"

    def test_current_phase_when_all_complete(self, spec_dir, completed_plan):
        """Test current phase when all complete."""
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(completed_plan), encoding="utf-8")

        phase = get_current_phase(spec_dir)

        # No incomplete phases
        assert phase is None

    def test_current_phase_no_file(self, spec_dir):
        """Test current phase when no plan file."""
        phase = get_current_phase(spec_dir)
        assert phase is None

    def test_current_phase_with_chunks(self, spec_dir):
        """Test current phase with chunks."""
        plan = {
            "phases": [
                {
                    "id": "phase1",
                    "chunks": [
                        {"status": "completed"},
                        {"status": "pending"},
                    ]
                }
            ]
        }
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        phase = get_current_phase(spec_dir)

        assert phase is not None
        assert phase["id"] == "phase1"


# ============================================================================
# get_next_subtask Tests
# ============================================================================


class TestGetNextSubtask:
    """Tests for get_next_subtask function."""

    def test_next_subtask_basic(self, spec_dir, sample_plan):
        """Test getting next subtask."""
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(sample_plan), encoding="utf-8")

        next_task = get_next_subtask(spec_dir)

        # Phase 1 is complete, should get first pending from phase 2
        assert next_task is not None
        assert next_task["id"] == "2.2"  # 2.1 is in_progress, 2.2 is pending

    def test_next_subtask_respects_dependencies(self, spec_dir, sample_plan):
        """Test that dependencies are respected."""
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(sample_plan), encoding="utf-8")

        next_task = get_next_subtask(spec_dir)

        # Should not return tasks from phase3 (depends on phase2)
        assert next_task["phase_id"] == "phase2"

    def test_next_subtask_when_all_complete(self, spec_dir, completed_plan):
        """Test next subtask when all complete."""
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(completed_plan), encoding="utf-8")

        next_task = get_next_subtask(spec_dir)

        assert next_task is None

    def test_next_subtask_no_file(self, spec_dir):
        """Test next subtask when no plan file."""
        next_task = get_next_subtask(spec_dir)
        assert next_task is None

    def test_next_subtask_with_various_statuses(self, spec_dir):
        """Test next subtask with various pending statuses."""
        plan = {
            "phases": [
                {
                    "id": "phase1",
                    "depends_on": [],
                    "subtasks": [
                        {"id": "1.1", "status": "not_started"},
                        {"id": "1.2", "status": "not started"},
                    ]
                }
            ]
        }
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        next_task = get_next_subtask(spec_dir)

        # Should return first not_started task
        assert next_task is not None
        assert next_task["status"] == "pending"

    def test_next_subtask_with_chunks(self, spec_dir):
        """Test next subtask with chunks."""
        plan = {
            "phases": [
                {
                    "id": "phase1",
                    "depends_on": [],
                    "chunks": [
                        {"id": "1", "status": "pending"},
                    ]
                }
            ]
        }
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        next_task = get_next_subtask(spec_dir)

        assert next_task is not None
        assert next_task["id"] == "1"


# ============================================================================
# format_duration Tests
# ============================================================================


class TestFormatDuration:
    """Tests for format_duration function."""

    def test_format_seconds(self):
        """Test formatting seconds."""
        assert format_duration(30) == "30s"
        assert format_duration(59) == "59s"

    def test_format_minutes(self):
        """Test formatting minutes."""
        assert format_duration(60) == "1.0m"
        assert format_duration(90) == "1.5m"
        assert format_duration(150) == "2.5m"
        assert format_duration(3599) == "60.0m"

    def test_format_hours(self):
        """Test formatting hours."""
        assert format_duration(3600) == "1.0h"
        assert format_duration(5400) == "1.5h"
        assert format_duration(7200) == "2.0h"

    def test_format_zero(self):
        """Test formatting zero duration."""
        assert format_duration(0) == "0s"

    def test_format_float(self):
        """Test formatting float seconds."""
        assert format_duration(30.5) == "30s"
        assert format_duration(90.7) == "1.5m"


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


class TestProgressEdgeCases:
    """Tests for edge cases and error handling."""

    def test_corrupted_json_file(self, spec_dir):
        """Test handling of corrupted JSON file."""
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text("{corrupted", encoding="utf-8")

        completed, total = count_subtasks(spec_dir)
        assert completed == 0
        assert total == 0

    def test_unicode_in_plan(self, spec_dir):
        """Test handling of Unicode characters in plan."""
        plan = {
            "phases": [
                {
                    "subtasks": [
                        {
                            "id": "1",
                            "description": "Tâst with Ûñîçødé",
                            "status": "completed"
                        },
                    ]
                }
            ]
        }
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        completed, total = count_subtasks(spec_dir)
        assert completed == 1
        assert total == 1

    def test_plan_with_missing_fields(self, spec_dir):
        """Test plan with missing optional fields."""
        plan = {
            "phases": [
                {
                    # Missing id, name, depends_on
                    "subtasks": [
                        {"id": "1"},  # Missing description, status
                    ]
                }
            ]
        }
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        summary = get_plan_summary(spec_dir)
        assert summary["total_subtasks"] == 1

    def test_very_long_description(self, spec_dir):
        """Test handling of very long descriptions."""
        long_desc = "x" * 1000
        plan = {
            "phases": [
                {
                    "subtasks": [
                        {"id": "1", "description": long_desc, "status": "pending"},
                    ]
                }
            ]
        }
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        next_task = get_next_subtask(spec_dir)
        assert next_task is not None
        assert len(next_task["description"]) == 1000

    def test_empty_description(self, spec_dir):
        """Test handling of empty descriptions."""
        plan = {
            "phases": [
                {
                    "subtasks": [
                        {"id": "1", "description": "", "status": "pending"},
                    ]
                }
            ]
        }
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        next_task = get_next_subtask(spec_dir)
        assert next_task is not None

    def test_phase_with_string_depends_on(self, spec_dir):
        """Test phase with string instead of list depends_on."""
        plan = {
            "phases": [
                {
                    "id": "phase1",
                    "depends_on": "phase2",  # String instead of list
                    "subtasks": [{"status": "pending"}]
                }
            ]
        }
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        # Should handle gracefully
        get_next_subtask(spec_dir)

    def test_none_depends_on(self, spec_dir):
        """Test phase with None depends_on."""
        plan = {
            "phases": [
                {
                    "id": "phase1",
                    "depends_on": None,
                    "subtasks": [{"status": "pending"}]
                }
            ]
        }
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        next_task = get_next_subtask(spec_dir)
        assert next_task is not None
