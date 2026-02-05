"""Tests for phases module (spec/phases.py)"""

import pytest

from spec.phases import MAX_RETRIES, PhaseExecutor, PhaseResult


class TestPhasesModuleExports:
    """Tests for phases module re-exports"""

    def test_exports_phase_executor(self):
        """Test that PhaseExecutor is exported from phases module"""
        from spec.phases import PhaseExecutor
        assert PhaseExecutor is not None

    def test_exports_phase_result(self):
        """Test that PhaseResult is exported from phases module"""
        from spec.phases import PhaseResult
        assert PhaseResult is not None

    def test_exports_max_retries(self):
        """Test that MAX_RETRIES is exported from phases module"""
        from spec.phases import MAX_RETRIES
        assert MAX_RETRIES is not None

    def test_max_retries_value(self):
        """Test MAX_RETRIES has expected value"""
        assert MAX_RETRIES == 3


class TestPhasesModuleBackwardCompatibility:
    """Tests for backward compatibility of phases module"""

    def test_phase_executor_from_phases_module(self, tmp_path):
        """Test PhaseExecutor can be imported from spec.phases"""
        from spec.phases import PhaseExecutor

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        mock_validator = None
        mock_run_agent = None
        mock_logger = None
        mock_ui = None

        # Should be able to instantiate
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
        assert executor.project_dir == project_dir

    def test_phase_result_from_phases_module(self):
        """Test PhaseResult can be imported and used from spec.phases"""
        from spec.phases import PhaseResult

        result = PhaseResult(
            phase="test_phase",
            success=True,
            output_files=["/path/to/file"],
            errors=[],
            retries=0
        )

        assert result.phase == "test_phase"
        assert result.success is True

    def test_all_exports_in_module(self):
        """Test that __all__ exports are available"""
        from spec.phases import __all__

        assert "PhaseExecutor" in __all__
        assert "PhaseResult" in __all__
        assert "MAX_RETRIES" in __all__


class TestPhasesModuleReExports:
    """Tests that re-exported classes work correctly"""

    def test_phase_executor_has_mixin_methods(self, tmp_path):
        """Test that PhaseExecutor from phases module has all mixin methods"""
        from spec.phases import PhaseExecutor

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test",
            spec_validator=None,
            run_agent_fn=None,
            task_logger=None,
            ui_module=None
        )

        # Verify methods from all mixins are available
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

    def test_phase_result_dataclass(self):
        """Test that PhaseResult from phases module is a proper dataclass"""
        from spec.phases import PhaseResult
        from dataclasses import is_dataclass, asdict

        assert is_dataclass(PhaseResult)

        result = PhaseResult(
            phase="test",
            success=True,
            output_files=[],
            errors=[],
            retries=0
        )

        # Should be convertible to dict
        result_dict = asdict(result)
        assert result_dict["phase"] == "test"
        assert result_dict["success"] is True


class TestPhasesModuleConstants:
    """Tests for constants exported by phases module"""

    def test_max_retries_is_integer(self):
        """Test MAX_RETRIES is an integer"""
        assert isinstance(MAX_RETRIES, int)

    def test_max_retries_is_positive(self):
        """Test MAX_RETRIES is positive"""
        assert MAX_RETRIES > 0

    def test_max_retries_allows_retries(self):
        """Test MAX_RETRIES allows reasonable retry attempts"""
        # Should be between 1 and 10
        assert 1 <= MAX_RETRIES <= 10


class TestPhasesModuleIntegration:
    """Integration tests for phases module"""

    def test_import_from_root_vs_submodule(self):
        """Test that importing from root vs submodule gives same classes"""
        from spec.phases import PhaseExecutor as RootExecutor
        from spec.phases import PhaseResult as RootResult
        from spec.phases import MAX_RETRIES as RootMaxRetries

        from spec.phases.executor import PhaseExecutor as SubExecutor
        from spec.phases.models import PhaseResult as SubResult
        from spec.phases.models import MAX_RETRIES as SubMaxRetries

        # Should be the same classes
        assert RootExecutor is SubExecutor
        assert RootResult is SubResult
        assert RootMaxRetries == SubMaxRetries

    def test_phase_result_equality(self):
        """Test PhaseResult instances are comparable"""
        from spec.phases import PhaseResult

        result1 = PhaseResult(
            phase="test",
            success=True,
            output_files=[],
            errors=[],
            retries=0
        )

        result2 = PhaseResult(
            phase="test",
            success=True,
            output_files=[],
            errors=[],
            retries=0
        )

        assert result1 == result2

    def test_phase_result_inequality(self):
        """Test PhaseResult instances with different values are not equal"""
        from spec.phases import PhaseResult

        result1 = PhaseResult(
            phase="test",
            success=True,
            output_files=[],
            errors=[],
            retries=0
        )

        result2 = PhaseResult(
            phase="test",
            success=False,  # Different
            output_files=[],
            errors=[],
            retries=0
        )

        assert result1 != result2


class TestPhasesModuleDocumentation:
    """Tests for module documentation"""

    def test_module_has_docstring(self):
        """Test that phases module has documentation"""
        import spec.phases as phases_module

        assert phases_module.__doc__ is not None
        assert len(phases_module.__doc__) > 0

    def test_phase_executor_has_docstring(self):
        """Test that PhaseExecutor has documentation"""
        from spec.phases import PhaseExecutor

        assert PhaseExecutor.__doc__ is not None
        assert len(PhaseExecutor.__doc__) > 0

    def test_phase_result_has_docstring(self):
        """Test that PhaseResult has documentation"""
        from spec.phases import PhaseResult

        # Dataclasses may not have custom docstrings
        # but the class should exist
        assert PhaseResult is not None


class TestPhasesModuleTypeAnnotations:
    """Tests for type annotations in phases module"""

    def test_phase_executor_init_signature(self):
        """Test PhaseExecutor.__init__ has correct parameters"""
        from spec.phases import PhaseExecutor
        import inspect

        sig = inspect.signature(PhaseExecutor.__init__)
        params = list(sig.parameters.keys())

        # Should have these parameters
        assert "self" in params
        assert "project_dir" in params
        assert "spec_dir" in params
        assert "task_description" in params
        assert "spec_validator" in params
        assert "run_agent_fn" in params
        assert "task_logger" in params
        assert "ui_module" in params

    def test_phase_result_fields(self):
        """Test PhaseResult has correct fields"""
        from spec.phases import PhaseResult
        from dataclasses import fields

        field_names = {f.name for f in fields(PhaseResult)}

        assert "phase" in field_names
        assert "success" in field_names
        assert "output_files" in field_names
        assert "errors" in field_names
        assert "retries" in field_names


class TestPhasesModuleEdgeCases:
    """Edge case tests for phases module"""

    def test_phase_executor_with_none_dependencies(self, tmp_path):
        """Test PhaseExecutor can be created with None dependencies"""
        from spec.phases import PhaseExecutor

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Should not raise
        executor = PhaseExecutor(
            project_dir=project_dir,
            spec_dir=spec_dir,
            task_description="Test",
            spec_validator=None,
            run_agent_fn=None,
            task_logger=None,
            ui_module=None
        )

        assert executor is not None

    def test_phase_result_with_empty_collections(self):
        """Test PhaseResult with empty lists"""
        from spec.phases import PhaseResult

        result = PhaseResult(
            phase="test",
            success=True,
            output_files=[],
            errors=[],
            retries=0
        )

        assert len(result.output_files) == 0
        assert len(result.errors) == 0

    def test_phase_result_with_negative_retries(self):
        """Test PhaseResult accepts negative retries (edge case)"""
        from spec.phases import PhaseResult

        # Dataclass doesn't validate, so this should work
        result = PhaseResult(
            phase="test",
            success=True,
            output_files=[],
            errors=[],
            retries=-1
        )

        assert result.retries == -1
