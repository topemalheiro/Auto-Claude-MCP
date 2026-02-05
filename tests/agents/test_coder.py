"""Tests for agents.coder module."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call
import pytest
import os

from agents.coder import run_autonomous_agent
from agents.base import HUMAN_INTERVENTION_FILE


class TestRunAutonomousAgent:
    """Test run_autonomous_agent function."""

    @pytest.fixture
    def mock_project_dir(self, tmp_path):
        """Create a temporary project directory."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        # Initialize as git repo
        import subprocess
        subprocess.run(["git", "init"], cwd=project_dir, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=project_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=project_dir, capture_output=True)
        # Create initial commit
        (project_dir / "test.txt").write_text("test")
        subprocess.run(["git", "add", "."], cwd=project_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=project_dir, capture_output=True)
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
        import json

        plan = {
            "feature": "Test feature",
            "workflow_type": "feature",
            "phases": [
                {
                    "id": "1",
                    "phase": "1",
                    "name": "Phase 1",
                    "subtasks": [
                        {
                            "id": "subtask-1",
                            "description": "Test subtask 1",
                            "status": "pending",
                        },
                        {
                            "id": "subtask-2",
                            "description": "Test subtask 2",
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
    async def test_respects_max_iterations(self, mock_project_dir, mock_spec_dir, mock_implementation_plan):
        """Test that max_iterations parameter is respected."""
        with patch("agents.coder.create_client") as mock_create_client, \
             patch("agents.coder.get_graphiti_context", new_callable=AsyncMock, return_value=None), \
             patch("agents.coder.run_agent_session", new_callable=AsyncMock) as mock_session, \
             patch("agents.coder.post_session_processing", new_callable=AsyncMock, return_value=False), \
             patch("agents.coder.is_build_complete", return_value=False):

            # Setup mock client
            mock_client = AsyncMock()
            mock_create_client.return_value.__aenter__.return_value = mock_client
            mock_create_client.return_value.__aexit__.return_value = None

            # Session returns continue (not complete)
            mock_session.return_value = ("continue", "Response", {})

            # Run with max_iterations=2
            await run_autonomous_agent(
                project_dir=mock_project_dir,
                spec_dir=mock_spec_dir,
                model="claude-3-5-sonnet-20241022",
                max_iterations=2,
                verbose=False,
            )

            # Should have run 2 iterations
            assert mock_session.call_count == 2

    @pytest.mark.asyncio
    async def test_paused_by_human_intervention(self, mock_project_dir, mock_spec_dir, mock_implementation_plan):
        """Test that PAUSE file causes agent to stop."""
        # Create PAUSE file
        pause_file = mock_spec_dir / HUMAN_INTERVENTION_FILE
        pause_file.write_text("Please stop and review")

        with patch("agents.coder.create_client") as mock_create_client, \
             patch("agents.coder.get_graphiti_context", new_callable=AsyncMock, return_value=None):

            # Setup mock client
            mock_client = AsyncMock()
            mock_create_client.return_value.__aenter__.return_value = mock_client
            mock_create_client.return_value.__aexit__.return_value = None

            # Should exit early due to PAUSE file
            await run_autonomous_agent(
                project_dir=mock_project_dir,
                spec_dir=mock_spec_dir,
                model="claude-3-5-sonnet-20241022",
                max_iterations=10,
                verbose=False,
            )

    @pytest.mark.asyncio
    async def test_exits_on_build_complete(self, mock_project_dir, mock_spec_dir, mock_implementation_plan):
        """Test that agent exits when build is complete."""
        with patch("agents.coder.create_client") as mock_create_client, \
             patch("agents.coder.get_graphiti_context", new_callable=AsyncMock, return_value=None), \
             patch("agents.coder.run_agent_session", new_callable=AsyncMock) as mock_session, \
             patch("agents.coder.post_session_processing", new_callable=AsyncMock, return_value=True), \
             patch("agents.coder.is_build_complete", return_value=True), \
             patch("agents.coder.print_build_complete_banner"), \
             patch("agents.coder.count_subtasks", return_value=(2, 2)):

            # Setup mock client
            mock_client = AsyncMock()
            mock_create_client.return_value.__aenter__.return_value = mock_client
            mock_create_client.return_value.__aexit__.return_value = None

            mock_session.return_value = ("complete", "Done", {})

            await run_autonomous_agent(
                project_dir=mock_project_dir,
                spec_dir=mock_spec_dir,
                model="claude-3-5-sonnet-20241022",
                verbose=False,
            )

            # Should have run only once before checking is_build_complete
            assert mock_session.call_count <= 2

    @pytest.mark.asyncio
    async def test_tool_concurrency_retry_logic(self, mock_project_dir, mock_spec_dir, mock_implementation_plan):
        """Test that tool concurrency errors trigger retries with exponential backoff."""
        from agents.base import MAX_CONCURRENCY_RETRIES, INITIAL_RETRY_DELAY_SECONDS

        with patch("agents.coder.create_client") as mock_create_client, \
             patch("agents.coder.get_graphiti_context", new_callable=AsyncMock, return_value=None), \
             patch("agents.coder.run_agent_session", new_callable=AsyncMock) as mock_session, \
             patch("agents.coder.post_session_processing", new_callable=AsyncMock, return_value=False), \
             patch("agents.coder.is_build_complete", return_value=False), \
             patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:

            # Setup mock client
            mock_client = AsyncMock()
            mock_create_client.return_value.__aenter__.return_value = mock_client
            mock_create_client.return_value.__aexit__.return_value = None

            # First call hits concurrency error, second succeeds
            concurrency_error_info = {
                "type": "tool_concurrency",
                "message": "400: tool concurrency error",
                "exception_type": "Exception"
            }
            # Use a list that gets consumed
            results = [
                ("error", "Error", concurrency_error_info),
                ("continue", "Success", {})
            ]
            call_count = [0]

            async def mock_session_func(*args, **kwargs):
                idx = call_count[0]
                call_count[0] += 1
                if idx >= len(results):
                    # Return default success to stop iteration
                    return ("complete", "Done", {})
                return results[idx]

            mock_session.side_effect = mock_session_func

            await run_autonomous_agent(
                project_dir=mock_project_dir,
                spec_dir=mock_spec_dir,
                model="claude-3-5-sonnet-20241022",
                max_iterations=10,
                verbose=False,
            )

            # Should have retried after concurrency error
            assert mock_session.call_count >= 2

            # Should have slept with exponential backoff
            assert mock_sleep.call_count >= 1
            # First sleep should be INITIAL_RETRY_DELAY_SECONDS
            assert mock_sleep.call_args_list[0][0][0] == INITIAL_RETRY_DELAY_SECONDS

    @pytest.mark.asyncio
    async def test_concurrency_error_max_retries_exceeded(self, mock_project_dir, mock_spec_dir, mock_implementation_plan):
        """Test that agent gives up after max concurrency retries."""
        from agents.base import MAX_CONCURRENCY_RETRIES

        with patch("agents.coder.create_client") as mock_create_client, \
             patch("agents.coder.get_graphiti_context", new_callable=AsyncMock, return_value=None), \
             patch("agents.coder.run_agent_session", new_callable=AsyncMock) as mock_session, \
             patch("agents.coder.is_build_complete", return_value=False), \
             patch("asyncio.sleep", new_callable=AsyncMock):

            # Setup mock client
            mock_client = AsyncMock()
            mock_create_client.return_value.__aenter__.return_value = mock_client
            mock_create_client.return_value.__aexit__.return_value = None

            # Always return concurrency error
            concurrency_error_info = {
                "type": "tool_concurrency",
                "message": "400: tool concurrency error",
                "exception_type": "Exception"
            }
            mock_session.return_value = ("error", "Error", concurrency_error_info)

            await run_autonomous_agent(
                project_dir=mock_project_dir,
                spec_dir=mock_spec_dir,
                model="claude-3-5-sonnet-20241022",
                max_iterations=100,  # High limit to test concurrency retry logic
                verbose=False,
            )

            # Should retry MAX_CONCURRENCY_RETRIES + 1 times (initial + retries)
            assert mock_session.call_count == MAX_CONCURRENCY_RETRIES + 1

    @pytest.mark.asyncio
    async def test_sets_project_dir_env_var(self, mock_project_dir, mock_spec_dir, mock_implementation_plan):
        """Test that PROJECT_DIR_ENV_VAR is set correctly."""
        from security.constants import PROJECT_DIR_ENV_VAR

        # Clear the env var first
        original_value = os.environ.get(PROJECT_DIR_ENV_VAR)
        if PROJECT_DIR_ENV_VAR in os.environ:
            del os.environ[PROJECT_DIR_ENV_VAR]

        try:
            with patch("agents.coder.create_client") as mock_create_client, \
                 patch("agents.coder.get_graphiti_context", new_callable=AsyncMock, return_value=None), \
                 patch("agents.coder.run_agent_session", new_callable=AsyncMock, return_value=("continue", "", {})), \
                 patch("agents.coder.post_session_processing", new_callable=AsyncMock, return_value=False), \
                 patch("agents.coder.is_build_complete", return_value=False):

                # Setup mock client
                mock_client = AsyncMock()
                mock_create_client.return_value.__aenter__.return_value = mock_client
                mock_create_client.return_value.__aexit__.return_value = None

                await run_autonomous_agent(
                    project_dir=mock_project_dir,
                    spec_dir=mock_spec_dir,
                    model="claude-3-5-sonnet-20241022",
                    max_iterations=1,
                    verbose=False,
                )

                # Check env var was set
                assert PROJECT_DIR_ENV_VAR in os.environ
                assert str(mock_project_dir.resolve()) in os.environ[PROJECT_DIR_ENV_VAR]

        finally:
            # Restore original value
            if original_value is not None:
                os.environ[PROJECT_DIR_ENV_VAR] = original_value
            elif PROJECT_DIR_ENV_VAR in os.environ:
                del os.environ[PROJECT_DIR_ENV_VAR]

    @pytest.mark.asyncio
    async def test_records_good_commit_on_success(self, mock_project_dir, mock_spec_dir, mock_implementation_plan):
        """Test that good commits are recorded to recovery manager."""
        from recovery import RecoveryManager

        # Create actual recovery manager
        recovery_manager = RecoveryManager(mock_spec_dir, mock_project_dir)

        with patch("agents.coder.create_client") as mock_create_client, \
             patch("agents.coder.get_graphiti_context", new_callable=AsyncMock, return_value=None), \
             patch("agents.coder.run_agent_session", new_callable=AsyncMock, return_value=("continue", "", {})), \
             patch("agents.coder.post_session_processing", new_callable=AsyncMock, return_value=False) as mock_post_session, \
             patch("agents.coder.is_build_complete", return_value=False):

            # Setup mock client
            mock_client = AsyncMock()
            mock_create_client.return_value.__aenter__.return_value = mock_client
            mock_create_client.return_value.__aexit__.return_value = None

            await run_autonomous_agent(
                project_dir=mock_project_dir,
                spec_dir=mock_spec_dir,
                model="claude-3-5-sonnet-20241022",
                max_iterations=1,
                verbose=False,
            )

            # post_session_processing should be called
            assert mock_post_session.call_count == 1

    @pytest.mark.asyncio
    async def test_fresh_run_creates_planner_session(self, mock_project_dir, mock_spec_dir):
        """Test that first run creates planner session."""
        # Don't create implementation plan - this is a fresh run
        with patch("agents.coder.create_client") as mock_create_client, \
             patch("agents.coder.get_graphiti_context", new_callable=AsyncMock, return_value=None), \
             patch("agents.coder.run_agent_session", new_callable=AsyncMock) as mock_session, \
             patch("agents.coder.is_build_complete", return_value=False), \
             patch("agents.coder.is_first_run", return_value=True), \
             patch("agents.coder.generate_planner_prompt", return_value="Plan this:"), \
             patch("agents.coder.linear_task_started", new_callable=AsyncMock), \
             patch("agents.coder.is_linear_enabled", return_value=False):

            # Setup mock client
            mock_client = AsyncMock()
            mock_create_client.return_value.__aenter__.return_value = mock_client
            mock_create_client.return_value.__aexit__.return_value = None

            mock_session.return_value = ("continue", "Plan created", {})

            await run_autonomous_agent(
                project_dir=mock_project_dir,
                spec_dir=mock_spec_dir,
                model="claude-3-5-sonnet-20241022",
                max_iterations=1,
                verbose=False,
            )

            # Should use planner agent type
            assert mock_create_client.called
            # Check that planner agent type was used
            call_kwargs = mock_create_client.call_args[1]
            assert call_kwargs["agent_type"] == "planner"

    @pytest.mark.asyncio
    async def test_continuation_loads_existing_plan(self, mock_project_dir, mock_spec_dir, mock_implementation_plan):
        """Test that continuation loads existing implementation plan."""
        with patch("agents.coder.create_client") as mock_create_client, \
             patch("agents.coder.get_graphiti_context", new_callable=AsyncMock, return_value=None), \
             patch("agents.coder.run_agent_session", new_callable=AsyncMock, return_value=("continue", "", {})), \
             patch("agents.coder.post_session_processing", new_callable=AsyncMock, return_value=False), \
             patch("agents.coder.is_build_complete", return_value=False), \
             patch("agents.coder.is_first_run", return_value=False), \
             patch("agents.coder.get_next_subtask", return_value={"id": "subtask-1", "description": "Test", "phase_name": "Phase 1"}), \
             patch("agents.coder.generate_subtask_prompt", return_value="Do this:"), \
             patch("agents.coder.load_subtask_context", return_value={}):

            # Setup mock client
            mock_client = AsyncMock()
            mock_create_client.return_value.__aenter__.return_value = mock_client
            mock_create_client.return_value.__aexit__.return_value = None

            await run_autonomous_agent(
                project_dir=mock_project_dir,
                spec_dir=mock_spec_dir,
                model="claude-3-5-sonnet-20241022",
                max_iterations=1,
                verbose=False,
            )

            # Should use coder agent type (not planner)
            assert mock_create_client.called
            call_kwargs = mock_create_client.call_args[1]
            assert call_kwargs["agent_type"] == "coder"
