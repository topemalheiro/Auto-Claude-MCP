"""Tests for agents.planner module."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from agents.planner import run_followup_planner
from task_logger import LogPhase


class TestRunFollowupPlanner:
    """Test run_followup_planner function."""

    @pytest.fixture
    def mock_project_dir(self, tmp_path):
        """Create a temporary project directory."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        return project_dir

    @pytest.fixture
    def mock_spec_dir(self, tmp_path):
        """Create a temporary spec directory."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        # Create spec.md
        (spec_dir / "spec.md").write_text("# Test Spec\n\nTest description.")
        return spec_dir

    @pytest.fixture
    def mock_implementation_plan(self, mock_spec_dir):
        """Create a mock implementation plan."""
        plan = {
            "feature": "Test feature",
            "workflow_type": "feature",
            "phases": [
                {
                    "id": "1",
                    "name": "Phase 1",
                    "subtasks": [
                        {
                            "id": "subtask-1",
                            "description": "Test subtask 1",
                            "status": "pending",
                        }
                    ],
                }
            ],
            "last_updated": "2024-01-01T00:00:00Z",
        }
        plan_file = mock_spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan))
        return plan

    @pytest.mark.asyncio
    async def test_successful_planning_with_pending_subtasks(self, mock_project_dir, mock_spec_dir, mock_implementation_plan):
        """Test successful planning with pending subtasks created."""
        from implementation_plan import ImplementationPlan

        with patch("agents.planner.create_client") as mock_create_client, \
             patch("prompts.get_followup_planner_prompt", return_value="Plan this follow-up:"), \
             patch("agents.planner.run_agent_session", new_callable=AsyncMock, return_value=("continue", "Plan updated", {})):

            # Setup mock client
            mock_client = AsyncMock()
            mock_create_client.return_value.__aenter__.return_value = mock_client
            mock_create_client.return_value.__aexit__.return_value = None

            result = await run_followup_planner(
                project_dir=mock_project_dir,
                spec_dir=mock_spec_dir,
                model="claude-3-5-sonnet-20241022",
                verbose=False,
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_planning_with_error_status(self, mock_project_dir, mock_spec_dir, mock_implementation_plan):
        """Test planning when agent returns error status."""
        with patch("agents.planner.create_client") as mock_create_client, \
             patch("prompts.get_followup_planner_prompt", return_value="Plan this follow-up:"), \
             patch("agents.planner.run_agent_session", new_callable=AsyncMock, return_value=("error", "Error occurred", {})):

            # Setup mock client
            mock_client = AsyncMock()
            mock_create_client.return_value.__aenter__.return_value = mock_client
            mock_create_client.return_value.__aexit__.return_value = None

            result = await run_followup_planner(
                project_dir=mock_project_dir,
                spec_dir=mock_spec_dir,
                model="claude-3-5-sonnet-20241022",
                verbose=False,
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_planning_no_pending_subtasks_after_planning(self, mock_project_dir, mock_spec_dir, mock_implementation_plan):
        """Test when planning completes but no pending subtasks are found."""
        # Create plan with all completed subtasks
        plan = {
            "feature": "Test feature",
            "workflow_type": "feature",
            "phases": [
                {
                    "id": "1",
                    "name": "Phase 1",
                    "subtasks": [
                        {
                            "id": "subtask-1",
                            "description": "Test subtask 1",
                            "status": "completed",
                        }
                    ],
                }
            ],
        }
        plan_file = mock_spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan))

        with patch("agents.planner.create_client") as mock_create_client, \
             patch("prompts.get_followup_planner_prompt", return_value="Plan this follow-up:"), \
             patch("agents.planner.run_agent_session", new_callable=AsyncMock, return_value=("continue", "Plan updated", {})):

            # Setup mock client
            mock_client = AsyncMock()
            mock_create_client.return_value.__aenter__.return_value = mock_client
            mock_create_client.return_value.__aexit__.return_value = None

            result = await run_followup_planner(
                project_dir=mock_project_dir,
                spec_dir=mock_spec_dir,
                model="claude-3-5-sonnet-20241022",
                verbose=False,
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_planning_plan_file_missing_after_session(self, mock_project_dir, mock_spec_dir):
        """Test when implementation_plan.json is missing after planning session."""
        with patch("agents.planner.create_client") as mock_create_client, \
             patch("prompts.get_followup_planner_prompt", return_value="Plan this follow-up:"), \
             patch("agents.planner.run_agent_session", new_callable=AsyncMock, return_value=("continue", "Done", {})):

            # Setup mock client
            mock_client = AsyncMock()
            mock_create_client.return_value.__aenter__.return_value = mock_client
            mock_create_client.return_value.__aexit__.return_value = None

            result = await run_followup_planner(
                project_dir=mock_project_dir,
                spec_dir=mock_spec_dir,
                model="claude-3-5-sonnet-20241022",
                verbose=False,
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_planning_exception_handling(self, mock_project_dir, mock_spec_dir):
        """Test exception handling during planning."""
        # create_client is called outside the try block, so patch run_agent_session instead
        with patch("agents.planner.create_client") as mock_create_client, \
             patch("prompts.get_followup_planner_prompt", return_value="Plan this:"), \
             patch("agents.planner.run_agent_session", new_callable=AsyncMock, side_effect=Exception("Planning error")):

            mock_client = AsyncMock()
            mock_create_client.return_value.__aenter__.return_value = mock_client
            mock_create_client.return_value.__aexit__.return_value = None

            result = await run_followup_planner(
                project_dir=mock_project_dir,
                spec_dir=mock_spec_dir,
                model="claude-3-5-sonnet-20241022",
                verbose=False,
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_planning_uses_correct_agent_type(self, mock_project_dir, mock_spec_dir, mock_implementation_plan):
        """Test that planning uses the correct agent type."""
        with patch("agents.planner.create_client") as mock_create_client, \
             patch("prompts.get_followup_planner_prompt", return_value="Plan this:"), \
             patch("agents.planner.run_agent_session", new_callable=AsyncMock, return_value=("continue", "Done", {})):

            # Setup mock client
            mock_client = AsyncMock()
            mock_create_client.return_value.__aenter__.return_value = mock_client
            mock_create_client.return_value.__aexit__.return_value = None

            await run_followup_planner(
                project_dir=mock_project_dir,
                spec_dir=mock_spec_dir,
                model="claude-3-5-sonnet-20241022",
                verbose=False,
            )

            # Check that create_client was called
            assert mock_create_client.called
