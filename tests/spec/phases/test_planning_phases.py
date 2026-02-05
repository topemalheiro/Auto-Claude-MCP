"""Tests for planning_phases module"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from spec.phases.planning_phases import PlanningPhaseMixin
from spec.phases.models import PhaseResult
from spec.validate_pkg.models import ValidationResult


class FakePlanningExecutor(PlanningPhaseMixin):
    """Fake executor for testing"""

    def __init__(
        self,
        project_dir=None,
        spec_dir=None,
        task_description="",
        ui=None,
        task_logger=None,
        spec_validator=None,
        run_agent_fn=None,
    ):
        self.project_dir = project_dir or Path("/tmp/project")
        self.spec_dir = spec_dir or Path("/tmp/spec")
        self.task_description = task_description
        self.ui = ui or MagicMock()
        self.task_logger = task_logger or MagicMock()
        self.spec_validator = spec_validator or MagicMock()
        self.run_agent_fn = run_agent_fn or (lambda *a, **k: (True, "response"))


@pytest.mark.asyncio
class TestPlanningPhaseMixin:
    """Tests for PlanningPhaseMixin"""

    async def test_phase_planning_success(self, tmp_path):
        """Test successful planning phase"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Mock run_agent_fn
        async def mock_run_agent(*args, **kwargs):
            # Create implementation_plan.json
            plan_file = spec_dir / "implementation_plan.json"
            plan_file.write_text('{"phases": []}', encoding="utf-8")
            return True, "Plan created"

        # Mock _run_script to fail (so it falls back to agent)
        def mock_run_script(script_name, args):
            return False, "Script not found"

        ui = MagicMock()
        ui.print_status = MagicMock()
        ui.muted = lambda x: x
        task_logger = MagicMock()

        from spec.validate_pkg.models import ValidationResult
        validator = MagicMock()
        validator.validate_implementation_plan.return_value = ValidationResult(
            valid=True, checkpoint="plan", errors=[], warnings=[], fixes=[]
        )

        executor = FakePlanningExecutor(
            spec_dir=spec_dir,
            ui=ui,
            task_logger=task_logger,
            spec_validator=validator,
            run_agent_fn=mock_run_agent,
        )
        # Add the _run_script mock
        executor._run_script = mock_run_script

        result = await executor.phase_planning()

        assert result.success is True
        assert result.phase == "planning"
        assert len(result.output_files) > 0

    async def test_phase_validation_success(self, tmp_path):
        """Test validation phase with all checks passing"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create required files
        (spec_dir / "spec.md").write_text("# Spec", encoding="utf-8")
        (spec_dir / "requirements.json").write_text('{}', encoding="utf-8")
        (spec_dir / "context.json").write_text('{}', encoding="utf-8")
        (spec_dir / "implementation_plan.json").write_text('{"phases": []}', encoding="utf-8")

        ui = MagicMock()
        ui.print_status = MagicMock()
        ui.muted = lambda x: x
        task_logger = MagicMock()

        from spec.validate_pkg.models import ValidationResult
        validator = MagicMock()
        validator.validate_all.return_value = [
            ValidationResult(valid=True, checkpoint="spec", errors=[], warnings=[], fixes=[]),
            ValidationResult(valid=True, checkpoint="context", errors=[], warnings=[], fixes=[]),
            ValidationResult(valid=True, checkpoint="plan", errors=[], warnings=[], fixes=[]),
        ]

        executor = FakePlanningExecutor(
            spec_dir=spec_dir,
            ui=ui,
            task_logger=task_logger,
            spec_validator=validator,
        )

        result = await executor.phase_validation()

        assert result.success is True
        assert result.phase == "validation"

    async def test_phase_validation_with_errors(self, tmp_path):
        """Test validation phase with validation errors"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Mock run_agent_fn for auto-fix attempts
        async def mock_run_agent(*args, **kwargs):
            return False, "Auto-fix failed"

        ui = MagicMock()
        ui.print_status = MagicMock()
        ui.muted = lambda x: x
        task_logger = MagicMock()

        validator = MagicMock()
        validator.validate_all.return_value = [
            ValidationResult(valid=False, checkpoint="spec", errors=["Missing spec.md"], warnings=[], fixes=[]),
            ValidationResult(valid=False, checkpoint="plan", errors=["Invalid plan"], warnings=[], fixes=[]),
        ]

        executor = FakePlanningExecutor(
            spec_dir=spec_dir,
            ui=ui,
            task_logger=task_logger,
            spec_validator=validator,
            run_agent_fn=mock_run_agent,
        )

        result = await executor.phase_validation()

        # Validation phase should fail when all retries exhausted
        assert result.success is False
        assert result.phase == "validation"
        assert len(result.errors) > 0

    # ==================== Additional phase_planning tests ====================

    async def test_phase_planning_existing_valid_plan_skips(self, tmp_path):
        """Test phase_planning skips when valid plan already exists"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create a valid implementation plan
        plan_file = spec_dir / "implementation_plan.json"
        plan_data = {
            "spec_name": "test-spec",
            "workflow_type": "feature",
            "phases": [
                {
                    "phase": 1,
                    "name": "Implementation",
                    "subtasks": [
                        {"id": "1", "description": "Task 1", "status": "pending"}
                    ]
                }
            ]
        }
        plan_file.write_text(json.dumps(plan_data), encoding="utf-8")

        ui = MagicMock()
        ui.print_status = MagicMock()
        task_logger = MagicMock()

        validator = MagicMock()
        validator.validate_implementation_plan.return_value = ValidationResult(
            valid=True, checkpoint="plan", errors=[], warnings=[], fixes=[]
        )

        executor = FakePlanningExecutor(
            spec_dir=spec_dir,
            ui=ui,
            task_logger=task_logger,
            spec_validator=validator,
        )

        result = await executor.phase_planning()

        assert result.success is True
        assert result.phase == "planning"
        assert result.retries == 0
        ui.print_status.assert_any_call(
            "implementation_plan.json already exists and is valid", "success"
        )

    async def test_phase_planning_existing_invalid_plan_regenerates(self, tmp_path):
        """Test phase_planning regenerates when existing plan is invalid"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create an invalid implementation plan
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text('{"invalid": "plan"}', encoding="utf-8")

        async def mock_run_agent(*args, **kwargs):
            # Write a valid plan
            plan_file.write_text(
                json.dumps({
                    "spec_name": "test-spec",
                    "phases": [{"phase": 1, "subtasks": []}]
                }),
                encoding="utf-8"
            )
            return True, "Plan created"

        def mock_run_script(script_name, args):
            return False, "Script failed"

        ui = MagicMock()
        ui.print_status = MagicMock()
        task_logger = MagicMock()

        # First call says invalid, second call (after regeneration) says valid
        validator = MagicMock()
        validator.validate_implementation_plan.side_effect = [
            ValidationResult(
                valid=False, checkpoint="plan",
                errors=["Invalid structure"], warnings=[], fixes=[]
            ),
            ValidationResult(
                valid=True, checkpoint="plan", errors=[], warnings=[], fixes=[]
            )
        ]

        executor = FakePlanningExecutor(
            spec_dir=spec_dir,
            ui=ui,
            task_logger=task_logger,
            spec_validator=validator,
            run_agent_fn=mock_run_agent,
        )
        executor._run_script = mock_run_script

        result = await executor.phase_planning()

        assert result.success is True
        ui.print_status.assert_any_call(
            "Plan exists but invalid, regenerating...", "warning"
        )

    async def test_phase_planning_script_success(self, tmp_path):
        """Test phase_planning succeeds via script execution"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Mock _run_script to succeed
        def mock_run_script(script_name, args):
            # Create a valid plan
            plan_file = spec_dir / "implementation_plan.json"
            plan_file.write_text(
                json.dumps({
                    "spec_name": "test-spec",
                    "phases": [{"phase": 1, "subtasks": []}]
                }),
                encoding="utf-8"
            )
            return True, "Script created plan"

        ui = MagicMock()
        ui.print_status = MagicMock()
        ui.muted = lambda x: x
        task_logger = MagicMock()

        validator = MagicMock()
        validator.validate_implementation_plan.return_value = ValidationResult(
            valid=True, checkpoint="plan", errors=[], warnings=[], fixes=[]
        )

        executor = FakePlanningExecutor(
            spec_dir=spec_dir,
            ui=ui,
            task_logger=task_logger,
            spec_validator=validator,
        )
        executor._run_script = mock_run_script

        result = await executor.phase_planning()

        assert result.success is True
        assert result.retries == 0
        # Should have tried script first
        ui.print_status.assert_any_call(
            "Trying planner.py (deterministic)...", "progress"
        )
        ui.print_status.assert_any_call(
            "Created valid implementation_plan.json via script", "success"
        )

    async def test_phase_planning_script_creates_invalid_plan_auto_fix(self, tmp_path):
        """Test phase_planning with auto-fix after invalid script output"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Mock _run_script to create invalid plan
        def mock_run_script(script_name, args):
            plan_file = spec_dir / "implementation_plan.json"
            plan_file.write_text('{"invalid": "data"}', encoding="utf-8")
            return True, "Script ran"

        ui = MagicMock()
        ui.print_status = MagicMock()
        ui.muted = lambda x: x
        task_logger = MagicMock()

        # First validation fails, but auto_fix makes it succeed
        # Patch at the correct import location: spec.validate_pkg.auto_fix.auto_fix_plan
        with patch("spec.validate_pkg.auto_fix.auto_fix_plan", return_value=True):
            validator = MagicMock()
            validator.validate_implementation_plan.side_effect = [
                ValidationResult(
                    valid=False, checkpoint="plan",
                    errors=["Missing phases"], warnings=[], fixes=[]
                ),
                ValidationResult(
                    valid=True, checkpoint="plan", errors=[], warnings=[], fixes=[]
                )
            ]

            executor = FakePlanningExecutor(
                spec_dir=spec_dir,
                ui=ui,
                task_logger=task_logger,
                spec_validator=validator,
            )
            executor._run_script = mock_run_script

            result = await executor.phase_planning()

        assert result.success is True

    async def test_phase_planning_agent_retries_success(self, tmp_path):
        """Test phase_planning agent retries then succeeds"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        attempts = [0]

        async def mock_run_agent(*args, **kwargs):
            attempts[0] += 1
            if attempts[0] == 1:
                return False, "First attempt failed"
            # Create valid plan on second attempt
            plan_file = spec_dir / "implementation_plan.json"
            plan_file.write_text(
                json.dumps({
                    "spec_name": "test-spec",
                    "phases": [{"phase": 1, "subtasks": []}]
                }),
                encoding="utf-8"
            )
            return True, "Plan created"

        def mock_run_script(script_name, args):
            return False, "Script not available"

        ui = MagicMock()
        ui.print_status = MagicMock()
        ui.muted = lambda x: x
        task_logger = MagicMock()

        validator = MagicMock()
        validator.validate_implementation_plan.return_value = ValidationResult(
            valid=True, checkpoint="plan", errors=[], warnings=[], fixes=[]
        )

        executor = FakePlanningExecutor(
            spec_dir=spec_dir,
            ui=ui,
            task_logger=task_logger,
            spec_validator=validator,
            run_agent_fn=mock_run_agent,
        )
        executor._run_script = mock_run_script

        result = await executor.phase_planning()

        assert result.success is True
        assert result.retries == 1

    async def test_phase_planning_all_retries_exhausted(self, tmp_path):
        """Test phase_planning fails after all retries exhausted"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        async def mock_run_agent(*args, **kwargs):
            return False, "Agent failed"

        def mock_run_script(script_name, args):
            return False, "Script failed"

        ui = MagicMock()
        ui.print_status = MagicMock()
        ui.muted = lambda x: x
        task_logger = MagicMock()

        validator = MagicMock()
        validator.validate_implementation_plan.return_value = ValidationResult(
            valid=False, checkpoint="plan",
            errors=["Missing required fields"], warnings=[], fixes=[]
        )

        # Patch at the correct import location: spec.validate_pkg.auto_fix.auto_fix_plan
        with patch("spec.validate_pkg.auto_fix.auto_fix_plan", return_value=False):
            executor = FakePlanningExecutor(
                spec_dir=spec_dir,
                ui=ui,
                task_logger=task_logger,
                spec_validator=validator,
                run_agent_fn=mock_run_agent,
            )
            executor._run_script = mock_run_script

            result = await executor.phase_planning()

        assert result.success is False
        assert len(result.errors) > 0

    # ==================== Additional phase_validation tests ====================

    async def test_phase_validation_with_auto_fix_success(self, tmp_path):
        """Test phase_validation succeeds after auto-fix"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create spec file that will be fixed
        (spec_dir / "spec.md").write_text("# Spec\n\nIncomplete", encoding="utf-8")
        (spec_dir / "requirements.json").write_text('{}', encoding="utf-8")
        (spec_dir / "context.json").write_text('{}', encoding="utf-8")

        fix_attempts = [0]

        async def mock_run_agent(*args, **kwargs):
            fix_attempts[0] += 1
            # Fix the spec on first auto-fix attempt
            if fix_attempts[0] == 1:
                (spec_dir / "spec.md").write_text(
                    "# Spec\n\n## Overview\n\nComplete spec content\n\n## Requirements\n\n- Requirement 1",
                    encoding="utf-8"
                )
            return True, "Fix applied"

        ui = MagicMock()
        ui.print_status = MagicMock()
        ui.muted = lambda x: x
        task_logger = MagicMock()

        validator = MagicMock()
        # First call: invalid, second call: valid after fix
        validator.validate_all.side_effect = [
            [
                ValidationResult(
                    valid=False, checkpoint="spec",
                    errors=["Incomplete spec"], warnings=[], fixes=[]
                ),
                ValidationResult(valid=True, checkpoint="req", errors=[], warnings=[], fixes=[]),
            ],
            [
                ValidationResult(valid=True, checkpoint="spec", errors=[], warnings=[], fixes=[]),
                ValidationResult(valid=True, checkpoint="req", errors=[], warnings=[], fixes=[]),
            ]
        ]

        executor = FakePlanningExecutor(
            spec_dir=spec_dir,
            ui=ui,
            task_logger=task_logger,
            spec_validator=validator,
            run_agent_fn=mock_run_agent,
        )

        result = await executor.phase_validation()

        assert result.success is True

    async def test_phase_validation_with_suggested_fixes(self, tmp_path):
        """Test phase_validation with suggested fixes in validation results"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        call_count = [0]

        async def mock_run_agent(*args, **kwargs):
            call_count[0] += 1
            return False, "Auto-fix failed"

        ui = MagicMock()
        ui.print_status = MagicMock()
        ui.muted = lambda x: x
        task_logger = MagicMock()

        validator = MagicMock()
        validator.validate_all.return_value = [
            ValidationResult(
                valid=False, checkpoint="spec",
                errors=["Missing section"],
                warnings=[],
                fixes=["Add ## Overview section"]
            ),
        ]

        executor = FakePlanningExecutor(
            spec_dir=spec_dir,
            ui=ui,
            task_logger=task_logger,
            spec_validator=validator,
            run_agent_fn=mock_run_agent,
        )

        result = await executor.phase_validation()

        # Should fail with errors
        assert result.success is False
        assert len(result.errors) > 0
        # The auto-fix agent should have been called with fix suggestions
        assert call_count[0] > 0

    async def test_phase_validation_partial_pass(self, tmp_path):
        """Test phase_validation with some checks passing, some failing"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        (spec_dir / "spec.md").write_text("# Valid Spec", encoding="utf-8")
        (spec_dir / "requirements.json").write_text('{}', encoding="utf-8")

        async def mock_run_agent(*args, **kwargs):
            return False, "Fix failed"

        ui = MagicMock()
        ui.print_status = MagicMock()
        ui.muted = lambda x: x
        task_logger = MagicMock()

        validator = MagicMock()
        validator.validate_all.return_value = [
            ValidationResult(valid=True, checkpoint="spec", errors=[], warnings=[], fixes=[]),
            ValidationResult(valid=False, checkpoint="context", errors=["Missing context"], warnings=[], fixes=[]),
        ]

        executor = FakePlanningExecutor(
            spec_dir=spec_dir,
            ui=ui,
            task_logger=task_logger,
            spec_validator=validator,
            run_agent_fn=mock_run_agent,
        )

        result = await executor.phase_validation()

        assert result.success is False
        assert "context" in result.errors[0] or "Missing context" in result.errors[0]
