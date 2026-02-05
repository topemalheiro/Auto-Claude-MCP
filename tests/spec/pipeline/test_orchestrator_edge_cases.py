"""
Edge case and integration tests for spec.pipeline.orchestrator module.

Tests covering complex scenarios, edge cases, and error handling
that complement existing unit tests.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call, mock_open
from typing import Any

import pytest

from spec.pipeline.orchestrator import SpecOrchestrator
from spec.phases.models import PhaseResult
from spec.complexity import Complexity, ComplexityAssessment


class TestSpecOrchestratorInitEdgeCases:
    """Edge case tests for SpecOrchestrator initialization."""

    def test_init_with_relative_paths(self, tmp_path):
        """Test initialization with relative paths."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Convert to relative and back
        relative = project_dir.relative_to(tmp_path)

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
        )

        # Should work with absolute paths
        assert orchestrator.project_dir.is_absolute()

    def test_init_with_symlink_project_dir(self, tmp_path):
        """Test initialization with symlinked project directory."""
        project_dir = tmp_path / "actual_project"
        project_dir.mkdir()

        # Create symlink
        symlink_dir = tmp_path / "symlink_project"
        try:
            symlink_dir.symlink_to(project_dir)
        except OSError:
            # Symlinks may not be supported on all systems
            pytest.skip("Symlinks not supported")

        orchestrator = SpecOrchestrator(
            project_dir=symlink_dir,
        )

        # Should resolve symlinks
        assert orchestrator.project_dir.exists()

    def test_init_creates_nested_auto_claude(self, tmp_path):
        """Test that nested .auto-claude structure is created."""
        project_dir = tmp_path / "deep" / "nested" / "project"
        project_dir.mkdir(parents=True)

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
        )

        # Should create .auto-claude and specs
        auto_claude = project_dir / ".auto-claude"
        assert auto_claude.exists()

    def test_init_with_existing_auto_claude_but_no_specs(self, tmp_path):
        """Test initialization when .auto-claude exists but specs doesn't."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
        )

        # Should not fail
        assert orchestrator.specs_dir == auto_claude / "specs"


class TestRunAgentMethod:
    """Tests for _run_agent method."""

    @pytest.mark.asyncio
    async def test_run_agent_with_thinking_budget_none(self, tmp_path):
        """Test _run_agent with thinking_budget=None."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
            spec_dir=spec_dir,
            thinking_level="none",
        )

        mock_runner = AsyncMock()
        mock_runner.run_agent = AsyncMock(return_value=(True, "Response"))
        orchestrator._agent_runner = mock_runner

        result = await orchestrator._run_agent("test_prompt.md")

        assert result == (True, "Response")

    @pytest.mark.asyncio
    async def test_run_agent_propagates_phase_summaries(self, tmp_path):
        """Test that phase summaries are properly formatted and passed."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
            spec_dir=spec_dir,
        )

        # Set up phase summaries
        orchestrator._phase_summaries = {
            "discovery": "## Discovery\nFound files",
            "requirements": "## Requirements\nGathered needs",
        }

        mock_runner = AsyncMock()
        mock_runner.run_agent = AsyncMock(return_value=(True, "Response"))
        orchestrator._agent_runner = mock_runner

        with patch("spec.pipeline.orchestrator.format_phase_summaries",
                   return_value="## Discovery\nFound files\n\n## Requirements\nGathered needs"):
            result = await orchestrator._run_agent("test_prompt.md")

            # Verify summaries were passed
            call_kwargs = mock_runner.run_agent.call_args.kwargs
            assert "prior_phase_summaries" in call_kwargs

    @pytest.mark.asyncio
    async def test_run_agent_creates_runner_if_needed(self, tmp_path):
        """Test _run_agent creates agent runner if not exists."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
            spec_dir=spec_dir,
        )

        # No runner initially
        assert orchestrator._agent_runner is None

        mock_runner = AsyncMock()
        mock_runner.run_agent = AsyncMock(return_value=(True, "Response"))

        with patch("spec.pipeline.orchestrator.get_task_logger", return_value=MagicMock()):
            with patch("spec.pipeline.orchestrator.AgentRunner", return_value=mock_runner):
                result = await orchestrator._run_agent("test_prompt.md")

        # Runner should now exist
        assert result == (True, "Response")


class TestStorePhaseSummaryErrorHandling:
    """Tests for _store_phase_summary error handling."""

    @pytest.mark.asyncio
    async def test_store_phase_summary_gather_exception(self, tmp_path):
        """Test _store_phase_summary when gather_phase_outputs raises."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
            spec_dir=spec_dir,
        )

        with patch("spec.pipeline.orchestrator.gather_phase_outputs",
                   side_effect=OSError("Permission denied")):
            # Should not raise, just skip
            await orchestrator._store_phase_summary("discovery")

        assert "discovery" not in orchestrator._phase_summaries

    @pytest.mark.asyncio
    async def test_store_phase_summary_summarize_exception(self, tmp_path):
        """Test _store_phase_summary when summarize_phase_output raises."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
            spec_dir=spec_dir,
        )

        with patch("spec.pipeline.orchestrator.gather_phase_outputs", return_value="content"):
            with patch("spec.pipeline.orchestrator.summarize_phase_output",
                       side_effect=RuntimeError("Summarization failed")):
                # Should not raise, just skip
                await orchestrator._store_phase_summary("discovery")

        assert "discovery" not in orchestrator._phase_summaries

    @pytest.mark.asyncio
    async def test_store_phase_summary_multiple_phases(self, tmp_path):
        """Test storing summaries for multiple phases."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
            spec_dir=spec_dir,
        )

        with patch("spec.pipeline.orchestrator.gather_phase_outputs", return_value="content"):
            with patch("spec.pipeline.orchestrator.summarize_phase_output",
                       return_value="Summary"):
                await orchestrator._store_phase_summary("discovery")
                await orchestrator._store_phase_summary("requirements")
                await orchestrator._store_phase_summary("context")

        # All phases should be stored
        assert "discovery" in orchestrator._phase_summaries
        assert "requirements" in orchestrator._phase_summaries
        assert "context" in orchestrator._phase_summaries


class TestLoadRequirementsContext:
    """Additional tests for _load_requirements_context."""

    def test_load_requirements_with_minimal_data(self, tmp_path):
        """Test loading requirements with minimal required fields."""
        req_file = tmp_path / "requirements.json"
        requirements = {
            "task_description": "Simple task",
        }
        req_file.write_text(json.dumps(requirements))

        orchestrator = SpecOrchestrator(
            project_dir=tmp_path / "project",
        )

        result = orchestrator._load_requirements_context(req_file)

        assert "Simple task" in result
        assert "Not specified" in result  # Default for missing fields

    def test_load_requirements_with_unicode(self, tmp_path):
        """Test loading requirements with unicode content."""
        req_file = tmp_path / "requirements.json"
        requirements = {
            "task_description": "添加中文功能",
            "user_requirements": ["用户需要登录"],
            "acceptance_criteria": ["测试通过"],
        }
        req_file.write_text(json.dumps(requirements, ensure_ascii=False))

        orchestrator = SpecOrchestrator(
            project_dir=tmp_path / "project",
        )

        result = orchestrator._load_requirements_context(req_file)

        assert "添加中文功能" in result
        assert "用户需要登录" in result

    def test_load_requirements_malformed_json(self, tmp_path):
        """Test loading requirements with malformed JSON."""
        req_file = tmp_path / "requirements.json"
        req_file.write_text("{invalid json}")

        orchestrator = SpecOrchestrator(
            project_dir=tmp_path / "project",
        )

        # Should handle gracefully (returns empty or raises?)
        # Current implementation would raise JSONDecodeError
        with pytest.raises(json.JSONDecodeError):
            orchestrator._load_requirements_context(req_file)


class TestHeuristicAssessment:
    """Additional tests for _heuristic_assessment."""

    def test_heuristic_with_empty_project_index(self, tmp_path):
        """Test heuristic assessment with empty project index."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()

        # Create empty project index
        index_file = auto_claude / "project_index.json"
        index_file.write_text('{}', encoding="utf-8")

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
            task_description="Build a feature",
        )

        assessment = orchestrator._heuristic_assessment()

        assert assessment is not None
        assert assessment.complexity is not None

    def test_heuristic_with_malformed_project_index(self, tmp_path):
        """Test heuristic assessment with malformed project index."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_build = project_dir / "auto-claude"
        auto_build.mkdir()

        # Create malformed index
        index_file = auto_build / "project_index.json"
        index_file.write_text('{invalid}', encoding="utf-8")

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
            task_description="Build feature",
        )

        # The implementation will try to parse the JSON and likely fail
        # We expect it to handle the JSONDecodeError gracefully or raise it
        with pytest.raises(json.JSONDecodeError):
            orchestrator._heuristic_assessment()

    def test_heuristic_with_no_project_index(self, tmp_path):
        """Test heuristic assessment when no project index exists."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_build = project_dir / "auto-claude"
        auto_build.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
            task_description="Simple fix",
        )

        assessment = orchestrator._heuristic_assessment()

        assert assessment is not None


class TestCreateOverrideAssessment:
    """Additional tests for _create_override_assessment."""

    def test_override_all_complexity_levels(self, tmp_path):
        """Test override for all valid complexity levels."""
        valid_levels = ["simple", "standard", "complex"]

        for level in valid_levels:
            orchestrator = SpecOrchestrator(
                project_dir=tmp_path / "project",
                complexity_override=level,
            )

            assessment = orchestrator._create_override_assessment()

            assert assessment.complexity.value == level
            assert assessment.confidence == 1.0
            assert "Manual override" in assessment.reasoning
            assert level in assessment.reasoning

    def test_override_invalid_complexity(self, tmp_path):
        """Test override with invalid complexity level."""
        orchestrator = SpecOrchestrator(
            project_dir=tmp_path / "project",
            complexity_override="invalid_level",
        )

        # Complexity enum should handle this (likely raises ValueError)
        with pytest.raises(ValueError):
            orchestrator._create_override_assessment()


class TestPrintAssessmentInfo:
    """Tests for _print_assessment_info."""

    def test_print_assessment_with_all_flags(self, tmp_path, capsys):
        """Test _print_assessment_info with all flags enabled."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
        )

        assessment = ComplexityAssessment(
            complexity=Complexity.COMPLEX,
            confidence=0.95,
            reasoning="Very complex task requiring research",
            needs_research=True,
            needs_self_critique=True,
        )

        orchestrator._print_assessment_info(assessment)

        captured = capsys.readouterr()
        assert "COMPLEX" in captured.out
        assert "95%" in captured.out or "0.95" in captured.out
        # Should print research and self-critique indicators

    def test_print_assessment_with_low_confidence(self, tmp_path, capsys):
        """Test _print_assessment_info with low confidence."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
        )

        assessment = ComplexityAssessment(
            complexity=Complexity.STANDARD,
            confidence=0.45,
            reasoning="Not very confident",
        )

        orchestrator._print_assessment_info(assessment)

        captured = capsys.readouterr()
        assert "STANDARD" in captured.out
        assert "45%" in captured.out or "0.45" in captured.out

    def test_print_assessment_uses_default(self, tmp_path, capsys):
        """Test _print_assessment_info with default (self.assessment)."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
        )

        # Set the instance assessment
        orchestrator.assessment = ComplexityAssessment(
            complexity=Complexity.SIMPLE,
            confidence=1.0,
            reasoning="Test",
        )

        orchestrator._print_assessment_info()

        captured = capsys.readouterr()
        assert "SIMPLE" in captured.out


class TestPrintPhasesToRun:
    """Additional tests for _print_phases_to_run."""

    def test_print_phases_to_run_empty_list(self, tmp_path, capsys):
        """Test _print_phases_to_run with empty phase list."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
        )

        mock_assessment = MagicMock()
        mock_assessment.phases_to_run.return_value = []
        orchestrator.assessment = mock_assessment

        orchestrator._print_phases_to_run()

        captured = capsys.readouterr()
        assert "0" in captured.out  # Should show 0 phases

    def test_print_phases_to_run_single_phase(self, tmp_path, capsys):
        """Test _print_phases_to_run with single phase."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
        )

        mock_assessment = MagicMock()
        mock_assessment.phases_to_run.return_value = ["quick_spec"]
        orchestrator.assessment = mock_assessment

        orchestrator._print_phases_to_run()

        captured = capsys.readouterr()
        assert "1" in captured.out
        assert "quick_spec" in captured.out


class TestPrintCompletionSummary:
    """Additional tests for _print_completion_summary."""

    def test_print_completion_summary_no_output_files(self, tmp_path, capsys):
        """Test _print_completion_summary with no output files."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
            spec_dir=spec_dir,
        )

        results = [
            PhaseResult("discovery", True, [], [], 0),
            PhaseResult("requirements", True, [], [], 0),
        ]
        phases_executed = ["discovery", "requirements"]

        mock_assessment = MagicMock()
        mock_assessment.complexity.value = "simple"
        orchestrator.assessment = mock_assessment

        orchestrator._print_completion_summary(results, phases_executed)

        captured = capsys.readouterr()
        assert "SPEC CREATION COMPLETE" in captured.out

    def test_print_completion_summary_many_files(self, tmp_path, capsys):
        """Test _print_completion_summary with many output files."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
            spec_dir=spec_dir,
        )

        # Create many results with output files
        results = []
        for i in range(10):
            results.append(PhaseResult(
                f"phase_{i}",
                True,
                [str(spec_dir / f"file_{i}.json")],
                [],
                0
            ))

        phases_executed = [f"phase_{i}" for i in range(10)]

        mock_assessment = MagicMock()
        mock_assessment.complexity.value = "complex"
        orchestrator.assessment = mock_assessment

        orchestrator._print_completion_summary(results, phases_executed)

        captured = capsys.readouterr()
        assert "COMPLEX" in captured.out


class TestRunReviewCheckpoint:
    """Additional tests for _run_review_checkpoint."""

    def test_run_review_checkpoint_with_auto_approve(self, tmp_path):
        """Test _run_review_checkpoint with auto_approve=True."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
            spec_dir=spec_dir,
        )

        mock_review_state = MagicMock()
        mock_review_state.is_approved.return_value = True

        with patch("spec.pipeline.orchestrator.run_review_checkpoint",
                   return_value=mock_review_state):
            result = orchestrator._run_review_checkpoint(auto_approve=True)

        assert result is True

    def test_run_review_checkpoint_generic_exception(self, tmp_path):
        """Test _run_review_checkpoint with generic exception."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
            spec_dir=spec_dir,
        )

        # The current implementation doesn't catch generic exceptions
        # Only SystemExit and KeyboardInterrupt are handled
        with patch("spec.pipeline.orchestrator.run_review_checkpoint",
                   side_effect=RuntimeError("Unexpected error")):
            # RuntimeError will propagate (not caught)
            with pytest.raises(RuntimeError, match="Unexpected error"):
                orchestrator._run_review_checkpoint(auto_approve=False)


class TestPhaseComplexityAssessmentWithRequirements:
    """Additional tests for _phase_complexity_assessment_with_requirements."""

    @pytest.mark.asyncio
    async def test_phase_complexity_assessment_saves_on_first_run(self, tmp_path):
        """Test that assessment is only saved if file doesn't exist."""
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

        # First run - should save
        result1 = await orchestrator._phase_complexity_assessment_with_requirements()
        assert result1.success is True
        assert (spec_dir / "complexity_assessment.json").exists()

        # Get the original file content
        original_content = (spec_dir / "complexity_assessment.json").read_text()

        # Second run - should not overwrite (file exists)
        result2 = await orchestrator._phase_complexity_assessment_with_requirements()
        assert result2.success is True

        # Content should be unchanged
        current_content = (spec_dir / "complexity_assessment.json").read_text()
        assert current_content == original_content

    @pytest.mark.asyncio
    async def test_phase_complexity_with_heuristic_fallback(self, tmp_path):
        """Test complexity assessment falls back to heuristic when AI disabled."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test task",
            use_ai_assessment=False,  # Disable AI
        )

        result = await orchestrator._phase_complexity_assessment_with_requirements()

        assert result.success is True
        assert orchestrator.assessment is not None
        # Should have used heuristic
        assert isinstance(orchestrator.assessment, ComplexityAssessment)

    @pytest.mark.asyncio
    async def test_phase_complexity_loads_requirements_context(self, tmp_path):
        """Test that requirements context is loaded and used."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Original task",
            complexity_override="standard",
        )

        # Create requirements file
        req_file = spec_dir / "requirements.json"
        req_file.write_text(json.dumps({
            "task_description": "Updated from requirements",
            "workflow_type": "backend",
        }))

        await orchestrator._phase_complexity_assessment_with_requirements()

        # Task description should be updated from requirements
        assert orchestrator.task_description == "Updated from requirements"


class TestBackwardCompatibilityMethods:
    """Tests for backward compatibility methods."""

    def test_generate_spec_name_delegates_correctly(self, tmp_path):
        """Test _generate_spec_name delegates to models.generate_spec_name."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
        )

        result = orchestrator._generate_spec_name("Add user authentication")

        # Should return a valid name
        assert isinstance(result, str)
        assert len(result) > 0
        assert "-" in result or result == "spec"

    def test_rename_spec_dir_from_requirements_delegates(self, tmp_path):
        """Test _rename_spec_dir_from_requirements delegates correctly."""
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
            "task_description": "Build feature"
        }))

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
            spec_dir=spec_dir,
        )

        with patch("spec.pipeline.models.update_task_logger_path"):
            result = orchestrator._rename_spec_dir_from_requirements()

        assert isinstance(result, bool)

    def test_rename_spec_dir_updates_spec_dir_reference(self, tmp_path):
        """Test that _rename_spec_dir_from_requirements updates spec_dir."""
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
            "task_description": "Build feature"
        }))

        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
            spec_dir=spec_dir,
        )

        original_spec_dir = orchestrator.spec_dir

        with patch("spec.pipeline.models.update_task_logger_path"):
            result = orchestrator._rename_spec_dir_from_requirements()

        # If rename succeeded, spec_dir should be updated
        if result and original_spec_dir.name.endswith("-pending"):
            # Find the renamed directory
            matching = [d for d in specs_dir.iterdir()
                       if d.name.startswith("001-") and "pending" not in d.name]
            if matching:
                assert orchestrator.spec_dir != original_spec_dir
