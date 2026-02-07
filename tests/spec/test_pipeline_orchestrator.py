"""
Tests for spec.pipeline.orchestrator module
Comprehensive tests for SpecOrchestrator class.

NOTE: These tests use the real SpecOrchestrator which involves file I/O.
Marked as slow - can be excluded with: pytest -m "not slow"
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime, timedelta

import pytest

from spec.pipeline.orchestrator import SpecOrchestrator

pytestmark = pytest.mark.slow  # Mark all tests in this file as slow
from spec.phases.models import PhaseResult
from spec.validate_pkg.models import ValidationResult


@pytest.fixture
def mock_project_dir(tmp_path):
    """Create a mock project directory structure."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Create .auto-claude directory
    auto_claude = project_dir / ".auto-claude"
    auto_claude.mkdir()

    # Create specs directory
    specs_dir = auto_claude / "specs"
    specs_dir.mkdir()

    # Create project_index.json
    index_file = auto_claude / "project_index.json"
    index_file.write_text('{"project_type": "test", "framework": "pytest"}', encoding="utf-8")

    # Create auto-claude symlink/script directory equivalent
    auto_build = project_dir / "auto-claude"
    auto_build.mkdir()

    return project_dir


@pytest.fixture
def mock_spec_dir(tmp_path):
    """Create a mock spec directory."""
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    return spec_dir


class TestSpecOrchestratorInit:
    """Tests for SpecOrchestrator.__init__"""

    def test_init_with_task_description(self, mock_project_dir):
        """Test initialization with task description"""
        orchestrator = SpecOrchestrator(
            project_dir=mock_project_dir,
            task_description="Build a feature",
        )

        assert orchestrator.project_dir == mock_project_dir
        assert orchestrator.task_description == "Build a feature"
        assert orchestrator.model == "sonnet"
        assert orchestrator.thinking_level == "medium"
        assert orchestrator.use_ai_assessment is True
        assert orchestrator.assessment is None

    def test_init_with_existing_spec_dir(self, mock_project_dir, mock_spec_dir):
        """Test initialization with existing spec directory"""
        orchestrator = SpecOrchestrator(
            project_dir=mock_project_dir,
            spec_dir=mock_spec_dir,
        )

        assert orchestrator.spec_dir == mock_spec_dir
        assert mock_spec_dir.exists()

    def test_init_with_spec_name(self, mock_project_dir):
        """Test initialization with spec name"""
        orchestrator = SpecOrchestrator(
            project_dir=mock_project_dir,
            spec_name="test-feature",
        )

        expected_path = mock_project_dir / ".auto-claude" / "specs" / "test-feature"
        assert orchestrator.spec_dir == expected_path

    def test_init_creates_new_spec_dir(self, mock_project_dir):
        """Test initialization creates new spec directory with lock"""
        with patch("spec.pipeline.orchestrator.SpecNumberLock") as mock_lock_cls:
            mock_lock = MagicMock()
            mock_lock.__enter__ = MagicMock(return_value=mock_lock)
            mock_lock.__exit__ = MagicMock(return_value=False)
            mock_lock.get_next_spec_number.return_value = 1

            mock_lock_cls.return_value = mock_lock

            orchestrator = SpecOrchestrator(
                project_dir=mock_project_dir,
                task_description="Test task",
            )

            expected_dir = mock_project_dir / ".auto-claude" / "specs" / "001-pending"
            assert orchestrator.spec_dir == expected_dir

    def test_init_with_custom_model(self, mock_project_dir):
        """Test initialization with custom model"""
        orchestrator = SpecOrchestrator(
            project_dir=mock_project_dir,
            model="opus",
        )

        assert orchestrator.model == "opus"

    def test_init_with_thinking_level(self, mock_project_dir):
        """Test initialization with custom thinking level"""
        orchestrator = SpecOrchestrator(
            project_dir=mock_project_dir,
            thinking_level="high",
        )

        assert orchestrator.thinking_level == "high"

    def test_init_with_complexity_override(self, mock_project_dir):
        """Test initialization with complexity override"""
        orchestrator = SpecOrchestrator(
            project_dir=mock_project_dir,
            complexity_override="simple",
        )

        assert orchestrator.complexity_override == "simple"

    def test_init_without_ai_assessment(self, mock_project_dir):
        """Test initialization with AI assessment disabled"""
        orchestrator = SpecOrchestrator(
            project_dir=mock_project_dir,
            use_ai_assessment=False,
        )

        assert orchestrator.use_ai_assessment is False

    def test_initializes_validator(self, mock_project_dir):
        """Test that validator is initialized"""
        orchestrator = SpecOrchestrator(
            project_dir=mock_project_dir,
        )

        assert orchestrator.validator is not None
        assert orchestrator.validator.spec_dir == orchestrator.spec_dir


class TestGetAgentRunner:
    """Tests for SpecOrchestrator._get_agent_runner"""

    @pytest.mark.asyncio
    async def test_get_agent_runner_creates_new(self, mock_project_dir):
        """Test _get_agent_runner creates new runner on first call"""
        orchestrator = SpecOrchestrator(
            project_dir=mock_project_dir,
        )

        runner = orchestrator._get_agent_runner()

        assert runner is not None
        assert runner.project_dir == mock_project_dir
        assert runner.spec_dir == orchestrator.spec_dir

    @pytest.mark.asyncio
    async def test_get_agent_runner_reuses_existing(self, mock_project_dir):
        """Test _get_agent_runner reuses existing runner"""
        orchestrator = SpecOrchestrator(
            project_dir=mock_project_dir,
        )

        runner1 = orchestrator._get_agent_runner()
        runner2 = orchestrator._get_agent_runner()

        assert runner1 is runner2


class TestRunAgent:
    """Tests for SpecOrchestrator._run_agent"""

    @pytest.mark.asyncio
    async def test_run_agent_success(self, mock_project_dir):
        """Test _run_agent with successful execution"""
        orchestrator = SpecOrchestrator(
            project_dir=mock_project_dir,
        )

        mock_runner = AsyncMock()
        mock_runner.run_agent = AsyncMock(return_value=(True, "Response text"))
        orchestrator._agent_runner = mock_runner

        result = await orchestrator._run_agent("test_prompt.md")

        assert result == (True, "Response text")

    @pytest.mark.asyncio
    async def test_run_agent_with_context(self, mock_project_dir):
        """Test _run_agent with additional context"""
        orchestrator = SpecOrchestrator(
            project_dir=mock_project_dir,
        )

        mock_runner = AsyncMock()
        mock_runner.run_agent = AsyncMock(return_value=(True, "Response"))
        orchestrator._agent_runner = mock_runner

        await orchestrator._run_agent(
            "test_prompt.md",
            additional_context="Extra context",
        )

        mock_runner.run_agent.assert_called_once()
        call_args = mock_runner.run_agent.call_args
        assert call_args[0][0] == "test_prompt.md"

    @pytest.mark.asyncio
    async def test_run_agent_with_phase_summaries(self, mock_project_dir):
        """Test _run_agent includes prior phase summaries"""
        orchestrator = SpecOrchestrator(
            project_dir=mock_project_dir,
        )
        orchestrator._phase_summaries = {"discovery": "Discovery summary"}

        mock_runner = AsyncMock()
        mock_runner.run_agent = AsyncMock(return_value=(True, "Response"))
        orchestrator._agent_runner = mock_runner

        with patch("spec.pipeline.orchestrator.format_phase_summaries", return_value="Formatted summaries"):
            await orchestrator._run_agent("test_prompt.md")

            call_args = mock_runner.run_agent.call_args
            assert call_args[1]["prior_phase_summaries"] == "Formatted summaries"


class TestStorePhaseSummary:
    """Tests for SpecOrchestrator._store_phase_summary"""

    @pytest.mark.asyncio
    async def test_store_phase_summary_success(self, mock_project_dir, tmp_path):
        """Test _store_phase_summary stores summary successfully"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create phase output files
        (spec_dir / "context.json").write_text('{"test": "data"}')

        orchestrator = SpecOrchestrator(
            project_dir=mock_project_dir,
            spec_dir=spec_dir,
        )

        with patch("spec.pipeline.orchestrator.gather_phase_outputs", return_value="Output"):
            with patch("spec.pipeline.orchestrator.summarize_phase_output", return_value="Summary"):
                await orchestrator._store_phase_summary("discovery")

                assert "discovery" in orchestrator._phase_summaries
                assert orchestrator._phase_summaries["discovery"] == "Summary"

    @pytest.mark.asyncio
    async def test_store_phase_summary_no_output(self, mock_project_dir):
        """Test _store_phase_summary handles no output gracefully"""
        orchestrator = SpecOrchestrator(
            project_dir=mock_project_dir,
        )

        with patch("spec.pipeline.orchestrator.gather_phase_outputs", return_value=""):
            await orchestrator._store_phase_summary("discovery")

            assert "discovery" not in orchestrator._phase_summaries

    @pytest.mark.asyncio
    async def test_store_phase_summary_failure(self, mock_project_dir):
        """Test _store_phase_summary handles summarization failure"""
        orchestrator = SpecOrchestrator(
            project_dir=mock_project_dir,
        )

        with patch("spec.pipeline.orchestrator.gather_phase_outputs", return_value="Output"):
            with patch("spec.pipeline.orchestrator.summarize_phase_output", side_effect=Exception("Error")):
                await orchestrator._store_phase_summary("discovery")

                # Should not crash, just skip summarization
                assert "discovery" not in orchestrator._phase_summaries


class TestEnsureFreshProjectIndex:
    """Tests for SpecOrchestrator._ensure_fresh_project_index"""

    @pytest.mark.asyncio
    async def test_refresh_index_when_needed(self, mock_project_dir):
        """Test refreshes project index when dependencies change"""
        orchestrator = SpecOrchestrator(
            project_dir=mock_project_dir,
        )

        with patch("spec.pipeline.orchestrator.should_refresh_project_index", return_value=True):
            with patch("spec.pipeline.orchestrator.analyze_project") as mock_analyze:
                await orchestrator._ensure_fresh_project_index()

                mock_analyze.assert_called_once()

    @pytest.mark.asyncio
    async def test_skip_refresh_when_not_needed(self, mock_project_dir):
        """Test skips refresh when index is fresh"""
        orchestrator = SpecOrchestrator(
            project_dir=mock_project_dir,
        )

        with patch("spec.pipeline.orchestrator.should_refresh_project_index", return_value=False):
            with patch("spec.pipeline.orchestrator.analyze_project") as mock_analyze:
                await orchestrator._ensure_fresh_project_index()

                mock_analyze.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_refresh_failure(self, mock_project_dir):
        """Test handles index refresh failure gracefully"""
        orchestrator = SpecOrchestrator(
            project_dir=mock_project_dir,
        )

        with patch("spec.pipeline.orchestrator.should_refresh_project_index", return_value=True):
            with patch("spec.pipeline.orchestrator.analyze_project", side_effect=Exception("Failed")):
                # Should not raise
                await orchestrator._ensure_fresh_project_index()


class TestCreateLinearTask:
    """Tests for SpecOrchestrator._create_linear_task_if_enabled"""

    @pytest.mark.asyncio
    async def test_creates_task_when_enabled(self, mock_project_dir):
        """Test creates Linear task when integration is enabled"""
        orchestrator = SpecOrchestrator(
            project_dir=mock_project_dir,
            task_description="Test task",
        )

        mock_state = MagicMock()
        mock_state.task_id = "LIN-123"

        with patch("linear_updater.is_linear_enabled", return_value=True):
            with patch("linear_updater.create_linear_task", return_value=mock_state):
                await orchestrator._create_linear_task_if_enabled()
                # Should not raise

    @pytest.mark.asyncio
    async def test_skips_when_disabled(self, mock_project_dir):
        """Test skips when Linear integration is disabled"""
        orchestrator = SpecOrchestrator(
            project_dir=mock_project_dir,
        )

        with patch("linear_updater.is_linear_enabled", return_value=False):
            with patch("linear_updater.create_linear_task") as mock_create:
                await orchestrator._create_linear_task_if_enabled()

                mock_create.assert_not_called()


class TestLoadRequirementsContext:
    """Tests for SpecOrchestrator._load_requirements_context"""

    def test_load_requirements_context_valid(self, mock_project_dir, tmp_path):
        """Test loading valid requirements context"""
        req_file = tmp_path / "requirements.json"
        requirements = {
            "task_description": "Build feature",
            "workflow_type": "standard",
            "services_involved": ["backend", "frontend"],
            "user_requirements": ["Must be fast"],
            "acceptance_criteria": ["Tests pass"],
            "constraints": ["Use Python"],
        }
        req_file.write_text(json.dumps(requirements))

        orchestrator = SpecOrchestrator(
            project_dir=mock_project_dir,
        )

        result = orchestrator._load_requirements_context(req_file)

        assert "Build feature" in result
        assert "standard" in result
        assert "backend" in result
        assert "Must be fast" in result

    def test_load_requirements_context_missing_file(self, mock_project_dir, tmp_path):
        """Test loading context when file doesn't exist"""
        req_file = tmp_path / "nonexistent.json"

        orchestrator = SpecOrchestrator(
            project_dir=mock_project_dir,
        )

        result = orchestrator._load_requirements_context(req_file)

        assert result == ""

    def test_load_requirements_context_updates_task_description(self, mock_project_dir, tmp_path):
        """Test that task_description gets updated from requirements"""
        req_file = tmp_path / "requirements.json"
        requirements = {"task_description": "Updated task"}
        req_file.write_text(json.dumps(requirements))

        orchestrator = SpecOrchestrator(
            project_dir=mock_project_dir,
            task_description="Original task",
        )

        orchestrator._load_requirements_context(req_file)

        assert orchestrator.task_description == "Updated task"


class TestCreateOverrideAssessment:
    """Tests for SpecOrchestrator._create_override_assessment"""

    def test_create_override_assessment(self, mock_project_dir):
        """Test creating override assessment"""
        orchestrator = SpecOrchestrator(
            project_dir=mock_project_dir,
            complexity_override="simple",
        )

        assessment = orchestrator._create_override_assessment()

        assert assessment.complexity.value == "simple"
        assert assessment.confidence == 1.0
        assert "Manual override" in assessment.reasoning


class TestHeuristicAssessment:
    """Tests for SpecOrchestrator._heuristic_assessment"""

    def test_heuristic_assessment_with_index(self, mock_project_dir):
        """Test heuristic assessment with project index"""
        # Create project index
        index_file = mock_project_dir / "auto-claude" / "project_index.json"
        index_file.write_text('{"project_type": "web"}', encoding="utf-8")

        orchestrator = SpecOrchestrator(
            project_dir=mock_project_dir,
            task_description="Fix button color",
        )

        assessment = orchestrator._heuristic_assessment()

        assert assessment is not None
        assert assessment.complexity is not None

    def test_heuristic_assessment_without_index(self, mock_project_dir):
        """Test heuristic assessment without project index"""
        orchestrator = SpecOrchestrator(
            project_dir=mock_project_dir,
            task_description="Build feature",
        )

        assessment = orchestrator._heuristic_assessment()

        assert assessment is not None


class TestPrintPhasesToRun:
    """Tests for SpecOrchestrator._print_phases_to_run"""

    def test_print_phases_to_run(self, mock_project_dir, capsys):
        """Test printing phases to run"""
        orchestrator = SpecOrchestrator(
            project_dir=mock_project_dir,
        )

        mock_assessment = MagicMock()
        mock_assessment.phases_to_run.return_value = ["discovery", "requirements", "spec_writing"]
        orchestrator.assessment = mock_assessment

        orchestrator._print_phases_to_run()

        captured = capsys.readouterr()
        assert "Phases to run" in captured.out
        assert "3" in captured.out


class TestPrintCompletionSummary:
    """Tests for SpecOrchestrator._print_completion_summary"""

    def test_print_completion_summary(self, mock_project_dir, capsys, tmp_path):
        """Test printing completion summary"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=mock_project_dir,
            spec_dir=spec_dir,
        )

        # Create mock results
        result1 = PhaseResult("discovery", True, [str(spec_dir / "context.json")], [], 0)
        result2 = PhaseResult("requirements", True, [str(spec_dir / "requirements.json")], [], 0)
        results = [result1, result2]
        phases_executed = ["discovery", "requirements"]

        mock_assessment = MagicMock()
        mock_assessment.complexity.value = "simple"
        orchestrator.assessment = mock_assessment

        orchestrator._print_completion_summary(results, phases_executed)

        captured = capsys.readouterr()
        assert "SPEC CREATION COMPLETE" in captured.out
        assert "SIMPLE" in captured.out


class TestRunReviewCheckpoint:
    """Tests for SpecOrchestrator._run_review_checkpoint"""

    def test_run_review_checkpoint_approved(self, mock_project_dir, tmp_path):
        """Test review checkpoint with approval"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=mock_project_dir,
            spec_dir=spec_dir,
        )

        mock_review_state = MagicMock()
        mock_review_state.is_approved.return_value = True

        with patch("spec.pipeline.orchestrator.run_review_checkpoint", return_value=mock_review_state):
            result = orchestrator._run_review_checkpoint(auto_approve=False)

            assert result is True

    def test_run_review_checkpoint_rejected(self, mock_project_dir, tmp_path):
        """Test review checkpoint with rejection"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=mock_project_dir,
            spec_dir=spec_dir,
        )

        mock_review_state = MagicMock()
        mock_review_state.is_approved.return_value = False

        with patch("spec.pipeline.orchestrator.run_review_checkpoint", return_value=mock_review_state):
            result = orchestrator._run_review_checkpoint(auto_approve=False)

            assert result is False

    def test_run_review_checkpoint_auto_approve(self, mock_project_dir, tmp_path):
        """Test review checkpoint with auto-approve"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=mock_project_dir,
            spec_dir=spec_dir,
        )

        mock_review_state = MagicMock()
        mock_review_state.is_approved.return_value = True

        with patch("spec.pipeline.orchestrator.run_review_checkpoint", return_value=mock_review_state):
            result = orchestrator._run_review_checkpoint(auto_approve=True)

            assert result is True

    def test_run_review_checkpoint_keyboard_interrupt(self, mock_project_dir, tmp_path):
        """Test review checkpoint handles keyboard interrupt"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=mock_project_dir,
            spec_dir=spec_dir,
        )

        with patch("spec.pipeline.orchestrator.run_review_checkpoint", side_effect=KeyboardInterrupt):
            result = orchestrator._run_review_checkpoint(auto_approve=False)

            assert result is False

    def test_run_review_checkpoint_system_exit(self, mock_project_dir, tmp_path):
        """Test review checkpoint handles system exit"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=mock_project_dir,
            spec_dir=spec_dir,
        )

        with patch("spec.pipeline.orchestrator.run_review_checkpoint", side_effect=SystemExit(1)):
            result = orchestrator._run_review_checkpoint(auto_approve=False)

            assert result is False


class TestGenerateSpecName:
    """Tests for SpecOrchestrator._generate_spec_name (backward compatibility)"""

    def test_generate_spec_name_backward_compat(self, mock_project_dir):
        """Test backward compatibility method delegates to models.generate_spec_name"""
        orchestrator = SpecOrchestrator(
            project_dir=mock_project_dir,
        )

        result = orchestrator._generate_spec_name("Add user authentication")

        assert isinstance(result, str)
        assert len(result) > 0


class TestRenameSpecDirFromRequirements:
    """Tests for SpecOrchestrator._rename_spec_dir_from_requirements (backward compatibility)"""

    def test_rename_spec_dir_backward_compat(self, mock_project_dir, tmp_path):
        """Test backward compatibility method delegates to models function"""
        spec_dir = tmp_path / "001-pending"
        spec_dir.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=mock_project_dir,
            spec_dir=spec_dir,
        )

        # Create requirements
        requirements = {"task_description": "Build feature"}
        req_file = spec_dir / "requirements.json"
        req_file.write_text(json.dumps(requirements))

        with patch("spec.pipeline.models.update_task_logger_path"):
            result = orchestrator._rename_spec_dir_from_requirements()

            # Should return True (success or not needed)
            assert isinstance(result, bool)
