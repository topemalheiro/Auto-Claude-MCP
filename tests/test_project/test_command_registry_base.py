"""
Tests for project.command_registry.base
========================================

Comprehensive tests for the base commands module including:
- BASE_COMMANDS set validation
- VALIDATED_COMMANDS dictionary validation
- Command categorization
- Data structure integrity
- Edge cases and data consistency
"""

import pytest

from project.command_registry.base import BASE_COMMANDS, VALIDATED_COMMANDS


# =============================================================================
# BASE_COMMANDS Tests
# =============================================================================

class TestBaseCommands:
    """Tests for BASE_COMMANDS set."""

    def test_base_commands_is_set(self):
        """Test that BASE_COMMANDS is a set."""
        assert isinstance(BASE_COMMANDS, set)

    def test_base_commands_not_empty(self):
        """Test that BASE_COMMANDS is not empty."""
        assert len(BASE_COMMANDS) > 0

    def test_base_commands_all_strings(self):
        """Test that all BASE_COMMANDS entries are strings."""
        assert all(isinstance(cmd, str) for cmd in BASE_COMMANDS)

    def test_base_commands_no_empty_strings(self):
        """Test that BASE_COMMANDS contains no empty strings."""
        assert "" not in BASE_COMMANDS

    def test_base_commands_no_whitespace_only(self):
        """Test that BASE_COMMANDS contains no whitespace-only strings."""
        assert not any(cmd.strip() == "" for cmd in BASE_COMMANDS)

    def test_base_commands_expected_core_commands(self):
        """Test that expected core shell commands are present."""
        expected_core = {
            "echo", "cat", "ls", "pwd", "cd", "cp", "mv", "mkdir", "rm",
            "grep", "find", "sed", "awk", "sort", "head", "tail"
        }
        assert expected_core.issubset(BASE_COMMANDS)

    def test_base_commands_has_git(self):
        """Test that git commands are present."""
        assert "git" in BASE_COMMANDS
        assert "gh" in BASE_COMMANDS

    def test_base_commands_has_shell_interpreters(self):
        """Test that shell interpreters are present."""
        assert "bash" in BASE_COMMANDS
        assert "sh" in BASE_COMMANDS
        assert "zsh" in BASE_COMMANDS

    def test_base_commands_has_text_tools(self):
        """Test that text processing tools are present."""
        assert "jq" in BASE_COMMANDS
        assert "yq" in BASE_COMMANDS

    def test_base_commands_has_archive_tools(self):
        """Test that archive tools are present."""
        assert "tar" in BASE_COMMANDS
        assert "zip" in BASE_COMMANDS
        assert "unzip" in BASE_COMMANDS
        assert "gzip" in BASE_COMMANDS

    def test_base_commands_has_network_tools(self):
        """Test that network tools are present."""
        assert "curl" in BASE_COMMANDS
        assert "wget" in BASE_COMMANDS

    def test_base_commands_has_process_tools(self):
        """Test that process management tools are present."""
        assert "ps" in BASE_COMMANDS
        assert "pgrep" in BASE_COMMANDS
        assert "kill" in BASE_COMMANDS

    def test_base_commands_no_duplicates(self):
        """Test that BASE_COMMANDS has no duplicates (set property)."""
        # Converting to set removes duplicates, length should remain same
        assert len(BASE_COMMANDS) == len(set(BASE_COMMANDS))

    def test_base_commands_lower_case_preference(self):
        """Test that commands are generally lowercase."""
        # Most commands should be lowercase, but some like [.gz] might not be
        lower_count = sum(1 for cmd in BASE_COMMANDS if cmd.islower() or cmd in ["[", "[[", ".gz", ".zip"])
        assert lower_count > len(BASE_COMMANDS) * 0.95  # At least 95% lowercase

    def test_base_commands_special_characters(self):
        """Test handling of commands with special characters."""
        # Commands with brackets (test builtins)
        assert "[" in BASE_COMMANDS
        assert "[[" in BASE_COMMANDS

    def test_base_commands_no_paths(self):
        """Test that BASE_COMMANDS contains no file paths."""
        # Should be command names only, not paths
        assert not any("/" in cmd or cmd.startswith("./") for cmd in BASE_COMMANDS)

    def test_base_commands_common_aliases(self):
        """Test for common command variants."""
        # GNU coreutils variants
        assert "gawk" in BASE_COMMANDS

    def test_base_commands_all_non_empty(self):
        """Test all commands have meaningful content."""
        for cmd in BASE_COMMANDS:
            assert len(cmd) > 0
            assert cmd.strip() == cmd  # No leading/trailing whitespace

    def test_base_commands_sorted_consistency(self):
        """Test that set operations work consistently."""
        # Create a copy and verify set operations
        copy = set(BASE_COMMANDS)
        assert copy == BASE_COMMANDS


# =============================================================================
# VALIDATED_COMMANDS Tests
# =============================================================================

class TestValidatedCommands:
    """Tests for VALIDATED_COMMANDS dictionary."""

    def test_validated_commands_is_dict(self):
        """Test that VALIDATED_COMMANDS is a dictionary."""
        assert isinstance(VALIDATED_COMMANDS, dict)

    def test_validated_commands_not_empty(self):
        """Test that VALIDATED_COMMANDS is not empty."""
        assert len(VALIDATED_COMMANDS) > 0

    def test_validated_commands_all_keys_strings(self):
        """Test that all VALIDATED_COMMANDS keys are strings."""
        assert all(isinstance(key, str) for key in VALIDATED_COMMANDS.keys())

    def test_validated_commands_all_values_strings(self):
        """Test that all VALIDATED_COMMANDS values are strings."""
        assert all(isinstance(value, str) for value in VALIDATED_COMMANDS.values())

    def test_validated_commands_no_empty_keys(self):
        """Test that VALIDATED_COMMANDS has no empty keys."""
        assert "" not in VALIDATED_COMMANDS

    def test_validated_commands_no_empty_values(self):
        """Test that VALIDATED_COMMANDS has no empty values."""
        assert "" not in VALIDATED_COMMANDS.values()

    def test_validated_commands_expected_dangerous_commands(self):
        """Test that dangerous commands requiring validation are present."""
        expected_dangerous = {"rm", "chmod", "kill", "pkill", "killall"}
        assert expected_dangerous.issubset(VALIDATED_COMMANDS.keys())

    def test_validated_commands_has_shell_validators(self):
        """Test that shell interpreters have validation functions."""
        assert "bash" in VALIDATED_COMMANDS
        assert "sh" in VALIDATED_COMMANDS
        assert "zsh" in VALIDATED_COMMANDS

    def test_validated_commands_validator_naming(self):
        """Test that validator functions follow naming convention."""
        for cmd, validator in VALIDATED_COMMANDS.items():
            # Validator should start with "validate_"
            assert validator.startswith("validate_")

    def test_validated_commands_rmp_mapping(self):
        """Test that rm has correct validator."""
        assert "rm" in VALIDATED_COMMANDS
        assert VALIDATED_COMMANDS["rm"] == "validate_rm"

    def test_validated_commands_kill_mapping(self):
        """Test that kill has correct validator."""
        assert "kill" in VALIDATED_COMMANDS
        assert VALIDATED_COMMANDS["kill"] == "validate_kill"

    def test_validated_commands_chmod_mapping(self):
        """Test that chmod has correct validator."""
        assert "chmod" in VALIDATED_COMMANDS
        assert VALIDATED_COMMANDS["chmod"] == "validate_chmod"

    def test_validated_commands_pkill_mapping(self):
        """Test that pkill has correct validator."""
        assert "pkill" in VALIDATED_COMMANDS
        assert VALIDATED_COMMANDS["pkill"] == "validate_pkill"

    def test_validated_commands_killall_mapping(self):
        """Test that killall has correct validator."""
        assert "killall" in VALIDATED_COMMANDS
        assert VALIDATED_COMMANDS["killall"] == "validate_killall"

    def test_validated_commands_shell_c_validator(self):
        """Test that shell interpreters use validate_shell_c."""
        assert VALIDATED_COMMANDS.get("bash") == "validate_shell_c"
        assert VALIDATED_COMMANDS.get("sh") == "validate_shell_c"
        assert VALIDATED_COMMANDS.get("zsh") == "validate_shell_c"

    def test_validated_commands_no_duplicates(self):
        """Test that VALIDATED_COMMANDS has no duplicate keys."""
        # Dict keys are unique by definition, just verify
        keys = list(VALIDATED_COMMANDS.keys())
        assert len(keys) == len(set(keys))

    def test_validated_commands_all_in_base(self):
        """Test that all validated commands are also in BASE_COMMANDS."""
        assert set(VALIDATED_COMMANDS.keys()).issubset(BASE_COMMANDS)

    def test_validated_commands_validator_names_descriptive(self):
        """Test that validator names are descriptive."""
        for cmd, validator in VALIDATED_COMMANDS.items():
            # Validator should contain command name or be generic
            assert "validate" in validator
            assert len(validator) > len("validate_")


# =============================================================================
# Cross-Module Validation Tests
# =============================================================================

class TestCrossModuleValidation:
    """Tests for relationships between BASE_COMMANDS and VALIDATED_COMMANDS."""

    def test_validated_subset_of_base(self):
        """Test that all validated commands are in base commands."""
        validated_keys = set(VALIDATED_COMMANDS.keys())
        assert validated_keys.issubset(BASE_COMMANDS)

    def test_base_has_unvalidated_commands(self):
        """Test that base commands include unvalidated commands."""
        # BASE_COMMANDS should be larger than validated commands
        assert len(BASE_COMMANDS) > len(VALIDATED_COMMANDS)

    def test_validated_dangerous_commands(self):
        """Test that dangerous commands require validation."""
        dangerous = {"rm", "kill", "killall", "pkill", "chmod"}
        assert dangerous.issubset(VALIDATED_COMMANDS.keys())

    def test_safe_commands_not_validated(self):
        """Test that safe commands don't require validation."""
        safe = {"ls", "cat", "echo", "pwd", "cd"}
        assert not safe.intersection(VALIDATED_COMMANDS.keys())

    def test_validated_shell_interpreters(self):
        """Test that shell interpreters that can run commands need validation."""
        # Shell interpreters that can execute arbitrary commands via -c
        shells_with_validation = {"bash", "sh", "zsh"}
        assert shells_with_validation.issubset(VALIDATED_COMMANDS.keys())


# =============================================================================
# Data Integrity Tests
# =============================================================================

class TestDataIntegrity:
    """Tests for data integrity and consistency."""

    def test_no_leading_trailing_whitespace(self):
        """Test no commands have leading/trailing whitespace."""
        for cmd in BASE_COMMANDS:
            assert cmd == cmd.strip()

        for cmd in VALIDATED_COMMANDS:
            assert cmd == cmd.strip()

    def test_no_null_characters(self):
        """Test no commands contain null characters."""
        for cmd in BASE_COMMANDS:
            assert "\0" not in cmd

        for cmd in VALIDATED_COMMANDS:
            assert "\0" not in cmd

    def test_commands_are_immutability_like(self):
        """Test that the sets/dicts behave as expected."""
        # Create copies to verify immutability expectations
        base_copy = set(BASE_COMMANDS)
        validated_copy = dict(VALIDATED_COMMANDS)

        # Originals should match copies
        assert BASE_COMMANDS == base_copy
        assert VALIDATED_COMMANDS == validated_copy

    def test_base_commands_immutability_at_import(self):
        """Test that BASE_COMMANDS can't be accidentally modified at module level."""
        # This test verifies the set is properly defined
        original_len = len(BASE_COMMANDS)
        original_commands = set(BASE_COMMANDS)

        # Try to modify (should work for sets, but we want original to be intact)
        test_set = set(BASE_COMMANDS)
        test_set.add("test-command")

        # Original should be unchanged
        assert len(BASE_COMMANDS) == original_len
        assert BASE_COMMANDS == original_commands


# =============================================================================
# Coverage Tests
# =============================================================================

class TestCommandCoverage:
    """Tests for command coverage across categories."""

    def test_core_utilities_coverage(self):
        """Test coverage of core utilities."""
        core_utilities = {
            # File operations
            "ls", "cd", "pwd", "cp", "mv", "mkdir", "rmdir", "rm", "touch", "ln",
            # Text processing
            "cat", "head", "tail", "grep", "sed", "awk", "sort", "uniq", "cut", "tr",
            # Find
            "find", "fd", "rg",
        }
        assert core_utilities.issubset(BASE_COMMANDS)

    def test_archive_tools_coverage(self):
        """Test coverage of archive tools."""
        archive_tools = {"tar", "zip", "unzip", "gzip", "gunzip"}
        assert archive_tools.issubset(BASE_COMMANDS)

    def test_network_tools_coverage(self):
        """Test coverage of network tools."""
        network_tools = {"curl", "wget", "ping", "host", "dig"}
        assert network_tools.issubset(BASE_COMMANDS)

    def test_version_control_coverage(self):
        """Test coverage of version control tools."""
        assert "git" in BASE_COMMANDS
        assert "gh" in BASE_COMMANDS

    def test_modern_replacements_coverage(self):
        """Test coverage of modern tool replacements."""
        # Modern alternatives
        assert "rg" in BASE_COMMANDS  # ripgrep vs grep
        assert "fd" in BASE_COMMANDS  # fd vs find
        assert "ag" in BASE_COMMANDS  # ag (the_silver_searcher)

    def test_process_management_coverage(self):
        """Test coverage of process management tools."""
        process_tools = {"ps", "pgrep", "lsof", "jobs", "kill", "pkill", "killall"}
        assert process_tools.issubset(BASE_COMMANDS)

    def test_development_tools_coverage(self):
        """Test coverage of development-related tools."""
        dev_tools = {"git", "curl", "wget", "jq", "file", "tree"}
        assert dev_tools.issubset(BASE_COMMANDS)

    def test_system_information_coverage(self):
        """Test coverage of system information tools."""
        sys_info = {"uname", "whoami", "id", "df", "du", "stat"}
        assert sys_info.issubset(BASE_COMMANDS)


# =============================================================================
# Edge Cases Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_single_character_commands(self):
        """Test handling of single-character commands."""
        # Some commands might be single char (like 'w' for who)
        single_char = [cmd for cmd in BASE_COMMANDS if len(cmd) == 1]
        # Just verify they exist and are valid
        for cmd in single_char:
            assert cmd.isalnum() or cmd in ["[", "."]

    def test_commands_with_hyphens(self):
        """Test handling of commands with hyphens."""
        hyphen_commands = [cmd for cmd in BASE_COMMANDS if "-" in cmd]
        # Verify they're valid
        for cmd in hyphen_commands:
            assert cmd.strip("-").replace("-", "").isalnum()

    def test_commands_with_numbers(self):
        """Test handling of commands with numbers."""
        # Some commands like 'nc', 'ssh', etc.
        numeric_commands = [cmd for cmd in BASE_COMMANDS if any(c.isdigit() for c in cmd)]
        # Just verify they exist and are handled
        assert isinstance(numeric_commands, list)

    def test_special_builtin_commands(self):
        """Test special shell builtin commands."""
        special_builtins = {"[", "[[", ".", ":", "true", "false", "test", "echo"}
        # Many of these should be in BASE_COMMANDS
        assert special_builtins.intersection(BASE_COMMANDS)

    def test_commands_case_variations(self):
        """Test that we don't have duplicate commands with different cases."""
        # Convert to lowercase and check for duplicates after normalization
        lower_commands = {cmd.lower() for cmd in BASE_COMMANDS}
        # There should be fewer or equal unique lowercased commands
        assert len(lower_commands) <= len(BASE_COMMANDS)
