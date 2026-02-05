"""
Comprehensive tests for validator_registry.py

Tests the central registry that maps command names to their validation functions.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call

from security.validator_registry import VALIDATORS, get_validator
from security.validation_models import ValidationResult, ValidatorFunction


class TestValidatorsDict:
    """Tests for the VALIDATORS dictionary"""

    def test_validators_is_dict(self):
        """Test that VALIDATORS is a dictionary"""
        assert isinstance(VALIDATORS, dict)

    def test_validators_not_empty(self):
        """Test that VALIDATORS is not empty"""
        assert len(VALIDATORS) > 0

    def test_validators_keys_are_strings(self):
        """Test that all VALIDATORS keys are strings"""
        for key in VALIDATORS.keys():
            assert isinstance(key, str)

    def test_validators_values_are_callables(self):
        """Test that all VALIDATORS values are callable"""
        for value in VALIDATORS.values():
            assert callable(value)

    def test_validators_expected_process_commands(self):
        """Test that expected process commands are registered"""
        expected_process_commands = ["pkill", "kill", "killall"]
        for cmd in expected_process_commands:
            assert cmd in VALIDATORS, f"Process command '{cmd}' not in VALIDATORS"

    def test_validators_expected_filesystem_commands(self):
        """Test that expected filesystem commands are registered"""
        expected_fs_commands = ["chmod", "rm", "init.sh"]
        for cmd in expected_fs_commands:
            assert cmd in VALIDATORS, f"Filesystem command '{cmd}' not in VALIDATORS"

    def test_validators_expected_git_commands(self):
        """Test that expected git commands are registered"""
        expected_git_commands = ["git"]
        for cmd in expected_git_commands:
            assert cmd in VALIDATORS, f"Git command '{cmd}' not in VALIDATORS"

    def test_validators_expected_shell_commands(self):
        """Test that expected shell commands are registered"""
        expected_shell_commands = ["bash", "sh", "zsh"]
        for cmd in expected_shell_commands:
            assert cmd in VALIDATORS, f"Shell command '{cmd}' not in VALIDATORS"

    def test_validators_expected_postgres_commands(self):
        """Test that expected PostgreSQL commands are registered"""
        expected_pg_commands = ["dropdb", "dropuser", "psql"]
        for cmd in expected_pg_commands:
            assert cmd in VALIDATORS, f"PostgreSQL command '{cmd}' not in VALIDATORS"

    def test_validators_expected_mysql_commands(self):
        """Test that expected MySQL/MariaDB commands are registered"""
        expected_mysql_commands = ["mysql", "mariadb", "mysqladmin"]
        for cmd in expected_mysql_commands:
            assert cmd in VALIDATORS, f"MySQL command '{cmd}' not in VALIDATORS"

    def test_validators_expected_nosql_commands(self):
        """Test that expected NoSQL commands are registered"""
        expected_nosql_commands = ["redis-cli", "mongosh", "mongo"]
        for cmd in expected_nosql_commands:
            assert cmd in VALIDATORS, f"NoSQL command '{cmd}' not in VALIDATORS"


class TestGetValidator:
    """Tests for the get_validator function"""

    def test_get_validator_returns_callable(self):
        """Test that get_validator returns a callable for valid commands"""
        result = get_validator("ls")
        if result is not None:
            assert callable(result)

    def test_get_validator_for_pkill(self):
        """Test get_validator for pkill command"""
        validator = get_validator("pkill")
        assert validator is not None
        assert callable(validator)

    def test_get_validator_for_kill(self):
        """Test get_validator for kill command"""
        validator = get_validator("kill")
        assert validator is not None
        assert callable(validator)

    def test_get_validator_for_killall(self):
        """Test get_validator for killall command"""
        validator = get_validator("killall")
        assert validator is not None
        assert callable(validator)

    def test_get_validator_for_chmod(self):
        """Test get_validator for chmod command"""
        validator = get_validator("chmod")
        assert validator is not None
        assert callable(validator)

    def test_get_validator_for_rm(self):
        """Test get_validator for rm command"""
        validator = get_validator("rm")
        assert validator is not None
        assert callable(validator)

    def test_get_validator_for_git(self):
        """Test get_validator for git command"""
        validator = get_validator("git")
        assert validator is not None
        assert callable(validator)

    def test_get_validator_for_bash(self):
        """Test get_validator for bash command"""
        validator = get_validator("bash")
        assert validator is not None
        assert callable(validator)

    def test_get_validator_for_sh(self):
        """Test get_validator for sh command"""
        validator = get_validator("sh")
        assert validator is not None
        assert callable(validator)

    def test_get_validator_for_zsh(self):
        """Test get_validator for zsh command"""
        validator = get_validator("zsh")
        assert validator is not None
        assert callable(validator)

    def test_get_validator_for_psql(self):
        """Test get_validator for psql command"""
        validator = get_validator("psql")
        assert validator is not None
        assert callable(validator)

    def test_get_validator_for_dropdb(self):
        """Test get_validator for dropdb command"""
        validator = get_validator("dropdb")
        assert validator is not None
        assert callable(validator)

    def test_get_validator_for_dropuser(self):
        """Test get_validator for dropuser command"""
        validator = get_validator("dropuser")
        assert validator is not None
        assert callable(validator)

    def test_get_validator_for_mysql(self):
        """Test get_validator for mysql command"""
        validator = get_validator("mysql")
        assert validator is not None
        assert callable(validator)

    def test_get_validator_for_mariadb(self):
        """Test get_validator for mariadb command (alias for mysql)"""
        validator = get_validator("mariadb")
        assert validator is not None
        assert callable(validator)

    def test_get_validator_for_mysqladmin(self):
        """Test get_validator for mysqladmin command"""
        validator = get_validator("mysqladmin")
        assert validator is not None
        assert callable(validator)

    def test_get_validator_for_redis_cli(self):
        """Test get_validator for redis-cli command"""
        validator = get_validator("redis-cli")
        assert validator is not None
        assert callable(validator)

    def test_get_validator_for_mongosh(self):
        """Test get_validator for mongosh command"""
        validator = get_validator("mongosh")
        assert validator is not None
        assert callable(validator)

    def test_get_validator_for_mongo(self):
        """Test get_validator for mongo command (legacy)"""
        validator = get_validator("mongo")
        assert validator is not None
        assert callable(validator)

    def test_get_validator_for_unknown_command(self):
        """Test get_validator for unknown command returns None"""
        validator = get_validator("unknown-command-xyz")
        assert validator is None

    def test_get_validator_for_empty_string(self):
        """Test get_validator for empty string returns None"""
        validator = get_validator("")
        assert validator is None

    def test_get_validator_case_sensitive(self):
        """Test that get_validator is case sensitive"""
        validator_lower = get_validator("git")
        validator_upper = get_validator("GIT")
        validator_mixed = get_validator("Git")

        # Only lowercase should return a validator
        assert validator_lower is not None
        assert validator_upper is None
        assert validator_mixed is None


class TestValidatorReturnType:
    """Tests that validators return correct types"""

    def test_validators_return_validation_result_type(self):
        """Test that all registered validators return ValidationResult"""
        for cmd_name, validator_func in VALIDATORS.items():
            result = validator_func("test command")
            assert isinstance(result, tuple), f"{cmd_name} should return tuple"
            assert len(result) == 2, f"{cmd_name} should return 2-tuple"
            assert isinstance(result[0], bool), f"{cmd_name} first element should be bool"
            assert isinstance(result[1], str), f"{cmd_name} second element should be str"


class TestValidatorRegistration:
    """Tests for validator registration patterns"""

    def test_mysql_and_mariadb_share_validator(self):
        """Test that mysql and mariadb use the same validator"""
        mysql_validator = VALIDATORS.get("mysql")
        mariadb_validator = VALIDATORS.get("mariadb")

        assert mysql_validator is not None
        assert mariadb_validator is not None
        assert mysql_validator is mariadb_validator

    def test_mongo_and_mongosh_share_validator(self):
        """Test that mongo and mongosh use the same validator"""
        mongo_validator = VALIDATORS.get("mongo")
        mongosh_validator = VALIDATORS.get("mongosh")

        assert mongo_validator is not None
        assert mongosh_validator is not None
        assert mongo_validator is mongosh_validator


class TestValidatorExecution:
    """Tests for executing validators from the registry"""

    def test_execute_pkill_validator(self):
        """Test executing pkill validator from registry"""
        validator = get_validator("pkill")
        assert validator is not None

        result = validator("pkill -f test")
        assert isinstance(result, tuple)
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)

    def test_execute_chmod_validator(self):
        """Test executing chmod validator from registry"""
        validator = get_validator("chmod")
        assert validator is not None

        result = validator("chmod 755 file.txt")
        assert isinstance(result, tuple)
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)

    def test_execute_git_validator(self):
        """Test executing git validator from registry"""
        validator = get_validator("git")
        assert validator is not None

        result = validator("git status")
        assert isinstance(result, tuple)
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)


class TestRegistryImmutability:
    """Tests for registry behavior and modification"""

    def test_registry_can_be_modified(self):
        """Test that VALIDATORS can be modified for custom validators"""
        original_count = len(VALIDATORS)

        # Add a custom validator
        def custom_validator(command: str) -> ValidationResult:
            return (True, "Custom validator")

        VALIDATORS["custom-cmd"] = custom_validator

        assert "custom-cmd" in VALIDATORS
        assert len(VALIDATORS) == original_count + 1

        # Clean up
        del VALIDATORS["custom-cmd"]
        assert len(VALIDATORS) == original_count
        assert "custom-cmd" not in VALIDATORS

    def test_get_validator_reflects_changes(self):
        """Test that get_validator sees registry changes"""
        # Ensure test command doesn't exist
        test_cmd = "temp-test-validator"
        assert get_validator(test_cmd) is None

        # Add a temporary validator
        def temp_validator(command: str) -> ValidationResult:
            return (True, "")

        VALIDATORS[test_cmd] = temp_validator
        assert get_validator(test_cmd) is not None

        # Clean up
        del VALIDATORS[test_cmd]
        assert get_validator(test_cmd) is None


class TestRegistryCoverage:
    """Tests for registry coverage of dangerous commands"""

    def test_dangerous_process_commands_covered(self):
        """Test that dangerous process commands have validators"""
        dangerous_commands = ["pkill", "kill", "killall"]
        for cmd in dangerous_commands:
            assert cmd in VALIDATORS, f"Dangerous command '{cmd}' should have a validator"

    def test_dangerous_filesystem_commands_covered(self):
        """Test that dangerous filesystem commands have validators"""
        dangerous_commands = ["chmod", "rm"]
        for cmd in dangerous_commands:
            assert cmd in VALIDATORS, f"Dangerous command '{cmd}' should have a validator"

    def test_dangerous_database_commands_covered(self):
        """Test that dangerous database commands have validators"""
        dangerous_commands = ["dropdb", "dropuser"]
        for cmd in dangerous_commands:
            assert cmd in VALIDATORS, f"Dangerous command '{cmd}' should have a validator"


class TestSpecialCases:
    """Tests for special cases and edge conditions"""

    def test_init_script_with_hyphen(self):
        """Test that init.sh command is registered (contains hyphen/dot)"""
        assert "init.sh" in VALIDATORS

    def test_redis_cli_with_hyphen(self):
        """Test that redis-cli command is registered (contains hyphen)"""
        assert "redis-cli" in VALIDATORS

    def test_get_validator_with_whitespace(self):
        """Test get_validator with whitespace in command name"""
        validator = get_validator("  git  ")
        # Should return None since whitespace isn't trimmed
        assert validator is None

    def test_all_registered_commands_lowercase(self):
        """Test that all registered commands are lowercase"""
        for cmd in VALIDATORS.keys():
            assert cmd == cmd.lower(), f"Command '{cmd}' should be lowercase"


class TestValidatorFunctionTypes:
    """Tests for validator function type compatibility"""

    def test_all_validators_match_type_signature(self):
        """Test that all validators match ValidatorFunction type"""
        for cmd_name, validator_func in VALIDATORS.items():
            # Should accept a string argument
            result = validator_func("test")
            # Should return a tuple[bool, str]
            assert isinstance(result, tuple)
            assert len(result) == 2
            assert isinstance(result[0], bool)
            assert isinstance(result[1], str)


class TestRegistryDocumentation:
    """Tests for registry documentation and structure"""

    def test_registry_has_expected_command_count(self):
        """Test that registry has expected minimum number of validators"""
        # At minimum should have these dangerous commands covered
        minimum_expected = 10
        assert len(VALIDATORS) >= minimum_expected

    def test_registry_commands_are_unique(self):
        """Test that all registered commands are unique"""
        commands = list(VALIDATORS.keys())
        assert len(commands) == len(set(commands)), "Registry should not have duplicate commands"
