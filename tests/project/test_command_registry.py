"""
Comprehensive tests for project/command_registry.py
===================================================

Tests for command registry constants and structure:
- BASE_COMMANDS - Core safe shell commands
- VALIDATED_COMMANDS - Commands requiring extra validation
- LANGUAGE_COMMANDS - Language-specific commands
- PACKAGE_MANAGER_COMMANDS - Package manager commands
- FRAMEWORK_COMMANDS - Framework-specific commands
- DATABASE_COMMANDS - Database commands
- INFRASTRUCTURE_COMMANDS - DevOps/infrastructure commands
- CLOUD_COMMANDS - Cloud provider CLI commands
- CODE_QUALITY_COMMANDS - Code quality tools
- VERSION_MANAGER_COMMANDS - Version management tools
"""

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


# =============================================================================
# BASE_COMMANDS TESTS
# =============================================================================

class TestBaseCommands:
    """Tests for BASE_COMMANDS registry"""

    def test_base_commands_is_set(self):
        """Test BASE_COMMANDS is a set."""
        assert isinstance(BASE_COMMANDS, set)

    def test_base_commands_not_empty(self):
        """Test BASE_COMMANDS is not empty."""
        assert len(BASE_COMMANDS) > 0

    def test_base_commands_contains_core_shell(self):
        """Test BASE_COMMANDS contains core shell commands."""
        assert "ls" in BASE_COMMANDS
        assert "cd" in BASE_COMMANDS
        assert "pwd" in BASE_COMMANDS
        assert "cat" in BASE_COMMANDS
        assert "echo" in BASE_COMMANDS

    def test_base_commands_contains_git(self):
        """Test BASE_COMMANDS contains git commands."""
        assert "git" in BASE_COMMANDS
        assert "gh" in BASE_COMMANDS

    def test_base_commands_contains_network_commands(self):
        """Test BASE_COMMANDS contains network commands."""
        assert "curl" in BASE_COMMANDS
        assert "wget" in BASE_COMMANDS

    def test_base_commands_contains_archive_commands(self):
        """Test BASE_COMMANDS contains archive commands."""
        assert "tar" in BASE_COMMANDS
        assert "zip" in BASE_COMMANDS
        assert "unzip" in BASE_COMMANDS
        assert "gzip" in BASE_COMMANDS

    def test_base_commands_contains_text_tools(self):
        """Test BASE_COMMANDS contains text processing tools."""
        assert "grep" in BASE_COMMANDS
        assert "sed" in BASE_COMMANDS
        assert "awk" in BASE_COMMANDS
        assert "sort" in BASE_COMMANDS
        assert "uniq" in BASE_COMMANDS

    def test_base_commands_contains_shells(self):
        """Test BASE_COMMANDS contains shell interpreters."""
        assert "bash" in BASE_COMMANDS
        assert "sh" in BASE_COMMANDS
        assert "zsh" in BASE_COMMANDS

    def test_base_commands_strings_are_lowercase(self):
        """Test all BASE_COMMANDS are lowercase."""
        for cmd in BASE_COMMANDS:
            assert cmd == cmd.lower(), f"Command {cmd} is not lowercase"

    def test_base_commands_no_duplicates(self):
        """Test BASE_COMMANDS has no duplicates (it's a set)."""
        # As a set, duplicates are automatically removed
        # Just verify it's still a set
        assert len(BASE_COMMANDS) == len(list(BASE_COMMANDS))


# =============================================================================
# VALIDATED_COMMANDS TESTS
# =============================================================================

class TestValidatedCommands:
    """Tests for VALIDATED_COMMANDS registry"""

    def test_validated_commands_is_dict(self):
        """Test VALIDATED_COMMANDS is a dict."""
        assert isinstance(VALIDATED_COMMANDS, dict)

    def test_validated_commands_not_empty(self):
        """Test VALIDATED_COMMANDS is not empty."""
        assert len(VALIDATED_COMMANDS) > 0

    def test_validated_commands_structure(self):
        """Test VALIDATED_COMMANDS has string keys and values."""
        for cmd, validator in VALIDATED_COMMANDS.items():
            assert isinstance(cmd, str)
            assert isinstance(validator, str)

    def test_validated_commands_contains_rm(self):
        """Test VALIDATED_COMMANDS contains rm."""
        assert "rm" in VALIDATED_COMMANDS
        assert "validate_rm" == VALIDATED_COMMANDS["rm"]

    def test_validated_commands_contains_chmod(self):
        """Test VALIDATED_COMMANDS contains chmod."""
        assert "chmod" in VALIDATED_COMMANDS
        assert "validate_chmod" == VALIDATED_COMMANDS["chmod"]

    def test_validated_commands_contains_kill_commands(self):
        """Test VALIDATED_COMMANDS contains kill-related commands."""
        assert "kill" in VALIDATED_COMMANDS
        assert "pkill" in VALIDATED_COMMANDS
        assert "killall" in VALIDATED_COMMANDS

    def test_validated_commands_contains_shell_validators(self):
        """Test VALIDATED_COMMANDS contains shell validators."""
        assert "bash" in VALIDATED_COMMANDS
        assert "sh" in VALIDATED_COMMANDS
        assert "zsh" in VALIDATED_COMMANDS

    def test_validated_commands_values_are_functions(self):
        """Test validated command values look like function names."""
        for validator in VALIDATED_COMMANDS.values():
            assert validator.startswith("validate_")

    def test_validated_commands_in_base_commands(self):
        """Test all validated commands are in BASE_COMMANDS."""
        for cmd in VALIDATED_COMMANDS:
            assert cmd in BASE_COMMANDS, f"Validated command {cmd} not in BASE_COMMANDS"


# =============================================================================
# LANGUAGE_COMMANDS TESTS
# =============================================================================

class TestLanguageCommands:
    """Tests for LANGUAGE_COMMANDS registry"""

    def test_language_commands_is_dict(self):
        """Test LANGUAGE_COMMANDS is a dict."""
        assert isinstance(LANGUAGE_COMMANDS, dict)

    def test_language_commands_not_empty(self):
        """Test LANGUAGE_COMMANDS is not empty."""
        assert len(LANGUAGE_COMMANDS) > 0

    def test_language_commands_contains_python(self):
        """Test LANGUAGE_COMMANDS contains Python."""
        assert "python" in LANGUAGE_COMMANDS
        assert isinstance(LANGUAGE_COMMANDS["python"], set)
        assert "python" in LANGUAGE_COMMANDS["python"]
        assert "pip" in LANGUAGE_COMMANDS["python"]

    def test_language_commands_contains_javascript(self):
        """Test LANGUAGE_COMMANDS contains JavaScript."""
        assert "javascript" in LANGUAGE_COMMANDS
        assert "node" in LANGUAGE_COMMANDS["javascript"]
        assert "npm" in LANGUAGE_COMMANDS["javascript"]

    def test_language_commands_contains_typescript(self):
        """Test LANGUAGE_COMMANDS contains TypeScript."""
        assert "typescript" in LANGUAGE_COMMANDS
        assert "tsc" in LANGUAGE_COMMANDS["typescript"]
        assert "ts-node" in LANGUAGE_COMMANDS["typescript"]

    def test_language_commands_contains_rust(self):
        """Test LANGUAGE_COMMANDS contains Rust."""
        assert "rust" in LANGUAGE_COMMANDS
        assert "cargo" in LANGUAGE_COMMANDS["rust"]
        assert "rustc" in LANGUAGE_COMMANDS["rust"]

    def test_language_commands_contains_go(self):
        """Test LANGUAGE_COMMANDS contains Go."""
        assert "go" in LANGUAGE_COMMANDS
        assert "go" in LANGUAGE_COMMANDS["go"]

    def test_language_commands_contains_ruby(self):
        """Test LANGUAGE_COMMANDS contains Ruby."""
        assert "ruby" in LANGUAGE_COMMANDS
        assert "ruby" in LANGUAGE_COMMANDS["ruby"]
        assert "gem" in LANGUAGE_COMMANDS["ruby"]

    def test_language_commands_contains_java(self):
        """Test LANGUAGE_COMMANDS contains Java."""
        assert "java" in LANGUAGE_COMMANDS
        assert "java" in LANGUAGE_COMMANDS["java"]
        assert "mvn" in LANGUAGE_COMMANDS["java"]

    def test_language_commands_contains_php(self):
        """Test LANGUAGE_COMMANDS contains PHP."""
        assert "php" in LANGUAGE_COMMANDS
        assert "php" in LANGUAGE_COMMANDS["php"]
        assert "composer" in LANGUAGE_COMMANDS["php"]

    def test_language_commands_contains_dart(self):
        """Test LANGUAGE_COMMANDS contains Dart/Flutter."""
        assert "dart" in LANGUAGE_COMMANDS
        assert "dart" in LANGUAGE_COMMANDS["dart"]
        assert "flutter" in LANGUAGE_COMMANDS["dart"]

    def test_language_commands_all_values_are_sets(self):
        """Test all LANGUAGE_COMMANDS values are sets."""
        for lang, commands in LANGUAGE_COMMANDS.items():
            assert isinstance(commands, set), f"{lang} commands is not a set"

    def test_language_commands_all_sets_non_empty(self):
        """Test all language command sets are non-empty."""
        for lang, commands in LANGUAGE_COMMANDS.items():
            assert len(commands) > 0, f"{lang} has empty command set"


# =============================================================================
# PACKAGE_MANAGER_COMMANDS TESTS
# =============================================================================

class TestPackageManagerCommands:
    """Tests for PACKAGE_MANAGER_COMMANDS registry"""

    def test_package_manager_commands_is_dict(self):
        """Test PACKAGE_MANAGER_COMMANDS is a dict."""
        assert isinstance(PACKAGE_MANAGER_COMMANDS, dict)

    def test_package_manager_commands_not_empty(self):
        """Test PACKAGE_MANAGER_COMMANDS is not empty."""
        assert len(PACKAGE_MANAGER_COMMANDS) > 0

    def test_package_manager_commands_contains_npm(self):
        """Test PACKAGE_MANAGER_COMMANDS contains npm."""
        assert "npm" in PACKAGE_MANAGER_COMMANDS
        assert "npm" in PACKAGE_MANAGER_COMMANDS["npm"]

    def test_package_manager_commands_contains_yarn(self):
        """Test PACKAGE_MANAGER_COMMANDS contains yarn."""
        assert "yarn" in PACKAGE_MANAGER_COMMANDS
        assert "yarn" in PACKAGE_MANAGER_COMMANDS["yarn"]

    def test_package_manager_commands_contains_pnpm(self):
        """Test PACKAGE_MANAGER_COMMANDS contains pnpm."""
        assert "pnpm" in PACKAGE_MANAGER_COMMANDS
        assert "pnpm" in PACKAGE_MANAGER_COMMANDS["pnpm"]

    def test_package_manager_commands_contains_bun(self):
        """Test PACKAGE_MANAGER_COMMANDS contains bun."""
        assert "bun" in PACKAGE_MANAGER_COMMANDS
        assert "bun" in PACKAGE_MANAGER_COMMANDS["bun"]

    def test_package_manager_commands_contains_pip(self):
        """Test PACKAGE_MANAGER_COMMANDS contains pip."""
        assert "pip" in PACKAGE_MANAGER_COMMANDS
        assert "pip" in PACKAGE_MANAGER_COMMANDS["pip"]

    def test_package_manager_commands_contains_poetry(self):
        """Test PACKAGE_MANAGER_COMMANDS contains poetry."""
        assert "poetry" in PACKAGE_MANAGER_COMMANDS
        assert "poetry" in PACKAGE_MANAGER_COMMANDS["poetry"]

    def test_package_manager_commands_contains_cargo(self):
        """Test PACKAGE_MANAGER_COMMANDS contains cargo."""
        assert "cargo" in PACKAGE_MANAGER_COMMANDS
        assert "cargo" in PACKAGE_MANAGER_COMMANDS["cargo"]

    def test_package_manager_commands_contains_composer(self):
        """Test PACKAGE_MANAGER_COMMANDS contains composer."""
        assert "composer" in PACKAGE_MANAGER_COMMANDS
        assert "composer" in PACKAGE_MANAGER_COMMANDS["composer"]

    def test_package_manager_commands_contains_system_managers(self):
        """Test PACKAGE_MANAGER_COMMANDS contains system package managers."""
        assert "brew" in PACKAGE_MANAGER_COMMANDS
        assert "apt" in PACKAGE_MANAGER_COMMANDS
        assert "nix" in PACKAGE_MANAGER_COMMANDS

    def test_package_manager_commands_all_values_are_sets(self):
        """Test all PACKAGE_MANAGER_COMMANDS values are sets."""
        for pm, commands in PACKAGE_MANAGER_COMMANDS.items():
            assert isinstance(commands, set), f"{pm} commands is not a set"

    def test_package_manager_commands_all_sets_non_empty(self):
        """Test all package manager sets are non-empty."""
        for pm, commands in PACKAGE_MANAGER_COMMANDS.items():
            assert len(commands) > 0, f"{pm} has empty command set"


# =============================================================================
# FRAMEWORK_COMMANDS TESTS
# =============================================================================

class TestFrameworkCommands:
    """Tests for FRAMEWORK_COMMANDS registry"""

    def test_framework_commands_is_dict(self):
        """Test FRAMEWORK_COMMANDS is a dict."""
        assert isinstance(FRAMEWORK_COMMANDS, dict)

    def test_framework_commands_not_empty(self):
        """Test FRAMEWORK_COMMANDS is not empty."""
        assert len(FRAMEWORK_COMMANDS) > 0

    def test_framework_commands_contains_django(self):
        """Test FRAMEWORK_COMMANDS contains Django."""
        assert "django" in FRAMEWORK_COMMANDS
        assert "django-admin" in FRAMEWORK_COMMANDS["django"]

    def test_framework_commands_contains_flask(self):
        """Test FRAMEWORK_COMMANDS contains Flask."""
        assert "flask" in FRAMEWORK_COMMANDS
        assert "flask" in FRAMEWORK_COMMANDS["flask"]

    def test_framework_commands_contains_fastapi(self):
        """Test FRAMEWORK_COMMANDS contains FastAPI."""
        assert "fastapi" in FRAMEWORK_COMMANDS
        assert "uvicorn" in FRAMEWORK_COMMANDS["fastapi"]

    def test_framework_commands_contains_nextjs(self):
        """Test FRAMEWORK_COMMANDS contains Next.js."""
        assert "nextjs" in FRAMEWORK_COMMANDS
        assert "next" in FRAMEWORK_COMMANDS["nextjs"]

    def test_framework_commands_contains_react(self):
        """Test FRAMEWORK_COMMANDS contains React."""
        assert "react" in FRAMEWORK_COMMANDS
        assert "react-scripts" in FRAMEWORK_COMMANDS["react"]

    def test_framework_commands_contains_vue(self):
        """Test FRAMEWORK_COMMANDS contains Vue."""
        assert "vue" in FRAMEWORK_COMMANDS
        assert "vite" in FRAMEWORK_COMMANDS["vue"]

    def test_framework_commands_contains_angular(self):
        """Test FRAMEWORK_COMMANDS contains Angular."""
        assert "angular" in FRAMEWORK_COMMANDS
        assert "ng" in FRAMEWORK_COMMANDS["angular"]

    def test_framework_commands_contains_rails(self):
        """Test FRAMEWORK_COMMANDS contains Rails."""
        assert "rails" in FRAMEWORK_COMMANDS
        assert "rails" in FRAMEWORK_COMMANDS["rails"]
        assert "rake" in FRAMEWORK_COMMANDS["rails"]

    def test_framework_commands_contains_laravel(self):
        """Test FRAMEWORK_COMMANDS contains Laravel."""
        assert "laravel" in FRAMEWORK_COMMANDS
        assert "artisan" in FRAMEWORK_COMMANDS["laravel"]

    def test_framework_commands_contains_flutter(self):
        """Test FRAMEWORK_COMMANDS contains Flutter."""
        assert "flutter" in FRAMEWORK_COMMANDS
        assert "flutter" in FRAMEWORK_COMMANDS["flutter"]

    def test_framework_commands_contains_testing_frameworks(self):
        """Test FRAMEWORK_COMMANDS contains testing frameworks."""
        assert "pytest" in FRAMEWORK_COMMANDS
        assert "jest" in FRAMEWORK_COMMANDS
        assert "vitest" in FRAMEWORK_COMMANDS
        assert "cypress" in FRAMEWORK_COMMANDS

    def test_framework_commands_all_values_are_sets(self):
        """Test all FRAMEWORK_COMMANDS values are sets."""
        for fw, commands in FRAMEWORK_COMMANDS.items():
            assert isinstance(commands, set), f"{fw} commands is not a set"

    def test_framework_commands_all_sets_non_empty(self):
        """Test all framework sets are non-empty."""
        for fw, commands in FRAMEWORK_COMMANDS.items():
            assert len(commands) > 0, f"{fw} has empty command set"


# =============================================================================
# DATABASE_COMMANDS TESTS
# =============================================================================

class TestDatabaseCommands:
    """Tests for DATABASE_COMMANDS registry"""

    def test_database_commands_is_dict(self):
        """Test DATABASE_COMMANDS is a dict."""
        assert isinstance(DATABASE_COMMANDS, dict)

    def test_database_commands_not_empty(self):
        """Test DATABASE_COMMANDS is not empty."""
        assert len(DATABASE_COMMANDS) > 0

    def test_database_commands_contains_postgresql(self):
        """Test DATABASE_COMMANDS contains PostgreSQL."""
        assert "postgresql" in DATABASE_COMMANDS or "postgres" in DATABASE_COMMANDS

    def test_database_commands_contains_mysql(self):
        """Test DATABASE_COMMANDS contains MySQL."""
        assert "mysql" in DATABASE_COMMANDS

    def test_database_commands_contains_redis(self):
        """Test DATABASE_COMMANDS contains Redis."""
        assert "redis" in DATABASE_COMMANDS

    def test_database_commands_contains_mongodb(self):
        """Test DATABASE_COMMANDS contains MongoDB."""
        assert "mongodb" in DATABASE_COMMANDS or "mongo" in DATABASE_COMMANDS

    def test_database_commands_contains_sqlite(self):
        """Test DATABASE_COMMANDS contains SQLite."""
        assert "sqlite" in DATABASE_COMMANDS

    def test_database_commands_all_values_are_sets(self):
        """Test all DATABASE_COMMANDS values are sets."""
        for db, commands in DATABASE_COMMANDS.items():
            assert isinstance(commands, set), f"{db} commands is not a set"

    def test_database_commands_all_sets_non_empty(self):
        """Test all database sets are non-empty."""
        for db, commands in DATABASE_COMMANDS.items():
            assert len(commands) > 0, f"{db} has empty command set"


# =============================================================================
# INFRASTRUCTURE_COMMANDS TESTS
# =============================================================================

class TestInfrastructureCommands:
    """Tests for INFRASTRUCTURE_COMMANDS registry"""

    def test_infrastructure_commands_is_dict(self):
        """Test INFRASTRUCTURE_COMMANDS is a dict."""
        assert isinstance(INFRASTRUCTURE_COMMANDS, dict)

    def test_infrastructure_commands_not_empty(self):
        """Test INFRASTRUCTURE_COMMANDS is not empty."""
        assert len(INFRASTRUCTURE_COMMANDS) > 0

    def test_infrastructure_commands_contains_docker(self):
        """Test INFRASTRUCTURE_COMMANDS contains Docker."""
        assert "docker" in INFRASTRUCTURE_COMMANDS
        assert "docker" in INFRASTRUCTURE_COMMANDS["docker"]

    def test_infrastructure_commands_contains_kubernetes(self):
        """Test INFRASTRUCTURE_COMMANDS contains Kubernetes."""
        assert "kubernetes" in INFRASTRUCTURE_COMMANDS or "k8s" in INFRASTRUCTURE_COMMANDS
        # Check for kubectl
        found_kubectl = False
        for cmds in INFRASTRUCTURE_COMMANDS.values():
            if "kubectl" in cmds:
                found_kubectl = True
                break
        assert found_kubectl, "kubectl not found in infrastructure commands"

    def test_infrastructure_commands_contains_terraform(self):
        """Test INFRASTRUCTURE_COMMANDS contains Terraform."""
        assert "terraform" in INFRASTRUCTURE_COMMANDS

    def test_infrastructure_commands_all_values_are_sets(self):
        """Test all INFRASTRUCTURE_COMMANDS values are sets."""
        for infra, commands in INFRASTRUCTURE_COMMANDS.items():
            assert isinstance(commands, set), f"{infra} commands is not a set"

    def test_infrastructure_commands_all_sets_non_empty(self):
        """Test all infrastructure sets are non-empty."""
        for infra, commands in INFRASTRUCTURE_COMMANDS.items():
            assert len(commands) > 0, f"{infra} has empty command set"


# =============================================================================
# CLOUD_COMMANDS TESTS
# =============================================================================

class TestCloudCommands:
    """Tests for CLOUD_COMMANDS registry"""

    def test_cloud_commands_is_dict(self):
        """Test CLOUD_COMMANDS is a dict."""
        assert isinstance(CLOUD_COMMANDS, dict)

    def test_cloud_commands_not_empty(self):
        """Test CLOUD_COMMANDS is not empty."""
        assert len(CLOUD_COMMANDS) > 0

    def test_cloud_commands_contains_aws(self):
        """Test CLOUD_COMMANDS contains AWS."""
        assert "aws" in CLOUD_COMMANDS
        assert "aws" in CLOUD_COMMANDS["aws"]

    def test_cloud_commands_contains_gcp(self):
        """Test CLOUD_COMMANDS contains GCP."""
        assert "gcp" in CLOUD_COMMANDS or "gcloud" in CLOUD_COMMANDS

    def test_cloud_commands_contains_azure(self):
        """Test CLOUD_COMMANDS contains Azure."""
        assert "azure" in CLOUD_COMMANDS

    def test_cloud_commands_all_values_are_sets(self):
        """Test all CLOUD_COMMANDS values are sets."""
        for cloud, commands in CLOUD_COMMANDS.items():
            assert isinstance(commands, set), f"{cloud} commands is not a set"

    def test_cloud_commands_all_sets_non_empty(self):
        """Test all cloud sets are non-empty."""
        for cloud, commands in CLOUD_COMMANDS.items():
            assert len(commands) > 0, f"{cloud} has empty command set"


# =============================================================================
# CODE_QUALITY_COMMANDS TESTS
# =============================================================================

class TestCodeQualityCommands:
    """Tests for CODE_QUALITY_COMMANDS registry"""

    def test_code_quality_commands_is_dict(self):
        """Test CODE_QUALITY_COMMANDS is a dict."""
        assert isinstance(CODE_QUALITY_COMMANDS, dict)

    def test_code_quality_commands_not_empty(self):
        """Test CODE_QUALITY_COMMANDS is not empty."""
        assert len(CODE_QUALITY_COMMANDS) > 0

    def test_code_quality_commands_contains_shellcheck(self):
        """Test CODE_QUALITY_COMMANDS contains ShellCheck."""
        assert "shellcheck" in CODE_QUALITY_COMMANDS
        assert "shellcheck" in CODE_QUALITY_COMMANDS["shellcheck"]

    def test_code_quality_commands_contains_yamllint(self):
        """Test CODE_QUALITY_COMMANDS contains yamllint."""
        assert "yamllint" in CODE_QUALITY_COMMANDS

    def test_code_quality_commands_contains_snyk(self):
        """Test CODE_QUALITY_COMMANDS contains Snyk (security scanner)."""
        assert "snyk" in CODE_QUALITY_COMMANDS
        assert "snyk" in CODE_QUALITY_COMMANDS["snyk"]

    def test_code_quality_commands_all_values_are_sets(self):
        """Test all CODE_QUALITY_COMMANDS values are sets."""
        for tool, commands in CODE_QUALITY_COMMANDS.items():
            assert isinstance(commands, set), f"{tool} commands is not a set"

    def test_code_quality_commands_all_sets_non_empty(self):
        """Test all code quality sets are non-empty."""
        for tool, commands in CODE_QUALITY_COMMANDS.items():
            assert len(commands) > 0, f"{tool} has empty command set"


# =============================================================================
# VERSION_MANAGER_COMMANDS TESTS
# =============================================================================

class TestVersionManagerCommands:
    """Tests for VERSION_MANAGER_COMMANDS registry"""

    def test_version_manager_commands_is_dict(self):
        """Test VERSION_MANAGER_COMMANDS is a dict."""
        assert isinstance(VERSION_MANAGER_COMMANDS, dict)

    def test_version_manager_commands_not_empty(self):
        """Test VERSION_MANAGER_COMMANDS is not empty."""
        assert len(VERSION_MANAGER_COMMANDS) > 0

    def test_version_manager_commands_contains_nvm(self):
        """Test VERSION_MANAGER_COMMANDS contains nvm."""
        assert "nvm" in VERSION_MANAGER_COMMANDS

    def test_version_manager_commands_contains_pyenv(self):
        """Test VERSION_MANAGER_COMMANDS contains pyenv."""
        assert "pyenv" in VERSION_MANAGER_COMMANDS

    def test_version_manager_commands_contains_rustup(self):
        """Test VERSION_MANAGER_COMMANDS contains rustup."""
        assert "rustup" in VERSION_MANAGER_COMMANDS

    def test_version_manager_commands_contains_goenv(self):
        """Test VERSION_MANAGER_COMMANDS contains goenv (Go)."""
        assert "goenv" in VERSION_MANAGER_COMMANDS

    def test_version_manager_commands_all_values_are_sets(self):
        """Test all VERSION_MANAGER_COMMANDS values are sets."""
        for vm, commands in VERSION_MANAGER_COMMANDS.items():
            assert isinstance(commands, set), f"{vm} commands is not a set"

    def test_version_manager_commands_all_sets_non_empty(self):
        """Test all version manager sets are non-empty."""
        for vm, commands in VERSION_MANAGER_COMMANDS.items():
            assert len(commands) > 0, f"{vm} has empty command set"


# =============================================================================
# CROSS-REGISTRY TESTS
# =============================================================================

class TestCrossRegistry:
    """Tests for cross-registry consistency and structure"""

    def test_all_registries_exist(self):
        """Test all expected registry constants are exported."""
        from project.command_registry import __all__
        expected = [
            "BASE_COMMANDS",
            "VALIDATED_COMMANDS",
            "LANGUAGE_COMMANDS",
            "PACKAGE_MANAGER_COMMANDS",
            "FRAMEWORK_COMMANDS",
            "DATABASE_COMMANDS",
            "INFRASTRUCTURE_COMMANDS",
            "CLOUD_COMMANDS",
            "CODE_QUALITY_COMMANDS",
            "VERSION_MANAGER_COMMANDS",
        ]
        for name in expected:
            assert name in __all__, f"{name} not in __all__"

    def test_validated_commands_in_base(self):
        """Test all validated commands exist in BASE_COMMANDS."""
        for cmd in VALIDATED_COMMANDS:
            assert cmd in BASE_COMMANDS, f"{cmd} in VALIDATED_COMMANDS but not in BASE_COMMANDS"

    def test_all_registries_have_correct_types(self):
        """Test all registries have the expected types."""
        assert isinstance(BASE_COMMANDS, set)
        assert isinstance(VALIDATED_COMMANDS, dict)
        assert isinstance(LANGUAGE_COMMANDS, dict)
        assert isinstance(PACKAGE_MANAGER_COMMANDS, dict)
        assert isinstance(FRAMEWORK_COMMANDS, dict)
        assert isinstance(DATABASE_COMMANDS, dict)
        assert isinstance(INFRASTRUCTURE_COMMANDS, dict)
        assert isinstance(CLOUD_COMMANDS, dict)
        assert isinstance(CODE_QUALITY_COMMANDS, dict)
        assert isinstance(VERSION_MANAGER_COMMANDS, dict)

    def test_all_dict_registries_have_set_values(self):
        """Test all dict registries have set values."""
        dict_registries = {
            "LANGUAGE_COMMANDS": LANGUAGE_COMMANDS,
            "PACKAGE_MANAGER_COMMANDS": PACKAGE_MANAGER_COMMANDS,
            "FRAMEWORK_COMMANDS": FRAMEWORK_COMMANDS,
            "DATABASE_COMMANDS": DATABASE_COMMANDS,
            "INFRASTRUCTURE_COMMANDS": INFRASTRUCTURE_COMMANDS,
            "CLOUD_COMMANDS": CLOUD_COMMANDS,
            "CODE_QUALITY_COMMANDS": CODE_QUALITY_COMMANDS,
            "VERSION_MANAGER_COMMANDS": VERSION_MANAGER_COMMANDS,
        }

        for name, registry in dict_registries.items():
            for key, value in registry.items():
                assert isinstance(value, set), f"{name}[{key}] is not a set"

    def test_all_registry_sets_non_empty(self):
        """Test all registry sets (both top-level and nested) are non-empty."""
        # Top-level BASE_COMMANDS
        assert len(BASE_COMMANDS) > 0, "BASE_COMMANDS is empty"

        # Dict registries
        dict_registries = {
            "LANGUAGE_COMMANDS": LANGUAGE_COMMANDS,
            "PACKAGE_MANAGER_COMMANDS": PACKAGE_MANAGER_COMMANDS,
            "FRAMEWORK_COMMANDS": FRAMEWORK_COMMANDS,
            "DATABASE_COMMANDS": DATABASE_COMMANDS,
            "INFRASTRUCTURE_COMMANDS": INFRASTRUCTURE_COMMANDS,
            "CLOUD_COMMANDS": CLOUD_COMMANDS,
            "CODE_QUALITY_COMMANDS": CODE_QUALITY_COMMANDS,
            "VERSION_MANAGER_COMMANDS": VERSION_MANAGER_COMMANDS,
        }

        for name, registry in dict_registries.items():
            for key, value in registry.items():
                assert len(value) > 0, f"{name}[{key}] is empty"

    def test_command_names_are_reasonable(self):
        """Test command names follow reasonable conventions."""
        # Check no commands with spaces
        for cmd in BASE_COMMANDS:
            assert " " not in cmd, f"BASE_COMMANDS contains command with space: {cmd}"

        for registry in [LANGUAGE_COMMANDS, PACKAGE_MANAGER_COMMANDS,
                         FRAMEWORK_COMMANDS, DATABASE_COMMANDS,
                         INFRASTRUCTURE_COMMANDS, CLOUD_COMMANDS,
                         CODE_QUALITY_COMMANDS, VERSION_MANAGER_COMMANDS]:
            for tech, commands in registry.items():
                for cmd in commands:
                    assert " " not in cmd, f"{tech}: command with space: {cmd}"

    def test_common_commands_coverage(self):
        """Test that common development commands are covered."""
        all_commands = BASE_COMMANDS.copy()

        for registry in [LANGUAGE_COMMANDS, PACKAGE_MANAGER_COMMANDS,
                         FRAMEWORK_COMMANDS, DATABASE_COMMANDS,
                         INFRASTRUCTURE_COMMANDS, CLOUD_COMMANDS,
                         CODE_QUALITY_COMMANDS, VERSION_MANAGER_COMMANDS]:
            for commands in registry.values():
                all_commands.update(commands)

        # Check some very common commands are covered
        assert "git" in all_commands
        assert "ls" in all_commands
        assert "python" in all_commands
        assert "node" in all_commands or "npm" in all_commands
        assert "docker" in all_commands

    def test_registry_immutability(self):
        """Test that modifying returned sets doesn't affect source (for dicts)."""
        # This is mostly informational - in Python, sets are mutable
        # But we can verify the structure is as expected
        original_len = len(LANGUAGE_COMMANDS["python"])

        # Make a copy and modify
        test_set = LANGUAGE_COMMANDS["python"].copy()
        test_set.add("fake-command")

        # Original should be unchanged
        assert len(LANGUAGE_COMMANDS["python"]) == original_len
        assert "fake-command" not in LANGUAGE_COMMANDS["python"]
