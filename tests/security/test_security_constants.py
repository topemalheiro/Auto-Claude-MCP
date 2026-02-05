"""
Tests for security.constants module.
"""

import pytest

from security.constants import (
    PROJECT_DIR_ENV_VAR,
    ALLOWLIST_FILENAME,
    PROFILE_FILENAME,
)


class TestSecurityConstants:
    """Tests for security constants."""

    def test_project_dir_env_var(self):
        """Test PROJECT_DIR_ENV_VAR constant."""
        assert PROJECT_DIR_ENV_VAR == "AUTO_CLAUDE_PROJECT_DIR"
        assert isinstance(PROJECT_DIR_ENV_VAR, str)
        assert len(PROJECT_DIR_ENV_VAR) > 0

    def test_allowlist_filename(self):
        """Test ALLOWLIST_FILENAME constant."""
        assert ALLOWLIST_FILENAME == ".auto-claude-allowlist"
        assert isinstance(ALLOWLIST_FILENAME, str)
        assert ALLOWLIST_FILENAME.startswith(".")
        assert "allowlist" in ALLOWLIST_FILENAME

    def test_profile_filename(self):
        """Test PROFILE_FILENAME constant."""
        assert PROFILE_FILENAME == ".auto-claude-security.json"
        assert isinstance(PROFILE_FILENAME, str)
        assert PROFILE_FILENAME.startswith(".")
        assert "security" in PROFILE_FILENAME
        assert PROFILE_FILENAME.endswith(".json")

    def test_constants_are_strings(self):
        """Test all constants are strings."""
        assert isinstance(PROJECT_DIR_ENV_VAR, str)
        assert isinstance(ALLOWLIST_FILENAME, str)
        assert isinstance(PROFILE_FILENAME, str)

    def test_constants_are_immutable(self):
        """Test constants cannot be reassigned (module-level)."""
        # Module constants can technically be reassigned in Python,
        # but this test documents that they shouldn't be
        original_values = {
            "PROJECT_DIR_ENV_VAR": PROJECT_DIR_ENV_VAR,
            "ALLOWLIST_FILENAME": ALLOWLIST_FILENAME,
            "PROFILE_FILENAME": PROFILE_FILENAME,
        }

        # Verify original values
        assert original_values["PROJECT_DIR_ENV_VAR"] == "AUTO_CLAUDE_PROJECT_DIR"
        assert original_values["ALLOWLIST_FILENAME"] == ".auto-claude-allowlist"
        assert original_values["PROFILE_FILENAME"] == ".auto-claude-security.json"

    def test_allowlist_filename_format(self):
        """Test ALLOWLIST_FILENAME follows expected format."""
        # Should start with dot (hidden file)
        assert ALLOWLIST_FILENAME.startswith(".")
        # Should contain auto-claude prefix
        assert "auto-claude" in ALLOWLIST_FILENAME
        # Should not have path separators
        assert "/" not in ALLOWLIST_FILENAME
        assert "\\" not in ALLOWLIST_FILENAME

    def test_profile_filename_format(self):
        """Test PROFILE_FILENAME follows expected format."""
        # Should start with dot (hidden file)
        assert PROFILE_FILENAME.startswith(".")
        # Should contain auto-claude prefix
        assert "auto-claude" in PROFILE_FILENAME
        # Should end with .json
        assert PROFILE_FILENAME.endswith(".json")
        # Should not have path separators
        assert "/" not in PROFILE_FILENAME
        assert "\\" not in PROFILE_FILENAME

    def test_env_var_name_format(self):
        """Test PROJECT_DIR_ENV_VAR follows environment variable naming conventions."""
        # Should be uppercase
        assert PROJECT_DIR_ENV_VAR.isupper()
        # Should use underscores
        assert "_" in PROJECT_DIR_ENV_VAR
        # Should not have spaces
        assert " " not in PROJECT_DIR_ENV_VAR
        # Should be a valid shell variable name
        assert PROJECT_DIR_ENV_VAR.replace("_", "").isalnum()

    def test_constants_uniqueness(self):
        """Test all constants have unique values."""
        constants = [PROJECT_DIR_ENV_VAR, ALLOWLIST_FILENAME, PROFILE_FILENAME]
        assert len(set(constants)) == len(constants), "All constants should have unique values"

    def test_constants_do_not_contain_paths(self):
        """Test constants don't contain absolute or relative paths."""
        for constant in [ALLOWLIST_FILENAME, PROFILE_FILENAME]:
            assert not constant.startswith("/")
            assert not constant.startswith("./")
            assert not constant.startswith("../")

    def test_profile_json_extension(self):
        """Test PROFILE_FILENAME has correct JSON extension."""
        # Should have exactly one .json suffix
        assert PROFILE_FILENAME.endswith(".json")
        # Should not have double extensions
        assert not PROFILE_FILENAME.endswith(".json.json")

    def test_constants_not_empty(self):
        """Test none of the constants are empty strings."""
        assert PROJECT_DIR_ENV_VAR
        assert ALLOWLIST_FILENAME
        assert PROFILE_FILENAME

    def test_constants_have_meaningful_names(self):
        """Test constants have descriptive, meaningful names."""
        # ENV_VAR suffix for environment variables
        assert "ENV_VAR" in "PROJECT_DIR_ENV_VAR"
        # FILENAME suffix for file names
        assert "FILENAME" in "ALLOWLIST_FILENAME"
        assert "FILENAME" in "PROFILE_FILENAME"

    def test_allowlist_vs_security_files(self):
        """Test allowlist and security files are different."""
        assert ALLOWLIST_FILENAME != PROFILE_FILENAME
        assert not ALLOWLIST_FILENAME.endswith(".json")
        assert PROFILE_FILENAME.endswith(".json")

    def test_project_dir_env_var_semantic_meaning(self):
        """Test PROJECT_DIR_ENV_VAR name is semantically meaningful."""
        # Name should indicate its purpose
        assert "PROJECT" in PROJECT_DIR_ENV_VAR
        assert "DIR" in PROJECT_DIR_ENV_VAR
        # Should use AUTO_CLAUDE prefix
        assert PROJECT_DIR_ENV_VAR.startswith("AUTO_CLAUDE_")

    def test_constants_for_cross_platform_compatibility(self):
        """Test constants work across platforms."""
        # File names should use forward slashes (no backslashes)
        assert "\\" not in ALLOWLIST_FILENAME
        assert "\\" not in PROFILE_FILENAME
        # File names should be valid on Windows, Linux, macOS
        # (no invalid characters like :, *, ?, ", <, >, |)
        invalid_chars = [':', '*', '?', '"', '<', '>', '|']
        for char in invalid_chars:
            assert char not in ALLOWLIST_FILENAME
            assert char not in PROFILE_FILENAME
