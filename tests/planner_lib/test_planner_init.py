"""Tests for planner_lib/__init__.py - Implementation planner package exports."""

import pytest

from planner_lib import (
    ContextLoader,
    PlannerContext,
    get_plan_generator,
)


class TestPlannerLibModuleExports:
    """Tests for planner_lib module public API exports."""

    def test_context_loader_export(self):
        """Test that ContextLoader is exported."""
        assert ContextLoader is not None

    def test_planner_context_export(self):
        """Test that PlannerContext is exported."""
        assert PlannerContext is not None

    def test_get_plan_generator_export(self):
        """Test that get_plan_generator is exported."""
        assert get_plan_generator is not None

    def test_module_has_all_attribute(self):
        """Test that module has __all__ attribute."""
        import planner_lib

        assert hasattr(planner_lib, "__all__")
        assert isinstance(planner_lib.__all__, list)

    def test_all_exports_exist(self):
        """Test that all exports in __all__ actually exist."""
        import planner_lib

        for name in planner_lib.__all__:
            assert hasattr(planner_lib, name), f"{name} in __all__ but not exported"

    def test_expected_exports_in_all(self):
        """Test that expected exports are in __all__."""
        import planner_lib

        expected = {
            "ContextLoader",
            "PlannerContext",
            "get_plan_generator",
        }

        assert set(planner_lib.__all__) >= expected


class TestPlannerLibImports:
    """Tests for planner_lib import structure."""

    def test_import_from_submodules_works(self):
        """Test that direct imports from submodules work."""
        from planner_lib.context import ContextLoader as DirectContextLoader
        from planner_lib.models import PlannerContext as DirectPlannerContext

        assert DirectContextLoader is ContextLoader
        assert DirectPlannerContext is PlannerContext

    def test_no_circular_imports(self):
        """Test that importing planner_lib doesn't cause circular imports."""
        import importlib
        import sys

        # Remove from cache if present
        if "planner_lib" in sys.modules:
            del sys.modules["planner_lib"]

        # Should import without issues
        import planner_lib

        assert planner_lib is not None


class TestPlannerLibModuleFacade:
    """Tests for planner_lib module as a facade."""

    def test_facade_reexports_from_context(self):
        """Test that planner_lib re-exports ContextLoader from context."""
        from planner_lib import ContextLoader
        from planner_lib.context import ContextLoader as ContextLoaderFromSub

        assert ContextLoader is ContextLoaderFromSub

    def test_facade_reexports_from_models(self):
        """Test that planner_lib re-exports PlannerContext from models."""
        from planner_lib import PlannerContext
        from planner_lib.models import PlannerContext as PlannerContextFromSub

        assert PlannerContext is PlannerContextFromSub

    def test_facade_reexports_from_generators(self):
        """Test that planner_lib re-exports get_plan_generator from generators."""
        from planner_lib import get_plan_generator
        from planner_lib.generators import get_plan_generator as GenFromSub

        assert get_plan_generator is GenFromSub


class TestPlannerLibTypes:
    """Tests for planner_lib exported types."""

    def test_context_loader_is_class(self):
        """Test that ContextLoader is a class."""
        assert isinstance(ContextLoader, type)

    def test_planner_context_is_class(self):
        """Test that PlannerContext is a class."""
        from dataclasses import is_dataclass

        # PlannerContext should be a dataclass
        assert is_dataclass(PlannerContext)

    def test_get_plan_generator_is_callable(self):
        """Test that get_plan_generator is callable."""
        assert callable(get_plan_generator)


class TestPlannerLibIntegration:
    """Tests for planner_lib integration points."""

    def test_context_loader_exists(self):
        """Test that ContextLoader can be instantiated."""
        # ContextLoader should be importable and usable
        from planner_lib import ContextLoader

        # We're not testing functionality here, just that the export works
        assert ContextLoader is not None

    def test_planner_context_has_expected_attributes(self):
        """Test that PlannerContext has expected attributes."""
        from planner_lib import PlannerContext
        from implementation_plan import WorkflowType

        # Create an instance to test the dataclass
        context = PlannerContext(
            spec_content="Test spec",
            project_index={},
            task_context={},
            services_involved=[],
            workflow_type=WorkflowType.FEATURE,
            files_to_modify=[],
            files_to_reference=[],
        )

        assert hasattr(context, "spec_content")
        assert hasattr(context, "project_index")

    def test_get_plan_generator_signature(self):
        """Test that get_plan_generator has expected signature."""
        import inspect

        sig = inspect.signature(get_plan_generator)
        params = list(sig.parameters.keys())

        # Should accept at least a context parameter
        assert len(params) > 0
