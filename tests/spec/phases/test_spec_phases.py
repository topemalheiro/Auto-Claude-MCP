"""Tests for spec_phases module"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from spec.phases.spec_phases import SpecPhaseMixin
from spec.phases.models import PhaseResult
from spec.validate_pkg.models import ValidationResult


class FakeSpecExecutor(SpecPhaseMixin):
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
class TestSpecPhaseMixin:
    """Tests for SpecPhaseMixin"""

    async def test_phase_quick_spec_success(self, tmp_path):
        """Test quick_spec phase creates spec.md"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        async def mock_run_agent(*args, **kwargs):
            spec_file = spec_dir / "spec.md"
            spec_file.write_text("# Quick Spec\n\nContent", encoding="utf-8")
            return True, "Spec created"

        ui = MagicMock()
        ui.print_status = MagicMock()
        task_logger = MagicMock()
        validator = MagicMock()
        validator.validate_spec_document.return_value = ValidationResult(
            valid=True, checkpoint="spec", errors=[], warnings=[], fixes=[]
        )

        executor = FakeSpecExecutor(
            spec_dir=spec_dir,
            ui=ui,
            task_logger=task_logger,
            spec_validator=validator,
            run_agent_fn=mock_run_agent,
        )

        result = await executor.phase_quick_spec()

        assert result.success is True
        assert result.phase == "quick_spec"
        assert (spec_dir / "spec.md").exists()

    async def test_phase_spec_writing_success(self, tmp_path):
        """Test spec_writing phase creates detailed spec"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create requirements
        req_file = spec_dir / "requirements.json"
        req_file.write_text('{"task_description": "Build feature"}', encoding="utf-8")

        async def mock_run_agent(*args, **kwargs):
            spec_file = spec_dir / "spec.md"
            spec_file.write_text("# Detailed Spec\n\nFull content here", encoding="utf-8")
            return True, "Spec written"

        ui = MagicMock()
        ui.print_status = MagicMock()
        task_logger = MagicMock()
        validator = MagicMock()
        validator.validate_spec_document.return_value = ValidationResult(
            valid=True, checkpoint="spec", errors=[], warnings=[], fixes=[]
        )

        executor = FakeSpecExecutor(
            spec_dir=spec_dir,
            ui=ui,
            task_logger=task_logger,
            spec_validator=validator,
            run_agent_fn=mock_run_agent,
        )

        result = await executor.phase_spec_writing()

        assert result.success is True
        assert result.phase == "spec_writing"

    async def test_phase_self_critique_creates_report(self, tmp_path):
        """Test self_critique phase creates critique report"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create spec.md
        spec_file = spec_dir / "spec.md"
        spec_file.write_text("# Spec", encoding="utf-8")

        async def mock_run_agent(*args, **kwargs):
            critique_file = spec_dir / "critique_notes.md"
            critique_file.write_text("Critique notes", encoding="utf-8")
            return True, "Critique done"

        ui = MagicMock()
        ui.print_status = MagicMock()
        task_logger = MagicMock()

        executor = FakeSpecExecutor(
            spec_dir=spec_dir,
            ui=ui,
            task_logger=task_logger,
            run_agent_fn=mock_run_agent,
        )

        result = await executor.phase_self_critique()

        assert result.success is True
        assert result.phase == "self_critique"
        assert (spec_dir / "critique_notes.md").exists()

    async def test_phase_self_critique_skips_with_no_issues_flag(self, tmp_path):
        """Test self_critique skips when critique report already exists with no issues"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create spec and critique report with no_issues_found=true
        (spec_dir / "spec.md").write_text("# Spec", encoding="utf-8")
        import json
        critique_file = spec_dir / "critique_report.json"
        critique_file.write_text(
            json.dumps({"no_issues_found": True, "issues_fixed": False}),
            encoding="utf-8"
        )

        ui = MagicMock()
        ui.print_status = MagicMock()
        task_logger = MagicMock()

        executor = FakeSpecExecutor(
            spec_dir=spec_dir, ui=ui, task_logger=task_logger
        )

        result = await executor.phase_self_critique()

        # Should skip if already has no_issues_found=true
        assert result.success is True
        assert result.phase == "self_critique"

    # ==================== Additional phase_quick_spec tests ====================

    async def test_phase_quick_spec_existing_files_skips(self, tmp_path):
        """Test phase_quick_spec skips when spec.md and plan.json exist"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create existing files
        (spec_dir / "spec.md").write_text("# Existing Spec", encoding="utf-8")
        (spec_dir / "implementation_plan.json").write_text(
            '{"phases": []}', encoding="utf-8"
        )

        ui = MagicMock()
        ui.print_status = MagicMock()
        task_logger = MagicMock()

        executor = FakeSpecExecutor(
            spec_dir=spec_dir, ui=ui, task_logger=task_logger
        )

        result = await executor.phase_quick_spec()

        assert result.success is True
        assert result.phase == "quick_spec"
        assert result.retries == 0
        ui.print_status.assert_called_with("Quick spec already exists", "success")

    async def test_phase_quick_spec_agent_retries(self, tmp_path):
        """Test phase_quick_spec with agent retries before success"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        attempts = [0]

        async def mock_run_agent(*args, **kwargs):
            attempts[0] += 1
            if attempts[0] == 1:
                return False, "First attempt failed"
            # Create spec on second attempt
            (spec_dir / "spec.md").write_text("# Quick Spec", encoding="utf-8")
            return True, "Spec created"

        ui = MagicMock()
        ui.print_status = MagicMock()
        task_logger = MagicMock()

        executor = FakeSpecExecutor(
            spec_dir=spec_dir, ui=ui, task_logger=task_logger, run_agent_fn=mock_run_agent
        )

        result = await executor.phase_quick_spec()

        assert result.success is True
        assert result.retries == 1

    async def test_phase_quick_spec_creates_minimal_plan(self, tmp_path):
        """Test phase_quick_spec creates minimal plan if agent doesn't"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        async def mock_run_agent(*args, **kwargs):
            # Agent creates spec but not plan
            (spec_dir / "spec.md").write_text("# Quick Spec", encoding="utf-8")
            return True, "Spec created"

        ui = MagicMock()
        ui.print_status = MagicMock()
        task_logger = MagicMock()

        executor = FakeSpecExecutor(
            spec_dir=spec_dir,
            task_description="Test task",
            ui=ui,
            task_logger=task_logger,
            run_agent_fn=mock_run_agent,
        )

        result = await executor.phase_quick_spec()

        assert result.success is True
        assert (spec_dir / "implementation_plan.json").exists()

    async def test_phase_quick_spec_all_retries_exhausted(self, tmp_path):
        """Test phase_quick_spec fails after all retries exhausted"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        async def mock_run_agent(*args, **kwargs):
            return False, "Agent failed"

        ui = MagicMock()
        ui.print_status = MagicMock()
        task_logger = MagicMock()

        executor = FakeSpecExecutor(
            spec_dir=spec_dir, ui=ui, task_logger=task_logger, run_agent_fn=mock_run_agent
        )

        result = await executor.phase_quick_spec()

        assert result.success is False
        assert len(result.errors) > 0

    # ==================== Additional phase_spec_writing tests ====================

    async def test_phase_spec_writing_existing_valid_skips(self, tmp_path):
        """Test phase_spec_writing skips when valid spec.md exists"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create valid spec
        (spec_dir / "spec.md").write_text("# Complete Spec\n\n## Overview\n\nContent", encoding="utf-8")

        ui = MagicMock()
        ui.print_status = MagicMock()
        task_logger = MagicMock()

        validator = MagicMock()
        validator.validate_spec_document.return_value = ValidationResult(
            valid=True, checkpoint="spec", errors=[], warnings=[], fixes=[]
        )

        executor = FakeSpecExecutor(
            spec_dir=spec_dir,
            ui=ui,
            task_logger=task_logger,
            spec_validator=validator,
        )

        result = await executor.phase_spec_writing()

        assert result.success is True
        assert result.retries == 0
        ui.print_status.assert_called_with("spec.md already exists and is valid", "success")

    async def test_phase_spec_writing_existing_invalid_regenerates(self, tmp_path):
        """Test phase_spec_writing regenerates when existing spec is invalid"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create invalid spec
        (spec_dir / "spec.md").write_text("# Invalid", encoding="utf-8")

        async def mock_run_agent(*args, **kwargs):
            (spec_dir / "spec.md").write_text(
                "# Complete Spec\n\n## Overview\n\nFull content", encoding="utf-8"
            )
            return True, "Spec written"

        ui = MagicMock()
        ui.print_status = MagicMock()
        task_logger = MagicMock()

        validator = MagicMock()
        # First call: invalid (triggers regeneration), second call: valid
        validator.validate_spec_document.side_effect = [
            ValidationResult(
                valid=False, checkpoint="spec",
                errors=["Incomplete"], warnings=[], fixes=[]
            ),
            ValidationResult(
                valid=True, checkpoint="spec", errors=[], warnings=[], fixes=[]
            )
        ]

        executor = FakeSpecExecutor(
            spec_dir=spec_dir,
            ui=ui,
            task_logger=task_logger,
            spec_validator=validator,
            run_agent_fn=mock_run_agent,
        )

        result = await executor.phase_spec_writing()

        assert result.success is True
        ui.print_status.assert_any_call(
            "spec.md exists but has issues, regenerating...", "warning"
        )

    async def test_phase_spec_writing_agent_retries(self, tmp_path):
        """Test phase_spec_writing with agent retries before success"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        attempts = [0]

        async def mock_run_agent(*args, **kwargs):
            attempts[0] += 1
            if attempts[0] == 1:
                return False, "First attempt failed"
            (spec_dir / "spec.md").write_text("# Valid Spec", encoding="utf-8")
            return True, "Spec written"

        ui = MagicMock()
        ui.print_status = MagicMock()
        task_logger = MagicMock()

        validator = MagicMock()
        validator.validate_spec_document.return_value = ValidationResult(
            valid=True, checkpoint="spec", errors=[], warnings=[], fixes=[]
        )

        executor = FakeSpecExecutor(
            spec_dir=spec_dir,
            ui=ui,
            task_logger=task_logger,
            spec_validator=validator,
            run_agent_fn=mock_run_agent,
        )

        result = await executor.phase_spec_writing()

        assert result.success is True
        assert result.retries == 1

    async def test_phase_spec_writing_all_retries_exhausted(self, tmp_path):
        """Test phase_spec_writing fails after all retries exhausted"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        async def mock_run_agent(*args, **kwargs):
            return False, "Agent failed"

        ui = MagicMock()
        ui.print_status = MagicMock()
        task_logger = MagicMock()

        validator = MagicMock()
        validator.validate_spec_document.return_value = ValidationResult(
            valid=False, checkpoint="spec", errors=["Invalid spec"], warnings=[], fixes=[]
        )

        executor = FakeSpecExecutor(
            spec_dir=spec_dir,
            ui=ui,
            task_logger=task_logger,
            spec_validator=validator,
            run_agent_fn=mock_run_agent,
        )

        result = await executor.phase_spec_writing()

        assert result.success is False
        assert len(result.errors) > 0

    # ==================== Additional phase_self_critique tests ====================

    async def test_phase_self_critique_no_spec_returns_error(self, tmp_path):
        """Test phase_self_critique returns error when spec.md doesn't exist"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        ui = MagicMock()
        ui.print_status = MagicMock()
        task_logger = MagicMock()

        executor = FakeSpecExecutor(
            spec_dir=spec_dir, ui=ui, task_logger=task_logger
        )

        result = await executor.phase_self_critique()

        assert result.success is False
        assert result.errors == ["spec.md does not exist"]
        ui.print_status.assert_called_with("No spec.md to critique", "error")

    async def test_phase_self_critique_existing_issues_fixed_skips(self, tmp_path):
        """Test phase_self_critique skips when critique report has issues_fixed=true"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        (spec_dir / "spec.md").write_text("# Spec", encoding="utf-8")

        import json
        critique_file = spec_dir / "critique_report.json"
        critique_file.write_text(
            json.dumps({"no_issues_found": False, "issues_fixed": True}),
            encoding="utf-8"
        )

        ui = MagicMock()
        ui.print_status = MagicMock()
        task_logger = MagicMock()

        executor = FakeSpecExecutor(
            spec_dir=spec_dir, ui=ui, task_logger=task_logger
        )

        result = await executor.phase_self_critique()

        assert result.success is True
        ui.print_status.assert_called_with("Self-critique already completed", "success")

    async def test_phase_self_critique_agent_success_validates_spec(self, tmp_path):
        """Test phase_self_critique agent success and validates spec"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        (spec_dir / "spec.md").write_text("# Spec", encoding="utf-8")

        async def mock_run_agent(*args, **kwargs):
            # Agent creates critique report
            import json
            critique_file = spec_dir / "critique_report.json"
            critique_file.write_text(
                json.dumps({
                    "issues_found": ["Minor issue"],
                    "issues_fixed": True,
                    "no_issues_found": False,
                    "critique_summary": "Fixed minor issues"
                }),
                encoding="utf-8"
            )
            return True, "Critique complete"

        ui = MagicMock()
        ui.print_status = MagicMock()
        task_logger = MagicMock()

        validator = MagicMock()
        validator.validate_spec_document.return_value = ValidationResult(
            valid=True, checkpoint="spec", errors=[], warnings=[], fixes=[]
        )

        executor = FakeSpecExecutor(
            spec_dir=spec_dir,
            ui=ui,
            task_logger=task_logger,
            spec_validator=validator,
            run_agent_fn=mock_run_agent,
        )

        result = await executor.phase_self_critique()

        assert result.success is True
        ui.print_status.assert_called_with(
            "Self-critique completed, spec is valid", "success"
        )

    async def test_phase_self_critique_creates_minimal_critique(self, tmp_path):
        """Test phase_self_critique creates minimal critique when agent succeeds but no file"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        (spec_dir / "spec.md").write_text("# Spec", encoding="utf-8")

        async def mock_run_agent(*args, **kwargs):
            # Agent succeeds but doesn't create critique file
            return True, "No issues found"

        ui = MagicMock()
        ui.print_status = MagicMock()
        task_logger = MagicMock()

        validator = MagicMock()
        validator.validate_spec_document.return_value = ValidationResult(
            valid=True, checkpoint="spec", errors=[], warnings=[], fixes=[]
        )

        executor = FakeSpecExecutor(
            spec_dir=spec_dir,
            ui=ui,
            task_logger=task_logger,
            spec_validator=validator,
            run_agent_fn=mock_run_agent,
        )

        result = await executor.phase_self_critique()

        assert result.success is True
        # Minimal critique should be created
        assert (spec_dir / "critique_report.json").exists()

    async def test_phase_self_critique_all_retries_exhausted(self, tmp_path):
        """Test phase_self_critique after all retries exhausted"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        (spec_dir / "spec.md").write_text("# Spec", encoding="utf-8")

        async def mock_run_agent(*args, **kwargs):
            return False, "Agent failed"

        ui = MagicMock()
        ui.print_status = MagicMock()
        task_logger = MagicMock()

        validator = MagicMock()
        validator.validate_spec_document.return_value = ValidationResult(
            valid=False, checkpoint="spec", errors=["Invalid"], warnings=[], fixes=[]
        )

        executor = FakeSpecExecutor(
            spec_dir=spec_dir,
            ui=ui,
            task_logger=task_logger,
            spec_validator=validator,
            run_agent_fn=mock_run_agent,
        )

        result = await executor.phase_self_critique()

        # Still returns True because it creates minimal critique
        assert result.success is True
        assert (spec_dir / "critique_report.json").exists()
        assert len(result.errors) > 0
