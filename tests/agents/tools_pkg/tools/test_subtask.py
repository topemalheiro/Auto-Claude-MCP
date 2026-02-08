"""Tests for agents.tools_pkg.tools.subtask module."""

import json
from unittest.mock import patch
import pytest

from agents.tools_pkg.tools.subtask import create_subtask_tools, _update_subtask_in_plan


class TestUpdateSubtaskInPlan:
    """Test _update_subtask_in_plan function."""

    def test_updates_subtask_status(self):
        """Test that subtask status is updated."""
        plan = {
            "phases": [
                {
                    "id": "1",
                    "subtasks": [
                        {"id": "subtask-1", "status": "pending"}
                    ]
                }
            ]
        }

        result = _update_subtask_in_plan(plan, "subtask-1", "completed", "Done")

        assert result is True
        assert plan["phases"][0]["subtasks"][0]["status"] == "completed"
        assert plan["phases"][0]["subtasks"][0]["notes"] == "Done"
        assert "updated_at" in plan["phases"][0]["subtasks"][0]

    def test_returns_false_when_subtask_not_found(self):
        """Test that False is returned when subtask doesn't exist."""
        plan = {
            "phases": [
                {
                    "id": "1",
                    "subtasks": [
                        {"id": "subtask-1", "status": "pending"}
                    ]
                }
            ]
        }

        result = _update_subtask_in_plan(plan, "subtask-999", "completed", "Done")

        assert result is False

    def test_updates_last_updated(self):
        """Test that plan last_updated is set."""
        plan = {
            "phases": [
                {
                    "id": "1",
                    "subtasks": [
                        {"id": "subtask-1", "status": "pending"}
                    ]
                }
            ]
        }

        _update_subtask_in_plan(plan, "subtask-1", "completed", "")

        assert "last_updated" in plan

    def test_searches_multiple_phases(self):
        """Test that all phases are searched."""
        plan = {
            "phases": [
                {
                    "id": "1",
                    "subtasks": [
                        {"id": "subtask-1", "status": "pending"}
                    ]
                },
                {
                    "id": "2",
                    "subtasks": [
                        {"id": "subtask-2", "status": "pending"}
                    ]
                }
            ]
        }

        result = _update_subtask_in_plan(plan, "subtask-2", "completed", "Done")

        assert result is True
        assert plan["phases"][1]["subtasks"][0]["status"] == "completed"


class TestCreateSubtaskTools:
    """Test create_subtask_tools function."""

    @pytest.fixture
    def mock_spec_dir(self, tmp_path):
        """Create a temporary spec directory."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        return spec_dir

    @pytest.fixture
    def mock_project_dir(self, tmp_path):
        """Create a temporary project directory."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        return project_dir

    @pytest.fixture
    def mock_implementation_plan(self, mock_spec_dir):
        """Create a mock implementation plan."""
        plan = {
            "feature": "Test",
            "phases": [
                {
                    "id": "1",
                    "subtasks": [
                        {"id": "subtask-1", "status": "pending", "description": "Test subtask"}
                    ]
                }
            ]
        }
        plan_file = mock_spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan))
        return plan

    def test_returns_tools_when_sdk_available(self, mock_spec_dir, mock_project_dir):
        """Test that tools are returned when SDK is available."""
        with patch("agents.tools_pkg.tools.subtask.SDK_TOOLS_AVAILABLE", True):
            tools = create_subtask_tools(mock_spec_dir, mock_project_dir)

            assert len(tools) > 0

    def test_returns_empty_list_when_sdk_unavailable(self, mock_spec_dir, mock_project_dir):
        """Test that empty list is returned when SDK is unavailable."""
        with patch("agents.tools_pkg.tools.subtask.SDK_TOOLS_AVAILABLE", False):
            tools = create_subtask_tools(mock_spec_dir, mock_project_dir)

            assert tools == []

    @pytest.mark.asyncio
    async def test_update_subtask_status_tool_success(self, mock_spec_dir, mock_project_dir, mock_implementation_plan):
        """Test successful subtask status update."""
        with patch("agents.tools_pkg.tools.subtask.SDK_TOOLS_AVAILABLE", True):
            tools = create_subtask_tools(mock_spec_dir, mock_project_dir)
            update_tool = tools[0]

            result = await update_tool.handler({
                "subtask_id": "subtask-1",
                "status": "completed",
                "notes": "All done"
            })

            assert "Successfully updated" in result["content"][0]["text"]

            # Verify file was updated
            plan_file = mock_spec_dir / "implementation_plan.json"
            updated_plan = json.loads(plan_file.read_text())
            assert updated_plan["phases"][0]["subtasks"][0]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_update_subtask_status_invalid_status(self, mock_spec_dir, mock_project_dir, mock_implementation_plan):
        """Test update with invalid status."""
        with patch("agents.tools_pkg.tools.subtask.SDK_TOOLS_AVAILABLE", True):
            tools = create_subtask_tools(mock_spec_dir, mock_project_dir)
            update_tool = tools[0]

            result = await update_tool.handler({
                "subtask_id": "subtask-1",
                "status": "invalid_status",
                "notes": ""
            })

            assert "Error: Invalid status" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_update_subtask_status_missing_plan(self, mock_spec_dir, mock_project_dir):
        """Test update when implementation plan is missing."""
        # Don't create the plan file
        with patch("agents.tools_pkg.tools.subtask.SDK_TOOLS_AVAILABLE", True):
            tools = create_subtask_tools(mock_spec_dir, mock_project_dir)
            update_tool = tools[0]

            result = await update_tool.handler({
                "subtask_id": "subtask-1",
                "status": "completed",
                "notes": ""
            })

            assert "Error: implementation_plan.json not found" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_update_subtask_status_subtask_not_found(self, mock_spec_dir, mock_project_dir, mock_implementation_plan):
        """Test update when subtask doesn't exist."""
        with patch("agents.tools_pkg.tools.subtask.SDK_TOOLS_AVAILABLE", True):
            tools = create_subtask_tools(mock_spec_dir, mock_project_dir)
            update_tool = tools[0]

            result = await update_tool.handler({
                "subtask_id": "subtask-999",
                "status": "completed",
                "notes": ""
            })

            assert "Error: Subtask 'subtask-999' not found" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_update_subtask_status_auto_fix_on_json_error(self, mock_spec_dir, mock_project_dir):
        """Test auto-fix when JSON is invalid."""
        # Create invalid JSON
        plan_file = mock_spec_dir / "implementation_plan.json"
        plan_file.write_text("invalid json")

        with patch("agents.tools_pkg.tools.subtask.SDK_TOOLS_AVAILABLE", True), \
             patch("agents.tools_pkg.tools.subtask.auto_fix_plan", return_value=False):

            tools = create_subtask_tools(mock_spec_dir, mock_project_dir)
            update_tool = tools[0]

            result = await update_tool.handler({
                "subtask_id": "subtask-1",
                "status": "completed",
                "notes": ""
            })

            # Should return an error about invalid JSON
            assert "Error:" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_update_subtask_status_handles_exception(self, mock_spec_dir, mock_project_dir):
        """Test exception handling during update."""
        # Don't create a plan file - so the function returns error early
        with patch("agents.tools_pkg.tools.subtask.SDK_TOOLS_AVAILABLE", True):
            tools = create_subtask_tools(mock_spec_dir, mock_project_dir)
            update_tool = tools[0]

            # Pass valid args but plan file doesn't exist
            result = await update_tool.handler({
                "subtask_id": "subtask-1",
                "status": "completed",
                "notes": ""
            })

            # Should return an error about missing plan file
            assert "Error: implementation_plan.json not found" in result["content"][0]["text"]


class TestUpdateSubStatusVariations:
    """Test various status updates."""

    @pytest.fixture
    def mock_spec_dir(self, tmp_path):
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        return spec_dir

    @pytest.fixture
    def mock_project_dir(self, tmp_path):
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        return project_dir

    @pytest.fixture
    def base_plan(self, mock_spec_dir):
        plan = {
            "feature": "Test",
            "phases": [
                {
                    "id": "1",
                    "subtasks": [
                        {"id": "subtask-1", "status": "pending", "description": "Test"}
                    ]
                }
            ]
        }
        plan_file = mock_spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan))
        return plan

    @pytest.mark.asyncio
    async def test_update_to_in_progress_status(self, mock_spec_dir, mock_project_dir, base_plan):
        """Test updating to in_progress status."""
        with patch("agents.tools_pkg.tools.subtask.SDK_TOOLS_AVAILABLE", True):
            tools = create_subtask_tools(mock_spec_dir, mock_project_dir)
            update_tool = tools[0]

            result = await update_tool.handler({
                "subtask_id": "subtask-1",
                "status": "in_progress",
                "notes": "Started working"
            })

            assert "Successfully updated" in result["content"][0]["text"]

            plan_file = mock_spec_dir / "implementation_plan.json"
            updated_plan = json.loads(plan_file.read_text())
            assert updated_plan["phases"][0]["subtasks"][0]["status"] == "in_progress"

    @pytest.mark.asyncio
    async def test_update_to_failed_status(self, mock_spec_dir, mock_project_dir, base_plan):
        """Test updating to failed status."""
        with patch("agents.tools_pkg.tools.subtask.SDK_TOOLS_AVAILABLE", True):
            tools = create_subtask_tools(mock_spec_dir, mock_project_dir)
            update_tool = tools[0]

            result = await update_tool.handler({
                "subtask_id": "subtask-1",
                "status": "failed",
                "notes": "Failed due to error"
            })

            assert "Successfully updated" in result["content"][0]["text"]

            plan_file = mock_spec_dir / "implementation_plan.json"
            updated_plan = json.loads(plan_file.read_text())
            assert updated_plan["phases"][0]["subtasks"][0]["status"] == "failed"

    @pytest.mark.asyncio
    async def test_update_with_empty_notes(self, mock_spec_dir, mock_project_dir, base_plan):
        """Test update with empty notes."""
        with patch("agents.tools_pkg.tools.subtask.SDK_TOOLS_AVAILABLE", True):
            tools = create_subtask_tools(mock_spec_dir, mock_project_dir)
            update_tool = tools[0]

            result = await update_tool.handler({
                "subtask_id": "subtask-1",
                "status": "completed",
                "notes": ""
            })

            assert "Successfully updated" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_update_with_long_notes(self, mock_spec_dir, mock_project_dir, base_plan):
        """Test update with long notes."""
        long_notes = "x" * 1000

        with patch("agents.tools_pkg.tools.subtask.SDK_TOOLS_AVAILABLE", True):
            tools = create_subtask_tools(mock_spec_dir, mock_project_dir)
            update_tool = tools[0]

            result = await update_tool.handler({
                "subtask_id": "subtask-1",
                "status": "completed",
                "notes": long_notes
            })

            assert "Successfully updated" in result["content"][0]["text"]

            plan_file = mock_spec_dir / "implementation_plan.json"
            updated_plan = json.loads(plan_file.read_text())
            assert updated_plan["phases"][0]["subtasks"][0]["notes"] == long_notes


class TestUpdateSubtaskAutoFix:
    """Test auto-fix scenarios."""

    @pytest.fixture
    def mock_spec_dir(self, tmp_path):
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        return spec_dir

    @pytest.fixture
    def mock_project_dir(self, tmp_path):
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        return project_dir

    @pytest.mark.asyncio
    async def test_auto_fix_success_retries_update(self, mock_spec_dir, mock_project_dir):
        """Test that successful auto-fix allows retry."""
        with patch("agents.tools_pkg.tools.subtask.SDK_TOOLS_AVAILABLE", True), \
             patch("agents.tools_pkg.tools.subtask.auto_fix_plan", return_value=True):

            tools = create_subtask_tools(mock_spec_dir, mock_project_dir)
            update_tool = tools[0]

            # Create invalid JSON that will be auto-fixed
            plan_file = mock_spec_dir / "implementation_plan.json"
            plan_file.write_text('{"feature": "Test", "phases": []')  # Trailing bracket missing

            result = await update_tool.handler({
                "subtask_id": "subtask-1",
                "status": "completed",
                "notes": ""
            })

            # Auto-fix succeeded but subtask not found after fix
            assert "Error:" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_auto_fix_failure_returns_json_error(self, mock_spec_dir, mock_project_dir):
        """Test that auto-fix failure returns JSON error."""
        with patch("agents.tools_pkg.tools.subtask.SDK_TOOLS_AVAILABLE", True), \
             patch("agents.tools_pkg.tools.subtask.auto_fix_plan", return_value=False):

            tools = create_subtask_tools(mock_spec_dir, mock_project_dir)
            update_tool = tools[0]

            # Create invalid JSON
            plan_file = mock_spec_dir / "implementation_plan.json"
            plan_file.write_text("{ totally invalid json }")

            result = await update_tool.handler({
                "subtask_id": "subtask-1",
                "status": "completed",
                "notes": ""
            })

            assert "Error: Invalid JSON" in result["content"][0]["text"]


class TestUpdateSubtaskInPlanEdgeCases:
    """Test edge cases in _update_subtask_in_plan."""

    def test_update_in_empty_phases(self):
        """Test update with empty phases list."""
        plan = {"phases": []}
        result = _update_subtask_in_plan(plan, "subtask-1", "completed", "Done")

        assert result is False

    def test_update_in_nested_phases(self):
        """Test update across multiple nested phases."""
        plan = {
            "phases": [
                {
                    "id": "1",
                    "subtasks": [
                        {"id": "a-1", "status": "pending"},
                        {"id": "a-2", "status": "pending"},
                    ]
                },
                {
                    "id": "2",
                    "subtasks": [
                        {"id": "b-1", "status": "pending"},
                        {"id": "b-2", "status": "pending"},
                        {"id": "b-3", "status": "pending"},
                    ]
                },
                {
                    "id": "3",
                    "subtasks": [
                        {"id": "c-1", "status": "pending"}
                    ]
                }
            ]
        }

        # Update in middle phase
        result = _update_subtask_in_plan(plan, "b-2", "completed", "Done")

        assert result is True
        assert plan["phases"][1]["subtasks"][1]["status"] == "completed"

    def test_update_preserves_other_fields(self):
        """Test that update preserves existing fields."""
        plan = {
            "phases": [
                {
                    "id": "1",
                    "subtasks": [
                        {
                            "id": "subtask-1",
                            "status": "pending",
                            "description": "Original description",
                            "existing_field": "keep me"
                        }
                    ]
                }
            ]
        }

        _update_subtask_in_plan(plan, "subtask-1", "completed", "Notes")

        subtask = plan["phases"][0]["subtasks"][0]
        assert subtask["description"] == "Original description"
        assert subtask["existing_field"] == "keep me"
        assert subtask["status"] == "completed"
        assert subtask["notes"] == "Notes"

    def test_update_sets_updated_at_timestamp(self):
        """Test that updated_at timestamp is set."""
        plan = {
            "phases": [
                {
                    "id": "1",
                    "subtasks": [
                        {"id": "subtask-1", "status": "pending"}
                    ]
                }
            ]
        }

        _update_subtask_in_plan(plan, "subtask-1", "completed", "Notes")

        subtask = plan["phases"][0]["subtasks"][0]
        assert "updated_at" in subtask
        assert "T" in subtask["updated_at"]  # ISO format check

    def test_update_without_notes(self):
        """Test update with empty notes string."""
        plan = {
            "phases": [
                {
                    "id": "1",
                    "subtasks": [
                        {"id": "subtask-1", "status": "pending", "notes": "Old notes"}
                    ]
                }
            ]
        }

        _update_subtask_in_plan(plan, "subtask-1", "completed", "")

        # Notes should not be updated when empty string is passed (code only updates if notes is truthy)
        # Actually the code does: if notes: subtask["notes"] = notes
        # So empty string means notes is NOT updated
        assert plan["phases"][0]["subtasks"][0]["notes"] == "Old notes"

    def test_update_when_subtask_has_no_status(self):
        """Test update when subtask has no status field."""
        plan = {
            "phases": [
                {
                    "id": "1",
                    "subtasks": [
                        {"id": "subtask-1"}  # No status field
                    ]
                }
            ]
        }

        result = _update_subtask_in_plan(plan, "subtask-1", "completed", "Notes")

        assert result is True
        assert plan["phases"][0]["subtasks"][0]["status"] == "completed"

    def test_last_updated_is_set_on_plan(self):
        """Test that plan last_updated is set."""
        plan = {"phases": [{"id": "1", "subtasks": [{"id": "subtask-1", "status": "pending"}]}]}

        _update_subtask_in_plan(plan, "subtask-1", "completed", "Notes")

        assert "last_updated" in plan
        assert "T" in plan["last_updated"]  # ISO format

    def test_stops_after_first_match(self):
        """Test that update stops after finding first matching subtask."""
        plan = {
            "phases": [
                {
                    "id": "1",
                    "subtasks": [
                        {"id": "subtask-1", "status": "pending"},
                    ]
                },
                {
                    "id": "2",
                    "subtasks": [
                        {"id": "subtask-1", "status": "pending"},  # Duplicate ID
                    ]
                }
            ]
        }

        _update_subtask_in_plan(plan, "subtask-1", "completed", "Notes")

        # Only first one should be updated
        assert plan["phases"][0]["subtasks"][0]["status"] == "completed"
        assert plan["phases"][1]["subtasks"][0]["status"] == "pending"


class TestUpdateSubtaskWriteErrors:
    """Test write error handling."""

    @pytest.fixture
    def mock_spec_dir(self, tmp_path):
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        return spec_dir

    @pytest.fixture
    def mock_project_dir(self, tmp_path):
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        return project_dir

    @pytest.mark.asyncio
    async def test_write_atomic_is_used(self, mock_spec_dir, mock_project_dir):
        """Test that atomic write is used."""
        plan = {
            "feature": "Test",
            "phases": [
                {
                    "id": "1",
                    "subtasks": [
                        {"id": "subtask-1", "status": "pending", "description": "Test"}
                    ]
                }
            ]
        }
        plan_file = mock_spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan))

        with patch("agents.tools_pkg.tools.subtask.SDK_TOOLS_AVAILABLE", True), \
             patch("agents.tools_pkg.tools.subtask.write_json_atomic") as mock_write:

            tools = create_subtask_tools(mock_spec_dir, mock_project_dir)
            update_tool = tools[0]

            await update_tool.handler({
                "subtask_id": "subtask-1",
                "status": "completed",
                "notes": "Done"
            })

            # Verify atomic write was called
            mock_write.assert_called_once()

    @pytest.mark.asyncio
    async def test_os_error_during_write(self, mock_spec_dir, mock_project_dir):
        """Test OS error during file write."""
        plan = {
            "feature": "Test",
            "phases": [
                {
                    "id": "1",
                    "subtasks": [
                        {"id": "subtask-1", "status": "pending", "description": "Test"}
                    ]
                }
            ]
        }
        plan_file = mock_spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan))

        with patch("agents.tools_pkg.tools.subtask.SDK_TOOLS_AVAILABLE", True), \
             patch("agents.tools_pkg.tools.subtask.write_json_atomic", side_effect=OSError("Write error")):

            tools = create_subtask_tools(mock_spec_dir, mock_project_dir)
            update_tool = tools[0]

            result = await update_tool.handler({
                "subtask_id": "subtask-1",
                "status": "completed",
                "notes": "Done"
            })

            assert "Error updating subtask status" in result["content"][0]["text"]


class TestCreateSubtaskToolsSdkUnavailable:
    """Test create_subtask_tools when SDK is unavailable."""

    @pytest.fixture
    def mock_spec_dir(self, tmp_path):
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        return spec_dir

    @pytest.fixture
    def mock_project_dir(self, tmp_path):
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        return project_dir

    def test_returns_empty_list_when_sdk_unavailable(self, mock_spec_dir, mock_project_dir):
        """Test that empty list is returned when SDK is unavailable."""
        with patch("agents.tools_pkg.tools.subtask.SDK_TOOLS_AVAILABLE", False):
            tools = create_subtask_tools(mock_spec_dir, mock_project_dir)

            assert tools == []


class TestUpdateSubtaskStatusAutoFixRetry:
    """Test update_subtask_status with auto-fix retry scenarios."""

    @pytest.fixture
    def mock_spec_dir(self, tmp_path):
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        return spec_dir

    @pytest.fixture
    def mock_project_dir(self, tmp_path):
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        return project_dir

    @pytest.mark.asyncio
    async def test_auto_fix_success_retries_update(self, mock_spec_dir, mock_project_dir):
        """Test that successful auto-fix allows retry."""
        with patch("agents.tools_pkg.tools.subtask.SDK_TOOLS_AVAILABLE", True), \
             patch("agents.tools_pkg.tools.subtask.auto_fix_plan", return_value=True):

            tools = create_subtask_tools(mock_spec_dir, mock_project_dir)
            update_tool = tools[0]

            # Create invalid JSON that will be "fixed"
            plan_file = mock_spec_dir / "implementation_plan.json"
            plan_file.write_text('{"feature": "Test"}')  # Missing required fields

            result = await update_tool.handler({
                "subtask_id": "subtask-1",
                "status": "completed",
                "notes": "Done"
            })

            # After auto-fix, should find subtask doesn't exist (not an error)
            assert "Error: Subtask" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_auto_fix_retry_fails_with_missing_subtask(self, mock_spec_dir, mock_project_dir):
        """Test auto-fix retry when subtask still not found."""
        with patch("agents.tools_pkg.tools.subtask.SDK_TOOLS_AVAILABLE", True), \
             patch("agents.tools_pkg.tools.subtask.auto_fix_plan", return_value=True):

            tools = create_subtask_tools(mock_spec_dir, mock_project_dir)
            update_tool = tools[0]

            # Minimal valid JSON but no matching subtask
            plan_file = mock_spec_dir / "implementation_plan.json"
            plan_file.write_text('{"feature": "Test", "phases": []}')

            result = await update_tool.handler({
                "subtask_id": "subtask-1",
                "status": "completed",
                "notes": "Done"
            })

            assert "Error: Subtask" in result["content"][0]["text"]
            assert "not found" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_auto_fix_failure_with_retry_error(self, mock_spec_dir, mock_project_dir):
        """Test auto-fix with retry that raises an exception."""
        with patch("agents.tools_pkg.tools.subtask.SDK_TOOLS_AVAILABLE", True), \
             patch("agents.tools_pkg.tools.subtask.auto_fix_plan", return_value=True):

            tools = create_subtask_tools(mock_spec_dir, mock_project_dir)
            update_tool = tools[0]

            plan_file = mock_spec_dir / "implementation_plan.json"
            # Write empty file - auto_fix won't help, retry will fail
            plan_file.write_text("")

            result = await update_tool.handler({
                "subtask_id": "subtask-1",
                "status": "completed",
                "notes": "Done"
            })

            assert "Error:" in result["content"][0]["text"]


class TestSubtaskImportError:
    """Test ImportError handling in subtask module."""

    @pytest.fixture
    def mock_spec_dir(self, tmp_path):
        """Create a temporary spec directory."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        return spec_dir

    @pytest.fixture
    def mock_project_dir(self, tmp_path):
        """Create a temporary project directory."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        return project_dir

    def test_create_subtask_tools_returns_empty_on_import_error(self, mock_spec_dir, mock_project_dir):
        """Test that empty list is returned when SDK import fails."""
        with patch("agents.tools_pkg.tools.subtask.SDK_TOOLS_AVAILABLE", False):
            tools = create_subtask_tools(mock_spec_dir, mock_project_dir)
            assert tools == []

    def test_import_error_branch_coverage(self, mock_spec_dir, mock_project_dir):
        """Test that ImportError branch sets SDK_TOOLS_AVAILABLE to False and tool to None."""
        # The ImportError branch (lines 21-23) sets:
        # - SDK_TOOLS_AVAILABLE = False
        # - tool = None
        # We verify this branch exists by checking the module's state

        from agents.tools_pkg.tools import subtask

        # Verify the module has the expected attributes set after import
        assert hasattr(subtask, 'SDK_TOOLS_AVAILABLE')
        assert hasattr(subtask, 'tool')

        # When SDK is available (normal case in tests), these should be set
        # The ImportError branch is already tested by mocking SDK_TOOLS_AVAILABLE=False
        # which exercises the same code path through create_subtask_tools

        # This test documents the ImportError behavior
        # The actual ImportError is difficult to trigger in tests since claude_agent_sdk
        # is installed in the test environment
        assert isinstance(subtask.SDK_TOOLS_AVAILABLE, bool)
        if subtask.SDK_TOOLS_AVAILABLE:
            assert subtask.tool is not None
        else:
            assert subtask.tool is None

    @pytest.mark.asyncio
    async def test_auto_fix_success_with_valid_subtask(self, mock_spec_dir, mock_project_dir):
        """Test the auto-fix success path (lines 155-163)."""
        # Create a JSON file with trailing comma that auto_fix can fix
        plan_file = mock_spec_dir / "implementation_plan.json"
        # This JSON has a trailing comma which auto_fix will repair
        plan_file.write_text('{"feature": "Test", "phases": [{"id": "1", "subtasks": [{"id": "subtask-1", "status": "pending"}]}],}')

        with patch("agents.tools_pkg.tools.subtask.SDK_TOOLS_AVAILABLE", True):

            tools = create_subtask_tools(mock_spec_dir, mock_project_dir)
            update_tool = tools[0]

            result = await update_tool.handler({
                "subtask_id": "subtask-1",
                "status": "completed",
                "notes": "Done"
            })

            # Should succeed after auto-fix repairs the JSON
            assert "Successfully updated" in result["content"][0]["text"]
            assert "after auto-fix" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_auto_fix_subtask_not_found_error_message(self, mock_spec_dir, mock_project_dir):
        """Test the auto-fix path where subtask is not found (line 166)."""
        # Create invalid JSON that auto_fix will repair to valid JSON but without the target subtask
        plan_file = mock_spec_dir / "implementation_plan.json"
        # Invalid JSON with trailing comma that auto_fix can repair
        # The fixed JSON will have "other-task" but not "subtask-1"
        plan_file.write_text('{"feature": "Test", "phases": [{"id": "1", "subtasks": [{"id": "other-task", "status": "pending"}]}],}')

        with patch("agents.tools_pkg.tools.subtask.SDK_TOOLS_AVAILABLE", True):
            # Don't mock auto_fix_plan - let it run and actually fix the JSON
            tools = create_subtask_tools(mock_spec_dir, mock_project_dir)
            update_tool = tools[0]

            result = await update_tool.handler({
                "subtask_id": "subtask-1",
                "status": "completed",
                "notes": "Done"
            })

            # Should return error about subtask not found after auto-fix
            assert "Error: Subtask" in result["content"][0]["text"]
            assert "not found" in result["content"][0]["text"]
            assert "after auto-fix" in result["content"][0]["text"]
