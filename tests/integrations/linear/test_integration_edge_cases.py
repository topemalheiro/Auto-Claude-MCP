"""
Edge case tests for Linear integration module.

Tests edge cases, boundary conditions, and less-traveled code paths.
"""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
import tempfile

import pytest

from integrations.linear.integration import (
    LinearManager,
    get_linear_manager,
    is_linear_enabled,
    prepare_coder_linear_instructions,
    prepare_planner_linear_instructions,
)


class TestLinearManagerEdgeCases:
    """Edge case tests for LinearManager."""

    def test_init_with_nonexistent_spec_dir(self, tmp_path: Path):
        """Test initialization with spec_dir that doesn't exist yet."""
        nonexistent = tmp_path / "does" / "not" / "exist"

        # Should not crash
        manager = LinearManager(nonexistent, tmp_path)
        assert manager.spec_dir == nonexistent
        assert manager.state is None

    def test_init_with_same_paths(self, tmp_path: Path):
        """Test initialization with spec_dir == project_dir."""
        manager = LinearManager(tmp_path, tmp_path)
        assert manager.spec_dir == tmp_path
        assert manager.project_dir == tmp_path

    def test_check_mcp_availability_with_invalid_config(self, tmp_path: Path):
        """Test MCP check with invalid config."""
        with patch.dict("os.environ", {"LINEAR_API_KEY": ""}):
            manager = LinearManager(tmp_path, tmp_path)
            # Empty API key means not available
            assert manager._mcp_available is False

    def test_is_enabled_with_false_config(self, tmp_path: Path):
        """Test is_enabled when config.enabled is False."""
        manager = LinearManager(tmp_path, tmp_path)

        # Patch config to have enabled=False
        with patch.object(manager.config, "enabled", False):
            assert manager.is_enabled is False

    def test_is_initialized_with_none_state(self, tmp_path: Path):
        """Test is_initialized with None state."""
        manager = LinearManager(tmp_path, tmp_path)
        assert manager.is_initialized is False

    def test_get_issue_id_with_empty_mapping(self, tmp_path: Path):
        """Test get_issue_id with empty issue_mapping."""
        manager = LinearManager(tmp_path, tmp_path)
        manager.state = MagicMock()
        manager.state.issue_mapping = {}

        result = manager.get_issue_id("any-subtask")
        assert result is None

    def test_get_issue_id_with_nonexistent_subtask(self, tmp_path: Path):
        """Test get_issue_id with subtask not in mapping."""
        manager = LinearManager(tmp_path, tmp_path)
        manager.state = MagicMock()
        manager.state.issue_mapping = {"other": "LIN-123"}

        result = manager.get_issue_id("nonexistent")
        assert result is None

    def test_set_issue_id_without_state(self, tmp_path: Path):
        """Test set_issue_id creates state if None."""
        manager = LinearManager(tmp_path, tmp_path)
        assert manager.state is None

        manager.set_issue_id("subtask-1", "LIN-123")

        # State should be created
        assert manager.state is not None
        assert manager.get_issue_id("subtask-1") == "LIN-123"

    def test_initialize_project_when_disabled(self, tmp_path: Path):
        """Test initialize_project returns False when disabled."""
        with patch.dict("os.environ", {}, clear=True):
            manager = LinearManager(tmp_path, tmp_path)
            result = manager.initialize_project("TEAM-123", "Project")

            assert result is False

    def test_update_project_id_without_state(self, tmp_path: Path):
        """Test update_project_id when state is None."""
        manager = LinearManager(tmp_path, tmp_path)
        manager.state = None

        # Should not crash
        manager.update_project_id("PROJ-123")

    def test_update_meta_issue_id_without_state(self, tmp_path: Path):
        """Test update_meta_issue_id when state is None."""
        manager = LinearManager(tmp_path, tmp_path)
        manager.state = None

        # Should not crash
        manager.update_meta_issue_id("META-123")

    def test_load_implementation_plan_with_empty_file(self, tmp_path: Path):
        """Test load_implementation_plan with empty file."""
        plan_file = tmp_path / "implementation_plan.json"
        plan_file.write_text("")

        manager = LinearManager(tmp_path, tmp_path)
        result = manager.load_implementation_plan()

        assert result is None

    def test_load_implementation_plan_with_dict_not_phases(self, tmp_path: Path):
        """Test load_implementation_plan without phases key."""
        plan = {"other_key": "value"}
        plan_file = tmp_path / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan))

        manager = LinearManager(tmp_path, tmp_path)
        result = manager.load_implementation_plan()

        # Should return dict but without phases
        assert result is not None
        assert "phases" not in result or result.get("phases") is None

    def test_get_subtasks_for_sync_returns_empty_on_no_plan(self, tmp_path: Path):
        """Test get_subtasks_for_sync returns empty list when no plan."""
        manager = LinearManager(tmp_path, tmp_path)

        # This line (175) was not covered - return [] when plan is None
        subtasks = manager.get_subtasks_for_sync()
        assert subtasks == []

    def test_get_subtasks_for_sync_with_phases_without_subtasks(self, tmp_path: Path):
        """Test get_subtasks_for_sync with phases but no subtasks."""
        plan = {
            "phases": [
                {
                    "phase": 1,
                    "name": "Phase 1",
                    "depends_on": [],
                }
            ]
        }
        plan_file = tmp_path / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan))

        manager = LinearManager(tmp_path, tmp_path)
        subtasks = manager.get_subtasks_for_sync()

        assert subtasks == []

    def test_get_subtasks_for_sync_with_missing_phase_fields(self, tmp_path: Path):
        """Test get_subtasks_for_sync with missing phase fields."""
        plan = {
            "phases": [
                {
                    # Missing 'phase' key
                    "name": "Phase 1",
                    "subtasks": [
                        {"id": "subtask-1", "description": "Test"},
                    ],
                }
            ]
        }
        plan_file = tmp_path / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan))

        manager = LinearManager(tmp_path, tmp_path)
        subtasks = manager.get_subtasks_for_sync()

        # Should use default phase=1
        assert len(subtasks) == 1
        assert subtasks[0]["phase_num"] == 1

    def test_get_subtasks_for_sync_with_subtask_missing_id(self, tmp_path: Path):
        """Test get_subtasks_for_sync with subtask missing id."""
        plan = {
            "phases": [
                {
                    "phase": 1,
                    "name": "Phase 1",
                    "subtasks": [
                        {"description": "Test"},  # Missing 'id'
                    ],
                }
            ]
        }
        plan_file = tmp_path / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan))

        manager = LinearManager(tmp_path, tmp_path)
        subtasks = manager.get_subtasks_for_sync()

        # Should still include subtask
        assert len(subtasks) == 1
        assert subtasks[0].get("id") is None

    def test_generate_issue_data_with_minimal_subtask(self, tmp_path: Path):
        """Test generate_issue_data with minimal subtask data."""
        manager = LinearManager(tmp_path, tmp_path)

        subtask = {
            "id": "subtask-1",
            # Missing description, service, etc.
        }

        issue_data = manager.generate_issue_data(subtask)

        assert "title" in issue_data
        assert "description" in issue_data
        assert "priority" in issue_data
        assert "labels" in issue_data
        assert "status" in issue_data
        assert "auto-claude" in issue_data["labels"]

    def test_generate_issue_data_without_service(self, tmp_path: Path):
        """Test generate_issue_data doesn't add service label if no service."""
        manager = LinearManager(tmp_path, tmp_path)

        subtask = {
            "id": "subtask-1",
            "description": "Test",
            "phase_num": 1,
            "total_phases": 4,
        }

        issue_data = manager.generate_issue_data(subtask)

        # Should not have service label
        assert not any("service-" in label for label in issue_data["labels"])

    def test_record_session_result_with_all_fields(self, tmp_path: Path):
        """Test record_session_result with all fields populated."""
        manager = LinearManager(tmp_path, tmp_path)

        comment = manager.record_session_result(
            subtask_id="subtask-1",
            session_num=5,
            success=False,
            approach="Test approach with some details",
            error="Test error with details",
            git_commit="abc123def456",
        )

        assert "## Session #5" in comment
        assert "subtask-1" in comment
        assert "Test approach" in comment
        assert "Test error" in comment
        assert "abc123de" in comment

    def test_prepare_status_update_without_state(self, tmp_path: Path):
        """Test prepare_status_update when state is None."""
        manager = LinearManager(tmp_path, tmp_path)

        result = manager.prepare_status_update("subtask-1", "in_progress")

        assert result["issue_id"] is None
        assert result["status"] == "In Progress"
        assert result["subtask_id"] == "subtask-1"

    def test_prepare_stuck_escalation_without_state(self, tmp_path: Path):
        """Test prepare_stuck_escalation when state is None."""
        manager = LinearManager(tmp_path, tmp_path)

        result = manager.prepare_stuck_escalation(
            subtask_id="subtask-1",
            attempt_count=5,
            attempts=[],
        )

        assert result["issue_id"] is None
        assert result["status"] == "Blocked"
        assert result["subtask_id"] == "subtask-1"

    def test_get_progress_summary_without_state(self, tmp_path: Path):
        """Test get_progress_summary when state is None."""
        manager = LinearManager(tmp_path, tmp_path)

        summary = manager.get_progress_summary()

        # When no plan, only these keys are present
        assert summary["enabled"] is False
        assert summary["initialized"] is False
        assert summary["total_subtasks"] == 0
        assert summary["mapped_subtasks"] == 0
        # These keys are only present when there's a plan
        assert "team_id" not in summary

    def test_save_state_without_state(self, tmp_path: Path):
        """Test save_state when state is None."""
        manager = LinearManager(tmp_path, tmp_path)
        manager.state = None

        # Should not crash
        manager.save_state()

        # No file should be created
        state_file = tmp_path / ".linear_project.json"
        assert not state_file.exists()


class TestLinearManagerGetLinearContextForPrompt:
    """Tests for get_linear_context_for_prompt method."""

    def test_returns_empty_when_disabled(self, tmp_path: Path):
        """Test returns empty string when Linear is disabled."""
        with patch.dict("os.environ", {}, clear=True):
            manager = LinearManager(tmp_path, tmp_path)
            context = manager.get_linear_context_for_prompt()

            assert context == ""

    def test_returns_instructions_when_not_initialized(self, tmp_path: Path):
        """Test returns setup instructions when not initialized."""
        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            manager = LinearManager(tmp_path, tmp_path)
            context = manager.get_linear_context_for_prompt()

            assert "Linear integration is enabled but not yet initialized" in context
            assert "mcp__linear-server__list_teams" in context

    def test_returns_progress_when_initialized(self, tmp_path: Path):
        """Test returns progress when initialized."""
        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            manager = LinearManager(tmp_path, tmp_path)
            manager.state = MagicMock(
                initialized=True,
                project_name="Test Project",
            )
            manager.get_progress_summary = MagicMock(
                return_value={
                    "project_name": "Test Project",
                    "mapped_subtasks": 5,
                    "total_subtasks": 10,
                    "enabled": True,
                    "initialized": True,
                }
            )

            context = manager.get_linear_context_for_prompt()

            assert "Test Project" in context
            assert "5/10" in context


class TestPrepareCoderLinearInstructions:
    """Tests for prepare_coder_linear_instructions function."""

    def test_returns_empty_when_disabled(self, tmp_path: Path):
        """Test returns empty string when Linear is disabled."""
        with patch.dict("os.environ", {}, clear=True):
            instructions = prepare_coder_linear_instructions(
                tmp_path, "subtask-1"
            )

            assert instructions == ""

    def test_returns_empty_when_not_initialized(self, tmp_path: Path):
        """Test returns empty string when project not initialized."""
        tmp_path.mkdir(parents=True, exist_ok=True)

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            instructions = prepare_coder_linear_instructions(
                tmp_path, "subtask-1"
            )

            assert instructions == ""

    def test_returns_empty_when_no_issue_mapping(self, tmp_path: Path):
        """Test returns empty string when subtask not mapped."""
        tmp_path.mkdir(parents=True, exist_ok=True)

        # Create state with empty mapping
        state_data = {
            "initialized": True,
            "issue_mapping": {},
        }
        state_file = tmp_path / ".linear_project.json"
        with open(state_file, "w") as f:
            json.dump(state_data, f)

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            instructions = prepare_coder_linear_instructions(
                tmp_path, "subtask-1"
            )

            # Line 523 - return "" when issue_id not found
            assert instructions == ""

    def test_returns_instructions_with_valid_mapping(self, tmp_path: Path):
        """Test returns instructions when valid mapping exists."""
        tmp_path.mkdir(parents=True, exist_ok=True)

        # Create state with mapping
        state_data = {
            "initialized": True,
            "issue_mapping": {"subtask-1": "LIN-123"},
        }
        state_file = tmp_path / ".linear_project.json"
        with open(state_file, "w") as f:
            json.dump(state_data, f)

        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            instructions = prepare_coder_linear_instructions(
                tmp_path, "subtask-1"
            )

            assert "LIN-123" in instructions
            assert "In Progress" in instructions
            assert "Done" in instructions


class TestPreparePlannerLinearInstructions:
    """Tests for prepare_planner_linear_instructions function."""

    def test_returns_empty_when_disabled(self, tmp_path: Path):
        """Test returns empty string when Linear is disabled."""
        with patch.dict("os.environ", {}, clear=True):
            instructions = prepare_planner_linear_instructions(tmp_path)

            assert instructions == ""

    def test_returns_instructions_when_enabled(self, tmp_path: Path):
        """Test returns instructions when Linear is enabled."""
        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            instructions = prepare_planner_linear_instructions(tmp_path)

            assert "Linear Integration Setup" in instructions
            assert "mcp__linear-server__list_teams" in instructions
            assert "mcp__linear-server__create_project" in instructions
            assert "mcp__linear-server__create_issue" in instructions


class TestGetLinearManager:
    """Tests for get_linear_manager function."""

    def test_returns_new_instance_each_time(self, tmp_path: Path):
        """Test returns a new instance each call."""
        spec_dir = tmp_path / "specs"
        project_dir = tmp_path / "project"

        manager1 = get_linear_manager(spec_dir, project_dir)
        manager2 = get_linear_manager(spec_dir, project_dir)

        # Different instances
        assert manager1 is not manager2
        # But same config
        assert manager1.spec_dir == manager2.spec_dir


class TestIsLinearEnabled:
    """Tests for is_linear_enabled function."""

    def test_returns_false_with_empty_key(self):
        """Test returns False when LINEAR_API_KEY is empty."""
        with patch.dict("os.environ", {"LINEAR_API_KEY": ""}):
            # Empty string is falsy in bool() check
            # But os.environ.get returns "", and bool("") is False
            from integrations.linear.integration import is_linear_enabled
            assert is_linear_enabled() is False

    def test_returns_true_with_any_key(self):
        """Test returns True with any non-empty key."""
        with patch.dict("os.environ", {"LINEAR_API_KEY": "any-value"}):
            from integrations.linear.integration import is_linear_enabled
            assert is_linear_enabled() is True


class TestLinearManagerWithRealFiles:
    """Tests with real file operations."""

    def test_multiple_save_and_load_cycles(self, tmp_path: Path):
        """Test multiple save/load cycles."""
        from integrations.linear.config import LinearProjectState

        manager = LinearManager(tmp_path, tmp_path)

        # First save - use real state object
        state1 = LinearProjectState(
            initialized=True,
            team_id="TEAM-1",
        )
        manager.state = state1
        manager.save_state()

        # Load in new manager
        manager2 = LinearManager(tmp_path, tmp_path)
        assert manager2.state is not None
        assert manager2.state.team_id == "TEAM-1"

        # Update and save again
        manager2.state.team_id = "TEAM-2"
        manager2.save_state()

        # Load again
        manager3 = LinearManager(tmp_path, tmp_path)
        assert manager3.state.team_id == "TEAM-2"

    def test_state_persistence_across_managers(self, tmp_path: Path):
        """Test state persists across different manager instances."""
        # Create and save state
        with patch.dict("os.environ", {"LINEAR_API_KEY": "test-key"}):
            manager1 = LinearManager(tmp_path, tmp_path)
            manager1.initialize_project("TEAM-123", "Test Project")
            manager1.set_issue_id("subtask-1", "LIN-456")

        # Load in new manager
        manager2 = LinearManager(tmp_path, tmp_path)

        assert manager2.state.initialized is True
        assert manager2.state.team_id == "TEAM-123"
        assert manager2.get_issue_id("subtask-1") == "LIN-456"
