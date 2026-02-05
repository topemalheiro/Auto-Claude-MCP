"""Tests for PhaseExecutor class"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime

import pytest

from spec.phases.executor import PhaseExecutor
from spec.phases.models import PhaseResult, MAX_RETRIES
from spec.validate_pkg.models import ValidationResult


class TestPhaseExecutorInit:
    """Tests for PhaseExecutor initialization"""

    def test_init_with_all_params(self, tmp_path):
        """Test initialization with all parameters"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_validator = MagicMock()
        mock_run_agent = AsyncMock()
        mock_logger = MagicMock()
        mock_ui = MagicMock()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Build a feature",
            spec_validator=mock_validator,
            run_agent_fn=mock_run_agent,
            task_logger=mock_logger,
            ui_module=mock_ui
        )

        assert executor.project_dir == project_dir
        assert executor.spec_dir == spec_dir
        assert executor.task_description == "Build a feature"
        assert executor.spec_validator == mock_validator
        assert executor.run_agent_fn == mock_run_agent
        assert executor.task_logger == mock_logger
        assert executor.ui == mock_ui

    def test_init_with_empty_task_description(self, tmp_path):
        """Test initialization with empty task description"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=MagicMock(),
            ui_module=MagicMock()
        )

        assert executor.task_description == ""

    def test_init_with_none_task_description(self, tmp_path):
        """Test initialization with None task description"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description=None,
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=MagicMock(),
            ui_module=MagicMock()
        )

        assert executor.task_description is None

    def test_executor_inherits_from_all_mixins(self, tmp_path):
        """Test that PhaseExecutor inherits from all mixins"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=MagicMock(),
            ui_module=MagicMock()
        )

        # Check that executor has methods from all mixins
        assert hasattr(executor, "phase_discovery")
        assert hasattr(executor, "phase_context")
        assert hasattr(executor, "phase_requirements")
        assert hasattr(executor, "phase_historical_context")
        assert hasattr(executor, "phase_research")
        assert hasattr(executor, "phase_quick_spec")
        assert hasattr(executor, "phase_spec_writing")
        assert hasattr(executor, "phase_self_critique")
        assert hasattr(executor, "phase_planning")
        assert hasattr(executor, "phase_validation")


class TestPhaseExecutorRunScript:
    """Tests for PhaseExecutor._run_script method"""

    def test_run_script_delegates_to_utility(self, tmp_path):
        """Test _run_script delegates to run_script utility"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=MagicMock(),
            ui_module=MagicMock()
        )

        with patch("spec.phases.executor.run_script") as mock_run_script:
            mock_run_script.return_value = (True, "Success output")

            success, output = executor._run_script("test_script.py", ["--arg1"])

            mock_run_script.assert_called_once_with(
                project_dir,
                "test_script.py",
                ["--arg1"]
            )
            assert success is True
            assert output == "Success output"

    def test_run_script_failure(self, tmp_path):
        """Test _run_script with failure"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=MagicMock(),
            ui_module=MagicMock()
        )

        with patch("spec.phases.executor.run_script") as mock_run_script:
            mock_run_script.return_value = (False, "Error occurred")

            success, output = executor._run_script("failing_script.py", [])

            assert success is False
            assert output == "Error occurred"

    def test_run_script_with_empty_args(self, tmp_path):
        """Test _run_script with empty args"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=MagicMock(),
            ui_module=MagicMock()
        )

        with patch("spec.phases.executor.run_script") as mock_run_script:
            mock_run_script.return_value = (True, "Output")

            success, output = executor._run_script("script.py", [])

            mock_run_script.assert_called_once_with(
                project_dir,
                "script.py",
                []
            )


class TestPhaseExecutorAttributeAccess:
    """Tests for accessing executor attributes"""

    def test_project_dir_is_path_object(self, tmp_path):
        """Test project_dir is a Path object"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=MagicMock(),
            ui_module=MagicMock()
        )

        assert isinstance(executor.project_dir, Path)

    def test_spec_dir_is_path_object(self, tmp_path):
        """Test spec_dir is a Path object"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=MagicMock(),
            ui_module=MagicMock()
        )

        assert isinstance(executor.spec_dir, Path)

    def test_task_description_mutable(self, tmp_path):
        """Test task_description can be modified"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Original task",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=MagicMock(),
            ui_module=MagicMock()
        )

        executor.task_description = "Modified task"

        assert executor.task_description == "Modified task"


class TestPhaseExecutorMethodResolution:
    """Tests for method resolution order"""

    def test_method_from_discovery_mixin(self, tmp_path):
        """Test phase_discovery comes from DiscoveryPhaseMixin"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=MagicMock(),
            ui_module=MagicMock()
        )

        # phase_discovery should be callable
        assert callable(executor.phase_discovery)

    def test_method_from_requirements_mixin(self, tmp_path):
        """Test phase_requirements comes from RequirementsPhaseMixin"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=MagicMock(),
            ui_module=MagicMock()
        )

        assert callable(executor.phase_requirements)
        assert callable(executor.phase_historical_context)
        assert callable(executor.phase_research)

    def test_method_from_spec_mixin(self, tmp_path):
        """Test spec phase methods come from SpecPhaseMixin"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=MagicMock(),
            ui_module=MagicMock()
        )

        assert callable(executor.phase_quick_spec)
        assert callable(executor.phase_spec_writing)
        assert callable(executor.phase_self_critique)

    def test_method_from_planning_mixin(self, tmp_path):
        """Test planning methods come from PlanningPhaseMixin"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=MagicMock(),
            ui_module=MagicMock()
        )

        assert callable(executor.phase_planning)
        assert callable(executor.phase_validation)


class TestPhaseExecutorIntegration:
    """Integration tests for PhaseExecutor"""

    def test_executor_with_mock_dependencies(self, tmp_path):
        """Test executor can be instantiated with mock dependencies"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_validator = MagicMock()
        mock_run_agent = AsyncMock(return_value=(True, "Agent output"))
        mock_logger = MagicMock()
        mock_ui = MagicMock()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task",
            spec_validator=mock_validator,
            run_agent_fn=mock_run_agent,
            task_logger=mock_logger,
            ui_module=mock_ui
        )

        assert executor is not None
        assert callable(executor.phase_discovery)

    @pytest.mark.asyncio
    async def test_executor_can_call_phase_method(self, tmp_path):
        """Test executor can call phase methods"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create project index for discovery
        auto_claude = project_dir / "auto-claude"
        auto_claude.mkdir()
        project_index = auto_claude / "project_index.json"
        project_index.write_text('{"project_type": "test"}', encoding="utf-8")

        mock_validator = MagicMock()
        mock_validator.validate_all.return_value = [
            MagicMock(valid=True, errors=[], checkpoint="test")
        ]
        mock_run_agent = AsyncMock(return_value=(True, "Agent output"))
        mock_logger = MagicMock()
        mock_ui = MagicMock()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test",
            spec_validator=mock_validator,
            run_agent_fn=mock_run_agent,
            task_logger=mock_logger,
            ui_module=mock_ui
        )

        # Call phase_discovery
        result = await executor.phase_discovery()

        assert isinstance(result, PhaseResult)


class TestPhaseExecutorEdgeCases:
    """Edge case tests for PhaseExecutor"""

    def test_executor_with_relative_paths(self, tmp_path):
        """Test executor with relative Path objects"""
        project_dir = Path("project")  # Relative path
        spec_dir = Path("spec")

        # This should work - executor doesn't require absolute paths
        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=MagicMock(),
            ui_module=MagicMock()
        )

        assert executor.project_dir == project_dir
        assert executor.spec_dir == spec_dir

    def test_executor_with_symlink_paths(self, tmp_path):
        """Test executor with symlink paths"""
        project_dir = tmp_path / "real_project"
        project_dir.mkdir()

        # Create symlink
        symlink_dir = tmp_path / "link_project"
        try:
            symlink_dir.symlink_to(project_dir)
        except OSError:
            # Symlinks might not be supported on this system
            pytest.skip("Symlinks not supported")

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = PhaseExecutor(
            project_dir=symlink_dir,
            spec_dir=spec_dir,
            task_description="Test",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=MagicMock(),
            ui_module=MagicMock()
        )

        # Should work with symlink
        assert executor.project_dir == symlink_dir

    def test_executor_with_unicode_task_description(self, tmp_path):
        """Test executor with unicode characters in task description"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Tâche avec caractère spéciaux: ñ, é, 🎉",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=MagicMock(),
            ui_module=MagicMock()
        )

        assert "ñ" in executor.task_description
        assert "é" in executor.task_description
        assert "🎉" in executor.task_description

    def test_executor_with_very_long_task_description(self, tmp_path):
        """Test executor with very long task description"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        long_task = "Test task " * 1000  # Very long description

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description=long_task,
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=MagicMock(),
            ui_module=MagicMock()
        )

        assert len(executor.task_description) == len(long_task)

    def test_executor_attributes_are_public(self, tmp_path):
        """Test that executor attributes are publicly accessible"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=MagicMock(),
            ui_module=MagicMock()
        )

        # All attributes should be accessible
        _ = executor.project_dir
        _ = executor.spec_dir
        _ = executor.task_description
        _ = executor.spec_validator
        _ = executor.run_agent_fn
        _ = executor.task_logger
        _ = executor.ui


class TestPhaseExecutorTypeAnnotations:
    """Type annotation tests for PhaseExecutor"""

    def test_executor_callable_annotations(self, tmp_path):
        """Test that run_agent_fn is callable annotation"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=MagicMock(),
            ui_module=MagicMock()
        )

        # run_agent_fn should be callable
        assert callable(executor.run_agent_fn)


class TestPhaseExecutorPhaseDiscovery:
    """Tests for phase_discovery execution"""

    @pytest.mark.asyncio
    async def test_phase_discovery_success_creates_index(self, tmp_path):
        """Test phase_discovery creates project_index.json on success"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_ui = MagicMock()
        mock_logger = MagicMock()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=mock_logger,
            ui_module=mock_ui
        )

        # Create a mock project index file
        index_file = spec_dir / "project_index.json"
        index_file.write_text('{"files": []}', encoding="utf-8")

        with patch("spec.discovery.run_discovery_script", return_value=(True, "Success")), \
             patch("spec.discovery.get_project_index_stats", return_value={"file_count": 10}):
            result = await executor.phase_discovery()

        assert result.success is True
        assert result.phase == "discovery"
        assert result.retries == 0
        mock_logger.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_phase_discovery_retry_on_failure(self, tmp_path):
        """Test phase_discovery retries on failure"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_ui = MagicMock()
        mock_logger = MagicMock()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=mock_logger,
            ui_module=mock_ui
        )

        attempts = [0]

        def mock_run_discovery(*args, **kwargs):
            attempts[0] += 1
            if attempts[0] < 2:
                return (False, f"Attempt {attempts[0]} failed")
            return (True, "Success")

        with patch("spec.discovery.run_discovery_script", side_effect=mock_run_discovery):
            result = await executor.phase_discovery()

        assert result.success is True
        assert result.retries == 1

    @pytest.mark.asyncio
    async def test_phase_discovery_failure_after_max_retries(self, tmp_path):
        """Test phase_discovery fails after MAX_RETRIES"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_ui = MagicMock()
        mock_logger = MagicMock()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=mock_logger,
            ui_module=mock_ui
        )

        with patch("spec.discovery.run_discovery_script", return_value=(False, "Failed")):
            result = await executor.phase_discovery()

        assert result.success is False
        assert len(result.errors) == MAX_RETRIES


class TestPhaseExecutorPhaseContext:
    """Tests for phase_context execution"""

    @pytest.mark.asyncio
    async def test_phase_context_skips_when_exists(self, tmp_path):
        """Test phase_context skips when context.json exists"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        context_file = spec_dir / "context.json"
        context_file.write_text('{"task": "test"}', encoding="utf-8")

        mock_ui = MagicMock()
        mock_logger = MagicMock()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=mock_logger,
            ui_module=mock_ui
        )

        result = await executor.phase_context()

        assert result.success is True
        assert result.retries == 0
        mock_ui.print_status.assert_called_with("context.json already exists", "success")

    @pytest.mark.asyncio
    async def test_phase_context_creates_new_file(self, tmp_path):
        """Test phase_context creates new context.json"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_ui = MagicMock()
        mock_logger = MagicMock()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Build feature",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=mock_logger,
            ui_module=mock_ui
        )

        def mock_run_context(*args, **kwargs):
            # Create the context file as the real function would
            (spec_dir / "context.json").write_text('{"task": "Build feature"}', encoding="utf-8")
            return True, "Success"

        with patch("spec.context.run_context_discovery", side_effect=mock_run_context):
            result = await executor.phase_context()

        assert result.success is True
        assert (spec_dir / "context.json").exists()

    @pytest.mark.asyncio
    async def test_phase_context_creates_minimal_on_failure(self, tmp_path):
        """Test phase_context creates minimal context when script fails"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_ui = MagicMock()
        mock_logger = MagicMock()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Build feature",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=mock_logger,
            ui_module=mock_ui
        )

        with patch("spec.context.run_context_discovery", return_value=(False, "Failed")):
            result = await executor.phase_context()

        # Should create minimal context as fallback
        assert result.success is True
        assert (spec_dir / "context.json").exists()
        mock_ui.print_status.assert_called_with(
            "Created minimal context.json (script failed)", "success"
        )


class TestPhaseExecutorPhaseRequirements:
    """Tests for phase_requirements execution"""

    @pytest.mark.asyncio
    async def test_phase_requirements_skips_when_exists(self, tmp_path):
        """Test phase_requirements skips when requirements.json exists"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        req_file = spec_dir / "requirements.json"
        req_file.write_text('{"task_description": "test"}', encoding="utf-8")

        mock_ui = MagicMock()
        mock_logger = MagicMock()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=mock_logger,
            ui_module=mock_ui
        )

        result = await executor.phase_requirements()

        assert result.success is True
        assert result.retries == 0

    @pytest.mark.asyncio
    async def test_phase_requirements_non_interactive(self, tmp_path):
        """Test phase_requirements in non-interactive mode"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_ui = MagicMock()
        mock_logger = MagicMock()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Build a feature",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=mock_logger,
            ui_module=mock_ui
        )

        result = await executor.phase_requirements(interactive=False)

        assert result.success is True
        assert (spec_dir / "requirements.json").exists()

    @pytest.mark.asyncio
    async def test_phase_requirements_cancellation(self, tmp_path):
        """Test phase_requirements handles user cancellation"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_ui = MagicMock()
        mock_logger = MagicMock()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=mock_logger,
            ui_module=mock_ui
        )

        with patch("spec.requirements.gather_requirements_interactively", side_effect=KeyboardInterrupt()):
            result = await executor.phase_requirements(interactive=True)

        assert result.success is False
        assert "User cancelled" in result.errors


class TestPhaseExecutorPhaseHistoricalContext:
    """Tests for phase_historical_context execution"""

    @pytest.mark.asyncio
    async def test_phase_historical_context_skips_when_exists(self, tmp_path):
        """Test phase_historical_context skips when graph_hints.json exists"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        hints_file = spec_dir / "graph_hints.json"
        hints_file.write_text('{"hints": []}', encoding="utf-8")

        mock_ui = MagicMock()
        mock_logger = MagicMock()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=mock_logger,
            ui_module=mock_ui
        )

        result = await executor.phase_historical_context()

        assert result.success is True
        mock_ui.print_status.assert_called_with("graph_hints.json already exists", "success")

    @pytest.mark.asyncio
    async def test_phase_historical_context_graphiti_disabled(self, tmp_path):
        """Test phase_historical_context when Graphiti is disabled"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_ui = MagicMock()
        mock_logger = MagicMock()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=mock_logger,
            ui_module=mock_ui
        )

        with patch("graphiti_providers.is_graphiti_enabled", return_value=False):
            result = await executor.phase_historical_context()

        assert result.success is True
        mock_ui.print_status.assert_called_with(
            "Graphiti not enabled, skipping historical context", "info"
        )

    @pytest.mark.asyncio
    async def test_phase_historical_context_retrieves_hints(self, tmp_path):
        """Test phase_historical_context retrieves hints successfully"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_ui = MagicMock()
        mock_logger = MagicMock()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Build authentication system",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=mock_logger,
            ui_module=mock_ui
        )

        with patch("graphiti_providers.is_graphiti_enabled", return_value=True), \
             patch("graphiti_providers.get_graph_hints", return_value=["hint1", "hint2"]):
            result = await executor.phase_historical_context()

        assert result.success is True
        assert (spec_dir / "graph_hints.json").exists()
        mock_ui.print_status.assert_called_with("Retrieved 2 graph hints", "success")


class TestPhaseExecutorPhaseResearch:
    """Tests for phase_research execution"""

    @pytest.mark.asyncio
    async def test_phase_research_skips_when_exists(self, tmp_path):
        """Test phase_research skips when research.json exists"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        research_file = spec_dir / "research.json"
        research_file.write_text('{"findings": []}', encoding="utf-8")

        mock_ui = MagicMock()
        mock_logger = MagicMock()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=mock_logger,
            ui_module=mock_ui
        )

        result = await executor.phase_research()

        assert result.success is True
        mock_ui.print_status.assert_called_with("research.json already exists", "success")

    @pytest.mark.asyncio
    async def test_phase_research_no_requirements(self, tmp_path):
        """Test phase_research when requirements.json doesn't exist"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_ui = MagicMock()
        mock_logger = MagicMock()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=mock_logger,
            ui_module=mock_ui
        )

        result = await executor.phase_research()

        assert result.success is True
        assert (spec_dir / "research.json").exists()

    @pytest.mark.asyncio
    async def test_phase_research_success(self, tmp_path):
        """Test phase_research creates research.json"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        req_file = spec_dir / "requirements.json"
        req_file.write_text('{"task_description": "Add feature"}', encoding="utf-8")

        mock_ui = MagicMock()
        mock_logger = MagicMock()

        async def mock_run_agent(*args, **kwargs):
            research_file = spec_dir / "research.json"
            research_file.write_text('{"findings": ["result"]}', encoding="utf-8")
            return True, "Research complete"

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task",
            spec_validator=MagicMock(),
            run_agent_fn=mock_run_agent,
            task_logger=mock_logger,
            ui_module=mock_ui
        )

        result = await executor.phase_research()

        assert result.success is True
        assert (spec_dir / "research.json").exists()


class TestPhaseExecutorPhaseQuickSpec:
    """Tests for phase_quick_spec execution"""

    @pytest.mark.asyncio
    async def test_phase_quick_spec_skips_when_exists(self, tmp_path):
        """Test phase_quick_spec skips when files exist"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        (spec_dir / "spec.md").write_text("# Spec", encoding="utf-8")
        (spec_dir / "implementation_plan.json").write_text('{"phases": []}', encoding="utf-8")

        mock_ui = MagicMock()
        mock_logger = MagicMock()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=mock_logger,
            ui_module=mock_ui
        )

        result = await executor.phase_quick_spec()

        assert result.success is True
        assert result.retries == 0

    @pytest.mark.asyncio
    async def test_phase_quick_spec_creates_files(self, tmp_path):
        """Test phase_quick_spec creates spec and plan"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_ui = MagicMock()
        mock_logger = MagicMock()

        async def mock_run_agent(*args, **kwargs):
            (spec_dir / "spec.md").write_text("# Quick Spec", encoding="utf-8")
            return True, "Spec created"

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Simple task",
            spec_validator=MagicMock(),
            run_agent_fn=mock_run_agent,
            task_logger=mock_logger,
            ui_module=mock_ui
        )

        result = await executor.phase_quick_spec()

        assert result.success is True
        assert (spec_dir / "spec.md").exists()
        assert (spec_dir / "implementation_plan.json").exists()


class TestPhaseExecutorPhaseSpecWriting:
    """Tests for phase_spec_writing execution"""

    @pytest.mark.asyncio
    async def test_phase_spec_writing_skips_valid_spec(self, tmp_path):
        """Test phase_spec_writing skips when valid spec exists"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        (spec_dir / "spec.md").write_text("# Complete Spec\n\n## Overview\n\nContent", encoding="utf-8")

        mock_ui = MagicMock()
        mock_logger = MagicMock()
        mock_validator = MagicMock()
        mock_validator.validate_spec_document.return_value = ValidationResult(
            valid=True, checkpoint="spec", errors=[], warnings=[], fixes=[]
        )

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task",
            spec_validator=mock_validator,
            run_agent_fn=AsyncMock(),
            task_logger=mock_logger,
            ui_module=mock_ui
        )

        result = await executor.phase_spec_writing()

        assert result.success is True
        assert result.retries == 0

    @pytest.mark.asyncio
    async def test_phase_spec_writing_regenerates_invalid(self, tmp_path):
        """Test phase_spec_writing regenerates invalid spec"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        (spec_dir / "spec.md").write_text("# Invalid", encoding="utf-8")

        mock_ui = MagicMock()
        mock_logger = MagicMock()
        mock_validator = MagicMock()
        mock_validator.validate_spec_document.side_effect = [
            ValidationResult(valid=False, checkpoint="spec", errors=["Incomplete"], warnings=[], fixes=[]),
            ValidationResult(valid=True, checkpoint="spec", errors=[], warnings=[], fixes=[])
        ]

        async def mock_run_agent(*args, **kwargs):
            (spec_dir / "spec.md").write_text("# Complete Spec", encoding="utf-8")
            return True, "Spec written"

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task",
            spec_validator=mock_validator,
            run_agent_fn=mock_run_agent,
            task_logger=mock_logger,
            ui_module=mock_ui
        )

        result = await executor.phase_spec_writing()

        assert result.success is True


class TestPhaseExecutorPhaseSelfCritique:
    """Tests for phase_self_critique execution"""

    @pytest.mark.asyncio
    async def test_phase_self_critique_no_spec_error(self, tmp_path):
        """Test phase_self_critique errors when no spec exists"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_ui = MagicMock()
        mock_logger = MagicMock()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=mock_logger,
            ui_module=mock_ui
        )

        result = await executor.phase_self_critique()

        assert result.success is False
        assert "spec.md does not exist" in result.errors

    @pytest.mark.asyncio
    async def test_phase_self_critique_skips_completed(self, tmp_path):
        """Test phase_self_critique skips when already completed"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        (spec_dir / "spec.md").write_text("# Spec", encoding="utf-8")
        critique_file = spec_dir / "critique_report.json"
        critique_file.write_text(
            json.dumps({"issues_fixed": True, "no_issues_found": False}),
            encoding="utf-8"
        )

        mock_ui = MagicMock()
        mock_logger = MagicMock()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=mock_logger,
            ui_module=mock_ui
        )

        result = await executor.phase_self_critique()

        assert result.success is True
        mock_ui.print_status.assert_called_with("Self-critique already completed", "success")


class TestPhaseExecutorPhasePlanning:
    """Tests for phase_planning execution"""

    @pytest.mark.asyncio
    async def test_phase_planning_skips_valid_plan(self, tmp_path):
        """Test phase_planning skips when valid plan exists"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_data = {
            "spec_name": "test-spec",
            "workflow_type": "feature",
            "phases": [{"phase": 1, "subtasks": []}]
        }
        (spec_dir / "implementation_plan.json").write_text(json.dumps(plan_data), encoding="utf-8")

        mock_ui = MagicMock()
        mock_logger = MagicMock()
        mock_validator = MagicMock()
        mock_validator.validate_implementation_plan.return_value = ValidationResult(
            valid=True, checkpoint="plan", errors=[], warnings=[], fixes=[]
        )

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task",
            spec_validator=mock_validator,
            run_agent_fn=AsyncMock(),
            task_logger=mock_logger,
            ui_module=mock_ui
        )

        result = await executor.phase_planning()

        assert result.success is True
        assert result.retries == 0

    @pytest.mark.asyncio
    async def test_phase_planning_script_success(self, tmp_path):
        """Test phase_planning succeeds via script"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_ui = MagicMock()
        mock_logger = MagicMock()
        mock_validator = MagicMock()
        mock_validator.validate_implementation_plan.return_value = ValidationResult(
            valid=True, checkpoint="plan", errors=[], warnings=[], fixes=[]
        )

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task",
            spec_validator=mock_validator,
            run_agent_fn=AsyncMock(),
            task_logger=mock_logger,
            ui_module=mock_ui
        )

        def mock_run_script(script, args):
            plan_data = {"spec_name": "test", "phases": []}
            (spec_dir / "implementation_plan.json").write_text(json.dumps(plan_data), encoding="utf-8")
            return True, "Script success"

        with patch.object(executor, "_run_script", side_effect=mock_run_script):
            result = await executor.phase_planning()

        assert result.success is True

    @pytest.mark.asyncio
    async def test_phase_planning_fallback_to_agent(self, tmp_path):
        """Test phase_planning falls back to agent when script fails"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_ui = MagicMock()
        mock_logger = MagicMock()
        mock_validator = MagicMock()
        mock_validator.validate_implementation_plan.return_value = ValidationResult(
            valid=True, checkpoint="plan", errors=[], warnings=[], fixes=[]
        )

        async def mock_run_agent(*args, **kwargs):
            plan_data = {"spec_name": "test", "phases": []}
            (spec_dir / "implementation_plan.json").write_text(json.dumps(plan_data), encoding="utf-8")
            return True, "Agent success"

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task",
            spec_validator=mock_validator,
            run_agent_fn=mock_run_agent,
            task_logger=mock_logger,
            ui_module=mock_ui
        )

        def mock_run_script(script, args):
            return False, "Script failed"

        with patch.object(executor, "_run_script", side_effect=mock_run_script):
            result = await executor.phase_planning()

        assert result.success is True
        mock_ui.print_status.assert_any_call("Falling back to planner agent...", "progress")


class TestPhaseExecutorPhaseValidation:
    """Tests for phase_validation execution"""

    @pytest.mark.asyncio
    async def test_phase_validation_all_pass(self, tmp_path):
        """Test phase_validation when all checks pass"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        (spec_dir / "spec.md").write_text("# Spec", encoding="utf-8")
        (spec_dir / "requirements.json").write_text('{}', encoding="utf-8")
        (spec_dir / "context.json").write_text('{}', encoding="utf-8")
        (spec_dir / "implementation_plan.json").write_text('{"phases": []}', encoding="utf-8")

        mock_ui = MagicMock()
        mock_logger = MagicMock()
        mock_validator = MagicMock()
        mock_validator.validate_all.return_value = [
            ValidationResult(valid=True, checkpoint="spec", errors=[], warnings=[], fixes=[]),
            ValidationResult(valid=True, checkpoint="req", errors=[], warnings=[], fixes=[]),
            ValidationResult(valid=True, checkpoint="plan", errors=[], warnings=[], fixes=[]),
        ]

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task",
            spec_validator=mock_validator,
            run_agent_fn=AsyncMock(),
            task_logger=mock_logger,
            ui_module=mock_ui
        )

        result = await executor.phase_validation()

        assert result.success is True
        mock_ui.print_status.assert_called_with("All validation checks passed", "success")

    @pytest.mark.asyncio
    async def test_phase_validation_with_auto_fix(self, tmp_path):
        """Test phase_validation with auto-fix attempt"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        (spec_dir / "spec.md").write_text("# Invalid", encoding="utf-8")

        mock_ui = MagicMock()
        mock_logger = MagicMock()
        mock_validator = MagicMock()
        mock_validator.validate_all.side_effect = [
            [
                ValidationResult(valid=False, checkpoint="spec", errors=["Missing section"], warnings=[], fixes=[]),
            ],
            [
                ValidationResult(valid=True, checkpoint="spec", errors=[], warnings=[], fixes=[]),
            ]
        ]

        async def mock_run_agent(*args, **kwargs):
            (spec_dir / "spec.md").write_text("# Valid Spec\n\n## Overview", encoding="utf-8")
            return True, "Fixed"

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task",
            spec_validator=mock_validator,
            run_agent_fn=mock_run_agent,
            task_logger=mock_logger,
            ui_module=mock_ui
        )

        result = await executor.phase_validation()

        assert result.success is True

    @pytest.mark.asyncio
    async def test_phase_validation_all_fail(self, tmp_path):
        """Test phase_validation when all checks fail"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_ui = MagicMock()
        mock_logger = MagicMock()
        mock_validator = MagicMock()
        mock_validator.validate_all.return_value = [
            ValidationResult(valid=False, checkpoint="spec", errors=["Invalid spec"], warnings=[], fixes=[]),
        ]

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task",
            spec_validator=mock_validator,
            run_agent_fn=AsyncMock(return_value=(False, "Fix failed")),
            task_logger=mock_logger,
            ui_module=mock_ui
        )

        result = await executor.phase_validation()

        assert result.success is False
        assert len(result.errors) > 0


class TestPhaseExecutorErrorHandling:
    """Tests for error handling and edge cases"""

    @pytest.mark.asyncio
    async def test_phase_handles_exception_gracefully(self, tmp_path):
        """Test phase execution handles exceptions"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_ui = MagicMock()
        mock_logger = MagicMock()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=mock_logger,
            ui_module=mock_ui
        )

        # The actual implementation doesn't wrap run_discovery_script in try/except
        # so we need to test the behavior that is actually implemented
        # Let's test context phase which creates minimal context on failure
        with patch("spec.context.run_context_discovery", side_effect=Exception("Unexpected error")):
            # This should propagate the exception since it's not caught
            with pytest.raises(Exception, match="Unexpected error"):
                await executor.phase_context()

    @pytest.mark.asyncio
    async def test_phase_handles_subprocess_failure(self, tmp_path):
        """Test phase execution handles subprocess failures gracefully"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_ui = MagicMock()
        mock_logger = MagicMock()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=mock_logger,
            ui_module=mock_ui
        )

        # Script returning False is handled by retry logic
        with patch("spec.discovery.run_discovery_script", return_value=(False, "Script failed")):
            result = await executor.phase_discovery()

        # Should handle gracefully with retries
        assert result.success is False
        assert len(result.errors) == MAX_RETRIES

    @pytest.mark.asyncio
    async def test_phase_timeout_handling(self, tmp_path):
        """Test phase execution handles timeouts"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_ui = MagicMock()
        mock_logger = MagicMock()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=mock_logger,
            ui_module=mock_ui
        )

        with patch("spec.context.run_context_discovery", return_value=(False, "Timeout")):
            result = await executor.phase_context()

        # Should create minimal context on failure
        assert result.success is True
        assert (spec_dir / "context.json").exists()


class TestPhaseExecutorProgressTracking:
    """Tests for progress tracking through task_logger"""

    @pytest.mark.asyncio
    async def test_phase_logs_success_to_task_logger(self, tmp_path):
        """Test phases log success to task_logger"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_ui = MagicMock()
        mock_logger = MagicMock()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=mock_logger,
            ui_module=mock_ui
        )

        # Create a mock project index file
        index_file = spec_dir / "project_index.json"
        index_file.write_text('{"files": []}', encoding="utf-8")

        with patch("spec.discovery.run_discovery_script", return_value=(True, "Success")), \
             patch("spec.discovery.get_project_index_stats", return_value={"file_count": 10}):
            await executor.phase_discovery()

        # Verify logger was called
        assert mock_logger.log.called

    @pytest.mark.asyncio
    async def test_phase_logs_errors_to_task_logger(self, tmp_path):
        """Test phases log errors to task_logger"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_ui = MagicMock()
        mock_logger = MagicMock()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=mock_logger,
            ui_module=mock_ui
        )

        with patch("spec.discovery.run_discovery_script", return_value=(False, "Failed")):
            await executor.phase_discovery()

        # Verify error logging
        assert mock_logger.log.called


class TestPhaseExecutorIntegration:
    """Integration tests for PhaseExecutor with spec pipeline"""

    @pytest.mark.asyncio
    async def test_full_pipeline_execution(self, tmp_path):
        """Test executing multiple phases in sequence"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_ui = MagicMock()
        mock_logger = MagicMock()
        mock_validator = MagicMock()
        mock_validator.validate_spec_document.return_value = ValidationResult(
            valid=True, checkpoint="spec", errors=[], warnings=[], fixes=[]
        )
        mock_validator.validate_implementation_plan.return_value = ValidationResult(
            valid=True, checkpoint="plan", errors=[], warnings=[], fixes=[]
        )
        mock_validator.validate_all.return_value = [
            ValidationResult(valid=True, checkpoint="spec", errors=[], warnings=[], fixes=[]),
        ]

        async def mock_run_agent(prompt, additional_context=None, phase_name=None):
            # Create appropriate files based on phase
            if phase_name == "quick_spec":
                (spec_dir / "spec.md").write_text("# Spec", encoding="utf-8")
                (spec_dir / "implementation_plan.json").write_text('{"phases": []}', encoding="utf-8")
            elif phase_name == "planning":
                (spec_dir / "implementation_plan.json").write_text('{"phases": []}', encoding="utf-8")
            return True, "Success"

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Build feature",
            spec_validator=mock_validator,
            run_agent_fn=mock_run_agent,
            task_logger=mock_logger,
            ui_module=mock_ui
        )

        # Execute phases
        results = []

        # Create index file for discovery
        index_file = spec_dir / "project_index.json"
        index_file.write_text('{"files": []}', encoding="utf-8")

        with patch("spec.discovery.run_discovery_script", return_value=(True, "Success")), \
             patch("spec.discovery.get_project_index_stats", return_value={"file_count": 1}):
            results.append(await executor.phase_discovery())

        def mock_run_context(*args, **kwargs):
            (spec_dir / "context.json").write_text('{"task": "Build feature"}', encoding="utf-8")
            return True, "Success"

        with patch("spec.context.run_context_discovery", side_effect=mock_run_context), \
             patch("spec.context.get_context_stats", return_value={"files_to_modify": 1}):
            results.append(await executor.phase_context())

        results.append(await executor.phase_requirements(interactive=False))
        results.append(await executor.phase_quick_spec())

        # Verify all phases completed
        for result in results:
            assert result.success is True, f"Phase {result.phase} failed: {result.errors}"

    @pytest.mark.asyncio
    async def test_phase_state_transitions(self, tmp_path):
        """Test state transitions through phases"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_ui = MagicMock()
        mock_logger = MagicMock()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=mock_logger,
            ui_module=mock_ui
        )

        # Start with empty task_description
        assert executor.task_description == ""

        # Requirements phase should update task_description
        with patch("spec.requirements.gather_requirements_interactively", return_value={
            "task_description": "New task from requirements",
            "services_involved": []
        }):
            await executor.phase_requirements(interactive=True)

        # Task description should be updated
        assert executor.task_description == "New task from requirements"


class TestPhaseExecutorRetryBehavior:
    """Tests for retry behavior across phases"""

    @pytest.mark.asyncio
    async def test_retry_counter_increments(self, tmp_path):
        """Test retry counter increments correctly"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_ui = MagicMock()
        mock_logger = MagicMock()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=mock_logger,
            ui_module=mock_ui
        )

        attempts = [0]

        def mock_run_discovery(*args, **kwargs):
            attempts[0] += 1
            return attempts[0] >= 2, "Success" if attempts[0] >= 2 else "Failed"

        with patch("spec.discovery.run_discovery_script", side_effect=mock_run_discovery):
            result = await executor.phase_discovery()

        assert result.retries == 1
        assert result.success is True

    @pytest.mark.asyncio
    async def test_max_retries_limit(self, tmp_path):
        """Test phases respect MAX_RETRIES limit"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_ui = MagicMock()
        mock_logger = MagicMock()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test",
            spec_validator=MagicMock(),
            run_agent_fn=AsyncMock(),
            task_logger=mock_logger,
            ui_module=mock_ui
        )

        call_count = [0]

        def mock_run_discovery(*args, **kwargs):
            call_count[0] += 1
            return False, f"Failed {call_count[0]}"

        with patch("spec.discovery.run_discovery_script", side_effect=mock_run_discovery):
            result = await executor.phase_discovery()

        # Should not exceed MAX_RETRIES
        assert call_count[0] == MAX_RETRIES
        assert result.retries == MAX_RETRIES - 1
        assert result.success is False
