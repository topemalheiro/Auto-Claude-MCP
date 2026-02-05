"""
Tests for project.models
========================

Comprehensive tests for the data models in the project module:
- SecurityProfile dataclass
- TechnologyStack dataclass
- CustomScripts dataclass

Tests cover:
- Dataclass instantiation with valid and invalid data
- Serialization methods (to_dict, from_dict)
- Property methods and computed values
- Edge cases (None values, empty strings, special characters)
- Set operations for command collections
"""

import json
from datetime import datetime
from pathlib import Path

import pytest

from project.models import SecurityProfile, TechnologyStack, CustomScripts


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_technology_stack() -> TechnologyStack:
    """Create a sample TechnologyStack for testing."""
    return TechnologyStack(
        languages=["python", "javascript", "typescript"],
        package_managers=["pip", "npm", "poetry"],
        frameworks=["django", "react", "fastapi"],
        databases=["postgresql", "redis", "mongodb"],
        infrastructure=["docker", "kubernetes"],
        cloud_providers=["aws", "gcp"],
        code_quality_tools=["pytest", "eslint", "ruff"],
        version_managers=["nvm", "pyenv"]
    )


@pytest.fixture
def sample_custom_scripts() -> CustomScripts:
    """Create a sample CustomScripts for testing."""
    return CustomScripts(
        npm_scripts=["build", "test", "lint", "dev"],
        make_targets=["all", "clean", "install", "deploy"],
        poetry_scripts=["format", "lint"],
        cargo_aliases=["build", "test", "run"],
        shell_scripts=["deploy.sh", "setup.sh", "backup.sh"]
    )


@pytest.fixture
def sample_security_profile(
    sample_technology_stack: TechnologyStack,
    sample_custom_scripts: CustomScripts
) -> SecurityProfile:
    """Create a sample SecurityProfile for testing."""
    return SecurityProfile(
        base_commands={"git", "ls", "cd", "pwd", "cat"},
        stack_commands={"python", "npm", "pytest", "django-admin"},
        script_commands={"npm", "make", "./deploy.sh"},
        custom_commands={"my-custom-tool", "another-tool"},
        detected_stack=sample_technology_stack,
        custom_scripts=sample_custom_scripts,
        project_dir="/path/to/project",
        created_at="2024-01-15T10:30:00",
        project_hash="abc123def456",
        inherited_from=""
    )


@pytest.fixture
def temp_profile_path(tmp_path: Path) -> Path:
    """Create a temporary path for profile testing."""
    return tmp_path / "test_profile.json"


# =============================================================================
# TechnologyStack Tests
# =============================================================================

class TestTechnologyStack:
    """Tests for TechnologyStack dataclass."""

    def test_default_initialization(self):
        """Test TechnologyStack initializes with empty lists by default."""
        stack = TechnologyStack()

        assert stack.languages == []
        assert stack.package_managers == []
        assert stack.frameworks == []
        assert stack.databases == []
        assert stack.infrastructure == []
        assert stack.cloud_providers == []
        assert stack.code_quality_tools == []
        assert stack.version_managers == []

    def test_initialization_with_values(self):
        """Test TechnologyStack initialization with values."""
        stack = TechnologyStack(
            languages=["python", "javascript"],
            package_managers=["pip", "npm"],
            frameworks=["django", "react"]
        )

        assert len(stack.languages) == 2
        assert "python" in stack.languages
        assert "javascript" in stack.languages
        assert "pip" in stack.package_managers
        assert "django" in stack.frameworks

    def test_initialization_with_empty_lists(self):
        """Test TechnologyStack with explicitly empty lists."""
        stack = TechnologyStack(
            languages=[],
            package_managers=[],
            frameworks=[]
        )

        assert stack.languages == []
        assert stack.package_managers == []
        assert stack.frameworks == []

    def test_list_field_is_factory(self):
        """Test that list fields use factory and don't share references."""
        stack1 = TechnologyStack()
        stack2 = TechnologyStack()

        # Modify stack1
        stack1.languages.append("python")

        # stack2 should remain unaffected
        assert stack2.languages == []
        assert "python" not in stack2.languages

    def test_all_fields_mutable(self):
        """Test that all fields are mutable after initialization."""
        stack = TechnologyStack()

        stack.languages.append("python")
        stack.package_managers.append("pip")
        stack.frameworks.append("django")
        stack.databases.append("postgresql")
        stack.infrastructure.append("docker")
        stack.cloud_providers.append("aws")
        stack.code_quality_tools.append("pytest")
        stack.version_managers.append("pyenv")

        assert len(stack.languages) == 1
        assert len(stack.package_managers) == 1
        assert len(stack.frameworks) == 1
        assert len(stack.databases) == 1
        assert len(stack.infrastructure) == 1
        assert len(stack.cloud_providers) == 1
        assert len(stack.code_quality_tools) == 1
        assert len(stack.version_managers) == 1

    def test_special_characters_in_values(self):
        """Test TechnologyStack with special characters in values."""
        stack = TechnologyStack(
            languages=["c++", "c#", "f#"],
            frameworks=[".net-core", "node.js"]
        )

        assert "c++" in stack.languages
        assert "c#" in stack.languages
        assert ".net-core" in stack.frameworks

    def test_duplicate_values_allowed(self):
        """Test that duplicate values are allowed in lists."""
        stack = TechnologyStack(
            languages=["python", "python", "javascript"]
        )

        assert stack.languages.count("python") == 2

    def test_case_sensitivity(self):
        """Test that values are case-sensitive."""
        stack = TechnologyStack(
            languages=["Python", "python", "PYTHON"]
        )

        assert len(stack.languages) == 3
        assert "Python" in stack.languages
        assert "python" in stack.languages
        assert "PYTHON" in stack.languages


# =============================================================================
# CustomScripts Tests
# =============================================================================

class TestCustomScripts:
    """Tests for CustomScripts dataclass."""

    def test_default_initialization(self):
        """Test CustomScripts initializes with empty lists by default."""
        scripts = CustomScripts()

        assert scripts.npm_scripts == []
        assert scripts.make_targets == []
        assert scripts.poetry_scripts == []
        assert scripts.cargo_aliases == []
        assert scripts.shell_scripts == []

    def test_initialization_with_values(self):
        """Test CustomScripts initialization with values."""
        scripts = CustomScripts(
            npm_scripts=["build", "test"],
            make_targets=["all", "clean"],
            poetry_scripts=["format"],
            cargo_aliases=["build", "run"],
            shell_scripts=["deploy.sh"]
        )

        assert "build" in scripts.npm_scripts
        assert "all" in scripts.make_targets
        assert "format" in scripts.poetry_scripts
        assert "run" in scripts.cargo_aliases
        assert "deploy.sh" in scripts.shell_scripts

    def test_initialization_with_empty_lists(self):
        """Test CustomScripts with explicitly empty lists."""
        scripts = CustomScripts(
            npm_scripts=[],
            make_targets=[],
            poetry_scripts=[]
        )

        assert scripts.npm_scripts == []
        assert scripts.make_targets == []
        assert scripts.poetry_scripts == []

    def test_list_field_is_factory(self):
        """Test that list fields use factory and don't share references."""
        scripts1 = CustomScripts()
        scripts2 = CustomScripts()

        # Modify scripts1
        scripts1.npm_scripts.append("build")

        # scripts2 should remain unaffected
        assert scripts2.npm_scripts == []
        assert "build" not in scripts2.npm_scripts

    def test_script_names_with_special_characters(self):
        """Test script names with special characters."""
        scripts = CustomScripts(
            npm_scripts=["build:prod", "test:unit", "dev:server"],
            make_targets=["install-deps", "build-all"],
            shell_scripts=["deploy-production.sh", "setup_local.sh"]
        )

        assert "build:prod" in scripts.npm_scripts
        assert "install-deps" in scripts.make_targets
        assert "deploy-production.sh" in scripts.shell_scripts

    def test_all_fields_mutable(self):
        """Test that all fields are mutable after initialization."""
        scripts = CustomScripts()

        scripts.npm_scripts.append("build")
        scripts.make_targets.append("all")
        scripts.poetry_scripts.append("format")
        scripts.cargo_aliases.append("run")
        scripts.shell_scripts.append("deploy.sh")

        assert len(scripts.npm_scripts) == 1
        assert len(scripts.make_targets) == 1
        assert len(scripts.poetry_scripts) == 1
        assert len(scripts.cargo_aliases) == 1
        assert len(scripts.shell_scripts) == 1


# =============================================================================
# SecurityProfile - Initialization Tests
# =============================================================================

class TestSecurityProfileInitialization:
    """Tests for SecurityProfile initialization."""

    def test_default_initialization(self):
        """Test SecurityProfile initializes with defaults."""
        profile = SecurityProfile()

        assert profile.base_commands == set()
        assert profile.stack_commands == set()
        assert profile.script_commands == set()
        assert profile.custom_commands == set()
        assert isinstance(profile.detected_stack, TechnologyStack)
        assert isinstance(profile.custom_scripts, CustomScripts)
        assert profile.project_dir == ""
        assert profile.created_at == ""
        assert profile.project_hash == ""
        assert profile.inherited_from == ""

    def test_initialization_with_all_fields(self):
        """Test SecurityProfile initialization with all fields."""
        stack = TechnologyStack(languages=["python"])
        scripts = CustomScripts(npm_scripts=["build"])

        profile = SecurityProfile(
            base_commands={"git", "ls"},
            stack_commands={"python"},
            script_commands={"npm"},
            custom_commands={"custom"},
            detected_stack=stack,
            custom_scripts=scripts,
            project_dir="/path/to/project",
            created_at="2024-01-15T10:00:00",
            project_hash="abc123",
            inherited_from="/parent/path"
        )

        assert profile.base_commands == {"git", "ls"}
        assert profile.stack_commands == {"python"}
        assert profile.script_commands == {"npm"}
        assert profile.custom_commands == {"custom"}
        assert profile.detected_stack == stack
        assert profile.custom_scripts == scripts
        assert profile.project_dir == "/path/to/project"
        assert profile.created_at == "2024-01-15T10:00:00"
        assert profile.project_hash == "abc123"
        assert profile.inherited_from == "/parent/path"

    def test_set_field_is_factory(self):
        """Test that set fields use factory and don't share references."""
        profile1 = SecurityProfile()
        profile2 = SecurityProfile()

        # Modify profile1
        profile1.base_commands.add("git")

        # profile2 should remain unaffected
        assert profile2.base_commands == set()
        assert "git" not in profile2.base_commands

    def test_default_stack_and_scripts_instances(self):
        """Test that default stack and scripts are independent instances."""
        profile1 = SecurityProfile()
        profile2 = SecurityProfile()

        # Modify profile1's stack
        profile1.detected_stack.languages.append("python")

        # profile2's stack should be unaffected
        assert profile2.detected_stack.languages == []

    def test_empty_string_metadata_fields(self):
        """Test SecurityProfile with empty string metadata."""
        profile = SecurityProfile(
            base_commands={"git"},
            project_dir="",
            created_at="",
            project_hash="",
            inherited_from=""
        )

        assert profile.project_dir == ""
        assert profile.created_at == ""
        assert profile.project_hash == ""
        assert profile.inherited_from == ""


# =============================================================================
# SecurityProfile - get_all_allowed_commands Tests
# =============================================================================

class TestGetAllAllowedCommands:
    """Tests for get_all_allowed_commands method."""

    def test_get_all_commands_empty_profile(self):
        """Test get_all_allowed_commands on empty profile."""
        profile = SecurityProfile()

        commands = profile.get_all_allowed_commands()

        assert commands == set()

    def test_get_all_commands_single_set(self):
        """Test get_all_allowed_commands with only base_commands."""
        profile = SecurityProfile(base_commands={"git", "ls"})

        commands = profile.get_all_allowed_commands()

        assert commands == {"git", "ls"}

    def test_get_all_commands_multiple_sets(self):
        """Test get_all_allowed_commands combines all command sets."""
        profile = SecurityProfile(
            base_commands={"git", "ls"},
            stack_commands={"python", "npm"},
            script_commands={"make", "./deploy.sh"},
            custom_commands={"custom-tool"}
        )

        commands = profile.get_all_allowed_commands()

        assert commands == {
            "git", "ls", "python", "npm", "make", "./deploy.sh", "custom-tool"
        }

    def test_get_all_commands_removes_duplicates(self):
        """Test get_all_allowed_commands removes duplicates across sets."""
        profile = SecurityProfile(
            base_commands={"git", "npm"},
            stack_commands={"npm", "python"},
            script_commands={"git", "make"}
        )

        commands = profile.get_all_allowed_commands()

        # Duplicates should be removed (sets don't have duplicates)
        assert commands == {"git", "npm", "python", "make"}
        assert len(commands) == 4

    def test_get_all_commands_returns_new_set(self):
        """Test that get_all_allowed_commands returns a new set, not reference."""
        profile = SecurityProfile(base_commands={"git"})

        commands1 = profile.get_all_allowed_commands()
        commands2 = profile.get_all_allowed_commands()

        # Modify commands1
        commands1.add("ls")

        # commands2 should be unaffected
        assert "ls" not in commands2
        assert commands1 != commands2

    def test_get_all_commands_with_inherited_from_set(self):
        """Test get_all_allowed_commands when inherited_from is set."""
        profile = SecurityProfile(
            base_commands={"git"},
            inherited_from="/parent/path"
        )

        commands = profile.get_all_allowed_commands()

        assert commands == {"git"}


# =============================================================================
# SecurityProfile - to_dict Tests
# =============================================================================

class TestToDict:
    """Tests for to_dict method."""

    def test_to_dict_basic_profile(self):
        """Test to_dict with basic profile."""
        profile = SecurityProfile(
            base_commands={"git", "ls"},
            stack_commands={"python"},
            project_dir="/path/to/project",
            created_at="2024-01-15T10:00:00",
            project_hash="abc123"
        )

        result = profile.to_dict()

        assert isinstance(result, dict)
        assert "base_commands" in result
        assert "stack_commands" in result
        assert "script_commands" in result
        assert "custom_commands" in result
        assert "detected_stack" in result
        assert "custom_scripts" in result
        assert "project_dir" in result
        assert "created_at" in result
        assert "project_hash" in result

    def test_to_dict_sorts_command_sets(self):
        """Test that to_dict sorts command sets for consistent output."""
        profile = SecurityProfile(
            base_commands={"zebra", "apple", "banana"},
            stack_commands={"python", "npm", "django"}
        )

        result = profile.to_dict()

        # Commands should be sorted
        assert result["base_commands"] == ["apple", "banana", "zebra"]
        assert result["stack_commands"] == ["django", "npm", "python"]

    def test_to_dict_includes_detected_stack(self):
        """Test that to_dict includes detected_stack as dict."""
        profile = SecurityProfile(
            detected_stack=TechnologyStack(
                languages=["python", "javascript"],
                frameworks=["django", "react"]
            )
        )

        result = profile.to_dict()

        assert "detected_stack" in result
        assert isinstance(result["detected_stack"], dict)
        assert result["detected_stack"]["languages"] == ["python", "javascript"]
        assert result["detected_stack"]["frameworks"] == ["django", "react"]

    def test_to_dict_includes_custom_scripts(self):
        """Test that to_dict includes custom_scripts as dict."""
        profile = SecurityProfile(
            custom_scripts=CustomScripts(
                npm_scripts=["build", "test"],
                make_targets=["all", "clean"]
            )
        )

        result = profile.to_dict()

        assert "custom_scripts" in result
        assert isinstance(result["custom_scripts"], dict)
        assert result["custom_scripts"]["npm_scripts"] == ["build", "test"]
        assert result["custom_scripts"]["make_targets"] == ["all", "clean"]

    def test_to_dict_with_empty_inherited_from(self):
        """Test to_dict doesn't include inherited_from when empty."""
        profile = SecurityProfile(
            base_commands={"git"},
            inherited_from=""
        )

        result = profile.to_dict()

        # Empty inherited_from should not be in dict (backward compatibility)
        assert "inherited_from" not in result

    def test_to_dict_with_non_empty_inherited_from(self):
        """Test to_dict includes inherited_from when set."""
        profile = SecurityProfile(
            base_commands={"git"},
            inherited_from="/parent/path"
        )

        result = profile.to_dict()

        assert "inherited_from" in result
        assert result["inherited_from"] == "/parent/path"

    def test_to_dict_complete_profile(self, sample_security_profile: SecurityProfile):
        """Test to_dict with complete profile."""
        result = sample_security_profile.to_dict()

        assert result["project_dir"] == sample_security_profile.project_dir
        assert result["created_at"] == sample_security_profile.created_at
        assert result["project_hash"] == sample_security_profile.project_hash
        assert len(result["base_commands"]) == len(sample_security_profile.base_commands)
        assert len(result["stack_commands"]) == len(sample_security_profile.stack_commands)

    def test_to_dict_empty_fields(self):
        """Test to_dict with empty command sets."""
        profile = SecurityProfile()

        result = profile.to_dict()

        assert result["base_commands"] == []
        assert result["stack_commands"] == []
        assert result["script_commands"] == []
        assert result["custom_commands"] == []

    def test_to_dict_preserves_metadata(self):
        """Test that to_dict preserves metadata fields."""
        profile = SecurityProfile(
            project_dir="/test/path",
            created_at="2024-01-15T10:30:00.123456",
            project_hash="a1b2c3d4"
        )

        result = profile.to_dict()

        assert result["project_dir"] == "/test/path"
        assert result["created_at"] == "2024-01-15T10:30:00.123456"
        assert result["project_hash"] == "a1b2c3d4"


# =============================================================================
# SecurityProfile - from_dict Tests
# =============================================================================

class TestFromDict:
    """Tests for from_dict class method."""

    def test_from_dict_minimal_data(self):
        """Test from_dict with minimal required data."""
        data = {}

        profile = SecurityProfile.from_dict(data)

        assert isinstance(profile, SecurityProfile)
        assert profile.base_commands == set()
        assert profile.stack_commands == set()
        assert profile.script_commands == set()
        assert profile.custom_commands == set()
        assert profile.project_dir == ""
        assert profile.created_at == ""
        assert profile.project_hash == ""
        assert profile.inherited_from == ""

    def test_from_dict_with_command_lists(self):
        """Test from_dict converts command lists to sets."""
        data = {
            "base_commands": ["git", "ls", "cd"],
            "stack_commands": ["python", "npm"],
            "script_commands": ["make"],
            "custom_commands": ["custom-tool"]
        }

        profile = SecurityProfile.from_dict(data)

        assert profile.base_commands == {"git", "ls", "cd"}
        assert profile.stack_commands == {"python", "npm"}
        assert profile.script_commands == {"make"}
        assert profile.custom_commands == {"custom-tool"}

    def test_from_dict_with_metadata(self):
        """Test from_dict with metadata fields."""
        data = {
            "project_dir": "/path/to/project",
            "created_at": "2024-01-15T10:30:00",
            "project_hash": "abc123def456",
            "inherited_from": "/parent/path"
        }

        profile = SecurityProfile.from_dict(data)

        assert profile.project_dir == "/path/to/project"
        assert profile.created_at == "2024-01-15T10:30:00"
        assert profile.project_hash == "abc123def456"
        assert profile.inherited_from == "/parent/path"

    def test_from_dict_with_detected_stack(self):
        """Test from_dict with detected_stack."""
        data = {
            "detected_stack": {
                "languages": ["python", "javascript"],
                "package_managers": ["pip", "npm"],
                "frameworks": ["django", "react"]
            }
        }

        profile = SecurityProfile.from_dict(data)

        assert isinstance(profile.detected_stack, TechnologyStack)
        assert profile.detected_stack.languages == ["python", "javascript"]
        assert profile.detected_stack.package_managers == ["pip", "npm"]
        assert profile.detected_stack.frameworks == ["django", "react"]

    def test_from_dict_with_custom_scripts(self):
        """Test from_dict with custom_scripts."""
        data = {
            "custom_scripts": {
                "npm_scripts": ["build", "test"],
                "make_targets": ["all", "clean"],
                "poetry_scripts": ["format"],
                "cargo_aliases": ["run"],
                "shell_scripts": ["deploy.sh"]
            }
        }

        profile = SecurityProfile.from_dict(data)

        assert isinstance(profile.custom_scripts, CustomScripts)
        assert profile.custom_scripts.npm_scripts == ["build", "test"]
        assert profile.custom_scripts.make_targets == ["all", "clean"]
        assert profile.custom_scripts.poetry_scripts == ["format"]
        assert profile.custom_scripts.cargo_aliases == ["run"]
        assert profile.custom_scripts.shell_scripts == ["deploy.sh"]

    def test_from_dict_complete_data(self, sample_security_profile: SecurityProfile):
        """Test from_dict with complete profile data."""
        data = sample_security_profile.to_dict()

        profile = SecurityProfile.from_dict(data)

        assert profile.base_commands == sample_security_profile.base_commands
        assert profile.stack_commands == sample_security_profile.stack_commands
        assert profile.script_commands == sample_security_profile.script_commands
        assert profile.custom_commands == sample_security_profile.custom_commands
        assert profile.detected_stack.languages == sample_security_profile.detected_stack.languages
        assert profile.custom_scripts.npm_scripts == sample_security_profile.custom_scripts.npm_scripts
        assert profile.project_dir == sample_security_profile.project_dir
        assert profile.created_at == sample_security_profile.created_at
        assert profile.project_hash == sample_security_profile.project_hash

    def test_from_dict_without_detected_stack(self):
        """Test from_dict without detected_stack uses default."""
        data = {
            "base_commands": ["git"]
        }

        profile = SecurityProfile.from_dict(data)

        # Should have default TechnologyStack
        assert isinstance(profile.detected_stack, TechnologyStack)
        assert profile.detected_stack.languages == []

    def test_from_dict_without_custom_scripts(self):
        """Test from_dict without custom_scripts uses default."""
        data = {
            "base_commands": ["git"]
        }

        profile = SecurityProfile.from_dict(data)

        # Should have default CustomScripts
        assert isinstance(profile.custom_scripts, CustomScripts)
        assert profile.custom_scripts.npm_scripts == []

    def test_from_dict_round_trip(self, sample_security_profile: SecurityProfile):
        """Test that to_dict -> from_dict preserves data."""
        # Use a profile without inherited_from for round-trip test
        profile = SecurityProfile(
            base_commands=sample_security_profile.base_commands,
            stack_commands=sample_security_profile.stack_commands,
            script_commands=sample_security_profile.script_commands,
            custom_commands=sample_security_profile.custom_commands,
            detected_stack=sample_security_profile.detected_stack,
            custom_scripts=sample_security_profile.custom_scripts,
            project_dir=sample_security_profile.project_dir,
            created_at=sample_security_profile.created_at,
            project_hash=sample_security_profile.project_hash
        )

        # Convert to dict and back
        data = profile.to_dict()
        restored = SecurityProfile.from_dict(data)

        # Verify all fields match
        assert restored.base_commands == profile.base_commands
        assert restored.stack_commands == profile.stack_commands
        assert restored.script_commands == profile.script_commands
        assert restored.custom_commands == profile.custom_commands
        assert restored.detected_stack.languages == profile.detected_stack.languages
        assert restored.custom_scripts.npm_scripts == profile.custom_scripts.npm_scripts
        assert restored.project_dir == profile.project_dir
        assert restored.created_at == profile.created_at
        assert restored.project_hash == profile.project_hash

    def test_from_dict_with_inherited_from(self):
        """Test from_dict with inherited_from field."""
        data = {
            "base_commands": ["git"],
            "inherited_from": "/path/to/parent"
        }

        profile = SecurityProfile.from_dict(data)

        assert profile.inherited_from == "/path/to/parent"

    def test_from_dict_empty_command_lists(self):
        """Test from_dict with empty command lists."""
        data = {
            "base_commands": [],
            "stack_commands": [],
            "script_commands": [],
            "custom_commands": []
        }

        profile = SecurityProfile.from_dict(data)

        assert profile.base_commands == set()
        assert profile.stack_commands == set()
        assert profile.script_commands == set()
        assert profile.custom_commands == set()


# =============================================================================
# SecurityProfile - JSON Serialization Tests
# =============================================================================

class TestJsonSerialization:
    """Tests for JSON serialization round-trips."""

    def test_json_round_trip(self, sample_security_profile: SecurityProfile):
        """Test complete JSON serialization round-trip."""
        # Convert to dict
        data = sample_security_profile.to_dict()

        # Serialize to JSON
        json_str = json.dumps(data)

        # Deserialize from JSON
        loaded_data = json.loads(json_str)

        # Reconstruct profile
        restored_profile = SecurityProfile.from_dict(loaded_data)

        # Verify
        assert restored_profile.base_commands == sample_security_profile.base_commands
        assert restored_profile.stack_commands == sample_security_profile.stack_commands
        assert restored_profile.project_dir == sample_security_profile.project_dir
        assert restored_profile.created_at == sample_security_profile.created_at
        assert restored_profile.project_hash == sample_security_profile.project_hash

    def test_json_serialization_to_file(
        self,
        sample_security_profile: SecurityProfile,
        temp_profile_path: Path
    ):
        """Test writing profile to JSON file."""
        # Write to file
        with open(temp_profile_path, "w") as f:
            json.dump(sample_security_profile.to_dict(), f)

        # Read from file
        with open(temp_profile_path, "r") as f:
            loaded_data = json.load(f)

        # Reconstruct and verify
        restored_profile = SecurityProfile.from_dict(loaded_data)
        assert restored_profile.project_dir == sample_security_profile.project_dir
        assert restored_profile.project_hash == sample_security_profile.project_hash


# =============================================================================
# Edge Cases and Special Characters Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_security_profile_with_special_characters_in_commands(self):
        """Test commands with special characters."""
        profile = SecurityProfile(
            base_commands={"./script.sh", "../relative/path", "/absolute/path"},
            script_commands={"npm run build:prod", "make install-deps"}
        )

        commands = profile.get_all_allowed_commands()

        assert "./script.sh" in commands
        assert "../relative/path" in commands
        assert "/absolute/path" in commands
        assert "npm run build:prod" in commands

    def test_technology_stack_with_unicode(self):
        """Test TechnologyStack with unicode characters."""
        stack = TechnologyStack(
            languages=["python", "javascript", "日本語"],
            frameworks=["django", "réacteur"]
        )

        assert "日本語" in stack.languages
        assert "réacteur" in stack.frameworks

    def test_custom_scripts_with_unicode(self):
        """Test CustomScripts with unicode characters."""
        scripts = CustomScripts(
            npm_scripts=["build", "тест"],
            shell_scripts=["deploy.sh", "部署.sh"]
        )

        assert "тест" in scripts.npm_scripts
        assert "部署.sh" in scripts.shell_scripts

    def test_security_profile_with_unicode_metadata(self):
        """Test SecurityProfile with unicode in metadata."""
        profile = SecurityProfile(
            project_dir="/path/to/项目",
            created_at="2024-01-15T10:00:00",
            project_hash="abc123"
        )

        assert profile.project_dir == "/path/to/项目"

    def test_very_long_command_names(self):
        """Test with very long command names."""
        long_command = "a" * 1000
        profile = SecurityProfile(
            custom_commands={long_command}
        )

        commands = profile.get_all_allowed_commands()
        assert long_command in commands

    def test_many_commands(self):
        """Test profile with many commands."""
        base_commands = {f"command{i}" for i in range(1000)}

        profile = SecurityProfile(base_commands=base_commands)

        commands = profile.get_all_allowed_commands()
        assert len(commands) == 1000

    def test_empty_vs_none_handling(self):
        """Test that empty strings are handled correctly."""
        profile = SecurityProfile(
            project_dir="",
            created_at="",
            project_hash="",
            inherited_from=""
        )

        assert profile.project_dir == ""
        assert profile.created_at == ""
        assert profile.project_hash == ""
        assert profile.inherited_from == ""

    def test_mixed_empty_and_populated_fields(self):
        """Test profile with some empty and some populated fields."""
        profile = SecurityProfile(
            base_commands={"git"},
            stack_commands=set(),
            script_commands={"make"},
            custom_commands=set()
        )

        all_commands = profile.get_all_allowed_commands()
        assert all_commands == {"git", "make"}

    def test_serialization_preserves_all_fields(self):
        """Test that serialization preserves all field types."""
        profile = SecurityProfile(
            base_commands={"git", "ls"},
            stack_commands={"python"},
            detected_stack=TechnologyStack(
                languages=["python"],
                package_managers=[],
                frameworks=["django"],
                databases=[],
                infrastructure=[],
                cloud_providers=[],
                code_quality_tools=["pytest"],
                version_managers=[]
            ),
            custom_scripts=CustomScripts(
                npm_scripts=["build"],
                make_targets=[],
                poetry_scripts=[],
                cargo_aliases=[],
                shell_scripts=[]
            )
        )

        data = profile.to_dict()
        restored = SecurityProfile.from_dict(data)

        # Verify all empty lists are preserved
        assert restored.detected_stack.package_managers == []
        assert restored.detected_stack.databases == []
        assert restored.custom_scripts.make_targets == []
        assert restored.custom_scripts.poetry_scripts == []
