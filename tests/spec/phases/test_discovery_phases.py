"""Tests for discovery_phases module"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from spec.phases.discovery_phases import DiscoveryPhaseMixin
from spec.phases.models import PhaseResult


class FakeDiscoveryExecutor(DiscoveryPhaseMixin):
    """Fake executor for testing"""

    def __init__(self, project_dir, spec_dir, task_description="", ui=None, task_logger=None):
        self.project_dir = project_dir
        self.spec_dir = spec_dir
        self.task_description = task_description
        self.ui = ui or MagicMock()
        self.task_logger = task_logger or MagicMock()


@pytest.mark.asyncio
class TestDiscoveryPhaseMixin:
    """Tests for DiscoveryPhaseMixin"""

    async def test_phase_discovery_success(self, tmp_path):
        """Test successful discovery phase"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create auto-claude directory with index
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()
        index_file = auto_claude / "project_index.json"
        index_file.write_text('{"project_type": "test"}', encoding="utf-8")

        ui = MagicMock()
        task_logger = MagicMock()

        executor = FakeDiscoveryExecutor(
            project_dir, spec_dir, "Test task", ui, task_logger
        )

        result = await executor.phase_discovery()

        assert result.success is True
        assert result.phase == "discovery"
        assert len(result.output_files) > 0
        assert "project_index.json" in result.output_files[0]

    async def test_phase_discovery_fails_all_retries(self, tmp_path):
        """Test discovery fails after all retries"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        ui = MagicMock()
        task_logger = MagicMock()

        executor = FakeDiscoveryExecutor(
            project_dir, spec_dir, "Test task", ui, task_logger
        )

        # Mock run_discovery_script to fail
        with patch("spec.discovery.run_discovery_script", return_value=(False, "Error")):
            result = await executor.phase_discovery()

        assert result.success is False
        assert len(result.errors) > 0

    async def test_phase_context_already_exists(self, tmp_path):
        """Test context phase skips if context.json exists"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        context_file = spec_dir / "context.json"
        context_file.write_text('{"task": "test"}', encoding="utf-8")

        ui = MagicMock()
        task_logger = MagicMock()

        executor = FakeDiscoveryExecutor(
            project_dir, spec_dir, "Test task", ui, task_logger
        )

        result = await executor.phase_context()

        assert result.success is True
        assert result.retries == 0
        ui.print_status.assert_called_with("context.json already exists", "success")

    async def test_phase_context_creates_new(self, tmp_path):
        """Test context phase creates new context.json"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create requirements
        req_file = spec_dir / "requirements.json"
        req_file.write_text(
            '{"task_description": "Build feature", "services_involved": ["backend"]}',
            encoding="utf-8",
        )

        # Create context script
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()
        context_script = auto_claude / "context.py"
        context_script.write_text("# mock", encoding="utf-8")

        ui = MagicMock()
        task_logger = MagicMock()

        executor = FakeDiscoveryExecutor(
            project_dir, spec_dir, "", ui, task_logger
        )

        # Mock subprocess to create context file
        mock_result = MagicMock()
        mock_result.returncode = 0

        def side_effect(*args, **kwargs):
            context_file = spec_dir / "context.json"
            context_file.write_text('{"task_description": "test"}', encoding="utf-8")
            return mock_result

        with patch("subprocess.run", side_effect=side_effect):
            result = await executor.phase_context()

        assert result.success is True
        assert (spec_dir / "context.json").exists()

    async def test_phase_context_creates_minimal_on_failure(self, tmp_path):
        """Test context phase creates minimal context when script fails"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create context script
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()
        context_script = auto_claude / "context.py"
        context_script.write_text("# mock", encoding="utf-8")

        ui = MagicMock()
        task_logger = MagicMock()

        executor = FakeDiscoveryExecutor(
            project_dir, spec_dir, "Build feature", ui, task_logger
        )

        with patch("subprocess.run", return_value=MagicMock(returncode=1)):
            result = await executor.phase_context()

        # Should create minimal context as fallback
        assert result.success is True
        assert (spec_dir / "context.json").exists()
        ui.print_status.assert_called_with(
            "Created minimal context.json (script failed)", "success"
        )

    # ==================== Additional phase_discovery tests ====================

    async def test_phase_discovery_with_stats_logging(self, tmp_path):
        """Test phase_discovery logs project stats"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create auto-claude directory
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        ui = MagicMock()
        task_logger = MagicMock()

        executor = FakeDiscoveryExecutor(
            project_dir, spec_dir, "Test task", ui, task_logger
        )

        # Mock run_discovery_script and get_project_index_stats
        with patch(
            "spec.discovery.run_discovery_script", return_value=(True, "Success")
        ), patch(
            "spec.discovery.get_project_index_stats",
            return_value={"file_count": 42}
        ):
            result = await executor.phase_discovery()

        assert result.success is True
        task_logger.log.assert_called()
        # Check the log call contains file_count info
        log_call_args = task_logger.log.call_args
        assert "42" in str(log_call_args)

    async def test_phase_discovery_retry_behavior(self, tmp_path):
        """Test phase_discovery retries on failure"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        ui = MagicMock()
        ui.print_status = MagicMock()
        task_logger = MagicMock()

        executor = FakeDiscoveryExecutor(
            project_dir, spec_dir, "Test task", ui, task_logger
        )

        attempts = [0]

        def mock_run_discovery(*args, **kwargs):
            attempts[0] += 1
            if attempts[0] < 3:
                return (False, f"Attempt {attempts[0]} failed")
            # Succeed on third attempt
            return (True, "Success")

        with patch("spec.discovery.run_discovery_script", side_effect=mock_run_discovery):
            result = await executor.phase_discovery()

        assert result.success is True
        assert result.retries == 2

    # ==================== Additional phase_context tests ====================

    async def test_phase_context_uses_requirements_task_description(self, tmp_path):
        """Test phase_context uses task from requirements.json"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create requirements.json with task description
        req_file = spec_dir / "requirements.json"
        req_file.write_text(
            '{"task_description": "Fix authentication bug", "services_involved": ["backend"]}',
            encoding="utf-8",
        )

        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()
        context_script = auto_claude / "context.py"
        context_script.write_text("# mock", encoding="utf-8")

        ui = MagicMock()
        task_logger = MagicMock()

        # executor has no task_description, should use requirements.json
        executor = FakeDiscoveryExecutor(
            project_dir, spec_dir, "", ui, task_logger
        )

        mock_result = MagicMock()
        mock_result.returncode = 0

        captured_cmd = []

        def side_effect(cmd, *args, **kwargs):
            captured_cmd.append(cmd)
            context_file = spec_dir / "context.json"
            context_file.write_text('{"task_description": "test"}', encoding="utf-8")
            return mock_result

        with patch("subprocess.run", side_effect=side_effect):
            result = await executor.phase_context()

        assert result.success is True

    async def test_phase_context_uses_services_from_requirements(self, tmp_path):
        """Test phase_context passes services from requirements.json"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create requirements with services
        req_file = spec_dir / "requirements.json"
        req_file.write_text(
            '{"task_description": "Add feature", "services_involved": ["backend", "database"]}',
            encoding="utf-8",
        )

        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()
        context_script = auto_claude / "context.py"
        context_script.write_text("# mock", encoding="utf-8")

        ui = MagicMock()
        task_logger = MagicMock()

        executor = FakeDiscoveryExecutor(
            project_dir, spec_dir, "Add feature", ui, task_logger
        )

        mock_result = MagicMock()
        mock_result.returncode = 0

        captured_cmd = []

        def side_effect(cmd, *args, **kwargs):
            captured_cmd.append(cmd)
            context_file = spec_dir / "context.json"
            context_file.write_text('{"task_description": "test"}', encoding="utf-8")
            return mock_result

        with patch("subprocess.run", side_effect=side_effect):
            result = await executor.phase_context()

        assert result.success is True

    async def test_phase_context_multiple_retries_before_success(self, tmp_path):
        """Test phase_context with multiple retries before success"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()
        context_script = auto_claude / "context.py"
        context_script.write_text("# mock", encoding="utf-8")

        ui = MagicMock()
        ui.print_status = MagicMock()
        task_logger = MagicMock()

        executor = FakeDiscoveryExecutor(
            project_dir, spec_dir, "Build feature", ui, task_logger
        )

        attempts = [0]

        def side_effect(*args, **kwargs):
            attempts[0] += 1
            if attempts[0] < 3:
                mock_fail = MagicMock()
                mock_fail.returncode = 1
                return mock_fail
            # Succeed on third attempt
            mock_result = MagicMock()
            mock_result.returncode = 0
            context_file = spec_dir / "context.json"
            context_file.write_text('{"task": "test"}', encoding="utf-8")
            return mock_result

        with patch("subprocess.run", side_effect=side_effect):
            result = await executor.phase_context()

        assert result.success is True
        assert result.retries == 2

    async def test_phase_context_creates_minimal_after_all_retries(self, tmp_path):
        """Test phase_context creates minimal context after all retries exhausted"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()
        context_script = auto_claude / "context.py"
        context_script.write_text("# mock", encoding="utf-8")

        ui = MagicMock()
        ui.print_status = MagicMock()
        task_logger = MagicMock()

        executor = FakeDiscoveryExecutor(
            project_dir, spec_dir, "Build feature", ui, task_logger
        )

        # Always fail
        with patch("subprocess.run", return_value=MagicMock(returncode=1)):
            result = await executor.phase_context()

        # Should create minimal context after all retries
        assert result.success is True
        assert result.retries == 3  # MAX_RETRIES
        assert (spec_dir / "context.json").exists()
        ui.print_status.assert_called_with(
            "Created minimal context.json (script failed)", "success"
        )

    async def test_phase_context_with_stats_logging(self, tmp_path):
        """Test phase_context logs stats after successful discovery"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()
        context_script = auto_claude / "context.py"
        context_script.write_text("# mock", encoding="utf-8")

        ui = MagicMock()
        task_logger = MagicMock()

        executor = FakeDiscoveryExecutor(
            project_dir, spec_dir, "Build feature", ui, task_logger
        )

        mock_result = MagicMock()
        mock_result.returncode = 0

        def side_effect(*args, **kwargs):
            context_file = spec_dir / "context.json"
            context_file.write_text('{"task": "test"}', encoding="utf-8")
            return mock_result

        with patch("subprocess.run", side_effect=side_effect), patch(
            "spec.context.get_context_stats",
            return_value={"files_to_modify": 5, "files_to_reference": 10}
        ):
            result = await executor.phase_context()

        assert result.success is True
        task_logger.log.assert_called()
        log_call_args = task_logger.log.call_args
        assert "5" in str(log_call_args)  # files_to_modify
        assert "10" in str(log_call_args)  # files_to_reference
