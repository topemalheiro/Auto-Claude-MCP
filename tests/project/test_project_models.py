"""
Comprehensive tests for project/models.py
==========================================

Tests for data models:
- TechnologyStack dataclass
- CustomScripts dataclass
- SecurityProfile dataclass and its methods:
  - get_all_allowed_commands()
  - to_dict()
  - from_dict()
"""

from datetime import datetime
from pathlib import Path

import pytest

from project.models import TechnologyStack, CustomScripts, SecurityProfile


# =============================================================================
# TECHNOLOGYSTACK TESTS
# =============================================================================

class TestTechnologyStack:
    """Tests for TechnologyStack dataclass"""

    def test_default_initialization(self):
        """Test TechnologyStack with default values."""
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
        """Test TechnologyStack with provided values."""
        stack = TechnologyStack(
            languages=["python", "javascript"],
            package_managers=["pip", "npm"],
            frameworks=["django", "react"],
            databases=["postgresql", "redis"],
            infrastructure=["docker", "kubernetes"],
            cloud_providers=["aws"],
            code_quality_tools=["pytest", "eslint"],
            version_managers=["pyenv", "nvm"]
        )

        assert len(stack.languages) == 2
        assert "python" in stack.languages
        assert len(stack.package_managers) == 2
        assert len(stack.frameworks) == 2
        assert len(stack.databases) == 2
        assert len(stack.infrastructure) == 2
        assert len(stack.cloud_providers) == 1
        assert len(stack.code_quality_tools) == 2
        assert len(stack.version_managers) == 2

    def test_list_factories_create_independent_lists(self):
        """Test that default_factory creates independent instances."""
        stack1 = TechnologyStack()
        stack2 = TechnologyStack()

        stack1.languages.append("python")

        assert "python" in stack1.languages
        assert "python" not in stack2.languages

    def test_mutable_operations(self):
        """Test mutable operations on TechnologyStack."""
        stack = TechnologyStack()

        stack.languages.append("python")
        stack.frameworks.extend(["django", "flask"])
        stack.databases += ["postgresql"]

        assert len(stack.languages) == 1
        assert len(stack.frameworks) == 2
        assert len(stack.databases) == 1


# =============================================================================
# CUSTOMSCRIPTS TESTS
# =============================================================================

class TestCustomScripts:
    """Tests for CustomScripts dataclass"""

    def test_default_initialization(self):
        """Test CustomScripts with default values."""
        scripts = CustomScripts()

        assert scripts.npm_scripts == []
        assert scripts.make_targets == []
        assert scripts.poetry_scripts == []
        assert scripts.cargo_aliases == []
        assert scripts.shell_scripts == []

    def test_initialization_with_values(self):
        """Test CustomScripts with provided values."""
        scripts = CustomScripts(
            npm_scripts=["build", "test", "lint"],
            make_targets=["install", "clean", "deploy"],
            poetry_scripts=["format", "publish"],
            cargo_aliases=["dev", "build"],
            shell_scripts=["deploy.sh", "backup.sh"]
        )

        assert len(scripts.npm_scripts) == 3
        assert len(scripts.make_targets) == 3
        assert len(scripts.poetry_scripts) == 2
        assert len(scripts.cargo_aliases) == 2
        assert len(scripts.shell_scripts) == 2

    def test_npm_scripts_operations(self):
        """Test npm_scripts list operations."""
        scripts = CustomScripts()

        scripts.npm_scripts.extend(["dev", "build", "test"])

        assert "dev" in scripts.npm_scripts
        assert "build" in scripts.npm_scripts
        assert len(scripts.npm_scripts) == 3

    def test_make_targets_operations(self):
        """Test make_targets list operations."""
        scripts = CustomScripts()

        scripts.make_targets.append("all")
        scripts.make_targets.append("clean")

        assert "all" in scripts.make_targets
        assert "clean" in scripts.make_targets

    def test_shell_scripts_operations(self):
        """Test shell_scripts list operations."""
        scripts = CustomScripts()

        scripts.shell_scripts.extend(["setup.sh", "deploy.sh"])

        assert "setup.sh" in scripts.shell_scripts
        assert "deploy.sh" in scripts.shell_scripts


# =============================================================================
# SECURITYPROFILE INITIALIZATION TESTS
# =============================================================================

class TestSecurityProfileInit:
    """Tests for SecurityProfile initialization"""

    def test_default_initialization(self):
        """Test SecurityProfile with default values."""
        profile = SecurityProfile()

        assert isinstance(profile.base_commands, set)
        assert isinstance(profile.stack_commands, set)
        assert isinstance(profile.script_commands, set)
        assert isinstance(profile.custom_commands, set)

        assert profile.base_commands == set()
        assert profile.stack_commands == set()
        assert profile.script_commands == set()
        assert profile.custom_commands == set()

    def test_initialization_with_command_sets(self):
        """Test SecurityProfile with provided command sets."""
        profile = SecurityProfile(
            base_commands={"git", "ls", "cat"},
            stack_commands={"npm", "node"},
            script_commands={"./build.sh"},
            custom_commands={"my-tool"}
        )

        assert "git" in profile.base_commands
        assert "npm" in profile.stack_commands
        assert "./build.sh" in profile.script_commands
        assert "my-tool" in profile.custom_commands

    def test_default_stack_and_scripts(self):
        """Test that detected_stack and custom_scripts have correct defaults."""
        profile = SecurityProfile()

        assert isinstance(profile.detected_stack, TechnologyStack)
        assert isinstance(profile.custom_scripts, CustomScripts)

        assert profile.detected_stack.languages == []
        assert profile.custom_scripts.npm_scripts == []

    def test_metadata_fields_defaults(self):
        """Test metadata field defaults."""
        profile = SecurityProfile()

        assert profile.project_dir == ""
        assert profile.created_at == ""
        assert profile.project_hash == ""
        assert profile.inherited_from == ""

    def test_set_factories_create_independent_sets(self):
        """Test that default_factory creates independent instances."""
        profile1 = SecurityProfile()
        profile2 = SecurityProfile()

        profile1.base_commands.add("git")

        assert "git" in profile1.base_commands
        assert "git" not in profile2.base_commands


# =============================================================================
# GET_ALL_ALLOWED_COMMANDS TESTS
# =============================================================================

class TestGetAllAllowedCommands:
    """Tests for SecurityProfile.get_all_allowed_commands"""

    def test_empty_profile(self):
        """Test get_all_allowed_commands with empty profile."""
        profile = SecurityProfile()

        commands = profile.get_all_allowed_commands()

        assert commands == set()

    def test_base_commands_only(self):
        """Test get_all_allowed_commands with base commands only."""
        profile = SecurityProfile()
        profile.base_commands = {"git", "ls", "cat"}

        commands = profile.get_all_allowed_commands()

        assert commands == {"git", "ls", "cat"}

    def test_multiple_command_sets(self):
        """Test get_all_allowed_commands combines all command sets."""
        profile = SecurityProfile()
        profile.base_commands = {"git", "ls"}
        profile.stack_commands = {"npm", "node"}
        profile.script_commands = {"./build.sh"}
        profile.custom_commands = {"my-tool"}

        commands = profile.get_all_allowed_commands()

        assert commands == {"git", "ls", "npm", "node", "./build.sh", "my-tool"}

    def test_command_set_union(self):
        """Test that overlapping commands are included once (set union)."""
        profile = SecurityProfile()
        profile.base_commands = {"git", "ls"}
        profile.stack_commands = {"git", "npm"}  # git is duplicated

        commands = profile.get_all_allowed_commands()

        assert "git" in commands
        assert len(commands) == 3  # git, ls, npm (git counted once)

    def test_all_command_types(self):
        """Test with all four command types populated."""
        profile = SecurityProfile(
            base_commands={"echo", "cat", "ls"},
            stack_commands={"python", "pip", "pytest"},
            script_commands={"./run.sh", "./test.sh"},
            custom_commands={"make", "gcc"}
        )

        commands = profile.get_all_allowed_commands()

        assert len(commands) == 10
        assert "echo" in commands
        assert "python" in commands
        assert "./run.sh" in commands
        assert "make" in commands

    def test_returns_new_set(self):
        """Test that get_all_allowed_commands returns a new set, not a reference."""
        profile = SecurityProfile()
        profile.base_commands = {"git"}

        commands1 = profile.get_all_allowed_commands()
        commands2 = profile.get_all_allowed_commands()

        # Modify one set
        commands1.add("ls")

        # Other set should be unaffected
        assert "ls" not in commands2

    def test_immutability_of_internal_sets(self):
        """Test that modifying returned set doesn't affect profile."""
        profile = SecurityProfile()
        profile.base_commands = {"git", "ls"}

        commands = profile.get_all_allowed_commands()
        commands.add("npm")

        # Profile should be unchanged
        assert "npm" not in profile.base_commands
        assert "npm" not in profile.stack_commands


# =============================================================================
# TO_DICT TESTS
# =============================================================================

class TestToDict:
    """Tests for SecurityProfile.to_dict"""

    def test_to_dict_empty_profile(self):
        """Test to_dict with empty profile."""
        profile = SecurityProfile()

        data = profile.to_dict()

        assert isinstance(data, dict)
        assert data["base_commands"] == []
        assert data["stack_commands"] == []
        assert data["script_commands"] == []
        assert data["custom_commands"] == []

    def test_to_dict_with_commands(self):
        """Test to_dict with command sets."""
        profile = SecurityProfile()
        profile.base_commands = {"git", "ls", "cat"}
        profile.stack_commands = {"npm", "node"}
        profile.script_commands = {"./build.sh"}
        profile.custom_commands = {"my-tool"}

        data = profile.to_dict()

        # Commands should be sorted lists
        assert data["base_commands"] == ["cat", "git", "ls"]
        assert data["stack_commands"] == ["node", "npm"]
        assert data["script_commands"] == ["./build.sh"]
        assert data["custom_commands"] == ["my-tool"]

    def test_to_dict_with_detected_stack(self):
        """Test to_dict serializes detected_stack."""
        profile = SecurityProfile()
        profile.detected_stack = TechnologyStack(
            languages=["python", "javascript"],
            frameworks=["django", "react"]
        )

        data = profile.to_dict()

        assert "detected_stack" in data
        assert data["detected_stack"]["languages"] == ["python", "javascript"]
        assert data["detected_stack"]["frameworks"] == ["django", "react"]

    def test_to_dict_with_custom_scripts(self):
        """Test to_dict serializes custom_scripts."""
        profile = SecurityProfile()
        profile.custom_scripts = CustomScripts(
            npm_scripts=["build", "test"],
            make_targets=["install"]
        )

        data = profile.to_dict()

        assert "custom_scripts" in data
        assert data["custom_scripts"]["npm_scripts"] == ["build", "test"]
        assert data["custom_scripts"]["make_targets"] == ["install"]

    def test_to_dict_with_metadata(self):
        """Test to_dict includes metadata fields."""
        profile = SecurityProfile()
        profile.project_dir = "/path/to/project"
        profile.created_at = "2024-01-01T12:00:00"
        profile.project_hash = "abc123"

        data = profile.to_dict()

        assert data["project_dir"] == "/path/to/project"
        assert data["created_at"] == "2024-01-01T12:00:00"
        assert data["project_hash"] == "abc123"

    def test_to_dict_without_inherited_from(self):
        """Test to_dict excludes inherited_from when empty."""
        profile = SecurityProfile()
        profile.inherited_from = ""

        data = profile.to_dict()

        assert "inherited_from" not in data

    def test_to_dict_with_inherited_from(self):
        """Test to_dict includes inherited_from when set."""
        profile = SecurityProfile()
        profile.inherited_from = "/path/to/parent"

        data = profile.to_dict()

        assert "inherited_from" in data
        assert data["inherited_from"] == "/path/to/parent"

    def test_to_dict_complete_profile(self):
        """Test to_dict with fully populated profile."""
        profile = SecurityProfile()
        profile.base_commands = {"git"}
        profile.stack_commands = {"npm"}
        profile.script_commands = {"./build.sh"}
        profile.custom_commands = {"make"}
        profile.detected_stack = TechnologyStack(languages=["python"])
        profile.custom_scripts = CustomScripts(npm_scripts=["test"])
        profile.project_dir = "/project"
        profile.created_at = "2024-01-01T12:00:00"
        profile.project_hash = "hash123"
        profile.inherited_from = "/parent"

        data = profile.to_dict()

        assert set(data.keys()) >= {
            "base_commands", "stack_commands", "script_commands", "custom_commands",
            "detected_stack", "custom_scripts", "project_dir", "created_at",
            "project_hash", "inherited_from"
        }

    def test_to_dict_sorts_commands(self):
        """Test that commands are sorted in output."""
        profile = SecurityProfile()
        profile.base_commands = {"zebra", "apple", "banana"}

        data = profile.to_dict()

        assert data["base_commands"] == ["apple", "banana", "zebra"]


# =============================================================================
# FROM_DICT TESTS
# =============================================================================

class TestFromDict:
    """Tests for SecurityProfile.from_dict"""

    def test_from_dict_empty(self):
        """Test from_dict with minimal dict."""
        data = {}

        profile = SecurityProfile.from_dict(data)

        assert isinstance(profile, SecurityProfile)
        assert profile.base_commands == set()
        assert profile.stack_commands == set()
        assert profile.project_dir == ""
        assert profile.created_at == ""
        assert profile.project_hash == ""

    def test_from_dict_with_commands(self):
        """Test from_dict with command sets."""
        data = {
            "base_commands": ["git", "ls", "cat"],
            "stack_commands": ["npm", "node"],
            "script_commands": ["./build.sh"],
            "custom_commands": ["my-tool"]
        }

        profile = SecurityProfile.from_dict(data)

        assert profile.base_commands == {"git", "ls", "cat"}
        assert profile.stack_commands == {"npm", "node"}
        assert profile.script_commands == {"./build.sh"}
        assert profile.custom_commands == {"my-tool"}

    def test_from_dict_with_metadata(self):
        """Test from_dict with metadata fields."""
        data = {
            "project_dir": "/path/to/project",
            "created_at": "2024-01-01T12:00:00",
            "project_hash": "abc123"
        }

        profile = SecurityProfile.from_dict(data)

        assert profile.project_dir == "/path/to/project"
        assert profile.created_at == "2024-01-01T12:00:00"
        assert profile.project_hash == "abc123"

    def test_from_dict_with_inherited_from(self):
        """Test from_dict with inherited_from field."""
        data = {
            "inherited_from": "/path/to/parent"
        }

        profile = SecurityProfile.from_dict(data)

        assert profile.inherited_from == "/path/to/parent"

    def test_from_dict_with_detected_stack(self):
        """Test from_dict with detected_stack."""
        data = {
            "detected_stack": {
                "languages": ["python", "javascript"],
                "frameworks": ["django", "react"],
                "package_managers": ["pip", "npm"]
            }
        }

        profile = SecurityProfile.from_dict(data)

        assert isinstance(profile.detected_stack, TechnologyStack)
        assert profile.detected_stack.languages == ["python", "javascript"]
        assert profile.detected_stack.frameworks == ["django", "react"]
        assert profile.detected_stack.package_managers == ["pip", "npm"]

    def test_from_dict_with_custom_scripts(self):
        """Test from_dict with custom_scripts."""
        data = {
            "custom_scripts": {
                "npm_scripts": ["build", "test"],
                "make_targets": ["install", "clean"]
            }
        }

        profile = SecurityProfile.from_dict(data)

        assert isinstance(profile.custom_scripts, CustomScripts)
        assert profile.custom_scripts.npm_scripts == ["build", "test"]
        assert profile.custom_scripts.make_targets == ["install", "clean"]

    def test_from_dict_complete(self):
        """Test from_dict with complete profile data."""
        data = {
            "base_commands": ["git"],
            "stack_commands": ["npm"],
            "script_commands": ["./build.sh"],
            "custom_commands": ["make"],
            "detected_stack": {
                "languages": ["python"],
                "frameworks": ["django"]
            },
            "custom_scripts": {
                "npm_scripts": ["test"]
            },
            "project_dir": "/project",
            "created_at": "2024-01-01T12:00:00",
            "project_hash": "hash123",
            "inherited_from": "/parent"
        }

        profile = SecurityProfile.from_dict(data)

        assert profile.base_commands == {"git"}
        assert profile.stack_commands == {"npm"}
        assert profile.script_commands == {"./build.sh"}
        assert profile.custom_commands == {"make"}
        assert profile.detected_stack.languages == ["python"]
        assert profile.custom_scripts.npm_scripts == ["test"]
        assert profile.project_dir == "/project"
        assert profile.created_at == "2024-01-01T12:00:00"
        assert profile.project_hash == "hash123"
        assert profile.inherited_from == "/parent"

    def test_from_dict_handles_missing_optional_fields(self):
        """Test from_dict handles missing detected_stack and custom_scripts."""
        data = {
            "base_commands": ["git"]
        }

        profile = SecurityProfile.from_dict(data)

        # Should have default instances
        assert isinstance(profile.detected_stack, TechnologyStack)
        assert isinstance(profile.custom_scripts, CustomScripts)


# =============================================================================
# ROUND-TRIP SERIALIZATION TESTS
# =============================================================================

class TestRoundTripSerialization:
    """Tests for to_dict/from_dict round-trip serialization"""

    def test_round_trip_empty_profile(self):
        """Test round-trip serialization of empty profile."""
        original = SecurityProfile()

        data = original.to_dict()
        restored = SecurityProfile.from_dict(data)

        assert restored.base_commands == original.base_commands
        assert restored.stack_commands == original.stack_commands
        assert restored.script_commands == original.script_commands
        assert restored.custom_commands == original.custom_commands

    def test_round_trip_full_profile(self):
        """Test round-trip serialization of full profile."""
        original = SecurityProfile()
        original.base_commands = {"git", "ls"}
        original.stack_commands = {"npm", "node"}
        original.script_commands = {"./build.sh"}
        original.custom_commands = {"make"}
        original.detected_stack = TechnologyStack(
            languages=["python", "javascript"],
            frameworks=["django", "react"],
            package_managers=["pip", "npm"],
            databases=["postgresql"],
            infrastructure=["docker"],
            cloud_providers=["aws"],
            code_quality_tools=["pytest"],
            version_managers=["pyenv"]
        )
        original.custom_scripts = CustomScripts(
            npm_scripts=["build", "test"],
            make_targets=["install"],
            poetry_scripts=["format"],
            cargo_aliases=["dev"],
            shell_scripts=["deploy.sh"]
        )
        original.project_dir = "/path/to/project"
        original.created_at = "2024-01-01T12:00:00"
        original.project_hash = "abc123def456"
        original.inherited_from = "/path/to/parent"

        data = original.to_dict()
        restored = SecurityProfile.from_dict(data)

        # Verify all fields
        assert restored.base_commands == original.base_commands
        assert restored.stack_commands == original.stack_commands
        assert restored.script_commands == original.script_commands
        assert restored.custom_commands == original.custom_commands
        assert restored.detected_stack.languages == original.detected_stack.languages
        assert restored.detected_stack.frameworks == original.detected_stack.frameworks
        assert restored.custom_scripts.npm_scripts == original.custom_scripts.npm_scripts
        assert restored.project_dir == original.project_dir
        assert restored.created_at == original.created_at
        assert restored.project_hash == original.project_hash
        assert restored.inherited_from == original.inherited_from

    def test_round_trip_preserves_all_commands(self):
        """Test that all commands are preserved through round-trip."""
        original = SecurityProfile()
        original.base_commands = {"git", "ls", "cat", "echo"}
        original.stack_commands = {"npm", "node", "python", "pip"}
        original.script_commands = {"./build.sh", "./test.sh", "./deploy.sh"}
        original.custom_commands = {"make", "gcc", "docker"}

        data = original.to_dict()
        restored = SecurityProfile.from_dict(data)

        assert restored.get_all_allowed_commands() == original.get_all_allowed_commands()

    def test_to_dict_creates_json_compatible_output(self):
        """Test that to_dict output is JSON-serializable."""
        import json

        profile = SecurityProfile()
        profile.base_commands = {"git"}
        profile.detected_stack = TechnologyStack(languages=["python"])
        profile.custom_scripts = CustomScripts(npm_scripts=["build"])

        data = profile.to_dict()

        # Should not raise an exception
        json_str = json.dumps(data)
        assert isinstance(json_str, str)

        # And should be deserializable
        parsed = json.loads(json_str)
        assert parsed["base_commands"] == ["git"]
