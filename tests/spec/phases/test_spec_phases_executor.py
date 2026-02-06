"""
Tests for spec.phases.executor module
Comprehensive tests for PhaseExecutor class.
"""

from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from spec.phases.executor import PhaseExecutor
from spec.phases.models import PhaseResult
from spec.validate_pkg.models import ValidationResult


class FakePhaseExecutor(PhaseExecutor):
    """Fake executor with access to _run_script for testing"""

    def _run_script(self, script: str, args: list) -> tuple[bool, str]:
        """Public wrapper for testing _run_script"""
        return super()._run_script(script, args)


class TestPhaseExecutorInit:
    """Tests for PhaseExecutor.__init__"""

    def test_init_basic(self, tmp_path):
        """Test basic initialization"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_validator = MagicMock()
        mock_run_agent = AsyncMock()
        mock_task_logger = MagicMock()
        mock_ui = MagicMock()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Build feature",
            spec_validator=mock_validator,
            run_agent_fn=mock_run_agent,
            task_logger=mock_task_logger,
            ui_module=mock_ui,
        )

        assert executor.project_dir == project_dir
        assert executor.spec_dir == spec_dir
        assert executor.task_description == "Build feature"
        assert executor.spec_validator is mock_validator
        assert executor.run_agent_fn is mock_run_agent
        assert executor.task_logger is mock_task_logger
        assert executor.ui is mock_ui

    def test_init_with_empty_task_description(self, tmp_path):
        """Test initialization with empty task description"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_validator = MagicMock()
        mock_run_agent = AsyncMock()
        mock_task_logger = MagicMock()
        mock_ui = MagicMock()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="",
            spec_validator=mock_validator,
            run_agent_fn=mock_run_agent,
            task_logger=mock_task_logger,
            ui_module=mock_ui,
        )

        assert executor.task_description == ""

    def test_init_with_none_task_description(self, tmp_path):
        """Test initialization with None task description"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_validator = MagicMock()
        mock_run_agent = AsyncMock()
        mock_task_logger = MagicMock()
        mock_ui = MagicMock()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description=None,
            spec_validator=mock_validator,
            run_agent_fn=mock_run_agent,
            task_logger=mock_task_logger,
            ui_module=mock_ui,
        )

        assert executor.task_description is None


class TestPhaseExecutorRunScript:
    """Tests for PhaseExecutor._run_script"""

    def test_run_script_success(self, tmp_path):
        """Test _run_script with successful execution"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Create the script
        auto_build = project_dir / ".auto-claude"
        auto_build.mkdir()
        script_path = auto_build / "test_script.py"
        script_path.write_text('print("Success")', encoding="utf-8")

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_validator = MagicMock()
        mock_task_logger = MagicMock()
        mock_ui = MagicMock()

        executor = FakePhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="",
            spec_validator=mock_validator,
            run_agent_fn=AsyncMock(),
            task_logger=mock_task_logger,
            ui_module=mock_ui,
        )

        success, output = executor._run_script("test_script.py", [])

        assert success is True
        assert "Success" in output

    def test_run_script_with_args(self, tmp_path):
        """Test _run_script with arguments"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Create the script
        auto_build = project_dir / ".auto-claude"
        auto_build.mkdir()
        script_path = auto_build / "test_script.py"
        script_path.write_text(
            'import sys; print("Args:", sys.argv[1:])', encoding="utf-8"
        )

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_validator = MagicMock()
        mock_task_logger = MagicMock()
        mock_ui = MagicMock()

        executor = FakePhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="",
            spec_validator=mock_validator,
            run_agent_fn=AsyncMock(),
            task_logger=mock_task_logger,
            ui_module=mock_ui,
        )

        success, output = executor._run_script("test_script.py", ["--arg1", "--arg2"])

        assert success is True
        assert "--arg1" in output
        assert "--arg2" in output

    def test_run_script_not_found(self, tmp_path):
        """Test _run_script when script doesn't exist"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_validator = MagicMock()
        mock_task_logger = MagicMock()
        mock_ui = MagicMock()

        executor = FakePhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="",
            spec_validator=mock_validator,
            run_agent_fn=AsyncMock(),
            task_logger=mock_task_logger,
            ui_module=mock_ui,
        )

        success, output = executor._run_script("nonexistent.py", [])

        assert success is False
        assert "not found" in output.lower()

    def test_run_script_failure(self, tmp_path):
        """Test _run_script when script fails"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Create a script that fails
        auto_build = project_dir / ".auto-claude"
        auto_build.mkdir()
        script_path = auto_build / "failing_script.py"
        script_path.write_text('import sys; sys.exit(1)', encoding="utf-8")

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_validator = MagicMock()
        mock_task_logger = MagicMock()
        mock_ui = MagicMock()

        executor = FakePhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="",
            spec_validator=mock_validator,
            run_agent_fn=AsyncMock(),
            task_logger=mock_task_logger,
            ui_module=mock_ui,
        )

        success, output = executor._run_script("failing_script.py", [])

        assert success is False

    def test_run_script_timeout(self, tmp_path):
        """Test _run_script when script times out"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Create a script that runs indefinitely
        auto_build = project_dir / ".auto-claude"
        auto_build.mkdir()
        script_path = auto_build / "timeout_script.py"
        script_path.write_text('import time; time.sleep(400)', encoding="utf-8")

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_validator = MagicMock()
        mock_task_logger = MagicMock()
        mock_ui = MagicMock()

        executor = FakePhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="",
            spec_validator=mock_validator,
            run_agent_fn=AsyncMock(),
            task_logger=mock_task_logger,
            ui_module=mock_ui,
        )

        # The run_script uses a 300 second timeout, we'll simulate timeout
        with patch("subprocess.run") as mock_run:
            import subprocess
            mock_run.side_effect = subprocess.TimeoutExpired("timeout_script.py", 300)

            success, output = executor._run_script("timeout_script.py", [])

            assert success is False
            assert "timed out" in output.lower()

    def test_run_script_exception(self, tmp_path):
        """Test _run_script handles exceptions"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Create the script so it passes the existence check
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()
        script_path = auto_claude / "exception_script.py"
        script_path.write_text('print("Hello")', encoding="utf-8")

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_validator = MagicMock()
        mock_task_logger = MagicMock()
        mock_ui = MagicMock()

        executor = FakePhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="",
            spec_validator=mock_validator,
            run_agent_fn=AsyncMock(),
            task_logger=mock_task_logger,
            ui_module=mock_ui,
        )

        with patch("subprocess.run", side_effect=Exception("Unexpected error")):
            success, output = executor._run_script("exception_script.py", [])

            assert success is False
            assert "Unexpected error" in output


class TestPhaseExecutorHasAllMixins:
    """Tests that PhaseExecutor has all expected mixin methods"""

    @pytest.mark.asyncio
    async def test_has_discovery_methods(self, tmp_path):
        """Test PhaseExecutor has discovery phase methods"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_validator = MagicMock()
        mock_run_agent = AsyncMock()
        mock_task_logger = MagicMock()
        mock_ui = MagicMock()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="",
            spec_validator=mock_validator,
            run_agent_fn=mock_run_agent,
            task_logger=mock_task_logger,
            ui_module=mock_ui,
        )

        # Check for discovery methods
        assert hasattr(executor, "phase_discovery")
        assert hasattr(executor, "phase_context")

    @pytest.mark.asyncio
    async def test_has_requirements_methods(self, tmp_path):
        """Test PhaseExecutor has requirements phase methods"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_validator = MagicMock()
        mock_run_agent = AsyncMock()
        mock_task_logger = MagicMock()
        mock_ui = MagicMock()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="",
            spec_validator=mock_validator,
            run_agent_fn=mock_run_agent,
            task_logger=mock_task_logger,
            ui_module=mock_ui,
        )

        # Check for requirements methods
        assert hasattr(executor, "phase_requirements")
        assert hasattr(executor, "phase_historical_context")
        assert hasattr(executor, "phase_research")

    @pytest.mark.asyncio
    async def test_has_spec_methods(self, tmp_path):
        """Test PhaseExecutor has spec phase methods"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_validator = MagicMock()
        mock_run_agent = AsyncMock()
        mock_task_logger = MagicMock()
        mock_ui = MagicMock()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="",
            spec_validator=mock_validator,
            run_agent_fn=mock_run_agent,
            task_logger=mock_task_logger,
            ui_module=mock_ui,
        )

        # Check for spec methods
        assert hasattr(executor, "phase_quick_spec")
        assert hasattr(executor, "phase_spec_writing")
        assert hasattr(executor, "phase_self_critique")

    @pytest.mark.asyncio
    async def test_has_planning_methods(self, tmp_path):
        """Test PhaseExecutor has planning phase methods"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_validator = MagicMock()
        mock_run_agent = AsyncMock()
        mock_task_logger = MagicMock()
        mock_ui = MagicMock()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="",
            spec_validator=mock_validator,
            run_agent_fn=mock_run_agent,
            task_logger=mock_task_logger,
            ui_module=mock_ui,
        )

        # Check for planning methods
        assert hasattr(executor, "phase_planning")
        assert hasattr(executor, "phase_validation")


class TestPhaseExecutorIntegration:
    """Integration tests for PhaseExecutor with all mixins"""

    @pytest.mark.asyncio
    async def test_all_phase_methods_callable(self, tmp_path):
        """Test that all phase methods are callable"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create required files
        (spec_dir / "context.json").write_text('{"task": "test"}')
        (spec_dir / "requirements.json").write_text('{"task_description": "test"}')

        mock_validator = MagicMock()
        mock_run_agent = AsyncMock(return_value=(True, "Response"))
        mock_task_logger = MagicMock()
        mock_ui = MagicMock()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task",
            spec_validator=mock_validator,
            run_agent_fn=mock_run_agent,
            task_logger=mock_task_logger,
            ui_module=mock_ui,
        )

        # Verify all phase methods exist and are callable
        phase_methods = [
            "phase_discovery",
            "phase_context",
            "phase_requirements",
            "phase_historical_context",
            "phase_research",
            "phase_quick_spec",
            "phase_spec_writing",
            "phase_self_critique",
            "phase_planning",
            "phase_validation",
        ]

        for method_name in phase_methods:
            assert hasattr(executor, method_name)
            method = getattr(executor, method_name)
            assert callable(method)
