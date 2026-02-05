"""Tests for RequirementsPhaseMixin"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from spec.phases.requirements_phases import RequirementsPhaseMixin
from spec.phases.models import PhaseResult


class MockRequirementsExecutor(RequirementsPhaseMixin):
    """Minimal mock executor for testing RequirementsPhaseMixin"""

    def __init__(
        self,
        project_dir: Path,
        spec_dir: Path,
        task_description: str,
    ):
        self.project_dir = project_dir
        self.spec_dir = spec_dir
        self.task_description = task_description
        self.ui = MagicMock()
        self.task_logger = MagicMock()
        self._run_script = MagicMock(return_value=(False, "Script not found"))


class TestPhaseHistoricalContext:
    """Tests for phase_historical_context method"""

    @pytest.mark.asyncio
    async def test_historical_context_already_exists(self, tmp_path):
        """Test when graph_hints.json already exists"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        hints_file = spec_dir / "graph_hints.json"
        hints_file.write_text('{"enabled": true, "hints": []}', encoding="utf-8")

        executor = MockRequirementsExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task"
        )

        result = await executor.phase_historical_context()

        assert result.success is True
        assert result.retries == 0
        assert result.errors == []
        assert str(hints_file) in result.output_files

    @pytest.mark.asyncio
    async def test_historical_context_graphiti_not_enabled(self, tmp_path):
        """Test when Graphiti is not enabled"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = MockRequirementsExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )

        with patch("graphiti_providers.is_graphiti_enabled", return_value=False):
            with patch("spec.phases.requirements_phases.validator.create_empty_hints") as mock_create:
                result = await executor.phase_historical_context()

                mock_create.assert_called_once_with(
                    spec_dir,
                    enabled=False,
                    reason="Graphiti not configured"
                )

        assert result.success is True
        assert len(result.output_files) == 1

    @pytest.mark.asyncio
    async def test_historical_context_no_task_description(self, tmp_path):
        """Test when no task description is available"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = MockRequirementsExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description=""
        )

        with patch("graphiti_providers.is_graphiti_enabled", return_value=True):
            with patch("spec.phases.requirements_phases.validator.create_empty_hints") as mock_create:
                result = await executor.phase_historical_context()

                mock_create.assert_called_once_with(
                    spec_dir,
                    enabled=True,
                    reason="No task description available"
                )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_historical_context_success_with_hints(self, tmp_path):
        """Test successful retrieval of graph hints"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = MockRequirementsExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Build authentication system"
        )

        mock_hints = [
            {"content": "Previous auth implementation used JWT"},
            {"content": "User model is in models/user.py"}
        ]

        with patch("graphiti_providers.is_graphiti_enabled", return_value=True):
            with patch("graphiti_providers.get_graph_hints", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_hints

                result = await executor.phase_historical_context()

        assert result.success is True
        assert str(spec_dir / "graph_hints.json") in result.output_files

        # Verify hints file was created
        hints_file = spec_dir / "graph_hints.json"
        assert hints_file.exists()
        with open(hints_file, encoding="utf-8") as f:
            data = json.load(f)
        assert data["enabled"] is True
        assert data["hint_count"] == 2
        assert len(data["hints"]) == 2

    @pytest.mark.asyncio
    async def test_historical_context_empty_hints(self, tmp_path):
        """Test when graph query returns no hints"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = MockRequirementsExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task"
        )

        with patch("graphiti_providers.is_graphiti_enabled", return_value=True):
            with patch("graphiti_providers.get_graph_hints", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = []

                result = await executor.phase_historical_context()

        assert result.success is True

    @pytest.mark.asyncio
    async def test_historical_context_error_handling(self, tmp_path):
        """Test error handling when graph query fails"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = MockRequirementsExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )

        with patch("graphiti_providers.is_graphiti_enabled", return_value=True):
            with patch("graphiti_providers.get_graph_hints", new_callable=AsyncMock) as mock_get:
                mock_get.side_effect = Exception("Graph connection failed")

                with patch("spec.phases.requirements_phases.validator.create_empty_hints") as mock_create:
                    result = await executor.phase_historical_context()

        assert result.success is True  # Still succeeds with empty hints
        assert len(result.errors) == 1
        assert "Graph connection failed" in result.errors[0]

    @pytest.mark.asyncio
    async def test_historical_context_uses_task_from_requirements(self, tmp_path):
        """Test historical context uses task from requirements.json"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create requirements with detailed task
        req_file = spec_dir / "requirements.json"
        req_data = {
            "task_description": "Implement OAuth2 authentication with refresh tokens"
        }
        req_file.write_text(json.dumps(req_data), encoding="utf-8")

        executor = MockRequirementsExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Simple task"  # Will be overridden
        )

        with patch("graphiti_providers.is_graphiti_enabled", return_value=True):
            with patch("graphiti_providers.get_graph_hints", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = []

                result = await executor.phase_historical_context()

                # Should use task from requirements
                call_args = mock_get.call_args
                query = call_args[1]["query"]
                assert "OAuth2" in query or "refresh tokens" in query


class TestPhaseRequirements:
    """Tests for phase_requirements method"""

    @pytest.mark.asyncio
    async def test_requirements_already_exists(self, tmp_path):
        """Test when requirements.json already exists"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        req_file = spec_dir / "requirements.json"
        req_file.write_text('{"task_description": "Existing task"}', encoding="utf-8")

        executor = MockRequirementsExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="New task"
        )

        result = await executor.phase_requirements()

        assert result.success is True
        assert result.retries == 0
        assert str(req_file) in result.output_files

    @pytest.mark.asyncio
    async def test_requirements_non_interactive_with_task(self, tmp_path):
        """Test non-interactive mode with task description"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = MockRequirementsExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Build REST API"
        )

        result = await executor.phase_requirements(interactive=False)

        assert result.success is True
        assert (spec_dir / "requirements.json").exists()

        # Verify requirements were created
        with open(spec_dir / "requirements.json", encoding="utf-8") as f:
            req = json.load(f)
        assert "Build REST API" in req.get("task_description", "")

    @pytest.mark.asyncio
    async def test_requirements_interactive_success(self, tmp_path):
        """Test interactive requirements gathering success"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = MockRequirementsExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description=""
        )

        mock_req_data = {
            "task_description": "User entered task",
            "type": "feature",
            "priority": "high"
        }

        with patch("spec.phases.requirements_phases.requirements.gather_requirements_interactively") as mock_gather:
            mock_gather.return_value = mock_req_data

            result = await executor.phase_requirements(interactive=True)

        assert result.success is True
        assert (spec_dir / "requirements.json").exists()

    @pytest.mark.asyncio
    async def test_requirements_interactive_cancellation(self, tmp_path):
        """Test interactive requirements cancellation"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = MockRequirementsExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )

        with patch("spec.phases.requirements_phases.requirements.gather_requirements_interactively") as mock_gather:
            mock_gather.side_effect = KeyboardInterrupt()

            result = await executor.phase_requirements(interactive=True)

        assert result.success is False
        assert len(result.errors) == 1
        assert "User cancelled" in result.errors[0]

    @pytest.mark.asyncio
    async def test_requirements_interactive_eof_error(self, tmp_path):
        """Test interactive requirements with EOF error"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = MockRequirementsExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )

        with patch("spec.phases.requirements_phases.requirements.gather_requirements_interactively") as mock_gather:
            mock_gather.side_effect = EOFError()

            result = await executor.phase_requirements(interactive=True)

        assert result.success is False
        assert "User cancelled" in result.errors[0]

    @pytest.mark.asyncio
    async def test_requirements_updates_task_description(self, tmp_path):
        """Test that interactive mode updates task_description"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = MockRequirementsExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Initial task"
        )

        mock_req_data = {
            "task_description": "Updated task from user",
            "type": "bugfix"
        }

        with patch("spec.phases.requirements_phases.requirements.gather_requirements_interactively") as mock_gather:
            mock_gather.return_value = mock_req_data

            await executor.phase_requirements(interactive=True)

        assert executor.task_description == "Updated task from user"

    @pytest.mark.asyncio
    async def test_requirements_creates_minimal_on_fallback(self, tmp_path):
        """Test minimal requirements created as fallback"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = MockRequirementsExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Some task"
        )

        # Not interactive, with task
        result = await executor.phase_requirements(interactive=False)

        assert result.success is True
        assert (spec_dir / "requirements.json").exists()


class TestPhaseResearch:
    """Tests for phase_research method"""

    @pytest.mark.asyncio
    async def test_research_already_exists(self, tmp_path):
        """Test when research.json already exists"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        research_file = spec_dir / "research.json"
        research_file.write_text('{"findings": []}', encoding="utf-8")

        mock_run_agent = AsyncMock(return_value=(True, "Agent output"))
        executor = MockRequirementsExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )
        executor.run_agent_fn = mock_run_agent

        result = await executor.phase_research()

        assert result.success is True
        assert result.retries == 0
        # Agent should not be called
        mock_run_agent.assert_not_called()

    @pytest.mark.asyncio
    async def test_research_no_requirements(self, tmp_path):
        """Test research when requirements.json doesn't exist"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_run_agent = AsyncMock(return_value=(True, "Agent output"))
        executor = MockRequirementsExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )
        executor.run_agent_fn = mock_run_agent

        with patch("spec.phases.requirements_phases.validator.create_minimal_research") as mock_create:
            result = await executor.phase_research()

            mock_create.assert_called_once_with(
                spec_dir,
                reason="No requirements file available"
            )

        assert result.success is True
        assert str(spec_dir / "research.json") in result.output_files

    @pytest.mark.asyncio
    async def test_research_success_on_first_try(self, tmp_path):
        """Test research succeeds on first agent attempt"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create requirements
        req_file = spec_dir / "requirements.json"
        req_file.write_text('{"task_description": "Test task"}', encoding="utf-8")

        mock_run_agent = AsyncMock(return_value=(True, "Research completed"))
        executor = MockRequirementsExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )
        executor.run_agent_fn = mock_run_agent

        # Create research file when agent runs
        def create_research(*args, **kwargs):
            research_file = spec_dir / "research.json"
            research_file.write_text('{"findings": ["API documentation"]}', encoding="utf-8")
            return True, "Research done"

        mock_run_agent.side_effect = create_research

        result = await executor.phase_research()

        assert result.success is True
        assert result.retries == 0

    @pytest.mark.asyncio
    async def test_research_retries_on_failure(self, tmp_path):
        """Test research retries on agent failure"""
        from spec.phases.models import MAX_RETRIES

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create requirements
        req_file = spec_dir / "requirements.json"
        req_file.write_text('{"task_description": "Test"}', encoding="utf-8")

        mock_run_agent = AsyncMock(return_value=(False, "Agent failed"))
        executor = MockRequirementsExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )
        executor.run_agent_fn = mock_run_agent

        with patch("spec.phases.requirements_phases.validator.create_minimal_research"):
            result = await executor.phase_research()

        assert result.retries == MAX_RETRIES
        assert len(result.errors) == MAX_RETRIES

    @pytest.mark.asyncio
    async def test_research_agent_succeeds_no_file(self, tmp_path):
        """Test when agent succeeds but doesn't create research.json"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create requirements
        req_file = spec_dir / "requirements.json"
        req_file.write_text('{"task_description": "Test"}', encoding="utf-8")

        mock_run_agent = AsyncMock(return_value=(True, "Done"))
        executor = MockRequirementsExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )
        executor.run_agent_fn = mock_run_agent

        with patch("spec.phases.requirements_phases.validator.create_minimal_research") as mock_create:
            result = await executor.phase_research()

        # Should create minimal research
        assert result.success is True

    @pytest.mark.asyncio
    async def test_research_uses_correct_prompt(self, tmp_path):
        """Test research calls agent with correct prompt"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        req_file = spec_dir / "requirements.json"
        req_file.write_text('{"task_description": "Test"}', encoding="utf-8")

        mock_run_agent = AsyncMock(return_value=(True, "Done"))
        executor = MockRequirementsExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )
        executor.run_agent_fn = mock_run_agent

        # Create research file
        def create_research(*args, **kwargs):
            research_file = spec_dir / "research.json"
            research_file.write_text('{"findings": []}', encoding="utf-8")
            return True, "Done"

        mock_run_agent.side_effect = create_research

        await executor.phase_research()

        # Verify agent was called with correct prompt
        call_args = mock_run_agent.call_args
        assert call_args[0][0] == "spec_researcher.md"
        assert call_args[1]["phase_name"] == "research"


class TestRequirementsPhaseMixinEdgeCases:
    """Edge case tests for RequirementsPhaseMixin"""

    @pytest.mark.asyncio
    async def test_requirements_with_empty_task_non_interactive(self, tmp_path):
        """Test requirements with empty task in non-interactive mode"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = MockRequirementsExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description=""
        )

        result = await executor.phase_requirements(interactive=False)

        assert result.success is True
        assert (spec_dir / "requirements.json").exists()

    @pytest.mark.asyncio
    async def test_requirements_with_none_task_non_interactive(self, tmp_path):
        """Test requirements with None task in non-interactive mode"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = MockRequirementsExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description=None
        )

        result = await executor.phase_requirements(interactive=False)

        assert result.success is True
        assert (spec_dir / "requirements.json").exists()

    @pytest.mark.asyncio
    async def test_historical_context_with_unicode_task(self, tmp_path):
        """Test historical context with unicode task description"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = MockRequirementsExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Tâche avec caractères: ñ, é, 🎉"
        )

        with patch("graphiti_providers.is_graphiti_enabled", return_value=True):
            with patch("graphiti_providers.get_graph_hints", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = []

                result = await executor.phase_historical_context()

        assert result.success is True

    @pytest.mark.asyncio
    async def test_research_with_invalid_requirements(self, tmp_path):
        """Test research with invalid requirements.json"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create invalid requirements
        req_file = spec_dir / "requirements.json"
        req_file.write_text('{invalid json}', encoding="utf-8")

        mock_run_agent = AsyncMock(return_value=(True, "Done"))
        executor = MockRequirementsExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )
        executor.run_agent_fn = mock_run_agent

        # Create research file
        def create_research(*args, **kwargs):
            research_file = spec_dir / "research.json"
            research_file.write_text('{"findings": []}', encoding="utf-8")
            return True, "Done"

        mock_run_agent.side_effect = create_research

        result = await executor.phase_research()

        # Should still work (loads empty requirements)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_requirements_logs_task_preview(self, tmp_path):
        """Test requirements logs task preview when long"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        long_task = "This is a very long task description that should be truncated " * 10

        executor = MockRequirementsExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description=long_task
        )
        mock_logger = MagicMock()
        executor.task_logger = mock_logger

        await executor.phase_requirements(interactive=False)

        # Should log with truncated preview
        mock_logger.log.assert_called()

    @pytest.mark.asyncio
    async def test_hints_file_includes_timestamp(self, tmp_path):
        """Test graph_hints.json includes created_at timestamp"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = MockRequirementsExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task"
        )

        mock_hints = [{"content": "Test hint"}]

        with patch("graphiti_providers.is_graphiti_enabled", return_value=True):
            with patch("graphiti_providers.get_graph_hints", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_hints

                await executor.phase_historical_context()

        hints_file = spec_dir / "graph_hints.json"
        with open(hints_file, encoding="utf-8") as f:
            data = json.load(f)

        assert "created_at" in data
        # Verify timestamp is valid ISO format
        datetime.fromisoformat(data["created_at"])

    @pytest.mark.asyncio
    async def test_research_ui_status_messages(self, tmp_path):
        """Test research prints UI status messages"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        req_file = spec_dir / "requirements.json"
        req_file.write_text('{"task_description": "Test"}', encoding="utf-8")

        mock_run_agent = AsyncMock(return_value=(False, "Failed"))
        executor = MockRequirementsExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )
        executor.run_agent_fn = mock_run_agent
        mock_ui = MagicMock()
        executor.ui = mock_ui

        with patch("spec.phases.requirements_phases.validator.create_minimal_research"):
            await executor.phase_research()

        # Should print retry messages
        assert mock_ui.print_status.call_count > 0

    @pytest.mark.asyncio
    async def test_research_max_retries_constant(self, tmp_path):
        """Test that research uses MAX_RETRIES constant"""
        from spec.phases.models import MAX_RETRIES

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        req_file = spec_dir / "requirements.json"
        req_file.write_text('{"task_description": "Test"}', encoding="utf-8")

        call_count = 0

        async def mock_agent(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return (False, f"Attempt {call_count}")

        mock_run_agent = AsyncMock(side_effect=mock_agent)
        executor = MockRequirementsExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )
        executor.run_agent_fn = mock_run_agent

        with patch("spec.phases.requirements_phases.validator.create_minimal_research"):
            result = await executor.phase_research()

        # Should retry MAX_RETRIES times
        assert call_count == MAX_RETRIES
        assert result.retries == MAX_RETRIES
