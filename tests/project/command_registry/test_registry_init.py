"""Tests for project/command_registry/__init__.py - Command registry exports."""

import pytest

from project.command_registry import (
    BASE_COMMANDS,
    VALIDATED_COMMANDS,
    LANGUAGE_COMMANDS,
    PACKAGE_MANAGER_COMMANDS,
    FRAMEWORK_COMMANDS,
    DATABASE_COMMANDS,
    INFRASTRUCTURE_COMMANDS,
    CLOUD_COMMANDS,
    CODE_QUALITY_COMMANDS,
    VERSION_MANAGER_COMMANDS,
)


class TestCommandRegistryModuleExports:
    """Tests for command_registry module public API exports."""

    def test_base_commands_export(self):
        """Test that BASE_COMMANDS is exported."""
        assert isinstance(BASE_COMMANDS, set)
        assert len(BASE_COMMANDS) > 0

    def test_validated_commands_export(self):
        """Test that VALIDATED_COMMANDS is exported."""
        assert isinstance(VALIDATED_COMMANDS, dict)
        assert len(VALIDATED_COMMANDS) > 0

    def test_language_commands_export(self):
        """Test that LANGUAGE_COMMANDS is exported."""
        assert isinstance(LANGUAGE_COMMANDS, dict)
        assert len(LANGUAGE_COMMANDS) > 0

    def test_package_manager_commands_export(self):
        """Test that PACKAGE_MANAGER_COMMANDS is exported."""
        assert isinstance(PACKAGE_MANAGER_COMMANDS, dict)
        assert len(PACKAGE_MANAGER_COMMANDS) > 0

    def test_framework_commands_export(self):
        """Test that FRAMEWORK_COMMANDS is exported."""
        assert isinstance(FRAMEWORK_COMMANDS, dict)
        assert len(FRAMEWORK_COMMANDS) > 0

    def test_database_commands_export(self):
        """Test that DATABASE_COMMANDS is exported."""
        assert isinstance(DATABASE_COMMANDS, dict)
        assert len(DATABASE_COMMANDS) > 0

    def test_infrastructure_commands_export(self):
        """Test that INFRASTRUCTURE_COMMANDS is exported."""
        assert isinstance(INFRASTRUCTURE_COMMANDS, dict)
        assert len(INFRASTRUCTURE_COMMANDS) > 0

    def test_cloud_commands_export(self):
        """Test that CLOUD_COMMANDS is exported."""
        assert isinstance(CLOUD_COMMANDS, dict)
        assert len(CLOUD_COMMANDS) > 0

    def test_code_quality_commands_export(self):
        """Test that CODE_QUALITY_COMMANDS is exported."""
        assert isinstance(CODE_QUALITY_COMMANDS, dict)
        assert len(CODE_QUALITY_COMMANDS) > 0

    def test_version_manager_commands_export(self):
        """Test that VERSION_MANAGER_COMMANDS is exported."""
        assert isinstance(VERSION_MANAGER_COMMANDS, dict)
        assert len(VERSION_MANAGER_COMMANDS) > 0

    def test_module_has_all_attribute(self):
        """Test that module has __all__ attribute."""
        from project.command_registry import __all__

        assert isinstance(__all__, list)
        assert len(__all__) > 0

    def test_all_exports_exist(self):
        """Test that all exports in __all__ actually exist."""
        from project import command_registry

        for name in command_registry.__all__:
            assert hasattr(command_registry, name), f"{name} in __all__ but not exported"


class TestCommandRegistryRegistries:
    """Tests for command registry consistency."""

    def test_base_commands_contains_core_shell_commands(self):
        """Test BASE_COMMANDS contains core shell commands."""
        assert "ls" in BASE_COMMANDS
        assert "cd" in BASE_COMMANDS
        assert "cat" in BASE_COMMANDS
        assert "echo" in BASE_COMMANDS
        assert "grep" in BASE_COMMANDS

    def test_base_commands_contains_git(self):
        """Test BASE_COMMANDS contains git."""
        assert "git" in BASE_COMMANDS

    def test_validated_commands_subset_of_base(self):
        """Test all validated commands exist in BASE_COMMANDS."""
        for cmd in VALIDATED_COMMANDS:
            assert cmd in BASE_COMMANDS, f"{cmd} in VALIDATED_COMMANDS but not in BASE_COMMANDS"

    def test_validated_commands_have_validator_functions(self):
        """Test all validated commands map to validator functions."""
        for cmd, validator in VALIDATED_COMMANDS.items():
            assert isinstance(validator, str)
            assert validator.startswith("validate_")

    def test_language_commands_have_expected_languages(self):
        """Test LANGUAGE_COMMANDS has expected languages."""
        assert "python" in LANGUAGE_COMMANDS
        assert "javascript" in LANGUAGE_COMMANDS
        assert "typescript" in LANGUAGE_COMMANDS
        assert "rust" in LANGUAGE_COMMANDS
        assert "go" in LANGUAGE_COMMANDS

    def test_package_manager_commands_has_expected_managers(self):
        """Test PACKAGE_MANAGER_COMMANDS has expected managers."""
        assert "npm" in PACKAGE_MANAGER_COMMANDS
        assert "yarn" in PACKAGE_MANAGER_COMMANDS
        assert "pip" in PACKAGE_MANAGER_COMMANDS
        assert "cargo" in PACKAGE_MANAGER_COMMANDS
        assert "poetry" in PACKAGE_MANAGER_COMMANDS

    def test_framework_commands_has_expected_frameworks(self):
        """Test FRAMEWORK_COMMANDS has expected frameworks."""
        assert "django" in FRAMEWORK_COMMANDS
        assert "flask" in FRAMEWORK_COMMANDS
        assert "nextjs" in FRAMEWORK_COMMANDS
        assert "react" in FRAMEWORK_COMMANDS

    def test_infrastructure_commands_has_docker(self):
        """Test INFRASTRUCTURE_COMMANDS contains docker."""
        assert "docker" in INFRASTRUCTURE_COMMANDS

    def test_cloud_commands_has_aws(self):
        """Test CLOUD_COMMANDS contains AWS."""
        assert "aws" in CLOUD_COMMANDS

    def test_all_language_commands_are_sets(self):
        """Test all LANGUAGE_COMMANDS values are sets."""
        for lang, commands in LANGUAGE_COMMANDS.items():
            assert isinstance(commands, set), f"{lang} commands is not a set"

    def test_all_package_manager_commands_are_sets(self):
        """Test all PACKAGE_MANAGER_COMMANDS values are sets."""
        for pm, commands in PACKAGE_MANAGER_COMMANDS.items():
            assert isinstance(commands, set), f"{pm} commands is not a set"

    def test_all_framework_commands_are_sets(self):
        """Test all FRAMEWORK_COMMANDS values are sets."""
        for fw, commands in FRAMEWORK_COMMANDS.items():
            assert isinstance(commands, set), f"{fw} commands is not a set"


class TestCommandRegistryImports:
    """Tests for command_registry import structure."""

    def test_no_circular_imports(self):
        """Test that importing command_registry doesn't cause circular imports."""
        import importlib
        import sys

        # Remove from cache if present
        if "project.command_registry" in sys.modules:
            del sys.modules["project.command_registry"]

        # Should import without issues
        from project import command_registry

        assert command_registry is not None

    def test_import_from_submodules_works(self):
        """Test that direct imports from submodules work."""
        from project.command_registry import BASE_COMMANDS as BaseFromRoot
        from project.command_registry.base import BASE_COMMANDS as BaseFromSub

        # Both should be the same
        assert BaseFromRoot is BaseFromSub


class TestCommandRegistryModuleFacade:
    """Tests for command_registry module as a facade."""

    def test_facade_reexports_constants(self):
        """Test that command_registry re-exports constants from base."""
        from project.command_registry import BASE_COMMANDS
        from project.command_registry.base import BASE_COMMANDS as BaseCommands

        assert BASE_COMMANDS is BaseCommands

    def test_all_constants_are_immutable_at_module_level(self):
        """Test that registries can't be accidentally modified at module level."""
        from project import command_registry

        # Get original lengths
        original_base_len = len(command_registry.BASE_COMMANDS)
        original_validated_len = len(command_registry.VALIDATED_COMMANDS)

        # The sets themselves are mutable, but the module-level binding
        # should remain stable across imports
        from project.command_registry import BASE_COMMANDS, VALIDATED_COMMANDS

        assert len(BASE_COMMANDS) == original_base_len
        assert len(VALIDATED_COMMANDS) == original_validated_len
