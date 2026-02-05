"""Tests for requirements_phases module"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from spec.phases.requirements_phases import RequirementsPhaseMixin
from spec.phases.models import PhaseResult


class FakeRequirementsExecutor(RequirementsPhaseMixin):
    """Fake executor for testing"""

    def __init__(
        self,
        project_dir=None,
        spec_dir=None,
        task_description="",
        ui=None,
        task_logger=None,
        run_agent_fn=None,
    ):
        self.project_dir = project_dir or Path("/tmp/project")
        self.spec_dir = spec_dir or Path("/tmp/spec")
        self.task_description = task_description
        self.ui = ui or MagicMock()
        self.task_logger = task_logger or MagicMock()
        self.run_agent_fn = run_agent_fn or (lambda *a, **k: (True, "response"))


@pytest.mark.asyncio
class TestRequirementsPhaseMixin:
    """Tests for RequirementsPhaseMixin"""

    # ==================== phase_historical_context tests ====================

    async def test_phase_historical_context_existing_file_returns_early(
        self, tmp_path
    ):
        """Test historical_context returns early when hints file exists"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create existing graph_hints.json
        hints_file = spec_dir / "graph_hints.json"
        hints_file.write_text('{"enabled": true, "hints": []}', encoding="utf-8")

        ui = MagicMock()
        task_logger = MagicMock()

        executor = FakeRequirementsExecutor(
            spec_dir=spec_dir, ui=ui, task_logger=task_logger
        )

        result = await executor.phase_historical_context()

        assert result.success is True
        assert result.phase == "historical_context"
        assert result.output_files == [str(hints_file)]
        assert result.errors == []
        # Should not call is_graphiti_enabled since file exists
        ui.print_status.assert_called_with(
            "graph_hints.json already exists", "success"
        )

    async def test_phase_historical_context_graphiti_enabled_no_task(
        self, tmp_path
    ):
        """Test historical_context with Graphiti enabled but no task description"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        ui = MagicMock()
        ui.muted = lambda x: x
        task_logger = MagicMock()

        executor = FakeRequirementsExecutor(
            spec_dir=spec_dir,
            ui=ui,
            task_logger=task_logger,
            task_description="",  # No task description
        )

        with patch(
            "graphiti_providers.is_graphiti_enabled", return_value=True
        ), patch("graphiti_providers.get_graph_hints", new_callable=AsyncMock):
            result = await executor.phase_historical_context()

        assert result.success is True
        assert result.phase == "historical_context"
        assert (spec_dir / "graph_hints.json").exists()

        # Verify the hints file has the correct structure
        import json

        with open(spec_dir / "graph_hints.json", encoding="utf-8") as f:
            hints_data = json.load(f)

        assert hints_data["enabled"] is True
        assert hints_data["reason"] == "No task description available"
        assert hints_data["hints"] == []

    async def test_phase_historical_context_successful_query_with_hints(
        self, tmp_path
    ):
        """Test historical_context successfully retrieves hints from Graphiti"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        ui = MagicMock()
        ui.muted = lambda x: x
        task_logger = MagicMock()

        executor = FakeRequirementsExecutor(
            spec_dir=spec_dir,
            ui=ui,
            task_logger=task_logger,
            task_description="Build authentication feature",
        )

        mock_hints = [
            {"entity": "UserAuth", "relation": "requires", "description": "JWT tokens"}
        ]

        with patch(
            "graphiti_providers.is_graphiti_enabled", return_value=True
        ), patch(
            "graphiti_providers.get_graph_hints",
            new_callable=AsyncMock,
            return_value=mock_hints,
        ) as mock_get_hints:
            result = await executor.phase_historical_context()

        assert result.success is True
        assert result.phase == "historical_context"
        assert (spec_dir / "graph_hints.json").exists()

        # Verify get_graph_hints was called with correct parameters
        mock_get_hints.assert_called_once()
        call_args = mock_get_hints.call_args
        assert call_args[1]["query"] == "Build authentication feature"
        assert call_args[1]["max_results"] == 10

        # Verify the hints file has the correct structure
        import json

        with open(spec_dir / "graph_hints.json", encoding="utf-8") as f:
            hints_data = json.load(f)

        assert hints_data["enabled"] is True
        assert hints_data["query"] == "Build authentication feature"
        assert hints_data["hints"] == mock_hints
        assert hints_data["hint_count"] == 1

    async def test_phase_historical_context_successful_query_no_hints(
        self, tmp_path
    ):
        """Test historical_context when Graphiti returns no hints"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        ui = MagicMock()
        ui.muted = lambda x: x
        task_logger = MagicMock()

        executor = FakeRequirementsExecutor(
            spec_dir=spec_dir,
            ui=ui,
            task_logger=task_logger,
            task_description="Build brand new feature",
        )

        with patch(
            "graphiti_providers.is_graphiti_enabled", return_value=True
        ), patch(
            "graphiti_providers.get_graph_hints",
            new_callable=AsyncMock,
            return_value=[],  # No hints found
        ):
            result = await executor.phase_historical_context()

        assert result.success is True
        assert result.phase == "historical_context"
        assert (spec_dir / "graph_hints.json").exists()

        # Verify the hints file
        import json

        with open(spec_dir / "graph_hints.json", encoding="utf-8") as f:
            hints_data = json.load(f)

        assert hints_data["enabled"] is True
        assert hints_data["hints"] == []
        assert hints_data["hint_count"] == 0

    async def test_phase_historical_context_exception_during_query(
        self, tmp_path
    ):
        """Test historical_context handles exceptions during Graphiti query"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        ui = MagicMock()
        ui.muted = lambda x: x
        task_logger = MagicMock()

        executor = FakeRequirementsExecutor(
            spec_dir=spec_dir,
            ui=ui,
            task_logger=task_logger,
            task_description="Build feature",
        )

        with patch(
            "graphiti_providers.is_graphiti_enabled", return_value=True
        ), patch(
            "graphiti_providers.get_graph_hints",
            new_callable=AsyncMock,
            side_effect=Exception("Connection failed"),
        ):
            result = await executor.phase_historical_context()

        assert result.success is True  # Still succeeds with fallback
        assert result.phase == "historical_context"
        assert len(result.errors) == 1
        assert "Connection failed" in result.errors[0]
        assert (spec_dir / "graph_hints.json").exists()

        # Verify the hints file has error info
        import json

        with open(spec_dir / "graph_hints.json", encoding="utf-8") as f:
            hints_data = json.load(f)

        assert hints_data["enabled"] is True
        assert "Connection failed" in hints_data["reason"]

    async def test_phase_historical_context_uses_task_from_requirements(
        self, tmp_path
    ):
        """Test historical_context uses task from requirements.json when available"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create requirements.json with a task description
        req_file = spec_dir / "requirements.json"
        req_file.write_text(
            '{"task_description": "Fix authentication bug", "workflow_type": "bugfix"}',
            encoding="utf-8",
        )

        ui = MagicMock()
        ui.muted = lambda x: x
        task_logger = MagicMock()

        # executor has empty task_description but requirements.json has one
        executor = FakeRequirementsExecutor(
            spec_dir=spec_dir,
            ui=ui,
            task_logger=task_logger,
            task_description="",  # Empty, should use requirements.json
        )

        with patch(
            "graphiti_providers.is_graphiti_enabled", return_value=True
        ), patch(
            "graphiti_providers.get_graph_hints",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_get_hints:
            result = await executor.phase_historical_context()

        assert result.success is True
        # Verify it used the task from requirements.json
        mock_get_hints.assert_called_once()
        call_args = mock_get_hints.call_args
        assert call_args[1]["query"] == "Fix authentication bug"

    # ==================== phase_requirements tests ====================

    async def test_phase_requirements_existing_file_returns_early(self, tmp_path):
        """Test requirements phase returns early when requirements.json exists"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create existing requirements.json
        req_file = spec_dir / "requirements.json"
        req_file.write_text(
            '{"task_description": "Existing task"}', encoding="utf-8"
        )

        ui = MagicMock()
        task_logger = MagicMock()

        executor = FakeRequirementsExecutor(
            spec_dir=spec_dir,
            task_description="Different task",
            ui=ui,
            task_logger=task_logger,
        )

        result = await executor.phase_requirements(interactive=False)

        assert result.success is True
        assert result.phase == "requirements"
        assert result.output_files == [str(req_file)]
        # Should not overwrite existing file
        import json

        with open(req_file, encoding="utf-8") as f:
            data = json.load(f)
        assert data["task_description"] == "Existing task"

    async def test_phase_requirements_from_task(self, tmp_path):
        """Test requirements phase from task description"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        ui = MagicMock()
        task_logger = MagicMock()

        executor = FakeRequirementsExecutor(
            spec_dir=spec_dir,
            task_description="Build new feature",
            ui=ui,
            task_logger=task_logger,
        )

        result = await executor.phase_requirements(interactive=False)

        assert result.success is True
        assert result.phase == "requirements"
        assert (spec_dir / "requirements.json").exists()

    async def test_phase_requirements_interactive_keyboard_interrupt(
        self, tmp_path, monkeypatch
    ):
        """Test requirements phase interactive mode with KeyboardInterrupt"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        ui = MagicMock()
        ui.bold = lambda x: x
        ui.muted = lambda x: x
        ui.print_status = MagicMock()
        task_logger = MagicMock()

        # Mock input to raise KeyboardInterrupt
        def mock_input(_):
            raise KeyboardInterrupt()
        monkeypatch.setattr("builtins.input", mock_input)

        executor = FakeRequirementsExecutor(
            spec_dir=spec_dir,
            task_description="",
            ui=ui,
            task_logger=task_logger,
        )

        result = await executor.phase_requirements(interactive=True)

        assert result.success is False
        assert result.phase == "requirements"
        assert result.errors == ["User cancelled"]
        ui.print_status.assert_called_with(
            "Requirements gathering cancelled", "warning"
        )

    async def test_phase_requirements_interactive_eof_error(
        self, tmp_path, monkeypatch
    ):
        """Test requirements phase interactive mode with EOFError"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        ui = MagicMock()
        ui.bold = lambda x: x
        ui.muted = lambda x: x
        ui.print_status = MagicMock()
        task_logger = MagicMock()

        # Mock input to raise EOFError
        def mock_input(_):
            raise EOFError()
        monkeypatch.setattr("builtins.input", mock_input)

        executor = FakeRequirementsExecutor(
            spec_dir=spec_dir,
            task_description="",
            ui=ui,
            task_logger=task_logger,
        )

        result = await executor.phase_requirements(interactive=True)

        assert result.success is False
        assert result.phase == "requirements"
        assert result.errors == ["User cancelled"]

    async def test_phase_requirements_fallback_no_task_not_interactive(
        self, tmp_path
    ):
        """Test requirements phase fallback with no task and not interactive"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        ui = MagicMock()
        ui.print_status = MagicMock()
        task_logger = MagicMock()

        executor = FakeRequirementsExecutor(
            spec_dir=spec_dir,
            task_description="",  # No task description
            ui=ui,
            task_logger=task_logger,
        )

        result = await executor.phase_requirements(interactive=False)

        assert result.success is True
        assert result.phase == "requirements"
        assert (spec_dir / "requirements.json").exists()

        # Verify it created minimal requirements with "Unknown task"
        import json

        with open(spec_dir / "requirements.json", encoding="utf-8") as f:
            data = json.load(f)
        assert data["task_description"] == "Unknown task"

    async def test_phase_requirements_interactive(self, tmp_path, monkeypatch):
        """Test requirements phase in interactive mode"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        ui = MagicMock()
        ui.bold = lambda x: x
        ui.muted = lambda x: x
        task_logger = MagicMock()

        # Mock input() calls - need to handle all input prompts
        # The interactive prompts are:
        # 1. Task description (empty line ends multiline input)
        # 2. Workflow type choice
        # 3. Additional context (empty line to skip)
        inputs = iter(["Build feature", "", "1", "", ""])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))

        executor = FakeRequirementsExecutor(
            spec_dir=spec_dir,
            task_description="",
            ui=ui,
            task_logger=task_logger,
        )

        result = await executor.phase_requirements(interactive=True)

        assert result.success is True
        assert (spec_dir / "requirements.json").exists()

    # ==================== phase_research tests ====================

    async def test_phase_research_existing_file_returns_early(self, tmp_path):
        """Test research phase returns early when research.json exists"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create existing research.json
        research_file = spec_dir / "research.json"
        research_file.write_text(
            '{"integrations_researched": ["jwt"]}', encoding="utf-8"
        )

        ui = MagicMock()
        task_logger = MagicMock()

        executor = FakeRequirementsExecutor(
            spec_dir=spec_dir, ui=ui, task_logger=task_logger
        )

        result = await executor.phase_research()

        assert result.success is True
        assert result.phase == "research"
        assert result.output_files == [str(research_file)]

    async def test_phase_research_no_requirements_skips(self, tmp_path):
        """Test research phase skips when no requirements.json exists"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        ui = MagicMock()
        ui.print_status = MagicMock()
        task_logger = MagicMock()

        executor = FakeRequirementsExecutor(
            spec_dir=spec_dir, ui=ui, task_logger=task_logger
        )

        result = await executor.phase_research()

        assert result.success is True
        assert result.phase == "research"
        assert (spec_dir / "research.json").exists()
        ui.print_status.assert_called_with(
            "No requirements.json - skipping research phase", "warning"
        )

        # Verify minimal research was created
        import json

        with open(spec_dir / "research.json", encoding="utf-8") as f:
            data = json.load(f)
        assert data["research_skipped"] is True
        assert data["reason"] == "No requirements file available"

    async def test_phase_research_agent_succeeds_on_first_try(self, tmp_path):
        """Test research phase when agent succeeds on first attempt"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create requirements.json
        req_file = spec_dir / "requirements.json"
        req_file.write_text(
            '{"services_involved": ["backend"], "task_description": "Add feature"}',
            encoding="utf-8",
        )

        ui = MagicMock()
        ui.print_status = MagicMock()
        task_logger = MagicMock()

        # Mock run_agent_fn that succeeds and creates research.json
        async def mock_run_agent(*args, **kwargs):
            # Create the research file as the agent would
            research_file = spec_dir / "research.json"
            research_file.write_text(
                '{"integrations_researched": ["pytest"]}', encoding="utf-8"
            )
            return True, "Research complete"

        executor = FakeRequirementsExecutor(
            spec_dir=spec_dir, ui=ui, task_logger=task_logger, run_agent_fn=mock_run_agent
        )

        result = await executor.phase_research()

        assert result.success is True
        assert result.phase == "research"
        assert result.retries == 0  # First attempt succeeded
        assert (spec_dir / "research.json").exists()

    async def test_phase_research_agent_succeeds_but_no_file_created(
        self, tmp_path
    ):
        """Test research phase when agent succeeds but doesn't create file"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create requirements.json
        req_file = spec_dir / "requirements.json"
        req_file.write_text(
            '{"services_involved": ["backend"], "task_description": "Add feature"}',
            encoding="utf-8",
        )

        ui = MagicMock()
        ui.print_status = MagicMock()
        task_logger = MagicMock()

        # Mock run_agent_fn that returns success but doesn't create file
        async def mock_run_agent(*args, **kwargs):
            return True, "Agent completed"

        executor = FakeRequirementsExecutor(
            spec_dir=spec_dir, ui=ui, task_logger=task_logger, run_agent_fn=mock_run_agent
        )

        result = await executor.phase_research()

        assert result.success is True
        assert result.phase == "research"
        assert (spec_dir / "research.json").exists()

        # Verify minimal research was created with the appropriate reason
        import json

        with open(spec_dir / "research.json", encoding="utf-8") as f:
            data = json.load(f)
        assert data["research_skipped"] is True
        assert data["reason"] == "Agent completed but created no findings"

    async def test_phase_research_creates_minimal(self, tmp_path):
        """Test research phase creates minimal research.json"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create requirements with services that might need research
        req_file = spec_dir / "requirements.json"
        req_file.write_text(
            '{"services_involved": ["backend"], "task_description": "Add feature"}',
            encoding="utf-8",
        )

        ui = MagicMock()
        task_logger = MagicMock()

        # Mock run_agent_fn that fails (causing minimal research to be created)
        async def mock_run_agent(*args, **kwargs):
            return False, "Agent failed"

        executor = FakeRequirementsExecutor(
            spec_dir=spec_dir, ui=ui, task_logger=task_logger, run_agent_fn=mock_run_agent
        )

        result = await executor.phase_research()

        # Should create minimal research after agent failure
        assert result.success is True
        assert (spec_dir / "research.json").exists()

    async def test_phase_research_multiple_retries(self, tmp_path):
        """Test research phase with multiple retries before success"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create requirements.json
        req_file = spec_dir / "requirements.json"
        req_file.write_text(
            '{"services_involved": ["backend"], "task_description": "Add feature"}',
            encoding="utf-8",
        )

        ui = MagicMock()
        ui.print_status = MagicMock()
        task_logger = MagicMock()

        attempts = [0]

        # Mock run_agent_fn that fails first, then succeeds
        async def mock_run_agent(*args, **kwargs):
            attempts[0] += 1
            if attempts[0] == 1:
                return False, "First attempt failed"
            # Create the research file on second attempt
            research_file = spec_dir / "research.json"
            research_file.write_text(
                '{"integrations_researched": ["pytest"]}', encoding="utf-8"
            )
            return True, "Research complete"

        executor = FakeRequirementsExecutor(
            spec_dir=spec_dir, ui=ui, task_logger=task_logger, run_agent_fn=mock_run_agent
        )

        result = await executor.phase_research()

        assert result.success is True
        assert result.retries == 1  # Failed once, succeeded on retry
        assert (spec_dir / "research.json").exists()

    # ==================== Original tests ====================

    async def test_phase_historical_context_skips_when_no_graphiti(
        self, tmp_path
    ):
        """Test historical_context skips when Graphiti not available"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        ui = MagicMock()
        ui.print_status = MagicMock()
        ui.muted = lambda x: x
        task_logger = MagicMock()

        executor = FakeRequirementsExecutor(
            spec_dir=spec_dir, ui=ui, task_logger=task_logger
        )

        # Mock is_graphiti_enabled at the actual module location
        # The import is: from graphiti_providers import is_graphiti_enabled
        # So we patch the graphiti_providers module directly
        with patch("graphiti_providers.is_graphiti_enabled", return_value=False):
            result = await executor.phase_historical_context()

        # Should succeed but skip historical context
        assert result.success is True
        assert (spec_dir / "graph_hints.json").exists()
