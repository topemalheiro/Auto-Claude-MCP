"""Tests for PlanningPhaseMixin"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from spec.phases.planning_phases import PlanningPhaseMixin
from spec.phases.models import PhaseResult


class MockPlanningExecutor(PlanningPhaseMixin):
    """Minimal mock executor for testing PlanningPhaseMixin"""

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
        self.spec_validator = MagicMock()
        self.run_agent_fn = AsyncMock()
        self._run_script = MagicMock(return_value=(False, "Script not found"))
        self.task_logger = MagicMock()


class TestPhasePlanning:
    """Tests for phase_planning method"""

    @pytest.mark.asyncio
    async def test_planning_already_valid(self, tmp_path):
        """Test when implementation_plan.json already exists and is valid"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        plan_data = {
            "phases": [
                {"subtasks": [{"id": "1", "description": "Task 1"}]}
            ]
        }
        plan_file.write_text(json.dumps(plan_data), encoding="utf-8")

        mock_validator = MagicMock()
        mock_result = MagicMock()
        mock_result.valid = True
        mock_validator.validate_implementation_plan.return_value = mock_result

        executor = MockPlanningExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )
        executor.spec_validator = mock_validator

        result = await executor.phase_planning()

        assert result.success is True
        assert result.retries == 0

    @pytest.mark.asyncio
    async def test_planning_script_success(self, tmp_path):
        """Test planning succeeds via planner.py script"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / "auto-claude"
        auto_claude.mkdir()
        script_path = auto_claude / "planner.py"
        script_path.write_text('# Planner script\nprint("Planning done")', encoding="utf-8")

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        plan_data = {
            "phases": [
                {"subtasks": [{"id": "1"}]}
            ]
        }
        plan_file.write_text(json.dumps(plan_data), encoding="utf-8")

        mock_validator = MagicMock()
        mock_result = MagicMock()
        mock_result.valid = True
        mock_validator.validate_implementation_plan.return_value = mock_result

        executor = MockPlanningExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )
        executor.spec_validator = mock_validator

        result = await executor.phase_planning()

        assert result.success is True
        assert result.retries == 0

    @pytest.mark.asyncio
    async def test_planning_script_with_auto_fix(self, tmp_path):
        """Test planning with auto-fix on validation failure"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / "auto-claude"
        auto_claude.mkdir()
        script_path = auto_claude / "planner.py"
        script_path.write_text('# Planner', encoding="utf-8")

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text('{"invalid": true}', encoding="utf-8")

        mock_validator = MagicMock()
        mock_invalid = MagicMock()
        mock_invalid.valid = False
        mock_invalid.errors = ["Missing required fields"]

        mock_valid = MagicMock()
        mock_valid.valid = True

        # Flow: 1) existing plan invalid, 2) script output invalid, 3) after auto-fix valid
        mock_validator.validate_implementation_plan.side_effect = [mock_invalid, mock_invalid, mock_valid]

        executor = MockPlanningExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )
        executor.spec_validator = mock_validator

        # Mock _run_script to succeed (script "ran" and file exists)
        with patch.object(executor, "_run_script", return_value=(True, "Success")):
            with patch("spec.validate_pkg.auto_fix.auto_fix_plan") as mock_auto_fix:
                mock_auto_fix.return_value = True

                result = await executor.phase_planning()

        # Should call auto_fix
        assert mock_auto_fix.called

    @pytest.mark.asyncio
    async def test_planning_fallback_to_agent(self, tmp_path):
        """Test planning falls back to agent when script fails"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # No planner script

        plan_file = spec_dir / "implementation_plan.json"

        mock_validator = MagicMock()
        mock_result = MagicMock()
        mock_result.valid = True
        mock_validator.validate_implementation_plan.return_value = mock_result

        executor = MockPlanningExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )
        executor.spec_validator = mock_validator

        def create_plan(*args, **kwargs):
            plan_file.write_text('{"phases": []}', encoding="utf-8")
            return (True, "Plan created")

        executor.run_agent_fn.side_effect = create_plan

        result = await executor.phase_planning()

        assert result.success is True

    @pytest.mark.asyncio
    async def test_planning_agent_retries_on_failure(self, tmp_path):
        """Test planning agent retries on failure"""
        from spec.phases.models import MAX_RETRIES

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_validator = MagicMock()
        mock_result = MagicMock()
        mock_result.valid = False
        mock_result.errors = ["Invalid plan"]
        mock_validator.validate_implementation_plan.return_value = mock_result

        executor = MockPlanningExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )
        executor.spec_validator = mock_validator

        with patch("spec.validate_pkg.auto_fix.auto_fix_plan", return_value=False):
            executor.run_agent_fn.return_value = (True, "Done")

            result = await executor.phase_planning()

        assert result.success is False
        assert result.retries == MAX_RETRIES

    @pytest.mark.asyncio
    async def test_planning_agent_with_auto_fix(self, tmp_path):
        """Test planning agent with auto-fix success"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"

        mock_validator = MagicMock()
        mock_invalid = MagicMock()
        mock_invalid.valid = False
        mock_invalid.errors = ["Missing field"]

        mock_valid = MagicMock()
        mock_valid.valid = True

        mock_validator.validate_implementation_plan.side_effect = [mock_invalid, mock_valid]

        executor = MockPlanningExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )
        executor.spec_validator = mock_validator

        def create_invalid_plan(*args, **kwargs):
            plan_file.write_text('{"invalid": true}', encoding="utf-8")
            return (True, "Plan created")

        executor.run_agent_fn.side_effect = create_invalid_plan

        with patch("spec.validate_pkg.auto_fix.auto_fix_plan") as mock_auto_fix:
            mock_auto_fix.return_value = True

            result = await executor.phase_planning()

        assert result.success is True
        assert mock_auto_fix.called

    @pytest.mark.asyncio
    async def test_planning_uses_planner_prompt(self, tmp_path):
        """Test planning uses planner.md prompt for agent"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"

        mock_validator = MagicMock()
        mock_result = MagicMock()
        mock_result.valid = True
        mock_validator.validate_implementation_plan.return_value = mock_result

        executor = MockPlanningExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )
        executor.spec_validator = mock_validator

        def create_plan(*args, **kwargs):
            plan_file.write_text('{"phases": []}', encoding="utf-8")
            return (True, "Plan created")

        executor.run_agent_fn.side_effect = create_plan

        # Script fails to trigger agent fallback
        with patch.object(executor, "_run_script", return_value=(False, "Script not found")):
            await executor.phase_planning()

        call_args = executor.run_agent_fn.call_args
        assert call_args[0][0] == "planner.md"
        assert call_args[1]["phase_name"] == "planning"

    @pytest.mark.asyncio
    async def test_planning_logs_stats_on_success(self, tmp_path):
        """Test planning logs stats when plan is created"""
        from task_logger import LogEntryType, LogPhase

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / "auto-claude"
        auto_claude.mkdir()
        script_path = auto_claude / "planner.py"
        script_path.write_text('# Planner', encoding="utf-8")

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        plan_data = {
            "phases": [
                {"subtasks": [{"id": "1"}]},
                {"subtasks": [{"id": "2"}]}
            ]
        }

        mock_validator = MagicMock()
        mock_result = MagicMock()
        mock_result.valid = True
        mock_validator.validate_implementation_plan.return_value = mock_result

        mock_logger = MagicMock()
        executor = MockPlanningExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )
        executor.spec_validator = mock_validator
        executor.task_logger = mock_logger

        # Mock _run_script to simulate script creating the plan
        def create_plan_via_script(*args, **kwargs):
            plan_file.write_text(json.dumps(plan_data), encoding="utf-8")
            return True, "Success"

        with patch.object(executor, "_run_script", side_effect=create_plan_via_script):
            await executor.phase_planning()

        # Should log stats
        mock_logger.log.assert_called()

    @pytest.mark.asyncio
    async def test_planning_script_doesnt_create_file(self, tmp_path):
        """Test when script succeeds but doesn't create plan file"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / "auto-claude"
        auto_claude.mkdir()
        script_path = auto_claude / "planner.py"
        script_path.write_text('# Planner', encoding="utf-8")

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # No plan file created

        mock_validator = MagicMock()

        executor = MockPlanningExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )
        executor.spec_validator = mock_validator

        # Script "succeeds" but no file
        with patch.object(executor, "_run_script", return_value=(True, "Done")):
            # Mock agent to create plan
            plan_file = spec_dir / "implementation_plan.json"

            def create_plan(*args, **kwargs):
                plan_file.write_text('{"phases": []}', encoding="utf-8")
                return (True, "Plan created")

            executor.run_agent_fn.side_effect = create_plan

            result = await executor.phase_planning()

        # Should fall back to agent
        assert isinstance(result, PhaseResult)


class TestPhaseValidation:
    """Tests for phase_validation method"""

    @pytest.mark.asyncio
    async def test_validation_all_valid_first_try(self, tmp_path):
        """Test validation when all checkpoints pass on first try"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_validator = MagicMock()
        mock_results = [
            MagicMock(valid=True, errors=[], checkpoint="requirements"),
            MagicMock(valid=True, errors=[], checkpoint="context"),
            MagicMock(valid=True, errors=[], checkpoint="spec")
        ]
        mock_validator.validate_all.return_value = mock_results

        mock_ui = MagicMock()
        executor = MockPlanningExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )
        executor.spec_validator = mock_validator
        executor.ui = mock_ui

        result = await executor.phase_validation()

        assert result.success is True
        assert result.retries == 0

    @pytest.mark.asyncio
    async def test_validation_with_auto_fix_success(self, tmp_path):
        """Test validation with successful auto-fix"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # First attempt has errors, second is valid
        mock_invalid = MagicMock()
        mock_invalid.valid = False
        mock_invalid.errors = ["Missing field"]
        mock_invalid.checkpoint = "requirements"
        mock_invalid.fixes = ["Add the field"]

        mock_valid = MagicMock()
        mock_valid.valid = True
        mock_valid.errors = []
        mock_valid.checkpoint = "requirements"

        mock_validator = MagicMock()
        mock_validator.validate_all.side_effect = [
            [mock_invalid],
            [mock_valid]
        ]

        executor = MockPlanningExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )
        executor.spec_validator = mock_validator

        executor.run_agent_fn.return_value = (True, "Fixed")

        result = await executor.phase_validation()

        assert result.success is True
        assert result.retries == 1

    @pytest.mark.asyncio
    async def test_validation_retries_exhausted(self, tmp_path):
        """Test validation when retries are exhausted"""
        from spec.phases.models import MAX_RETRIES

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_invalid = MagicMock()
        mock_invalid.valid = False
        mock_invalid.errors = ["Critical error"]
        mock_invalid.checkpoint = "spec"

        mock_validator = MagicMock()
        mock_validator.validate_all.return_value = [mock_invalid]

        executor = MockPlanningExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )
        executor.spec_validator = mock_validator

        executor.run_agent_fn.return_value = (False, "Fix failed")

        result = await executor.phase_validation()

        assert result.success is False
        assert result.retries == MAX_RETRIES
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_validation_prints_status_messages(self, tmp_path):
        """Test validation prints status for each checkpoint"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_results = [
            MagicMock(valid=True, errors=[], checkpoint="requirements"),
            MagicMock(valid=False, errors=["Error"], checkpoint="context"),
            MagicMock(valid=True, errors=[], checkpoint="spec")
        ]

        mock_validator = MagicMock()
        mock_validator.validate_all.return_value = mock_results

        mock_ui = MagicMock()
        executor = MockPlanningExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )
        executor.spec_validator = mock_validator
        executor.ui = mock_ui

        # Mock run_agent_fn for auto-fix attempt
        executor.run_agent_fn.return_value = (True, "Fixed")

        await executor.phase_validation()

        # Should print status for each checkpoint
        assert mock_ui.print_status.call_count >= 3

    @pytest.mark.asyncio
    async def test_validation_collects_all_errors(self, tmp_path):
        """Test validation collects all errors from failed checkpoints"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_results = [
            MagicMock(valid=False, errors=["Error 1", "Error 2"], checkpoint="req"),
            MagicMock(valid=False, errors=["Error 3"], checkpoint="spec")
        ]

        mock_validator = MagicMock()
        mock_validator.validate_all.return_value = mock_results

        executor = MockPlanningExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )
        executor.spec_validator = mock_validator

        executor.run_agent_fn.return_value = (True, "Fixed")

        result = await executor.phase_validation()

        # Should have collected all errors
        assert len(result.errors) >= 3

    @pytest.mark.asyncio
    async def test_validation_includes_fixes_in_context(self, tmp_path):
        """Test validation includes suggested fixes in agent context"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_invalid = MagicMock()
        mock_invalid.valid = False
        mock_invalid.errors = ["Missing field"]
        mock_invalid.checkpoint = "requirements"
        mock_invalid.fixes = ["Add required_field: value"]

        mock_validator = MagicMock()
        mock_validator.validate_all.return_value = [mock_invalid]

        executor = MockPlanningExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )
        executor.spec_validator = mock_validator

        executor.run_agent_fn.return_value = (True, "Fixed")

        await executor.phase_validation()

        # Check that fixes were included in context
        call_args = executor.run_agent_fn.call_args
        context = call_args[1].get("additional_context", "")
        assert "Suggested fixes" in context or "fixes" in context.lower()

    @pytest.mark.asyncio
    async def test_validation_uses_validation_fixer_prompt(self, tmp_path):
        """Test validation uses validation_fixer.md prompt"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_invalid = MagicMock()
        mock_invalid.valid = False
        mock_invalid.errors = ["Error"]
        mock_invalid.checkpoint = "spec"
        mock_invalid.fixes = []

        mock_validator = MagicMock()
        mock_validator.validate_all.return_value = [mock_invalid]

        executor = MockPlanningExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )
        executor.spec_validator = mock_validator

        executor.run_agent_fn.return_value = (True, "Fixed")

        await executor.phase_validation()

        call_args = executor.run_agent_fn.call_args
        assert call_args[0][0] == "validation_fixer.md"
        assert call_args[1]["phase_name"] == "validation"


class TestPlanningPhaseMixinEdgeCases:
    """Edge case tests for PlanningPhaseMixin"""

    @pytest.mark.asyncio
    async def test_planning_with_invalid_existing_plan(self, tmp_path):
        """Test planning when existing plan is invalid"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text('{invalid json}', encoding="utf-8")

        mock_validator = MagicMock()
        mock_result = MagicMock()
        mock_result.valid = True
        mock_validator.validate_implementation_plan.return_value = mock_result

        executor = MockPlanningExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )
        executor.spec_validator = mock_validator

        # Agent creates valid plan
        def create_plan(*args, **kwargs):
            plan_file.write_text('{"phases": []}', encoding="utf-8")
            return (True, "Plan created")

        executor.run_agent_fn.side_effect = create_plan

        # Script fails
        with patch.object(executor, "_run_script", return_value=(False, "Failed")):
            result = await executor.phase_planning()

        assert result.success is True

    @pytest.mark.asyncio
    async def test_planning_auto_fix_fails_then_agent_succeeds(self, tmp_path):
        """Test when auto-fix fails but agent creates valid plan"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"

        mock_validator = MagicMock()
        mock_invalid = MagicMock()
        mock_invalid.valid = False
        mock_invalid.errors = ["Error"]

        mock_valid = MagicMock()
        mock_valid.valid = True

        mock_validator.validate_implementation_plan.side_effect = [mock_invalid, mock_valid]

        executor = MockPlanningExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )
        executor.spec_validator = mock_validator

        with patch("spec.validate_pkg.auto_fix.auto_fix_plan", return_value=False):
            def create_plan(*args, **kwargs):
                plan_file.write_text('{"phases": []}', encoding="utf-8")
                return (True, "Plan created")

            executor.run_agent_fn.side_effect = create_plan

            with patch.object(executor, "_run_script", return_value=(False, "Script failed")):
                result = await executor.phase_planning()

        assert result.success is True

    @pytest.mark.asyncio
    async def test_validation_with_empty_checkpoints(self, tmp_path):
        """Test validation with no checkpoints"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_validator = MagicMock()
        mock_validator.validate_all.return_value = []

        executor = MockPlanningExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )
        executor.spec_validator = mock_validator

        result = await executor.phase_validation()

        # Empty results means all valid (vacuously true)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_validation_multiple_checkpoints_mixed(self, tmp_path):
        """Test validation with mixed valid/invalid checkpoints"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # First attempt: mixed
        mock_results_mixed = [
            MagicMock(valid=True, errors=[], checkpoint="requirements"),
            MagicMock(valid=False, errors=["Error"], checkpoint="spec"),
            MagicMock(valid=True, errors=[], checkpoint="plan")
        ]

        # Second attempt: all valid
        mock_results_valid = [
            MagicMock(valid=True, errors=[], checkpoint="requirements"),
            MagicMock(valid=True, errors=[], checkpoint="spec"),
            MagicMock(valid=True, errors=[], checkpoint="plan")
        ]

        mock_validator = MagicMock()
        mock_validator.validate_all.side_effect = [mock_results_mixed, mock_results_valid]

        executor = MockPlanningExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )
        executor.spec_validator = mock_validator

        executor.run_agent_fn.return_value = (True, "Fixed")

        result = await executor.phase_validation()

        assert result.success is True
        assert result.retries == 1

    @pytest.mark.asyncio
    async def test_planning_agent_fails_to_create_file(self, tmp_path):
        """Test when agent fails to create plan file"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_validator = MagicMock()

        executor = MockPlanningExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )
        executor.spec_validator = mock_validator
        executor.run_agent_fn.return_value = (True, "Done but no file")

        with patch.object(executor, "_run_script", return_value=(False, "Script failed")):
            result = await executor.phase_planning()

        assert result.success is False

    @pytest.mark.asyncio
    async def test_validation_ui_messages_with_muted_errors(self, tmp_path):
        """Test validation prints errors with muted formatting"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_invalid = MagicMock()
        mock_invalid.valid = False
        mock_invalid.errors = ["Error 1", "Error 2"]
        mock_invalid.checkpoint = "spec"

        mock_validator = MagicMock()
        mock_validator.validate_all.return_value = [mock_invalid]

        mock_ui = MagicMock()
        mock_ui.muted = lambda x: f"[muted]{x}[/muted]"

        executor = MockPlanningExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )
        executor.spec_validator = mock_validator
        executor.ui = mock_ui

        executor.run_agent_fn.return_value = (True, "Fixed")

        await executor.phase_validation()

        # Should have called print_status and muted
        assert mock_ui.print_status.called or mock_ui.muted.called

    @pytest.mark.asyncio
    async def test_validation_max_retries_minus_one(self, tmp_path):
        """Test validation tries auto-fix MAX_RETRIES - 1 times"""
        from spec.phases.models import MAX_RETRIES

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_invalid = MagicMock()
        mock_invalid.valid = False
        mock_invalid.errors = ["Error"]
        mock_invalid.checkpoint = "spec"

        mock_validator = MagicMock()
        mock_validator.validate_all.return_value = [mock_invalid]

        executor = MockPlanningExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )
        executor.spec_validator = mock_validator

        call_count = 0

        async def mock_agent(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return (True, f"Attempt {call_count}")

        executor.run_agent_fn = AsyncMock(side_effect=mock_agent)

        result = await executor.phase_validation()

        # The agent is only called when attempt < MAX_RETRIES - 1
        # For MAX_RETRIES=3, this means attempts 0 and 1 (2 calls total)
        # The final iteration (attempt 2) does NOT call the agent
        assert call_count == MAX_RETRIES - 1

    @pytest.mark.asyncio
    async def test_planning_uses_run_script_method(self, tmp_path):
        """Test planning uses _run_script for planner.py"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_validator = MagicMock()
        mock_result = MagicMock()
        mock_result.valid = True
        mock_validator.validate_implementation_plan.return_value = mock_result

        executor = MockPlanningExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )
        executor.spec_validator = mock_validator

        # Create plan file AFTER _run_script is mocked to simulate script creating it
        plan_file = spec_dir / "implementation_plan.json"

        # Mock _run_script to simulate script creating the plan
        def create_plan_via_script(*args, **kwargs):
            plan_file.write_text('{"phases": []}', encoding="utf-8")
            return True, "Success"

        with patch.object(executor, "_run_script", side_effect=create_plan_via_script) as mock_run:
            result = await executor.phase_planning()

            # Should call _run_script for planner.py
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[0][0] == "planner.py"

        assert result.success is True

    @pytest.mark.asyncio
    async def test_planning_with_writer_stats(self, tmp_path):
        """Test planning retrieves and logs plan stats"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / "auto-claude"
        auto_claude.mkdir()

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        plan_data = {
            "phases": [
                {"subtasks": [{"id": "1"}, {"id": "2"}]},
                {"subtasks": [{"id": "3"}]}
            ]
        }

        mock_validator = MagicMock()
        mock_result = MagicMock()
        mock_result.valid = True
        mock_validator.validate_implementation_plan.return_value = mock_result

        mock_logger = MagicMock()
        executor = MockPlanningExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test"
        )
        executor.spec_validator = mock_validator
        executor.task_logger = mock_logger

        # Mock _run_script to simulate script creating the plan
        def create_plan_via_script(*args, **kwargs):
            plan_file.write_text(json.dumps(plan_data), encoding="utf-8")
            return True, "Success"

        with patch.object(executor, "_run_script", side_effect=create_plan_via_script):
            await executor.phase_planning()

        # Should log stats about subtasks
        mock_logger.log.assert_called()
