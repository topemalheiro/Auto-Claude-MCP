"""Tests for DiscoveryPhaseMixin"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from spec.phases.discovery_phases import DiscoveryPhaseMixin
from spec.phases.models import PhaseResult


class MockDiscoveryExecutor(DiscoveryPhaseMixin):
    """Minimal mock executor for testing DiscoveryPhaseMixin"""

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


class TestPhaseDiscovery:
    """Tests for phase_discovery method"""

    @pytest.mark.asyncio
    async def test_discovery_success_with_existing_index(self, tmp_path):
        """Test successful discovery with existing auto-claude index"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / "auto-claude"
        auto_claude.mkdir()
        project_index = auto_claude / "project_index.json"
        project_index.write_text('{"project_type": "test"}', encoding="utf-8")

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = MockDiscoveryExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task"
        )

        result = await executor.phase_discovery()

        assert isinstance(result, PhaseResult)
        assert result.phase == "discovery"
        assert result.success is True
        assert len(result.output_files) == 1
        assert str(spec_dir / "project_index.json") in result.output_files

    @pytest.mark.asyncio
    async def test_discovery_with_script_run(self, tmp_path):
        """Test discovery running analyzer script"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / "auto-claude"
        auto_claude.mkdir()
        # Don't create index - script should create it

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = MockDiscoveryExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )

        # Mock the run_discovery_script to simulate script creating index
        with patch("spec.phases.discovery_phases.discovery.run_discovery_script") as mock_run:
            with patch("spec.phases.discovery_phases.discovery.get_project_index_stats") as mock_stats:
                mock_run.return_value = (True, "Created")
                mock_stats.return_value = {"file_count": 10}

                # Create the index file manually to simulate script
                index_file = spec_dir / "project_index.json"
                index_file.write_text('{"project_type": "analyzed"}', encoding="utf-8")

                result = await executor.phase_discovery()

        assert result.success is True

    @pytest.mark.asyncio
    async def test_discovery_retries_on_failure(self, tmp_path):
        """Test discovery retries on failure"""
        from spec.phases.models import MAX_RETRIES

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / "auto-claude"
        auto_claude.mkdir()

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = MockDiscoveryExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )

        with patch("spec.phases.discovery_phases.discovery.run_discovery_script") as mock_run:
            # Always fail
            mock_run.return_value = (False, "Error occurred")

            result = await executor.phase_discovery()

        assert result.success is False
        assert result.retries == MAX_RETRIES - 1  #最后一次尝试后的重试次数
        assert len(result.errors) == MAX_RETRIES

    @pytest.mark.asyncio
    async def test_discovery_logs_to_task_logger(self, tmp_path):
        """Test discovery logs success to task logger"""
        from task_logger import LogEntryType, LogPhase

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / "auto-claude"
        auto_claude.mkdir()
        project_index = auto_claude / "project_index.json"
        project_index.write_text('{"project_type": "test"}', encoding="utf-8")

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_logger = MagicMock()
        executor = MockDiscoveryExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )
        executor.task_logger = mock_logger

        await executor.phase_discovery()

        # Should log success
        mock_logger.log.assert_called()

    @pytest.mark.asyncio
    async def test_discovery_logs_failure(self, tmp_path):
        """Test discovery logs failures to task logger"""
        from task_logger import LogEntryType, LogPhase

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / "auto-claude"
        auto_claude.mkdir()

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_logger = MagicMock()
        executor = MockDiscoveryExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )
        executor.task_logger = mock_logger

        with patch("spec.phases.discovery_phases.discovery.run_discovery_script") as mock_run:
            mock_run.return_value = (False, "Script error")

            await executor.phase_discovery()

        # Should log errors for each attempt
        assert mock_logger.log.call_count >= 1


class TestPhaseContext:
    """Tests for phase_context method"""

    @pytest.mark.asyncio
    async def test_context_already_exists(self, tmp_path):
        """Test context when context.json already exists"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        context_file = spec_dir / "context.json"
        context_file.write_text('{"task": "test"}', encoding="utf-8")

        executor = MockDiscoveryExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task"
        )

        result = await executor.phase_context()

        assert result.success is True
        assert result.retries == 0
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_context_runs_discovery_success(self, tmp_path):
        """Test context runs discovery script successfully"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = MockDiscoveryExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Build API endpoint"
        )

        with patch("spec.phases.discovery_phases.context.run_context_discovery") as mock_run:
            with patch("spec.phases.discovery_phases.context.get_context_stats") as mock_stats:
                mock_run.return_value = (True, "Created context")
                mock_stats.return_value = {
                    "files_to_modify": 5,
                    "files_to_reference": 3
                }

                # Create the context file
                context_file = spec_dir / "context.json"
                context_file.write_text('{"task": "Build API endpoint"}', encoding="utf-8")

                result = await executor.phase_context()

        assert result.success is True
        assert result.retries == 0

    @pytest.mark.asyncio
    async def test_context_creates_minimal_on_failure(self, tmp_path):
        """Test context creates minimal context when script fails"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = MockDiscoveryExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task"
        )

        with patch("spec.phases.discovery_phases.context.run_context_discovery") as mock_run:
            mock_run.return_value = (False, "Script failed")

            with patch("spec.phases.discovery_phases.context.create_minimal_context") as mock_minimal:
                result = await executor.phase_context()

                # Should create minimal context
                mock_minimal.assert_called_once_with(
                    spec_dir,
                    "Test task",
                    []
                )

        assert result.success is True
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_context_uses_task_from_requirements(self, tmp_path):
        """Test context uses task description from requirements.json"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create requirements with different task description
        requirements_file = spec_dir / "requirements.json"
        req_data = {
            "task_description": "Detailed task from requirements",
            "services_involved": ["api", "database"]
        }
        requirements_file.write_text(json.dumps(req_data), encoding="utf-8")

        executor = MockDiscoveryExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Simple task"
        )

        with patch("spec.phases.discovery_phases.context.run_context_discovery") as mock_run:
            with patch("spec.phases.discovery_phases.context.get_context_stats") as mock_stats:
                mock_run.return_value = (True, "Success")
                mock_stats.return_value = {}

                result = await executor.phase_context()

                # Should use task from requirements
                call_args = mock_run.call_args
                assert "Detailed task from requirements" in str(call_args)

    @pytest.mark.asyncio
    async def test_context_with_services_from_requirements(self, tmp_path):
        """Test context passes services from requirements"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        requirements_file = spec_dir / "requirements.json"
        req_data = {
            "task_description": "Test task",
            "services_involved": ["frontend", "backend", "database"]
        }
        requirements_file.write_text(json.dumps(req_data), encoding="utf-8")

        executor = MockDiscoveryExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )

        with patch("spec.phases.discovery_phases.context.run_context_discovery") as mock_run:
            mock_run.return_value = (True, "Success")

            result = await executor.phase_context()

            # Should pass services list
            call_args = mock_run.call_args
            services = call_args[0][3]  # services is 4th arg
            assert services == ["frontend", "backend", "database"]

    @pytest.mark.asyncio
    async def test_context_retries_on_failure(self, tmp_path):
        """Test context retries on script failure"""
        from spec.phases.models import MAX_RETRIES

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = MockDiscoveryExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )

        with patch("spec.phases.discovery_phases.context.run_context_discovery") as mock_run:
            # Always fail
            mock_run.return_value = (False, "Failed")

            result = await executor.phase_context()

        assert result.success is True  # Creates minimal context
        assert result.retries == MAX_RETRIES
        assert len(result.errors) == MAX_RETRIES

    @pytest.mark.asyncio
    async def test_context_logs_stats_on_success(self, tmp_path):
        """Test context logs statistics on successful discovery"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = MockDiscoveryExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )
        mock_logger = MagicMock()
        executor.task_logger = mock_logger

        with patch("spec.phases.discovery_phases.context.run_context_discovery") as mock_run:
            with patch("spec.phases.discovery_phases.context.get_context_stats") as mock_stats:
                mock_run.return_value = (True, "Success")
                mock_stats.return_value = {
                    "files_to_modify": 10,
                    "files_to_reference": 5
                }

                result = await executor.phase_context()

        # Should log stats
        mock_logger.log.assert_called()


class TestDiscoveryPhaseMixinEdgeCases:
    """Edge case tests for DiscoveryPhaseMixin"""

    @pytest.mark.asyncio
    async def test_discovery_with_empty_project_dir(self, tmp_path):
        """Test discovery with empty project directory"""
        project_dir = tmp_path / "empty_project"
        project_dir.mkdir()
        # No auto-claude directory

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = MockDiscoveryExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )

        with patch("spec.phases.discovery_phases.discovery.run_discovery_script") as mock_run:
            mock_run.return_value = (True, "Created from analyzer")

            # Manually create the index
            index_file = spec_dir / "project_index.json"
            index_file.write_text('{}', encoding="utf-8")

            result = await executor.phase_discovery()

        assert result.success is True

    @pytest.mark.asyncio
    async def test_context_with_empty_task_description(self, tmp_path):
        """Test context with empty task description"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = MockDiscoveryExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description=""
        )

        with patch("spec.phases.discovery_phases.context.run_context_discovery") as mock_run:
            with patch("spec.phases.discovery_phases.context.create_minimal_context") as mock_minimal:
                mock_run.return_value = (False, "Failed")

                result = await executor.phase_context()

                # Should pass "unknown task" when empty
                mock_minimal.assert_called_once()
                call_args = mock_minimal.call_args[0]
                assert call_args[1] == "" or "unknown" in call_args[1]

    @pytest.mark.asyncio
    async def test_discovery_ui_messages(self, tmp_path):
        """Test discovery prints UI status messages"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / "auto-claude"
        auto_claude.mkdir()
        project_index = auto_claude / "project_index.json"
        project_index.write_text('{"project_type": "test"}', encoding="utf-8")

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_ui = MagicMock()
        executor = MockDiscoveryExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )
        executor.ui = mock_ui

        await executor.phase_discovery()

        # Should print status message
        mock_ui.print_status.assert_called()

    @pytest.mark.asyncio
    async def test_context_ui_messages_on_retry(self, tmp_path):
        """Test context prints UI messages during retries"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_ui = MagicMock()
        executor = MockDiscoveryExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )
        executor.ui = mock_ui

        with patch("spec.phases.discovery_phases.context.run_context_discovery") as mock_run:
            # Fail first attempt
            mock_run.return_value = (False, "Failed")

            with patch("spec.phases.discovery_phases.context.create_minimal_context"):
                result = await executor.phase_context()

        # Should print retry messages
        assert mock_ui.print_status.call_count > 0

    @pytest.mark.asyncio
    async def test_discovery_with_invalid_existing_index(self, tmp_path):
        """Test discovery when existing index is invalid"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / "auto-claude"
        auto_claude.mkdir()
        project_index = auto_claude / "project_index.json"
        project_index.write_text('{invalid json}', encoding="utf-8")

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = MockDiscoveryExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )

        # Script should be run since copy will fail
        with patch("spec.phases.discovery_phases.discovery.run_discovery_script") as mock_run:
            mock_run.return_value = (True, "Ran script")

            # Create valid index
            index_file = spec_dir / "project_index.json"
            index_file.write_text('{"project_type": "valid"}', encoding="utf-8")

            result = await executor.phase_discovery()

        assert result.success is True
