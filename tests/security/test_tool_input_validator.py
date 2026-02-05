"""Tests for tool_input_validator"""

import pytest
from unittest.mock import MagicMock

from security.tool_input_validator import (
    TOOL_REQUIRED_KEYS,
    get_safe_tool_input,
    validate_tool_input,
)


class TestValidateToolInput:
    """Tests for validate_tool_input function"""

    def test_none_input_returns_error(self):
        """Test that None tool_input returns error"""
        result = validate_tool_input("Bash", None)
        assert result == (False, "Bash: tool_input is None (malformed tool call)")

    def test_non_dict_input_returns_error(self):
        """Test that non-dict tool_input returns error"""
        result = validate_tool_input("Bash", "invalid string")
        assert result == (False, "Bash: tool_input must be dict, got str")

    def test_list_input_returns_error(self):
        """Test that list input returns error"""
        result = validate_tool_input("Glob", ["pattern"])
        assert result == (False, "Glob: tool_input must be dict, got list")

    def test_integer_input_returns_error(self):
        """Test that integer input returns error"""
        result = validate_tool_input("Read", 123)
        assert result == (False, "Read: tool_input must be dict, got int")

    def test_missing_required_key_for_bash(self):
        """Test missing 'command' key for Bash tool"""
        result = validate_tool_input("Bash", {"other_key": "value"})
        assert result == (False, "Bash: missing required keys: command")

    def test_missing_required_key_for_read(self):
        """Test missing 'file_path' key for Read tool"""
        result = validate_tool_input("Read", {"other_key": "value"})
        assert result == (False, "Read: missing required keys: file_path")

    def test_missing_required_key_for_write(self):
        """Test missing required keys for Write tool"""
        result = validate_tool_input("Write", {"file_path": "/tmp/test.txt"})
        assert result == (False, "Write: missing required keys: content")

    def test_missing_all_required_keys_for_write(self):
        """Test missing all required keys for Write tool"""
        result = validate_tool_input("Write", {})
        assert result == (False, "Write: missing required keys: file_path, content")

    def test_missing_required_key_for_edit(self):
        """Test missing required keys for Edit tool"""
        result = validate_tool_input("Edit", {"file_path": "/tmp/test.txt", "old_string": "old"})
        assert result == (False, "Edit: missing required keys: new_string")

    def test_missing_all_required_keys_for_edit(self):
        """Test missing all required keys for Edit tool"""
        result = validate_tool_input("Edit", {})
        assert result == (False, "Edit: missing required keys: file_path, old_string, new_string")

    def test_missing_required_key_for_glob(self):
        """Test missing 'pattern' key for Glob tool"""
        result = validate_tool_input("Glob", {})
        assert result == (False, "Glob: missing required keys: pattern")

    def test_missing_required_key_for_grep(self):
        """Test missing 'pattern' key for Grep tool"""
        result = validate_tool_input("Grep", {})
        assert result == (False, "Grep: missing required keys: pattern")

    def test_missing_required_key_for_webfetch(self):
        """Test missing 'url' key for WebFetch tool"""
        result = validate_tool_input("WebFetch", {})
        assert result == (False, "WebFetch: missing required keys: url")

    def test_missing_required_key_for_websearch(self):
        """Test missing 'query' key for WebSearch tool"""
        result = validate_tool_input("WebSearch", {})
        assert result == (False, "WebSearch: missing required keys: query")

    def test_unknown_tool_no_required_keys(self):
        """Test that unknown tools have no required keys"""
        result = validate_tool_input("UnknownTool", {})
        assert result == (True, None)

    def test_unknown_tool_with_valid_input(self):
        """Test that unknown tools pass with any dict"""
        result = validate_tool_input("UnknownTool", {"any_key": "value"})
        assert result == (True, None)

    def test_bash_non_string_command(self):
        """Test Bash with non-string command"""
        result = validate_tool_input("Bash", {"command": 123})
        assert result == (False, "Bash: 'command' must be string, got int")

    def test_bash_list_command(self):
        """Test Bash with list as command"""
        result = validate_tool_input("Bash", {"command": ["ls"]})
        assert result == (False, "Bash: 'command' must be string, got list")

    def test_bash_dict_command(self):
        """Test Bash with dict as command"""
        result = validate_tool_input("Bash", {"command": {"cmd": "ls"}})
        assert result == (False, "Bash: 'command' must be string, got dict")

    def test_bash_empty_command(self):
        """Test Bash with empty string command"""
        result = validate_tool_input("Bash", {"command": ""})
        assert result == (False, "Bash: 'command' is empty")

    def test_bash_whitespace_only_command(self):
        """Test Bash with whitespace-only command"""
        result = validate_tool_input("Bash", {"command": "   "})
        assert result == (False, "Bash: 'command' is empty")

    def test_bash_valid_command(self):
        """Test Bash with valid command"""
        result = validate_tool_input("Bash", {"command": "ls -la"})
        assert result == (True, None)

    def test_read_valid_input(self):
        """Test Read with valid input"""
        result = validate_tool_input("Read", {"file_path": "/tmp/test.txt"})
        assert result == (True, None)

    def test_write_valid_input(self):
        """Test Write with valid input"""
        result = validate_tool_input("Write", {"file_path": "/tmp/test.txt", "content": "test"})
        assert result == (True, None)

    def test_edit_valid_input(self):
        """Test Edit with valid input"""
        result = validate_tool_input(
            "Edit",
            {"file_path": "/tmp/test.txt", "old_string": "old", "new_string": "new"},
        )
        assert result == (True, None)

    def test_glob_valid_input(self):
        """Test Glob with valid input"""
        result = validate_tool_input("Glob", {"pattern": "*.py"})
        assert result == (True, None)

    def test_grep_valid_input(self):
        """Test Grep with valid input"""
        result = validate_tool_input("Grep", {"pattern": "test"})
        assert result == (True, None)

    def test_webfetch_valid_input(self):
        """Test WebFetch with valid input"""
        result = validate_tool_input("WebFetch", {"url": "https://example.com"})
        assert result == (True, None)

    def test_websearch_valid_input(self):
        """Test WebSearch with valid input"""
        result = validate_tool_input("WebSearch", {"query": "test search"})
        assert result == (True, None)

    def test_all_tools_have_required_keys_defined(self):
        """Test that all expected tools are in TOOL_REQUIRED_KEYS"""
        expected_tools = {
            "Bash",
            "Read",
            "Write",
            "Edit",
            "Glob",
            "Grep",
            "WebFetch",
            "WebSearch",
        }
        assert set(TOOL_REQUIRED_KEYS.keys()) == expected_tools


class TestGetSafeToolInput:
    """Tests for get_safe_tool_input function"""

    def test_block_without_input_attribute(self):
        """Test block without input attribute returns default"""
        block = MagicMock(spec=[])  # No input attribute
        result = get_safe_tool_input(block)
        assert result == {}

    def test_block_with_none_input(self):
        """Test block with None input returns default"""
        block = MagicMock()
        block.input = None
        result = get_safe_tool_input(block)
        assert result == {}

    def test_block_with_non_dict_input(self):
        """Test block with non-dict input returns default"""
        block = MagicMock()
        block.input = "invalid"
        result = get_safe_tool_input(block)
        assert result == {}

    def test_block_with_list_input(self):
        """Test block with list input returns default"""
        block = MagicMock()
        block.input = ["item1", "item2"]
        result = get_safe_tool_input(block)
        assert result == {}

    def test_block_with_integer_input(self):
        """Test block with integer input returns default"""
        block = MagicMock()
        block.input = 123
        result = get_safe_tool_input(block)
        assert result == {}

    def test_block_with_valid_dict_input(self):
        """Test block with valid dict input"""
        block = MagicMock()
        block.input = {"command": "ls"}
        result = get_safe_tool_input(block)
        assert result == {"command": "ls"}

    def test_block_with_empty_dict_input(self):
        """Test block with empty dict input"""
        block = MagicMock()
        block.input = {}
        result = get_safe_tool_input(block)
        assert result == {}

    def test_custom_default(self):
        """Test with custom default value"""
        block = MagicMock(spec=[])
        custom_default = {"custom": "value"}
        result = get_safe_tool_input(block, custom_default)
        assert result == custom_default

    def test_custom_default_with_none_input(self):
        """Test custom default with None input"""
        block = MagicMock()
        block.input = None
        custom_default = {"custom": "value"}
        result = get_safe_tool_input(block, custom_default)
        assert result == custom_default

    def test_custom_default_with_invalid_input(self):
        """Test custom default with invalid input"""
        block = MagicMock()
        block.input = "invalid"
        custom_default = {"custom": "value"}
        result = get_safe_tool_input(block, custom_default)
        assert result == custom_default

    def test_valid_input_overrides_custom_default(self):
        """Test that valid input is used instead of custom default"""
        block = MagicMock()
        block.input = {"command": "ls"}
        custom_default = {"custom": "value"}
        result = get_safe_tool_input(block, custom_default)
        assert result == {"command": "ls"}
        assert result != custom_default

    def test_default_is_not_mutated(self):
        """Test that the default dict is not mutated"""
        block = MagicMock(spec=[])
        default = {}
        original_id = id(default)
        result = get_safe_tool_input(block, default)
        assert id(result) == original_id

    def test_none_default_defaults_to_empty_dict(self):
        """Test that None default results in empty dict"""
        block = MagicMock(spec=[])
        result = get_safe_tool_input(block, None)
        assert result == {}
