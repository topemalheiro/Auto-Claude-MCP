"""
Tests for Linear integration module.

Tests LinearManager class, project state management, and instruction generation.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from integrations.linear.integration import (
    LinearManager,
    get_linear_manager,
    is_linear_enabled,
    prepare_coder_linear_instructions,
    prepare_planner_linear_instructions,
)


class TestIsLinearEnabled:
    """Test is_linear_enabled function."""

    def test_returns_false_when_no_key(self):
        """Test returns False when LINEAR_API_KEY is not set."""
        with patch.dict("os.environ", {}, clear=True):
            assert is_linear_enabled() is False

    def test_returns_true_when_key_set(self):
        """Test returns True when LINEAR_API_KEY is set."""
        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            assert is_linear_enabled() is True


class TestGetLinearManager:
    """Test get_linear_manager function."""

    def test_returns_manager_instance(self, tmp_path: Path):
        """Test returns a LinearManager instance."""
        spec_dir = tmp_path / "specs" / "001-test"
        project_dir = tmp_path / "project"
        spec_dir.mkdir(parents=True)

        manager = get_linear_manager(spec_dir, project_dir)

        assert isinstance(manager, LinearManager)
        assert manager.spec_dir == spec_dir
        assert manager.project_dir == project_dir


class TestLinearManagerInit:
    """Test LinearManager initialization."""

    def test_initialization(self, tmp_path: Path):
        """Test LinearManager __init__."""
        spec_dir = tmp_path / "specs" / "001-test"
        project_dir = tmp_path / "project"
        spec_dir.mkdir(parents=True)

        manager = LinearManager(spec_dir, project_dir)

        assert manager.spec_dir == spec_dir
        assert manager.project_dir == project_dir
        assert manager.config is not None
        assert manager.state is None
        assert manager._mcp_available is False

    def test_loads_existing_state(self, tmp_path: Path):
        """Test loading existing state from disk."""
        spec_dir = tmp_path / "specs" / "001-test"
        project_dir = tmp_path / "project"
        spec_dir.mkdir(parents=True)

        # Create existing state
        state_data = {
            "initialized": True,
            "team_id": "TEAM-123",
            "project_id": "PROJ-456",
            "project_name": "Test Project",
            "meta_issue_id": "META-789",
            "issue_mapping": {"subtask-1": "LIN-100"},
        }
        state_file = spec_dir / ".linear_project.json"
        with open(state_file, "w") as f:
            json.dump(state_data, f)

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            manager = LinearManager(spec_dir, project_dir)

            assert manager.state is not None
            assert manager.state.initialized is True
            assert manager.state.team_id == "TEAM-123"

    def test_checks_mcp_availability(self, tmp_path: Path):
        """Test MCP availability check during init."""
        spec_dir = tmp_path / "specs" / "001-test"
        project_dir = tmp_path / "project"
        spec_dir.mkdir(parents=True)

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            manager = LinearManager(spec_dir, project_dir)

            assert manager._mcp_available is True


class TestLinearManagerProperties:
    """Test LinearManager properties."""

    def test_is_enabled_property(self, tmp_path: Path):
        """Test is_enabled property."""
        spec_dir = tmp_path / "specs" / "001-test"
        project_dir = tmp_path / "project"
        spec_dir.mkdir(parents=True)

        with patch.dict("os.environ", {}, clear=True):
            manager = LinearManager(spec_dir, project_dir)
            assert manager.is_enabled is False

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            manager = LinearManager(spec_dir, project_dir)
            assert manager.is_enabled is True

    def test_is_initialized_property(self, tmp_path: Path):
        """Test is_initialized property."""
        spec_dir = tmp_path / "specs" / "001-test"
        project_dir = tmp_path / "project"
        spec_dir.mkdir(parents=True)

        manager = LinearManager(spec_dir, project_dir)
        assert manager.is_initialized is False

        # Create initialized state
        manager.state = MagicMock(initialized=True)
        assert manager.is_initialized is True


class TestLinearManagerIssueMapping:
    """Test issue ID mapping methods."""

    def test_get_issue_id_no_state(self, tmp_path: Path):
        """Test get_issue_id returns None when no state."""
        spec_dir = tmp_path / "specs" / "001-test"
        project_dir = tmp_path / "project"
        spec_dir.mkdir(parents=True)

        manager = LinearManager(spec_dir, project_dir)

        result = manager.get_issue_id("subtask-1")

        assert result is None

    def test_get_issue_id_existing_mapping(self, tmp_path: Path):
        """Test get_issue_id returns mapped issue ID."""
        spec_dir = tmp_path / "specs" / "001-test"
        project_dir = tmp_path / "project"
        spec_dir.mkdir(parents=True)

        manager = LinearManager(spec_dir, project_dir)
        manager.state = MagicMock()
        manager.state.issue_mapping = {"subtask-1": "LIN-123"}

        result = manager.get_issue_id("subtask-1")

        assert result == "LIN-123"

    def test_set_issue_id(self, tmp_path: Path):
        """Test set_issue_id stores mapping."""
        spec_dir = tmp_path / "specs" / "001-test"
        project_dir = tmp_path / "project"
        spec_dir.mkdir(parents=True)

        manager = LinearManager(spec_dir, project_dir)
        manager.set_issue_id("subtask-1", "LIN-123")

        assert manager.get_issue_id("subtask-1") == "LIN-123"


class TestLinearManagerProjectManagement:
    """Test project management methods."""

    def test_initialize_project(self, tmp_path: Path):
        """Test initialize_project creates state."""
        spec_dir = tmp_path / "specs" / "001-test"
        project_dir = tmp_path / "project"
        spec_dir.mkdir(parents=True)

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            manager = LinearManager(spec_dir, project_dir)
            result = manager.initialize_project("TEAM-123", "Test Project")

            assert result is True
            assert manager.state.initialized is True
            assert manager.state.team_id == "TEAM-123"
            assert manager.state.project_name == "Test Project"

    def test_initialize_project_disabled(self, tmp_path: Path):
        """Test initialize_project returns False when disabled."""
        spec_dir = tmp_path / "specs" / "001-test"
        project_dir = tmp_path / "project"
        spec_dir.mkdir(parents=True)

        with patch.dict("os.environ", {}, clear=True):
            manager = LinearManager(spec_dir, project_dir)
            result = manager.initialize_project("TEAM-123", "Test Project")

            assert result is False

    def test_update_project_id(self, tmp_path: Path):
        """Test update_project_id updates state."""
        spec_dir = tmp_path / "specs" / "001-test"
        project_dir = tmp_path / "project"
        spec_dir.mkdir(parents=True)

        manager = LinearManager(spec_dir, project_dir)
        manager.state = MagicMock(initialized=True)

        manager.update_project_id("PROJ-123")

        assert manager.state.project_id == "PROJ-123"

    def test_update_meta_issue_id(self, tmp_path: Path):
        """Test update_meta_issue_id updates state."""
        spec_dir = tmp_path / "specs" / "001-test"
        project_dir = tmp_path / "project"
        spec_dir.mkdir(parents=True)

        manager = LinearManager(spec_dir, project_dir)
        manager.state = MagicMock(initialized=True)

        manager.update_meta_issue_id("META-456")

        assert manager.state.meta_issue_id == "META-456"


class TestLinearManagerImplementationPlan:
    """Test implementation plan loading and processing."""

    def test_load_implementation_plan(self, tmp_path: Path):
        """Test loading implementation plan from file."""
        spec_dir = tmp_path / "specs" / "001-test"
        project_dir = tmp_path / "project"
        spec_dir.mkdir(parents=True)

        # Create plan file
        plan = {
            "phases": [
                {
                    "phase": 1,
                    "name": "Phase 1",
                    "subtasks": [
                        {"id": "subtask-1", "description": "Task 1"},
                        {"id": "subtask-2", "description": "Task 2"},
                    ],
                }
            ]
        }
        plan_file = spec_dir / "implementation_plan.json"
        with open(plan_file, "w") as f:
            json.dump(plan, f)

        manager = LinearManager(spec_dir, project_dir)
        result = manager.load_implementation_plan()

        assert result is not None
        assert "phases" in result
        assert len(result["phases"]) == 1

    def test_load_implementation_plan_no_file(self, tmp_path: Path):
        """Test load_implementation_plan returns None when missing."""
        spec_dir = tmp_path / "specs" / "001-test"
        project_dir = tmp_path / "project"
        spec_dir.mkdir(parents=True)

        manager = LinearManager(spec_dir, project_dir)
        result = manager.load_implementation_plan()

        assert result is None

    def test_get_subtasks_for_sync(self, tmp_path: Path):
        """Test getting subtasks with phase context."""
        spec_dir = tmp_path / "specs" / "001-test"
        project_dir = tmp_path / "project"
        spec_dir.mkdir(parents=True)

        # Create plan file
        plan = {
            "phases": [
                {
                    "phase": 1,
                    "name": "Phase 1",
                    "depends_on": [],
                    "subtasks": [
                        {"id": "subtask-1", "description": "Task 1"},
                    ],
                },
                {
                    "phase": 2,
                    "name": "Phase 2",
                    "depends_on": [1],
                    "subtasks": [
                        {"id": "subtask-2", "description": "Task 2"},
                    ],
                },
            ]
        }
        plan_file = spec_dir / "implementation_plan.json"
        with open(plan_file, "w") as f:
            json.dump(plan, f)

        manager = LinearManager(spec_dir, project_dir)
        subtasks = manager.get_subtasks_for_sync()

        assert len(subtasks) == 2

        # Check first subtask has phase context
        st1 = subtasks[0]
        assert st1["id"] == "subtask-1"
        assert st1["phase_num"] == 1
        assert st1["phase_name"] == "Phase 1"
        assert st1["total_phases"] == 2
        assert st1["phase_depends_on"] == []

        # Check second subtask
        st2 = subtasks[1]
        assert st2["id"] == "subtask-2"
        assert st2["phase_num"] == 2
        assert st2["phase_depends_on"] == [1]

    def test_generate_issue_data(self, tmp_path: Path):
        """Test generating Linear issue data from subtask."""
        spec_dir = tmp_path / "specs" / "001-test"
        project_dir = tmp_path / "project"
        spec_dir.mkdir(parents=True)

        manager = LinearManager(spec_dir, project_dir)

        subtask = {
            "id": "subtask-1",
            "description": "Test subtask",
            "service": "backend",
            "status": "pending",
            "phase_num": 1,
            "total_phases": 3,
            "phase_name": "Phase 1",
            "files_to_modify": ["file1.py", "file2.py"],
        }

        issue_data = manager.generate_issue_data(subtask)

        assert "title" in issue_data
        assert "description" in issue_data
        assert "priority" in issue_data
        assert "labels" in issue_data
        assert "status" in issue_data
        assert "subtask-1" in issue_data["title"]
        # Phase 1 of 3: 1/3 = 0.33, which is > 0.25, so High priority (2)
        assert issue_data["priority"] == 2
        assert "auto-claude" in issue_data["labels"]
        assert "phase-1" in issue_data["labels"]


class TestLinearManagerSessionRecording:
    """Test session result recording."""

    def test_record_session_result(self, tmp_path: Path):
        """Test recording session result as comment."""
        spec_dir = tmp_path / "specs" / "001-test"
        project_dir = tmp_path / "project"
        spec_dir.mkdir(parents=True)

        manager = LinearManager(spec_dir, project_dir)

        comment = manager.record_session_result(
            subtask_id="subtask-1",
            session_num=3,
            success=True,
            approach="Used approach X",
            error="",
            git_commit="abc123",
        )

        assert "Session #3" in comment
        assert "subtask-1" in comment
        assert "Completed" in comment
        assert "approach X" in comment
        assert "abc123" in comment

    def test_record_session_result_failed(self, tmp_path: Path):
        """Test recording failed session result."""
        spec_dir = tmp_path / "specs" / "001-test"
        project_dir = tmp_path / "project"
        spec_dir.mkdir(parents=True)

        manager = LinearManager(spec_dir, project_dir)

        comment = manager.record_session_result(
            subtask_id="subtask-1",
            session_num=2,
            success=False,
            approach="",
            error="Test error message",
            git_commit="",
        )

        assert "Session #2" in comment
        assert "In Progress" in comment
        assert "Test error message" in comment


class TestLinearManagerStatusUpdates:
    """Test status update preparation."""

    def test_prepare_status_update(self, tmp_path: Path):
        """Test preparing status update data."""
        spec_dir = tmp_path / "specs" / "001-test"
        project_dir = tmp_path / "project"
        spec_dir.mkdir(parents=True)

        manager = LinearManager(spec_dir, project_dir)
        manager.state = MagicMock()
        manager.state.issue_mapping = {"subtask-1": "LIN-123"}

        result = manager.prepare_status_update("subtask-1", "in_progress")

        assert result["issue_id"] == "LIN-123"
        assert result["status"] == "In Progress"
        assert result["subtask_id"] == "subtask-1"

    def test_prepare_stuck_escalation(self, tmp_path: Path):
        """Test preparing stuck subtask escalation."""
        spec_dir = tmp_path / "specs" / "001-test"
        project_dir = tmp_path / "project"
        spec_dir.mkdir(parents=True)

        manager = LinearManager(spec_dir, project_dir)
        manager.state = MagicMock()
        manager.state.issue_mapping = {"subtask-1": "LIN-123"}

        attempts = [
            {"success": False, "approach": "Approach 1", "error": "Error 1"},
            {"success": False, "approach": "Approach 2", "error": "Error 2"},
        ]

        result = manager.prepare_stuck_escalation(
            subtask_id="subtask-1",
            attempt_count=2,
            attempts=attempts,
            reason="Configuration issue",
        )

        assert result["issue_id"] == "LIN-123"
        assert result["status"] == "Blocked"
        assert "subtask-1" in result["comment"]
        assert "Configuration issue" in result["comment"]
        assert "stuck" in result["labels"]
        assert "needs-review" in result["labels"]


class TestLinearManagerProgressSummary:
    """Test progress summary and context generation."""

    def test_get_progress_summary_no_plan(self, tmp_path: Path):
        """Test progress summary when no plan exists."""
        spec_dir = tmp_path / "specs" / "001-test"
        project_dir = tmp_path / "project"
        spec_dir.mkdir(parents=True)

        manager = LinearManager(spec_dir, project_dir)

        summary = manager.get_progress_summary()

        assert summary["enabled"] is False
        assert summary["initialized"] is False
        assert summary["total_subtasks"] == 0
        assert summary["mapped_subtasks"] == 0

    def test_get_progress_summary_with_plan(self, tmp_path: Path):
        """Test progress summary with implementation plan."""
        spec_dir = tmp_path / "specs" / "001-test"
        project_dir = tmp_path / "project"
        spec_dir.mkdir(parents=True)

        # Create plan
        plan = {
            "phases": [
                {
                    "phase": 1,
                    "name": "Phase 1",
                    "subtasks": [
                        {"id": "subtask-1", "description": "Task 1"},
                        {"id": "subtask-2", "description": "Task 2"},
                    ],
                }
            ]
        }
        plan_file = spec_dir / "implementation_plan.json"
        with open(plan_file, "w") as f:
            json.dump(plan, f)

        manager = LinearManager(spec_dir, project_dir)
        manager.state = MagicMock(initialized=True)
        manager.state.issue_mapping = {"subtask-1": "LIN-100"}

        summary = manager.get_progress_summary()

        assert summary["total_subtasks"] == 2
        assert summary["mapped_subtasks"] == 1

    def test_get_linear_context_for_prompt_disabled(self, tmp_path: Path):
        """Test context generation returns empty string when disabled."""
        spec_dir = tmp_path / "specs" / "001-test"
        project_dir = tmp_path / "project"
        spec_dir.mkdir(parents=True)

        with patch.dict("os.environ", {}, clear=True):
            manager = LinearManager(spec_dir, project_dir)
            context = manager.get_linear_context_for_prompt()

            assert context == ""

    def test_get_linear_context_for_prompt_not_initialized(self, tmp_path: Path):
        """Test context generation when not initialized."""
        spec_dir = tmp_path / "specs" / "001-test"
        project_dir = tmp_path / "project"
        spec_dir.mkdir(parents=True)

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            manager = LinearManager(spec_dir, project_dir)
            context = manager.get_linear_context_for_prompt()

            assert "Linear integration is enabled but not yet initialized" in context
            assert "mcp__linear-server__list_teams" in context

    def test_get_linear_context_for_prompt_initialized(self, tmp_path: Path):
        """Test context generation when initialized."""
        spec_dir = tmp_path / "specs" / "001-test"
        project_dir = tmp_path / "project"
        spec_dir.mkdir(parents=True)

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            manager = LinearManager(spec_dir, project_dir)
            manager.state = MagicMock(
                initialized=True,
                project_name="Test Project",
                total_issues=5,
            )

            # Mock get_progress_summary - ensure all required keys are present
            manager.get_progress_summary = MagicMock(
                return_value={
                    "project_name": "Test Project",
                    "mapped_subtasks": 3,
                    "total_subtasks": 5,
                    "enabled": True,
                    "initialized": True,
                }
            )

            context = manager.get_linear_context_for_prompt()

            assert "Test Project" in context
            assert "3/5" in context
            assert "In Progress" in context
            assert "Done" in context


class TestLinearManagerStatePersistence:
    """Test state persistence methods."""

    def test_save_state(self, tmp_path: Path):
        """Test save_state writes to disk."""
        spec_dir = tmp_path / "specs" / "001-test"
        project_dir = tmp_path / "project"
        spec_dir.mkdir(parents=True)

        # Create a real state object with proper to_dict method
        from integrations.linear.config import LinearProjectState

        state = LinearProjectState()
        state.initialized = True
        state.team_id = "TEAM-123"

        manager = LinearManager(spec_dir, project_dir)
        manager.state = state

        manager.save_state()

        state_file = spec_dir / ".linear_project.json"
        assert state_file.exists()

        with open(state_file) as f:
            data = json.load(f)

        assert data["team_id"] == "TEAM-123"


class TestInstructionGeneration:
    """Test instruction generation for agents."""

    def test_prepare_planner_instructions_disabled(self, tmp_path: Path):
        """Test planner instructions return empty string when disabled."""
        spec_dir = tmp_path / "specs" / "001-test"

        with patch.dict("os.environ", {}, clear=True):
            instructions = prepare_planner_linear_instructions(spec_dir)

            assert instructions == ""

    def test_prepare_planner_instructions_enabled(self, tmp_path: Path):
        """Test planner instructions content when enabled."""
        spec_dir = tmp_path / "specs" / "001-test"

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            instructions = prepare_planner_linear_instructions(spec_dir)

            assert "Linear Integration Setup" in instructions
            assert "mcp__linear-server__list_teams" in instructions
            assert "mcp__linear-server__create_project" in instructions
            assert "mcp__linear-server__create_issue" in instructions
            # Note: create_comment is not in planner instructions, only in coder instructions

    def test_prepare_coder_instructions_disabled(self, tmp_path: Path):
        """Test coder instructions return empty string when disabled."""
        spec_dir = tmp_path / "specs" / "001-test"

        with patch.dict("os.environ", {}, clear=True):
            instructions = prepare_coder_linear_instructions(
                spec_dir, "subtask-1"
            )

            assert instructions == ""

    def test_prepare_coder_instructions_no_issue(self, tmp_path: Path):
        """Test coder instructions when no issue mapped."""
        spec_dir = tmp_path / "specs" / "001-test"

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            instructions = prepare_coder_linear_instructions(
                spec_dir, "subtask-1"
            )

            assert instructions == ""

    def test_prepare_coder_instructions_with_issue(self, tmp_path: Path):
        """Test coder instructions content when issue mapped."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)  # Create directory first

        # Create state with mapping
        state_data = {
            "initialized": True,
            "issue_mapping": {"subtask-1": "LIN-123"},
        }
        state_file = spec_dir / ".linear_project.json"
        with open(state_file, "w") as f:
            json.dump(state_data, f)

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            instructions = prepare_coder_linear_instructions(
                spec_dir, "subtask-1"
            )

            assert "LIN-123" in instructions
            assert "In Progress" in instructions
            assert "Done" in instructions
            assert "mcp__linear-server__update_issue" in instructions
            assert "mcp__linear-server__create_comment" in instructions


class TestLinearManagerErrorHandling:
    """Test error handling in LinearManager."""

    def test_load_implementation_plan_invalid_json(self, tmp_path: Path):
        """Test load_implementation_plan with invalid JSON."""
        spec_dir = tmp_path / "specs" / "001-test"
        project_dir = tmp_path / "project"
        spec_dir.mkdir(parents=True)

        # Create invalid JSON file
        plan_file = spec_dir / "implementation_plan.json"
        with open(plan_file, "w") as f:
            f.write("invalid json {{{")

        manager = LinearManager(spec_dir, project_dir)
        result = manager.load_implementation_plan()

        assert result is None

    def test_load_implementation_plan_unicode_error(self, tmp_path: Path):
        """Test load_implementation_plan with Unicode error."""
        spec_dir = tmp_path / "specs" / "001-test"
        project_dir = tmp_path / "project"
        spec_dir.mkdir(parents=True)

        # Create file with invalid UTF-8
        plan_file = spec_dir / "implementation_plan.json"
        with open(plan_file, "wb") as f:
            f.write(b"\xff\xfe invalid utf-16")

        manager = LinearManager(spec_dir, project_dir)
        result = manager.load_implementation_plan()

        assert result is None

    def test_load_implementation_plan_os_error(self, tmp_path: Path):
        """Test load_implementation_plan with OS error (permission denied)."""
        spec_dir = tmp_path / "specs" / "001-test"
        project_dir = tmp_path / "project"
        spec_dir.mkdir(parents=True)

        # Create file and then remove read permissions
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text('{"phases": []}')
        plan_file.chmod(0o000)

        manager = LinearManager(spec_dir, project_dir)
        result = manager.load_implementation_plan()

        # Should handle gracefully - may return None or succeed depending on OS
        assert result is None or "phases" in result

    def test_get_subtasks_for_sync_empty_phases(self, tmp_path: Path):
        """Test get_subtasks_for_sync with empty phases list."""
        spec_dir = tmp_path / "specs" / "001-test"
        project_dir = tmp_path / "project"
        spec_dir.mkdir(parents=True)

        # Create plan with empty phases
        plan = {"phases": []}
        plan_file = spec_dir / "implementation_plan.json"
        with open(plan_file, "w") as f:
            json.dump(plan, f)

        manager = LinearManager(spec_dir, project_dir)
        subtasks = manager.get_subtasks_for_sync()

        assert subtasks == []

    def test_get_subtasks_for_sync_no_subtasks_in_phase(self, tmp_path: Path):
        """Test get_subtasks_for_sync with phase but no subtasks."""
        spec_dir = tmp_path / "specs" / "001-test"
        project_dir = tmp_path / "project"
        spec_dir.mkdir(parents=True)

        # Create plan with phase but no subtasks
        plan = {
            "phases": [
                {
                    "phase": 1,
                    "name": "Phase 1",
                    "depends_on": [],
                    "subtasks": [],
                }
            ]
        }
        plan_file = spec_dir / "implementation_plan.json"
        with open(plan_file, "w") as f:
            json.dump(plan, f)

        manager = LinearManager(spec_dir, project_dir)
        subtasks = manager.get_subtasks_for_sync()

        assert subtasks == []
