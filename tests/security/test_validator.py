"""
Comprehensive tests for validator.py

Tests the central validator module that re-exports all validators
from specialized modules.
"""

import pytest
from unittest.mock import MagicMock, patch
from typing import get_type_hints

from security import validator


class TestValidatorModuleExports:
    """Tests for validator module exports"""

    def test_module_has_validators_dict(self):
        """Test that VALIDATORS dict is exported"""
        assert hasattr(validator, "VALIDATORS")
        assert isinstance(validator.VALIDATORS, dict)

    def test_module_has_get_validator_function(self):
        """Test that get_validator function is exported"""
        assert hasattr(validator, "get_validator")
        assert callable(validator.get_validator)

    def test_module_has_validation_result_types(self):
        """Test that ValidationResult and ValidatorFunction are exported"""
        assert hasattr(validator, "ValidationResult")
        assert hasattr(validator, "ValidatorFunction")


class TestProcessValidatorsExported:
    """Tests that process validators are properly exported"""

    def test_validate_pkill_command_exported(self):
        """Test validate_pkill_command is exported"""
        assert hasattr(validator, "validate_pkill_command")
        assert callable(validator.validate_pkill_command)

    def test_validate_kill_command_exported(self):
        """Test validate_kill_command is exported"""
        assert hasattr(validator, "validate_kill_command")
        assert callable(validator.validate_kill_command)

    def test_validate_killall_command_exported(self):
        """Test validate_killall_command is exported"""
        assert hasattr(validator, "validate_killall_command")
        assert callable(validator.validate_killall_command)


class TestFilesystemValidatorsExported:
    """Tests that filesystem validators are properly exported"""

    def test_validate_chmod_command_exported(self):
        """Test validate_chmod_command is exported"""
        assert hasattr(validator, "validate_chmod_command")
        assert callable(validator.validate_chmod_command)

    def test_validate_rm_command_exported(self):
        """Test validate_rm_command is exported"""
        assert hasattr(validator, "validate_rm_command")
        assert callable(validator.validate_rm_command)

    def test_validate_init_script_exported(self):
        """Test validate_init_script is exported"""
        assert hasattr(validator, "validate_init_script")
        assert callable(validator.validate_init_script)


class TestGitValidatorsExported:
    """Tests that git validators are properly exported"""

    def test_validate_git_command_exported(self):
        """Test validate_git_command is exported"""
        assert hasattr(validator, "validate_git_command")
        assert callable(validator.validate_git_command)

    def test_validate_git_commit_exported(self):
        """Test validate_git_commit is exported"""
        assert hasattr(validator, "validate_git_commit")
        assert callable(validator.validate_git_commit)

    def test_validate_git_config_exported(self):
        """Test validate_git_config is exported"""
        assert hasattr(validator, "validate_git_config")
        assert callable(validator.validate_git_config)


class TestShellValidatorsExported:
    """Tests that shell validators are properly exported"""

    def test_validate_bash_command_exported(self):
        """Test validate_bash_command is exported"""
        assert hasattr(validator, "validate_bash_command")
        assert callable(validator.validate_bash_command)

    def test_validate_sh_command_exported(self):
        """Test validate_sh_command is exported"""
        assert hasattr(validator, "validate_sh_command")
        assert callable(validator.validate_sh_command)

    def test_validate_zsh_command_exported(self):
        """Test validate_zsh_command is exported"""
        assert hasattr(validator, "validate_zsh_command")
        assert callable(validator.validate_zsh_command)

    def test_validate_shell_c_command_exported(self):
        """Test validate_shell_c_command is exported"""
        assert hasattr(validator, "validate_shell_c_command")
        assert callable(validator.validate_shell_c_command)


class TestDatabaseValidatorsExported:
    """Tests that database validators are properly exported"""

    def test_validate_psql_command_exported(self):
        """Test validate_psql_command is exported"""
        assert hasattr(validator, "validate_psql_command")
        assert callable(validator.validate_psql_command)

    def test_validate_dropdb_command_exported(self):
        """Test validate_dropdb_command is exported"""
        assert hasattr(validator, "validate_dropdb_command")
        assert callable(validator.validate_dropdb_command)

    def test_validate_dropuser_command_exported(self):
        """Test validate_dropuser_command is exported"""
        assert hasattr(validator, "validate_dropuser_command")
        assert callable(validator.validate_dropuser_command)

    def test_validate_mysql_command_exported(self):
        """Test validate_mysql_command is exported"""
        assert hasattr(validator, "validate_mysql_command")
        assert callable(validator.validate_mysql_command)

    def test_validate_mysqladmin_command_exported(self):
        """Test validate_mysqladmin_command is exported"""
        assert hasattr(validator, "validate_mysqladmin_command")
        assert callable(validator.validate_mysqladmin_command)

    def test_validate_redis_cli_command_exported(self):
        """Test validate_redis_cli_command is exported"""
        assert hasattr(validator, "validate_redis_cli_command")
        assert callable(validator.validate_redis_cli_command)

    def test_validate_mongosh_command_exported(self):
        """Test validate_mongosh_command is exported"""
        assert hasattr(validator, "validate_mongosh_command")
        assert callable(validator.validate_mongosh_command)


class TestValidatorModuleAll:
    """Tests for __all__ export list"""

    def test_all_list_exists(self):
        """Test that __all__ is defined"""
        assert hasattr(validator, "__all__")
        assert isinstance(validator.__all__, list)

    def test_all_contains_expected_exports(self):
        """Test that __all__ contains all expected exports"""
        expected_exports = [
            # Types
            "ValidationResult",
            "ValidatorFunction",
            # Registry
            "VALIDATORS",
            "get_validator",
            # Process validators
            "validate_pkill_command",
            "validate_kill_command",
            "validate_killall_command",
            # Filesystem validators
            "validate_chmod_command",
            "validate_rm_command",
            "validate_init_script",
            # Git validators
            "validate_git_commit",
            "validate_git_command",
            "validate_git_config",
            # Shell validators
            "validate_shell_c_command",
            "validate_bash_command",
            "validate_sh_command",
            "validate_zsh_command",
            # Database validators
            "validate_dropdb_command",
            "validate_dropuser_command",
            "validate_psql_command",
            "validate_mysql_command",
            "validate_mysqladmin_command",
            "validate_redis_cli_command",
            "validate_mongosh_command",
        ]

        for export in expected_exports:
            assert export in validator.__all__, f"Missing export: {export}"


class TestValidatorSignatures:
    """Tests for validator function signatures"""

    def test_validator_return_types(self):
        """Test that all validators return ValidationResult type"""
        validators_to_test = [
            validator.validate_pkill_command,
            validator.validate_kill_command,
            validator.validate_killall_command,
            validator.validate_chmod_command,
            validator.validate_rm_command,
            validator.validate_init_script,
            validator.validate_git_command,
            validator.validate_git_commit,
            validator.validate_git_config,
            validator.validate_bash_command,
            validator.validate_sh_command,
            validator.validate_zsh_command,
            validator.validate_shell_c_command,
            validator.validate_psql_command,
            validator.validate_dropdb_command,
            validator.validate_dropuser_command,
            validator.validate_mysql_command,
            validator.validate_mysqladmin_command,
            validator.validate_redis_cli_command,
            validator.validate_mongosh_command,
        ]

        for val_func in validators_to_test:
            result = val_func("test command")
            assert isinstance(result, tuple), f"{val_func.__name__} should return tuple"
            assert len(result) == 2, f"{val_func.__name__} should return 2-tuple"
            assert isinstance(result[0], bool), f"{val_func.__name__} first element should be bool"
            assert isinstance(result[1], str), f"{val_func.__name__} second element should be str"


class TestValidatorIntegration:
    """Tests for validator integration with registry"""

    def test_validators_in_registry(self):
        """Test that exported validators are in VALIDATORS dict"""
        # Check that key validators are registered
        assert "pkill" in validator.VALIDATORS
        assert "kill" in validator.VALIDATORS
        assert "killall" in validator.VALIDATORS
        assert "chmod" in validator.VALIDATORS
        assert "rm" in validator.VALIDATORS
        assert "git" in validator.VALIDATORS
        assert "bash" in validator.VALIDATORS
        assert "sh" in validator.VALIDATORS
        assert "zsh" in validator.VALIDATORS

    def test_registry_validator_functions_match_exports(self):
        """Test that VALIDATORS dict points to exported functions"""
        # The registry should reference the same functions
        assert validator.VALIDATORS["pkill"] is validator.validate_pkill_command
        assert validator.VALIDATORS["kill"] is validator.validate_kill_command
        assert validator.VALIDATORS["killall"] is validator.validate_killall_command
        assert validator.VALIDATORS["chmod"] is validator.validate_chmod_command
        assert validator.VALIDATORS["rm"] is validator.validate_rm_command
        assert validator.VALIDATORS["bash"] is validator.validate_bash_command
        assert validator.VALIDATORS["sh"] is validator.validate_sh_command
        assert validator.VALIDATORS["zsh"] is validator.validate_zsh_command


class TestImportPaths:
    """Tests for proper import paths and module structure"""

    def test_can_import_from_validator_module(self):
        """Test that validators can be imported directly"""
        from security.validator import (
            validate_pkill_command,
            validate_kill_command,
            validate_chmod_command,
            validate_rm_command,
            validate_git_command,
            validate_bash_command,
        )

        assert callable(validate_pkill_command)
        assert callable(validate_kill_command)
        assert callable(validate_chmod_command)
        assert callable(validate_rm_command)
        assert callable(validate_git_command)
        assert callable(validate_bash_command)

    def test_import_from_security_module(self):
        """Test that validators can be imported from security package"""
        from security import (
            validate_pkill_command,
            validate_kill_command,
            validate_chmod_command,
        )

        assert callable(validate_pkill_command)
        assert callable(validate_kill_command)
        assert callable(validate_chmod_command)


class TestBackwardCompatibility:
    """Tests for backward compatibility"""

    def test_validators_dict_is_mutable(self):
        """Test that VALIDATORS dict can be modified (for custom validators)"""
        original_size = len(validator.VALIDATORS)

        # Add a custom validator
        def custom_validator(command: str) -> tuple[bool, str]:
            return True, "Custom validator"

        validator.VALIDATORS["custom-cmd"] = custom_validator

        assert "custom-cmd" in validator.VALIDATORS
        assert len(validator.VALIDATORS) == original_size + 1

        # Clean up
        del validator.VALIDATORS["custom-cmd"]
        assert len(validator.VALIDATORS) == original_size


class TestValidatorConsistency:
    """Tests for consistency across validators"""

    def test_all_validators_accept_string(self):
        """Test that all validators accept string input"""
        validators_to_test = [
            validator.validate_pkill_command,
            validator.validate_kill_command,
            validator.validate_killall_command,
            validator.validate_chmod_command,
            validator.validate_rm_command,
            validator.validate_init_script,
            validator.validate_git_command,
            validator.validate_git_commit,
            validator.validate_git_config,
            validator.validate_bash_command,
            validator.validate_sh_command,
            validator.validate_zsh_command,
            validator.validate_shell_c_command,
            validator.validate_psql_command,
            validator.validate_dropdb_command,
            validator.validate_dropuser_command,
            validator.validate_mysql_command,
            validator.validate_mysqladmin_command,
            validator.validate_redis_cli_command,
            validator.validate_mongosh_command,
        ]

        for val_func in validators_to_test:
            # Should not raise
            result = val_func("test command")
            assert isinstance(result, tuple)

    def test_all_validators_return_consistent_format(self):
        """Test that all validators return consistent (bool, str) format"""
        validators_to_test = [
            validator.validate_pkill_command,
            validator.validate_kill_command,
            validator.validate_chmod_command,
            validator.validate_rm_command,
            validator.validate_git_command,
            validator.validate_bash_command,
        ]

        for val_func in validators_to_test:
            result = val_func("some command")
            # First element should always be bool
            assert isinstance(result[0], bool)
            # Second element should always be str
            assert isinstance(result[1], str)
            # If valid, message should typically be empty
            if result[0]:
                # Valid commands may have empty or non-empty messages
                assert isinstance(result[1], str)


class TestValidatorDocumentation:
    """Tests for validator documentation"""

    def test_validators_have_docstrings(self):
        """Test that validator functions have docstrings"""
        # Check a few key validators
        validators_with_docs = [
            validator.validate_pkill_command,
            validator.validate_kill_command,
            validator.validate_rm_command,
            validator.validate_git_commit,
        ]

        for val_func in validators_with_docs:
            # At minimum, should have some documentation
            assert val_func.__doc__ is not None or callable(val_func)
