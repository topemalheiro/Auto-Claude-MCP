"""Tests for project/__init__.py - Module facade exports."""

import pytest

from project import (
    ProjectAnalyzer,
    SecurityProfile,
    TechnologyStack,
    get_or_create_profile,
    is_command_allowed,
    needs_validation,
    VALIDATED_COMMANDS,
)


class TestProjectModuleExports:
    """Tests for project module public API exports."""

    def test_project_analyzer_export(self):
        """Test that ProjectAnalyzer is exported."""
        assert ProjectAnalyzer is not None

    def test_security_profile_export(self):
        """Test that SecurityProfile is exported."""
        assert SecurityProfile is not None

    def test_technology_stack_export(self):
        """Test that TechnologyStack is exported."""
        assert TechnologyStack is not None

    def test_get_or_create_profile_export(self):
        """Test that get_or_create_profile is exported."""
        assert get_or_create_profile is not None

    def test_is_command_allowed_export(self):
        """Test that is_command_allowed is exported."""
        assert is_command_allowed is not None

    def test_needs_validation_export(self):
        """Test that needs_validation is exported."""
        assert needs_validation is not None

    def test_validated_commands_export(self):
        """Test that VALIDATED_COMMANDS is exported."""
        assert isinstance(VALIDATED_COMMANDS, dict)
        assert len(VALIDATED_COMMANDS) > 0

    def test_module_has_all_attribute(self):
        """Test that module has __all__ attribute."""
        import project

        assert hasattr(project, "__all__")
        assert isinstance(project.__all__, list)

    def test_all_exports_exist(self):
        """Test that all exports in __all__ actually exist."""
        import project

        for name in project.__all__:
            assert hasattr(project, name), f"{name} in __all__ but not exported"


class TestProjectModuleImports:
    """Tests for project module import structure."""

    def test_import_from_project_submodules(self):
        """Test that key classes can be imported from submodules."""
        from project.analyzer import ProjectAnalyzer as DirectProjectAnalyzer
        from project.models import SecurityProfile as DirectSecurityProfile

        assert DirectProjectAnalyzer is ProjectAnalyzer
        assert DirectSecurityProfile is SecurityProfile

    def test_cross_module_imports_work(self):
        """Test that cross-module imports work correctly."""
        from project import get_or_create_profile
        from project.models import SecurityProfile

        # Ensure the function exists and can accept the expected arguments
        assert callable(get_or_create_profile)
        assert SecurityProfile is not None


class TestProjectModuleFacade:
    """Tests for project module as a facade."""

    def test_facade_pattern(self):
        """Test that project module acts as a facade to submodules."""
        # The project module should re-export from its submodules
        from project import ProjectAnalyzer
        from project.analyzer import ProjectAnalyzer as AnalyzerFromSubmodule

        # Both should be the same class
        assert ProjectAnalyzer is AnalyzerFromSubmodule

    def test_no_circular_imports(self):
        """Test that importing project module doesn't cause circular imports."""
        import importlib
        import sys

        # Remove from cache if present
        if "project" in sys.modules:
            del sys.modules["project"]

        # Should import without issues
        import project

        assert project is not None


class TestProjectModuleConstants:
    """Tests for constants exported from project module."""

    def test_validated_commands_is_dict(self):
        """Test that VALIDATED_COMMANDS is a dictionary."""
        assert isinstance(VALIDATED_COMMANDS, dict)

    def test_validated_commands_has_expected_entries(self):
        """Test that VALIDATED_COMMANDS has expected command validators."""
        assert "rm" in VALIDATED_COMMANDS
        assert "chmod" in VALIDATED_COMMANDS
        assert "kill" in VALIDATED_COMMANDS
        assert VALIDATED_COMMANDS["rm"] == "validate_rm"


class TestProjectModuleUtilityFunctions:
    """Tests for utility functions in project module."""

    def test_is_command_allowed_signature(self):
        """Test that is_command_allowed has correct signature."""
        import inspect

        sig = inspect.signature(is_command_allowed)
        params = list(sig.parameters.keys())

        assert "command" in params
        assert "profile" in params

    def test_needs_validation_signature(self):
        """Test that needs_validation has correct signature."""
        import inspect

        sig = inspect.signature(needs_validation)
        params = list(sig.parameters.keys())

        assert "command" in params

    def test_get_or_create_profile_signature(self):
        """Test that get_or_create_profile has correct signature."""
        import inspect

        sig = inspect.signature(get_or_create_profile)
        params = list(sig.parameters.keys())

        assert "project_dir" in params
        assert "spec_dir" in params
        assert "force_reanalyze" in params
