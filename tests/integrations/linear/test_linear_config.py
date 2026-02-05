"""
Comprehensive tests for Linear config module.

Tests LinearConfig, LinearProjectState, and utility functions.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from integrations.linear.config import (
    LABELS,
    STATUS_BLOCKED,
    STATUS_TODO,
    STATUS_IN_PROGRESS,
    STATUS_DONE,
    STATUS_CANCELED,
    PRIORITY_URGENT,
    PRIORITY_HIGH,
    PRIORITY_MEDIUM,
    PRIORITY_LOW,
    PRIORITY_NONE,
    SUBTASK_TO_LINEAR_STATUS,
    LinearConfig,
    LinearProjectState,
    get_linear_status,
    get_priority_for_phase,
    format_subtask_description,
    format_session_comment,
    format_stuck_subtask_comment,
    LINEAR_PROJECT_MARKER,
)


class TestLinearConfig:
    """Tests for LinearConfig class."""

    def test_default_values(self):
        """Test LinearConfig default values."""
        config = LinearConfig(api_key="")

        assert config.api_key == ""
        assert config.team_id is None
        assert config.project_id is None
        assert config.project_name is None
        assert config.meta_issue_id is None
        assert config.enabled is True

    def test_from_env_no_api_key(self):
        """Test from_env when LINEAR_API_KEY is not set."""
        with patch.dict(os.environ, {}, clear=True):
            config = LinearConfig.from_env()
            assert config.api_key == ""
            assert config.team_id is None
            assert config.project_id is None
            assert config.enabled is False

    def test_from_env_with_api_key(self):
        """Test from_env with LINEAR_API_KEY set."""
        with patch.dict(os.environ, {"LINEAR_API_KEY": "test-key"}):
            config = LinearConfig.from_env()
            assert config.api_key == "test-key"
            assert config.enabled is True

    def test_from_env_with_team_id(self):
        """Test from_env with LINEAR_TEAM_ID set."""
        env = {
            "LINEAR_API_KEY": "test-key",
            "LINEAR_TEAM_ID": "TEAM-123",
        }
        with patch.dict(os.environ, env):
            config = LinearConfig.from_env()
            assert config.team_id == "TEAM-123"

    def test_from_env_with_project_id(self):
        """Test from_env with LINEAR_PROJECT_ID set."""
        env = {
            "LINEAR_API_KEY": "test-key",
            "LINEAR_PROJECT_ID": "PROJ-456",
        }
        with patch.dict(os.environ, env):
            config = LinearConfig.from_env()
            assert config.project_id == "PROJ-456"

    def test_is_valid_with_api_key(self):
        """Test is_valid returns True when API key is set."""
        config = LinearConfig(api_key="test-key")
        assert config.is_valid() is True

    def test_is_valid_without_api_key(self):
        """Test is_valid returns False when API key is empty."""
        config = LinearConfig(api_key="")
        assert config.is_valid() is False


class TestLinearProjectState:
    """Tests for LinearProjectState class."""

    def test_default_values(self):
        """Test LinearProjectState default values."""
        state = LinearProjectState()

        assert state.initialized is False
        assert state.team_id is None
        assert state.project_id is None
        assert state.project_name is None
        assert state.meta_issue_id is None
        assert state.total_issues == 0
        assert state.created_at is None
        assert state.issue_mapping == {}

    def test_to_dict(self):
        """Test to_dict method."""
        state = LinearProjectState(
            initialized=True,
            team_id="TEAM-123",
            project_id="PROJ-456",
            project_name="Test Project",
            meta_issue_id="META-789",
            total_issues=5,
            created_at="2024-01-01T00:00:00",
            issue_mapping={"subtask-1": "LIN-100"},
        )

        data = state.to_dict()

        assert data["initialized"] is True
        assert data["team_id"] == "TEAM-123"
        assert data["project_id"] == "PROJ-456"
        assert data["project_name"] == "Test Project"
        assert data["meta_issue_id"] == "META-789"
        assert data["total_issues"] == 5
        assert data["created_at"] == "2024-01-01T00:00:00"
        assert data["issue_mapping"] == {"subtask-1": "LIN-100"}

    def test_from_dict(self):
        """Test from_dict class method."""
        data = {
            "initialized": True,
            "team_id": "TEAM-123",
            "project_id": "PROJ-456",
            "project_name": "Test Project",
            "meta_issue_id": "META-789",
            "total_issues": 5,
            "created_at": "2024-01-01T00:00:00",
            "issue_mapping": {"subtask-1": "LIN-100"},
        }

        state = LinearProjectState.from_dict(data)

        assert state.initialized is True
        assert state.team_id == "TEAM-123"
        assert state.project_id == "PROJ-456"
        assert state.project_name == "Test Project"
        assert state.meta_issue_id == "META-789"
        assert state.total_issues == 5
        assert state.created_at == "2024-01-01T00:00:00"
        assert state.issue_mapping == {"subtask-1": "LIN-100"}

    def test_from_dict_with_defaults(self):
        """Test from_dict with missing values uses defaults."""
        state = LinearProjectState.from_dict({})

        assert state.initialized is False
        assert state.team_id is None
        assert state.project_id is None
        assert state.project_name is None
        assert state.meta_issue_id is None
        assert state.total_issues == 0
        assert state.created_at is None
        assert state.issue_mapping == {}

    def test_save(self, tmp_path: Path):
        """Test save method writes state file."""
        state = LinearProjectState(
            initialized=True,
            team_id="TEAM-123",
            project_name="Test Project",
        )

        state.save(tmp_path)

        state_file = tmp_path / LINEAR_PROJECT_MARKER
        assert state_file.exists()

        with open(state_file) as f:
            data = json.load(f)
            assert data["initialized"] is True
            assert data["team_id"] == "TEAM-123"

    def test_load(self, tmp_path: Path):
        """Test load class method reads state file."""
        data = {
            "initialized": True,
            "team_id": "TEAM-123",
            "project_id": "PROJ-456",
            "project_name": "Test Project",
            "meta_issue_id": "META-789",
            "total_issues": 5,
            "created_at": "2024-01-01T00:00:00",
            "issue_mapping": {"subtask-1": "LIN-100"},
        }

        state_file = tmp_path / LINEAR_PROJECT_MARKER
        with open(state_file, "w") as f:
            json.dump(data, f)

        state = LinearProjectState.load(tmp_path)

        assert state is not None
        assert state.initialized is True
        assert state.team_id == "TEAM-123"

    def test_load_nonexistent(self, tmp_path: Path):
        """Test load returns None when file doesn't exist."""
        state = LinearProjectState.load(tmp_path)
        assert state is None

    def test_load_invalid_json(self, tmp_path: Path):
        """Test load returns None with invalid JSON."""
        state_file = tmp_path / LINEAR_PROJECT_MARKER
        with open(state_file, "w") as f:
            f.write("invalid json")

        state = LinearProjectState.load(tmp_path)
        assert state is None


class TestGetLinearStatus:
    """Tests for get_linear_status function."""

    def test_status_pending(self):
        """Test pending status maps to Todo."""
        assert get_linear_status("pending") == STATUS_TODO

    def test_status_in_progress(self):
        """Test in_progress status maps to In Progress."""
        assert get_linear_status("in_progress") == STATUS_IN_PROGRESS

    def test_status_completed(self):
        """Test completed status maps to Done."""
        assert get_linear_status("completed") == STATUS_DONE

    def test_status_blocked(self):
        """Test blocked status maps to Blocked."""
        assert get_linear_status("blocked") == STATUS_BLOCKED

    def test_status_failed(self):
        """Test failed status maps to Blocked."""
        assert get_linear_status("failed") == STATUS_BLOCKED

    def test_status_stuck(self):
        """Test stuck status maps to Blocked."""
        assert get_linear_status("stuck") == STATUS_BLOCKED

    def test_status_unknown_defaults_to_todo(self):
        """Test unknown status defaults to Todo."""
        assert get_linear_status("unknown") == STATUS_TODO


class TestGetPriorityForPhase:
    """Tests for get_priority_for_phase function."""

    def test_single_phase_high_priority(self):
        """Test single phase gets High priority."""
        assert get_priority_for_phase(1, 1) == PRIORITY_HIGH

    def test_first_quarter_urgent(self):
        """Test first quarter of phases gets Urgent priority."""
        # 1/4 = 0.25, which is <= 0.25
        assert get_priority_for_phase(1, 4) == PRIORITY_URGENT
        # 2/8 = 0.25, which is <= 0.25
        assert get_priority_for_phase(2, 8) == PRIORITY_URGENT

    def test_second_quarter_high(self):
        """Test second quarter gets High priority."""
        # 2/4 = 0.5, which is > 0.25 and <= 0.5
        assert get_priority_for_phase(2, 4) == PRIORITY_HIGH
        # 3/8 = 0.375, which is > 0.25 and <= 0.5
        assert get_priority_for_phase(3, 8) == PRIORITY_HIGH

    def test_third_quarter_medium(self):
        """Test third quarter gets Medium priority."""
        # 3/4 = 0.75, which is > 0.5 and <= 0.75
        assert get_priority_for_phase(3, 4) == PRIORITY_MEDIUM
        # 5/8 = 0.625, which is > 0.5 and <= 0.75
        assert get_priority_for_phase(5, 8) == PRIORITY_MEDIUM

    def test_fourth_quarter_low(self):
        """Test fourth quarter gets Low priority."""
        # 4/4 = 1.0, which is > 0.75
        assert get_priority_for_phase(4, 4) == PRIORITY_LOW
        # 7/8 = 0.875, which is > 0.75
        assert get_priority_for_phase(7, 8) == PRIORITY_LOW


class TestFormatSubtaskDescription:
    """Tests for format_subtask_description function."""

    def test_basic_description(self):
        """Test basic description formatting."""
        subtask = {"description": "Test description"}
        result = format_subtask_description(subtask)

        assert "## Description" in result
        assert "Test description" in result

    def test_with_service(self):
        """Test description with service."""
        subtask = {
            "description": "Test task",
            "service": "backend",
        }
        result = format_subtask_description(subtask)

        assert "**Service:** backend" in result

    def test_with_all_services(self):
        """Test description with all_services flag."""
        subtask = {
            "description": "Test task",
            "all_services": True,
        }
        result = format_subtask_description(subtask)

        assert "**Scope:** All services" in result

    def test_with_phase_info(self):
        """Test description with phase context."""
        subtask = {"description": "Test task"}
        phase = {"name": "Phase 1", "id": 1}
        result = format_subtask_description(subtask, phase)

        assert "**Phase:** Phase 1" in result

    def test_with_phase_id_only(self):
        """Test description with phase ID only."""
        subtask = {"description": "Test task"}
        phase = {"id": 2}
        result = format_subtask_description(subtask, phase)

        assert "**Phase:** 2" in result

    def test_with_files_to_modify(self):
        """Test description with files to modify."""
        subtask = {
            "description": "Test task",
            "files_to_modify": ["file1.py", "file2.py", "file3.py"],
        }
        result = format_subtask_description(subtask)

        assert "## Files to Modify" in result
        assert "- `file1.py`" in result
        assert "- `file2.py`" in result
        assert "- `file3.py`" in result

    def test_with_files_to_create(self):
        """Test description with files to create."""
        subtask = {
            "description": "Test task",
            "files_to_create": ["new_file.py", "another.py"],
        }
        result = format_subtask_description(subtask)

        assert "## Files to Create" in result
        assert "- `new_file.py`" in result
        assert "- `another.py`" in result

    def test_with_patterns_from(self):
        """Test description with reference patterns."""
        subtask = {
            "description": "Test task",
            "patterns_from": ["pattern1.py", "pattern2.py"],
        }
        result = format_subtask_description(subtask)

        assert "## Reference Patterns" in result
        assert "- `pattern1.py`" in result
        assert "- `pattern2.py`" in result

    def test_with_verification_run(self):
        """Test description with verification run command."""
        subtask = {
            "description": "Test task",
            "verification": {
                "type": "test",
                "run": "pytest tests/",
            },
        }
        result = format_subtask_description(subtask)

        assert "## Verification" in result
        assert "**Type:** test" in result
        assert "**Command:** `pytest tests/`" in result

    def test_with_verification_url(self):
        """Test description with verification URL."""
        subtask = {
            "description": "Test task",
            "verification": {
                "type": "url",
                "url": "http://localhost:8080",
            },
        }
        result = format_subtask_description(subtask)

        assert "## Verification" in result
        assert "**URL:** http://localhost:8080" in result

    def test_with_verification_scenario(self):
        """Test description with verification scenario."""
        subtask = {
            "description": "Test task",
            "verification": {
                "type": "manual",
                "scenario": "Open the app and verify feature works",
            },
        }
        result = format_subtask_description(subtask)

        assert "## Verification" in result
        assert "**Scenario:** Open the app and verify feature works" in result

    def test_includes_auto_build_footer(self):
        """Test description includes Auto-Build Framework footer."""
        subtask = {"description": "Test task"}
        result = format_subtask_description(subtask)

        assert "---" in result
        assert "Auto-Build Framework" in result

    def test_complete_description(self):
        """Test complete description with all fields."""
        subtask = {
            "description": "Implement feature X",
            "service": "backend",
            "files_to_modify": ["api.py"],
            "files_to_create": ["new_feature.py"],
            "patterns_from": ["reference.py"],
            "verification": {
                "type": "test",
                "run": "pytest",
            },
        }
        phase = {"name": "Phase 1", "id": 1}
        result = format_subtask_description(subtask, phase)

        assert "## Description" in result
        assert "Implement feature X" in result
        assert "**Service:** backend" in result
        assert "**Phase:** Phase 1" in result
        assert "## Files to Modify" in result
        assert "## Files to Create" in result
        assert "## Reference Patterns" in result
        assert "## Verification" in result


class TestFormatSessionComment:
    """Tests for format_session_comment function."""

    def test_successful_session(self):
        """Test formatting successful session."""
        result = format_session_comment(
            session_num=3,
            subtask_id="subtask-1",
            success=True,
            approach="Used approach X",
            error="",
            git_commit="abc123def",
        )

        assert "## Session #3" in result
        assert "✅" in result
        assert "**Subtask:** `subtask-1`" in result
        assert "**Status:** Completed" in result
        assert "**Approach:** Used approach X" in result
        assert "**Commit:** `abc123de`" in result

    def test_failed_session(self):
        """Test formatting failed session."""
        result = format_session_comment(
            session_num=2,
            subtask_id="subtask-2",
            success=False,
            approach="Attempted fix",
            error="Test error occurred",
            git_commit="",
        )

        assert "## Session #2" in result
        assert "❌" in result
        assert "**Status:** In Progress" in result
        assert "**Approach:** Attempted fix" in result
        assert "**Error:**" in result
        assert "Test error occurred" in result

    def test_minimal_comment(self):
        """Test formatting minimal comment."""
        result = format_session_comment(
            session_num=1,
            subtask_id="subtask-1",
            success=True,
        )

        assert "## Session #1" in result
        assert "✅" in result
        assert "**Subtask:** `subtask-1`" in result
        assert "**Status:** Completed" in result
        assert "**Time:**" in result

    def test_includes_timestamp(self):
        """Test comment includes timestamp."""
        result = format_session_comment(
            session_num=1,
            subtask_id="subtask-1",
            success=True,
        )

        # Check for timestamp format
        assert "**Time:**" in result
        # Should have date
        assert any(str(datetime.now().year) in line for line in result.split("\n"))

    def test_long_error_truncated(self):
        """Test long error messages are truncated."""
        long_error = "x" * 600
        result = format_session_comment(
            session_num=1,
            subtask_id="subtask-1",
            success=False,
            error=long_error,
        )

        # Error should be truncated to 500 chars
        # Find the line with the error in code block
        lines = result.split("\n")
        error_block_start = None
        for i, line in enumerate(lines):
            if "```" in line:
                error_block_start = i + 1
                break

        if error_block_start and error_block_start < len(lines):
            error_line = lines[error_block_start]
            assert len(error_line) <= 500


class TestFormatStuckSubtaskComment:
    """Tests for format_stuck_subtask_comment function."""

    def test_basic_stuck_comment(self):
        """Test basic stuck subtask comment."""
        result = format_stuck_subtask_comment(
            subtask_id="subtask-1",
            attempt_count=3,
            attempts=[],
            reason="Configuration issue",
        )

        assert "## ⚠️ Subtask Marked as STUCK" in result
        assert "**Subtask:** `subtask-1`" in result
        assert "**Attempts:** 3" in result
        assert "**Reason:** Configuration issue" in result
        assert "**Time:**" in result

    def test_with_attempt_history(self):
        """Test stuck comment with attempt history."""
        attempts = [
            {"success": False, "approach": "Approach 1", "error": "Error 1"},
            {"success": False, "approach": "Approach 2", "error": "Error 2"},
            {"success": True, "approach": "Approach 3", "error": ""},
        ]

        result = format_stuck_subtask_comment(
            subtask_id="subtask-1",
            attempt_count=3,
            attempts=attempts,
        )

        assert "### Attempt History" in result
        assert "**Attempt 1:**" in result
        assert "❌" in result
        assert "Approach 1" in result
        assert "**Attempt 2:**" in result
        assert "**Attempt 3:**" in result
        assert "✅" in result

    def test_attempt_history_limited_to_5(self):
        """Test attempt history limited to last 5 attempts."""
        # Create 10 attempts
        attempts = [
            {"success": False, "approach": f"Approach {i}", "error": f"Error {i}"}
            for i in range(1, 11)
        ]

        result = format_stuck_subtask_comment(
            subtask_id="subtask-1",
            attempt_count=10,
            attempts=attempts,
        )

        # Should only show last 5 (attempts 6-10 are sliced from the end)
        # Since we use attempts[-5:], we get attempts 6,7,8,9,10 (indices 5-9)
        # The format numbers them 1-5 in the display
        assert "**Attempt 1:**" in result  # This is attempt 6 in the list
        assert "Approach 6" in result
        assert "Approach 10" in result

    def test_attempt_without_approach(self):
        """Test attempts without approach field."""
        attempts = [
            {"success": False, "error": "Error without approach"},
        ]

        result = format_stuck_subtask_comment(
            subtask_id="subtask-1",
            attempt_count=1,
            attempts=attempts,
        )

        # Should not crash, should show error
        assert "### Attempt History" in result

    def test_attempt_without_error(self):
        """Test attempts without error field (successful)."""
        attempts = [
            {"success": True, "approach": "Success approach"},
        ]

        result = format_stuck_subtask_comment(
            subtask_id="subtask-1",
            attempt_count=1,
            attempts=attempts,
        )

        # Should show checkmark
        assert "✅" in result
        assert "Success approach" in result

    def test_includes_recommended_actions(self):
        """Test stuck comment includes recommended actions."""
        result = format_stuck_subtask_comment(
            subtask_id="subtask-1",
            attempt_count=3,
            attempts=[],
        )

        assert "### Recommended Actions" in result
        assert "1. Review the approach" in result
        assert "2. Check for missing dependencies" in result
        assert "3. Consider manual intervention" in result
        assert "4. Update HUMAN_INPUT.md" in result

    def test_attempt_text_truncated(self):
        """Test long approach/error text is truncated."""
        long_text = "x" * 300
        attempts = [
            {"success": False, "approach": long_text, "error": long_text},
        ]

        result = format_stuck_subtask_comment(
            subtask_id="subtask-1",
            attempt_count=1,
            attempts=attempts,
        )

        # Should truncate to 200 chars
        # Count x's in the result
        x_count = result.count("x")
        assert x_count < 600  # Both approach and error truncated


class TestConstants:
    """Tests for module constants."""

    def test_status_constants(self):
        """Test status constants are defined correctly."""
        assert STATUS_TODO == "Todo"
        assert STATUS_IN_PROGRESS == "In Progress"
        assert STATUS_DONE == "Done"
        assert STATUS_BLOCKED == "Blocked"
        assert STATUS_CANCELED == "Canceled"

    def test_priority_constants(self):
        """Test priority constants are defined correctly."""
        assert PRIORITY_URGENT == 1
        assert PRIORITY_HIGH == 2
        assert PRIORITY_MEDIUM == 3
        assert PRIORITY_LOW == 4
        assert PRIORITY_NONE == 0

    def test_labels_dict(self):
        """Test LABELS dict is defined correctly."""
        assert LABELS["phase"] == "phase"
        assert LABELS["service"] == "service"
        assert LABELS["stuck"] == "stuck"
        assert LABELS["auto_build"] == "auto-claude"
        assert LABELS["needs_review"] == "needs-review"

    def test_subtask_status_mapping(self):
        """Test SUBTASK_TO_LINEAR_STATUS mapping."""
        assert SUBTASK_TO_LINEAR_STATUS["pending"] == STATUS_TODO
        assert SUBTASK_TO_LINEAR_STATUS["in_progress"] == STATUS_IN_PROGRESS
        assert SUBTASK_TO_LINEAR_STATUS["completed"] == STATUS_DONE
        assert SUBTASK_TO_LINEAR_STATUS["blocked"] == STATUS_BLOCKED
        assert SUBTASK_TO_LINEAR_STATUS["failed"] == STATUS_BLOCKED
        assert SUBTASK_TO_LINEAR_STATUS["stuck"] == STATUS_BLOCKED
