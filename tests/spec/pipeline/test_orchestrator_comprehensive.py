"""
Comprehensive tests for spec.pipeline.orchestrator module.

Additional tests to improve coverage for SpecOrchestrator class,
focusing on previously untested code paths.

NOTE: Tests SpecOrchestrator which involves async operations and file I/O.
Marked as slow - can be excluded with: pytest -m "not slow"
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call
from typing import Any

import pytest

pytestmark = pytest.mark.slow

from spec.pipeline.orchestrator import SpecOrchestrator
from spec.phases.models import PhaseResult
from spec.complexity import Complexity, ComplexityAssessment


class TestSpecOrchestratorStorePhaseSummaryEdgeCases:
    """Additional tests for _store_phase_summary edge cases."""

    @pytest.mark.asyncio
    async def test_store_phase_summary_no_outputs(self, tmp_path):
        """Test _store_phase_summary when gather_phase_outputs returns None."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
            spec_dir=spec_dir,
        )

        with patch("spec.pipeline.orchestrator.gather_phase_outputs", return_value=None):
            await orchestrator._store_phase_summary("discovery")

        # Should not store summary
        assert "discovery" not in orchestrator._phase_summaries

    @pytest.mark.asyncio
    async def test_store_phase_summary_empty_outputs(self, tmp_path):
        """Test _store_phase_summary when gather_phase_outputs returns empty."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
            spec_dir=spec_dir,
        )

        with patch("spec.pipeline.orchestrator.gather_phase_outputs", return_value=""):
            await orchestrator._store_phase_summary("discovery")

        # Should not store summary
        assert "discovery" not in orchestrator._phase_summaries

    @pytest.mark.asyncio
    async def test_store_phase_summary_summarize_returns_none(self, tmp_path):
        """Test _store_phase_summary when summarize_phase_output returns None."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
            spec_dir=spec_dir,
        )

        with patch("spec.pipeline.orchestrator.gather_phase_outputs", return_value="content"):
            with patch("spec.pipeline.orchestrator.summarize_phase_output", return_value=None):
                await orchestrator._store_phase_summary("discovery")

        # Should not store summary
        assert "discovery" not in orchestrator._phase_summaries


class TestSpecOrchestratorEnsureFreshProjectIndexErrors:
    """Tests for _ensure_fresh_project_index error handling."""

    @pytest.mark.asyncio
    async def test_ensure_fresh_project_index_analyze_project_fails(self, tmp_path, capsys):
        """Test _ensure_fresh_project_index when analyze_project fails."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
        )

        with patch("spec.pipeline.orchestrator.should_refresh_project_index", return_value=True):
            with patch("spec.pipeline.orchestrator.analyze_project", side_effect=Exception("Analysis failed")):
                await orchestrator._ensure_fresh_project_index()

        captured = capsys.readouterr()
        # Should print warning but not crash
        assert "failed" in captured.out.lower() or "warning" in captured.out.lower()

    @pytest.mark.asyncio
    async def test_ensure_fresh_project_index_no_index_and_no_refresh(self, tmp_path):
        """Test _ensure_fresh_project_index when no index exists and refresh not needed."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
        )

        with patch("spec.pipeline.orchestrator.should_refresh_project_index", return_value=False):
            await orchestrator._ensure_fresh_project_index()

        # Should complete without error


class TestSpecOrchestratorRunAiAssessment:
    """Tests for _run_ai_assessment method."""

    @pytest.mark.asyncio
    async def test_run_ai_assessment_returns_none_falls_back(self, tmp_path, capsys):
        """Test _run_ai_assessment falls back to heuristic when AI returns None."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task",
        )

        mock_logger = MagicMock()

        async def mock_ai_assessment(*args, **kwargs):
            return None

        with patch("spec.complexity.run_ai_complexity_assessment", side_effect=mock_ai_assessment):
            assessment = await orchestrator._run_ai_assessment(mock_logger)

        # Should fall back to heuristic
        assert assessment is not None
        assert isinstance(assessment, ComplexityAssessment)

        captured = capsys.readouterr()
        assert "heuristics" in captured.out.lower()

    @pytest.mark.asyncio
    async def test_run_ai_assessment_success(self, tmp_path):
        """Test _run_ai_assessment successful AI assessment."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task",
        )

        expected_assessment = ComplexityAssessment(
            complexity=Complexity.STANDARD,
            confidence=0.9,
            reasoning="AI reasoning",
        )

        mock_logger = MagicMock()

        async def mock_ai_assessment(*args, **kwargs):
            return expected_assessment

        with patch("spec.complexity.run_ai_complexity_assessment", side_effect=mock_ai_assessment):
            assessment = await orchestrator._run_ai_assessment(mock_logger)

        assert assessment == expected_assessment


class TestSpecOrchestratorCreateLinearTaskFailures:
    """Tests for _create_linear_task_if_enabled failure cases."""

    @pytest.mark.asyncio
    async def test_create_linear_task_returns_none(self, tmp_path, capsys):
        """Test _create_linear_task_if_enabled when create_linear_task returns None."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task",
        )

        async def mock_create_linear_task(*args, **kwargs):
            return None

        with patch("linear_updater.is_linear_enabled", return_value=True):
            with patch("linear_updater.create_linear_task", side_effect=mock_create_linear_task):
                await orchestrator._create_linear_task_if_enabled()

        captured = capsys.readouterr()
        assert "failed" in captured.out.lower() or "continuing" in captured.out.lower()


class TestSpecOrchestratorRunReviewCheckpointErrors:
    """Tests for _run_review_checkpoint error handling."""

    @pytest.mark.asyncio
    async def test_run_review_checkpoint_system_exit_nonzero(self, tmp_path, capsys):
        """Test _run_review_checkpoint with SystemExit non-zero code."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
            spec_dir=spec_dir,
        )

        with patch("spec.pipeline.orchestrator.run_review_checkpoint", side_effect=SystemExit(1)):
            result = orchestrator._run_review_checkpoint(auto_approve=False)

        assert result is False

    @pytest.mark.asyncio
    async def test_run_review_checkpoint_keyboard_interrupt(self, tmp_path, capsys):
        """Test _run_review_checkpoint with KeyboardInterrupt."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
            spec_dir=spec_dir,
        )

        with patch("spec.pipeline.orchestrator.run_review_checkpoint", side_effect=KeyboardInterrupt()):
            result = orchestrator._run_review_checkpoint(auto_approve=False)

        assert result is False

        captured = capsys.readouterr()
        assert "interrupted" in captured.out.lower()


class TestSpecOrchestratorRunPhaseFailures:
    """Tests for run() method when phases fail."""

    @pytest.mark.asyncio
    async def test_run_discovery_phase_failure(self, tmp_path):
        """Test run() when discovery phase fails."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task",
        )

        mock_logger = MagicMock()

        with patch("spec.pipeline.orchestrator.get_task_logger", return_value=mock_logger):
            with patch("spec.pipeline.orchestrator.TaskEventEmitter"):
                with patch("spec.pipeline.orchestrator.should_refresh_project_index", return_value=False):
                    # Mock phase executor to fail discovery
                    with patch("spec.pipeline.orchestrator.phases.PhaseExecutor") as MockExecutor:
                        mock_executor = MagicMock()
                        mock_executor.phase_discovery = AsyncMock(return_value=PhaseResult(
                            "discovery", False, [], ["Discovery error"], 0
                        ))
                        MockExecutor.return_value = mock_executor

                        result = await orchestrator.run(interactive=False)

        assert result is False
        mock_logger.end_phase.assert_called()

    @pytest.mark.asyncio
    async def test_run_requirements_phase_failure(self, tmp_path):
        """Test run() when requirements phase fails."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task",
        )

        mock_logger = MagicMock()

        with patch("spec.pipeline.orchestrator.get_task_logger", return_value=mock_logger):
            with patch("spec.pipeline.orchestrator.TaskEventEmitter"):
                with patch("spec.pipeline.orchestrator.should_refresh_project_index", return_value=False):
                    with patch("spec.pipeline.orchestrator.phases.PhaseExecutor") as MockExecutor:
                        mock_executor = MagicMock()
                        # Discovery succeeds, requirements fails
                        mock_executor.phase_discovery = AsyncMock(return_value=PhaseResult(
                            "discovery", True, ["project_index.json"], [], 0
                        ))
                        mock_executor.phase_requirements = AsyncMock(return_value=PhaseResult(
                            "requirements", False, [], ["Requirements error"], 0
                        ))
                        MockExecutor.return_value = mock_executor

                        with patch.object(orchestrator, "_store_phase_summary", new_callable=AsyncMock):
                            result = await orchestrator.run(interactive=False)

        assert result is False

    @pytest.mark.asyncio
    async def test_run_complexity_assessment_failure(self, tmp_path):
        """Test run() when complexity assessment fails."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task",
            use_ai_assessment=False,  # Use heuristic to avoid AI
        )

        mock_logger = MagicMock()

        with patch("spec.pipeline.orchestrator.get_task_logger", return_value=mock_logger):
            with patch("spec.pipeline.orchestrator.TaskEventEmitter"):
                with patch("spec.pipeline.orchestrator.should_refresh_project_index", return_value=False):
                    with patch("spec.pipeline.orchestrator.phases.PhaseExecutor") as MockExecutor:
                        mock_executor = MagicMock()
                        mock_executor.phase_discovery = AsyncMock(return_value=PhaseResult(
                            "discovery", True, ["project_index.json"], [], 0
                        ))
                        mock_executor.phase_requirements = AsyncMock(return_value=PhaseResult(
                            "requirements", True, ["requirements.json"], [], 0
                        ))
                        MockExecutor.return_value = mock_executor

                        # Mock _phase_complexity_assessment_with_requirements to fail
                        with patch.object(orchestrator, "_phase_complexity_assessment_with_requirements", new_callable=AsyncMock, return_value=PhaseResult(
                            "complexity_assessment", False, [], ["Assessment error"], 0
                        )):
                            with patch.object(orchestrator, "_store_phase_summary", new_callable=AsyncMock):
                                with patch("spec.pipeline.orchestrator.rename_spec_dir_from_requirements", return_value=True):
                                    result = await orchestrator.run(interactive=False)

        assert result is False


class TestSpecOrchestratorRunMainLoopPhases:
    """Tests for main phase execution loop in run()."""

    @pytest.mark.asyncio
    async def test_run_unknown_phase_skipped(self, tmp_path, capsys):
        """Test run() skips unknown phases."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task",
            complexity_override="simple",
        )

        # Set up assessment with an unknown phase
        orchestrator.assessment = ComplexityAssessment(
            complexity=Complexity.SIMPLE,
            confidence=1.0,
            reasoning="Test",
        )

        # Mock phases_to_run to include unknown phase
        with patch.object(orchestrator.assessment, "phases_to_run", return_value=[
            "discovery", "requirements", "unknown_phase"
        ]):
            mock_logger = MagicMock()

            with patch("spec.pipeline.orchestrator.get_task_logger", return_value=mock_logger):
                with patch("spec.pipeline.orchestrator.TaskEventEmitter"):
                    with patch("spec.pipeline.orchestrator.should_refresh_project_index", return_value=False):
                        with patch("spec.pipeline.orchestrator.phases.PhaseExecutor") as MockExecutor:
                            mock_executor = MagicMock()
                            mock_executor.phase_discovery = AsyncMock(return_value=PhaseResult(
                                "discovery", True, [], [], 0
                            ))
                            mock_executor.phase_requirements = AsyncMock(return_value=PhaseResult(
                                "requirements", True, [], [], 0
                            ))
                            MockExecutor.return_value = mock_executor

                            with patch.object(orchestrator, "_phase_complexity_assessment_with_requirements", new_callable=AsyncMock, return_value=PhaseResult("complexity_assessment", True, [], [], 0)):
                                with patch.object(orchestrator, "_store_phase_summary", new_callable=AsyncMock):
                                    with patch("spec.pipeline.orchestrator.rename_spec_dir_from_requirements"):
                                        with patch("spec.pipeline.orchestrator.requirements.load_requirements", return_value={}):
                                            with patch.object(orchestrator, "_create_linear_task_if_enabled", new_callable=AsyncMock):
                                                with patch("spec.pipeline.orchestrator.run_review_checkpoint", return_value=MagicMock(is_approved=lambda: True)):
                                                    result = await orchestrator.run(interactive=False)

        # Should complete despite unknown phase
        captured = capsys.readouterr()
        assert "unknown" in captured.out.lower() or "skipping" in captured.out.lower()

    @pytest.mark.asyncio
    async def test_run_phase_in_loop_failure(self, tmp_path):
        """Test run() when a phase in the main loop fails."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task",
            complexity_override="simple",
        )

        orchestrator.assessment = ComplexityAssessment(
            complexity=Complexity.SIMPLE,
            confidence=1.0,
            reasoning="Test",
        )

        mock_logger = MagicMock()

        with patch("spec.pipeline.orchestrator.get_task_logger", return_value=mock_logger):
            with patch("spec.pipeline.orchestrator.TaskEventEmitter"):
                with patch("spec.pipeline.orchestrator.should_refresh_project_index", return_value=False):
                    with patch("spec.pipeline.orchestrator.phases.PhaseExecutor") as MockExecutor:
                        mock_executor = MagicMock()
                        # Set up all phase methods as AsyncMock to avoid "object MagicMock can't be used in 'await' expression"
                        mock_executor.phase_discovery = AsyncMock(return_value=PhaseResult(
                            "discovery", True, [], [], 0
                        ))
                        mock_executor.phase_requirements = AsyncMock(return_value=PhaseResult(
                            "requirements", True, [], [], 0
                        ))
                        mock_executor.phase_historical_context = AsyncMock(return_value=PhaseResult(
                            "historical_context", True, [], [], 0
                        ))
                        # quick_spec phase fails
                        mock_executor.phase_quick_spec = AsyncMock(return_value=PhaseResult(
                            "quick_spec", False, [], ["Quick spec error"], 2
                        ))
                        mock_executor.phase_validation = AsyncMock(return_value=PhaseResult(
                            "validation", True, [], [], 0
                        ))
                        mock_executor.phase_research = AsyncMock(return_value=PhaseResult(
                            "research", True, [], [], 0
                        ))
                        mock_executor.phase_context = AsyncMock(return_value=PhaseResult(
                            "context", True, [], [], 0
                        ))
                        mock_executor.phase_spec_writing = AsyncMock(return_value=PhaseResult(
                            "spec_writing", True, [], [], 0
                        ))
                        mock_executor.phase_self_critique = AsyncMock(return_value=PhaseResult(
                            "self_critique", True, [], [], 0
                        ))
                        mock_executor.phase_planning = AsyncMock(return_value=PhaseResult(
                            "planning", True, [], [], 0
                        ))
                        MockExecutor.return_value = mock_executor

                        with patch.object(orchestrator, "_phase_complexity_assessment_with_requirements", new_callable=AsyncMock, return_value=PhaseResult("complexity_assessment", True, [], [], 0)):
                            with patch.object(orchestrator, "_store_phase_summary", new_callable=AsyncMock):
                                with patch("spec.pipeline.orchestrator.rename_spec_dir_from_requirements"):
                                    with patch("spec.pipeline.orchestrator.requirements.load_requirements", return_value={}):
                                        with patch.object(orchestrator, "_create_linear_task_if_enabled", new_callable=AsyncMock):
                                            result = await orchestrator.run(interactive=False)

        assert result is False


class TestSpecOrchestratorRunWithMetadata:
    """Tests for run() with task metadata."""

    @pytest.mark.asyncio
    async def test_run_with_require_review_before_coding(self, tmp_path):
        """Test run() with requireReviewBeforeCoding in metadata."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task",
            complexity_override="simple",
        )

        orchestrator.assessment = ComplexityAssessment(
            complexity=Complexity.SIMPLE,
            confidence=1.0,
            reasoning="Test",
        )

        # Create task_metadata.json
        task_metadata_file = spec_dir / "task_metadata.json"
        task_metadata_file.write_text(json.dumps({
            "requireReviewBeforeCoding": True
        }), encoding="utf-8")

        mock_logger = MagicMock()
        mock_emitter = MagicMock()

        with patch("spec.pipeline.orchestrator.get_task_logger", return_value=mock_logger):
            with patch("spec.pipeline.orchestrator.TaskEventEmitter.from_spec_dir", return_value=mock_emitter):
                with patch("spec.pipeline.orchestrator.should_refresh_project_index", return_value=False):
                    with patch("spec.pipeline.orchestrator.phases.PhaseExecutor") as MockExecutor:
                        mock_executor = MagicMock()
                        mock_executor.phase_discovery = AsyncMock(return_value=PhaseResult(
                            "discovery", True, [], [], 0
                        ))
                        mock_executor.phase_requirements = AsyncMock(return_value=PhaseResult(
                            "requirements", True, [], [], 0
                        ))
                        mock_executor.phase_historical_context = AsyncMock(return_value=PhaseResult(
                            "historical_context", True, [], [], 0
                        ))
                        mock_executor.phase_quick_spec = AsyncMock(return_value=PhaseResult(
                            "quick_spec", True, ["spec.md"], [], 0
                        ))
                        mock_executor.phase_validation = AsyncMock(return_value=PhaseResult(
                            "validation", True, [], [], 0
                        ))
                        MockExecutor.return_value = mock_executor

                        with patch.object(orchestrator, "_phase_complexity_assessment_with_requirements", new_callable=AsyncMock, return_value=PhaseResult("complexity_assessment", True, [], [], 0)):
                            with patch.object(orchestrator, "_store_phase_summary", new_callable=AsyncMock):
                                with patch("spec.pipeline.orchestrator.rename_spec_dir_from_requirements"):
                                    with patch("spec.pipeline.orchestrator.requirements.load_requirements", return_value={}):
                                        with patch.object(orchestrator, "_create_linear_task_if_enabled", new_callable=AsyncMock):
                                            with patch("spec.pipeline.orchestrator.run_review_checkpoint", return_value=MagicMock(is_approved=lambda: True)):
                                                result = await orchestrator.run(interactive=False)

        # Verify PLANNING_COMPLETE was emitted with requireReviewBeforeCoding=True
        assert mock_emitter.emit.called
        planning_complete_calls = [call for call in mock_emitter.emit.call_args_list
                                   if "PLANNING_COMPLETE" in str(call)]
        assert any(planning_complete_calls)


class TestSpecOrchestratorAssessmentPrinting:
    """Tests for assessment printing methods."""

    def test_print_assessment_info_with_needs_research(self, tmp_path, capsys):
        """Test _print_assessment_info with needs_research=True."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        orchestrator = SpecOrchestrator(project_dir=project_dir)

        assessment = ComplexityAssessment(
            complexity=Complexity.COMPLEX,
            confidence=0.85,
            reasoning="Complex task with multiple components",
            needs_research=True,
            needs_self_critique=False,
        )

        orchestrator._print_assessment_info(assessment)

        captured = capsys.readouterr()
        # Just verify it doesn't crash

    def test_print_assessment_info_with_needs_self_critique(self, tmp_path, capsys):
        """Test _print_assessment_info with needs_self_critique=True."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        orchestrator = SpecOrchestrator(project_dir=project_dir)

        assessment = ComplexityAssessment(
            complexity=Complexity.STANDARD,
            confidence=0.75,
            reasoning="Standard task",
            needs_research=False,
            needs_self_critique=True,
        )

        orchestrator._print_assessment_info(assessment)

        captured = capsys.readouterr()
        # Just verify it doesn't crash


class TestSpecOrchestratorBackwardCompatibilityRename:
    """Additional tests for backward compatibility rename method."""

    def test_rename_spec_dir_updates_internal_reference(self, tmp_path):
        """Test _rename_spec_dir_from_requirements updates self.spec_dir."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()
        specs_dir = auto_claude / "specs"
        specs_dir.mkdir()

        spec_dir = specs_dir / "001-pending"
        spec_dir.mkdir()

        req_file = spec_dir / "requirements.json"
        req_file.write_text(json.dumps({
            "task_description": "Build authentication system"
        }), encoding="utf-8")

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
            spec_dir=spec_dir,
        )

        original_spec_dir = orchestrator.spec_dir
        result = orchestrator._rename_spec_dir_from_requirements()

        assert result is True
        # spec_dir should be updated
        assert "pending" not in orchestrator.spec_dir.name
        assert orchestrator.spec_dir != original_spec_dir


class TestSpecOrchestratorComplexityAssessmentWithRequirements:
    """Tests for _phase_complexity_assessment_with_requirements."""

    @pytest.mark.asyncio
    async def test_phase_complexity_saves_assessment(self, tmp_path):
        """Test that assessment is saved to file."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task",
            complexity_override="standard",
        )

        result = await orchestrator._phase_complexity_assessment_with_requirements()

        assert result.success is True
        assert (spec_dir / "complexity_assessment.json").exists()
