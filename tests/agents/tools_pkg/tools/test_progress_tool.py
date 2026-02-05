"""Tests for agents.tools_pkg.tools.progress module."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch
import pytest

from agents.tools_pkg.tools.progress import create_progress_tools


class TestCreateProgressTools:
    """Test create_progress_tools function."""

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

    def test_returns_tools_when_sdk_available(self, mock_spec_dir, mock_project_dir):
        """Test that tools are returned when SDK is available."""
        with patch("agents.tools_pkg.tools.progress.SDK_TOOLS_AVAILABLE", True):
            tools = create_progress_tools(mock_spec_dir, mock_project_dir)

            assert len(tools) == 1  # get_build_progress

    def test_returns_empty_list_when_sdk_unavailable(self, mock_spec_dir, mock_project_dir):
        """Test that empty list is returned when SDK is unavailable."""
        with patch("agents.tools_pkg.tools.progress.SDK_TOOLS_AVAILABLE", False):
            tools = create_progress_tools(mock_spec_dir, mock_project_dir)

            assert tools == []


class TestGetBuildProgress:
    """Test get_build_progress tool."""

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
            "feature": "Test Feature",
            "phases": [
                {
                    "id": "1",
                    "name": "Phase 1",
                    "subtasks": [
                        {"id": "subtask-1-1", "status": "completed", "description": "First subtask"},
                        {"id": "subtask-1-2", "status": "pending", "description": "Second subtask"},
                    ]
                },
                {
                    "id": "2",
                    "name": "Phase 2",
                    "subtasks": [
                        {"id": "subtask-2-1", "status": "in_progress", "description": "Third subtask"},
                    ]
                }
            ]
        }
        plan_file = mock_spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan))
        return plan

    @pytest.mark.asyncio
    async def test_get_build_progress_no_plan(self, mock_spec_dir, mock_project_dir):
        """Test get_build_progress when no plan exists."""
        with patch("agents.tools_pkg.tools.progress.SDK_TOOLS_AVAILABLE", True):
            tools = create_progress_tools(mock_spec_dir, mock_project_dir)
            progress_tool = tools[0]

            result = await progress_tool.handler({})

            assert "No implementation plan found" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_get_build_progress_with_plan(self, mock_spec_dir, mock_project_dir, mock_implementation_plan):
        """Test get_build_progress with a valid plan."""
        with patch("agents.tools_pkg.tools.progress.SDK_TOOLS_AVAILABLE", True):
            tools = create_progress_tools(mock_spec_dir, mock_project_dir)
            progress_tool = tools[0]

            result = await progress_tool.handler({})

            content = result["content"][0]["text"]
            assert "Build Progress: 1/3" in content
            assert "Completed: 1" in content
            assert "In Progress: 1" in content
            assert "Pending: 1" in content
            assert "Phase 1: 1/2" in content
            assert "Phase 2: 0/1" in content
            assert "Next subtask to work on" in content

    @pytest.mark.asyncio
    async def test_get_build_progress_all_completed(self, mock_spec_dir, mock_project_dir):
        """Test get_build_progress when all subtasks are completed."""
        plan = {
            "feature": "Test",
            "phases": [
                {
                    "id": "1",
                    "name": "Phase 1",
                    "subtasks": [
                        {"id": "subtask-1", "status": "completed", "description": "Done"}
                    ]
                }
            ]
        }
        plan_file = mock_spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan))

        with patch("agents.tools_pkg.tools.progress.SDK_TOOLS_AVAILABLE", True):
            tools = create_progress_tools(mock_spec_dir, mock_project_dir)
            progress_tool = tools[0]

            result = await progress_tool.handler({})

            content = result["content"][0]["text"]
            assert "100%" in content
            assert "All subtasks completed!" in content

    @pytest.mark.asyncio
    async def test_get_build_progress_with_failed_subtasks(self, mock_spec_dir, mock_project_dir):
        """Test get_build_progress with failed subtasks."""
        plan = {
            "feature": "Test",
            "phases": [
                {
                    "id": "1",
                    "name": "Phase 1",
                    "subtasks": [
                        {"id": "subtask-1", "status": "completed", "description": "Done"},
                        {"id": "subtask-2", "status": "failed", "description": "Failed"},
                    ]
                }
            ]
        }
        plan_file = mock_spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan))

        with patch("agents.tools_pkg.tools.progress.SDK_TOOLS_AVAILABLE", True):
            tools = create_progress_tools(mock_spec_dir, mock_project_dir)
            progress_tool = tools[0]

            result = await progress_tool.handler({})

            content = result["content"][0]["text"]
            assert "Failed: 1" in content
            assert "Build Progress: 1/2" in content

    @pytest.mark.asyncio
    async def test_get_build_progress_zero_subtasks(self, mock_spec_dir, mock_project_dir):
        """Test get_build_progress with no subtasks."""
        plan = {
            "feature": "Test",
            "phases": []
        }
        plan_file = mock_spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan))

        with patch("agents.tools_pkg.tools.progress.SDK_TOOLS_AVAILABLE", True):
            tools = create_progress_tools(mock_spec_dir, mock_project_dir)
            progress_tool = tools[0]

            result = await progress_tool.handler({})

            content = result["content"][0]["text"]
            assert "0/0" in content
            assert "0%" in content

    @pytest.mark.asyncio
    async def test_get_build_progress_all_in_progress(self, mock_spec_dir, mock_project_dir):
        """Test get_build_progress when all subtasks are in progress."""
        plan = {
            "feature": "Test",
            "phases": [
                {
                    "id": "1",
                    "name": "Phase 1",
                    "subtasks": [
                        {"id": "subtask-1", "status": "in_progress", "description": "Working"},
                        {"id": "subtask-2", "status": "in_progress", "description": "Also working"},
                    ]
                }
            ]
        }
        plan_file = mock_spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan))

        with patch("agents.tools_pkg.tools.progress.SDK_TOOLS_AVAILABLE", True):
            tools = create_progress_tools(mock_spec_dir, mock_project_dir)
            progress_tool = tools[0]

            result = await progress_tool.handler({})

            content = result["content"][0]["text"]
            assert "In Progress: 2" in content
            assert "Completed: 0" in content

    @pytest.mark.asyncio
    async def test_get_build_progress_next_subtask_selection(self, mock_spec_dir, mock_project_dir):
        """Test that next subtask is selected correctly."""
        plan = {
            "feature": "Test",
            "phases": [
                {
                    "id": "1",
                    "name": "Phase 1",
                    "subtasks": [
                        {"id": "subtask-1", "status": "completed", "description": "Done"},
                        {"id": "subtask-2", "status": "pending", "description": "Next one"},
                    ]
                }
            ]
        }
        plan_file = mock_spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan))

        with patch("agents.tools_pkg.tools.progress.SDK_TOOLS_AVAILABLE", True):
            tools = create_progress_tools(mock_spec_dir, mock_project_dir)
            progress_tool = tools[0]

            result = await progress_tool.handler({})

            content = result["content"][0]["text"]
            assert "Next subtask to work on" in content
            assert "subtask-2" in content
            assert "Next one" in content

    @pytest.mark.asyncio
    async def test_get_build_progress_invalid_json(self, mock_spec_dir, mock_project_dir):
        """Test get_build_progress with invalid JSON."""
        plan_file = mock_spec_dir / "implementation_plan.json"
        plan_file.write_text("{ invalid json }")

        with patch("agents.tools_pkg.tools.progress.SDK_TOOLS_AVAILABLE", True):
            tools = create_progress_tools(mock_spec_dir, mock_project_dir)
            progress_tool = tools[0]

            result = await progress_tool.handler({})

            assert "Error reading build progress" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_get_build_progress_phase_without_id(self, mock_spec_dir, mock_project_dir):
        """Test get_build_progress with phase missing id field."""
        plan = {
            "feature": "Test",
            "phases": [
                {
                    "name": "Unnamed Phase",
                    "subtasks": [
                        {"id": "subtask-1", "status": "pending", "description": "Test"}
                    ]
                }
            ]
        }
        plan_file = mock_spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan))

        with patch("agents.tools_pkg.tools.progress.SDK_TOOLS_AVAILABLE", True):
            tools = create_progress_tools(mock_spec_dir, mock_project_dir)
            progress_tool = tools[0]

            result = await progress_tool.handler({})

            content = result["content"][0]["text"]
            assert "Unnamed Phase: 0/1" in content

    @pytest.mark.asyncio
    async def test_get_build_progress_phase_with_phase_field(self, mock_spec_dir, mock_project_dir):
        """Test get_build_progress with phase using 'phase' field instead of 'id'."""
        plan = {
            "feature": "Test",
            "phases": [
                {
                    "phase": "1",
                    "name": "Phase 1",
                    "subtasks": [
                        {"id": "subtask-1", "status": "pending", "description": "Test"}
                    ]
                }
            ]
        }
        plan_file = mock_spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan))

        with patch("agents.tools_pkg.tools.progress.SDK_TOOLS_AVAILABLE", True):
            tools = create_progress_tools(mock_spec_dir, mock_project_dir)
            progress_tool = tools[0]

            result = await progress_tool.handler({})

            content = result["content"][0]["text"]
            assert "Phase 1: 0/1" in content

    @pytest.mark.asyncio
    async def test_get_build_progress_subtask_without_description(self, mock_spec_dir, mock_project_dir):
        """Test get_build_progress with subtask missing description."""
        plan = {
            "feature": "Test",
            "phases": [
                {
                    "id": "1",
                    "name": "Phase 1",
                    "subtasks": [
                        {"id": "subtask-1", "status": "pending"}
                    ]
                }
            ]
        }
        plan_file = mock_spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan))

        with patch("agents.tools_pkg.tools.progress.SDK_TOOLS_AVAILABLE", True):
            tools = create_progress_tools(mock_spec_dir, mock_project_dir)
            progress_tool = tools[0]

            result = await progress_tool.handler({})

            # Should handle missing description gracefully
            assert "Build Progress" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_get_build_progress_multiple_phases(self, mock_spec_dir, mock_project_dir):
        """Test get_build_progress with multiple phases."""
        plan = {
            "feature": "Test",
            "phases": [
                {
                    "id": "1",
                    "name": "Planning",
                    "subtasks": [
                        {"id": "subtask-1", "status": "completed", "description": "Plan"},
                    ]
                },
                {
                    "id": "2",
                    "name": "Implementation",
                    "subtasks": [
                        {"id": "subtask-2", "status": "completed", "description": "Code"},
                        {"id": "subtask-3", "status": "pending", "description": "Test"},
                    ]
                },
                {
                    "id": "3",
                    "name": "QA",
                    "subtasks": [
                        {"id": "subtask-4", "status": "pending", "description": "Review"},
                    ]
                }
            ]
        }
        plan_file = mock_spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan))

        with patch("agents.tools_pkg.tools.progress.SDK_TOOLS_AVAILABLE", True):
            tools = create_progress_tools(mock_spec_dir, mock_project_dir)
            progress_tool = tools[0]

            result = await progress_tool.handler({})

            content = result["content"][0]["text"]
            assert "Planning: 1/1" in content
            assert "Implementation: 1/2" in content
            assert "QA: 0/1" in content
            assert "Build Progress: 2/4" in content
            assert "50%" in content

    @pytest.mark.asyncio
    async def test_get_build_progress_all_statuses(self, mock_spec_dir, mock_project_dir):
        """Test get_build_progress with all possible statuses."""
        plan = {
            "feature": "Test",
            "phases": [
                {
                    "id": "1",
                    "name": "Phase 1",
                    "subtasks": [
                        {"id": "subtask-1", "status": "completed", "description": "Done"},
                        {"id": "subtask-2", "status": "in_progress", "description": "Working"},
                        {"id": "subtask-3", "status": "pending", "description": "Todo"},
                        {"id": "subtask-4", "status": "failed", "description": "Failed"},
                        {"id": "subtask-5", "status": "blocked", "description": "Blocked"},
                    ]
                }
            ]
        }
        plan_file = mock_spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan))

        with patch("agents.tools_pkg.tools.progress.SDK_TOOLS_AVAILABLE", True):
            tools = create_progress_tools(mock_spec_dir, mock_project_dir)
            progress_tool = tools[0]

            result = await progress_tool.handler({})

            content = result["content"][0]["text"]
            assert "Completed: 1" in content
            assert "In Progress: 1" in content
            # Note: blocked and unknown statuses fall into "pending"
            # The code only has 4 status buckets: completed, in_progress, failed, pending
            pending_count = content.count("Pending:")
            assert pending_count >= 1


class TestCreateProgressToolsSdkUnavailable:
    """Test create_progress_tools when SDK is unavailable."""

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

    def test_returns_empty_list_when_sdk_unavailable(self, mock_spec_dir, mock_project_dir):
        """Test that empty list is returned when SDK is unavailable."""
        with patch("agents.tools_pkg.tools.progress.SDK_TOOLS_AVAILABLE", False):
            tools = create_progress_tools(mock_spec_dir, mock_project_dir)

            assert tools == []


class TestProgressImportError:
    """Test ImportError handling in progress module."""

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

    def test_create_progress_tools_returns_empty_on_import_error(self, mock_spec_dir, mock_project_dir):
        """Test that empty list is returned when SDK import fails."""
        with patch("agents.tools_pkg.tools.progress.SDK_TOOLS_AVAILABLE", False):
            tools = create_progress_tools(mock_spec_dir, mock_project_dir)
            assert tools == []

    def test_import_error_branch_coverage(self, mock_spec_dir, mock_project_dir):
        """Test that ImportError branch sets SDK_TOOLS_AVAILABLE to False and tool to None."""
        # The ImportError branch (lines 16-18) sets:
        # - SDK_TOOLS_AVAILABLE = False
        # - tool = None
        # We verify this branch exists by checking the module's state

        from agents.tools_pkg.tools import progress

        # Verify the module has the expected attributes set after import
        assert hasattr(progress, 'SDK_TOOLS_AVAILABLE')
        assert hasattr(progress, 'tool')

        # When SDK is available (normal case in tests), these should be set
        # The ImportError branch is already tested by mocking SDK_TOOLS_AVAILABLE=False
        # which exercises the same code path through create_progress_tools

        # This test documents the ImportError behavior
        # The actual ImportError is difficult to trigger in tests since claude_agent_sdk
        # is installed in the test environment
        assert isinstance(progress.SDK_TOOLS_AVAILABLE, bool)
        if progress.SDK_TOOLS_AVAILABLE:
            assert progress.tool is not None
        else:
            assert progress.tool is None
