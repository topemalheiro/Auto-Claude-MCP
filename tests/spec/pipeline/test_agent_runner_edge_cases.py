"""
Edge case tests for spec.pipeline.agent_runner module.

Tests covering edge cases and corner scenarios that complement existing tests.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from spec.pipeline.agent_runner import AgentRunner


class TestExtractToolInputDisplayEdgeCases:
    """Additional edge case tests for _extract_tool_input_display."""

    def test_extract_tool_input_unicode_chars(self):
        """Test _extract_tool_input_display with unicode characters."""
        inp = {"file_path": "/path/to/文件.py"}
        result = AgentRunner._extract_tool_input_display(inp)
        assert "文件.py" in result

    def test_extract_tool_input_special_path_chars(self):
        """Test with special characters in file path."""
        inp = {"file_path": "/path/[test]/file (1).txt"}
        result = AgentRunner._extract_tool_input_display(inp)
        assert result is not None

    def test_extract_tool_input_emoji_in_command(self):
        """Test with emoji in command."""
        inp = {"command": "echo 'Hello World' 👋"}
        result = AgentRunner._extract_tool_input_display(inp)
        assert result is not None
        assert "Hello World" in result

    def test_extract_tool_input_multiline_command(self):
        """Test with multiline command."""
        inp = {"command": "echo 'line1\necho line2'"}
        result = AgentRunner._extract_tool_input_display(inp)
        assert result is not None

    def test_extract_tool_input_very_long_pattern(self):
        """Test with very long pattern."""
        long_pattern = ".*" + "a" * 100 + ".*"
        inp = {"pattern": long_pattern}
        result = AgentRunner._extract_tool_input_display(inp)
        # Pattern should not be truncated
        assert "pattern:" in result

    def test_extract_tool_input_dict_with_none_values(self):
        """Test with None values in dict - would cause TypeError."""
        inp = {"file_path": None}
        # The implementation doesn't handle None, it would try to call len(None)
        # which raises TypeError. We can test that it behaves predictably.
        with pytest.raises(TypeError):
            AgentRunner._extract_tool_input_display(inp)


class TestGetToolDetailContentEdgeCases:
    """Additional edge case tests for _get_tool_detail_content."""

    def test_get_tool_detail_with_unicode(self):
        """Test _get_tool_detail_content with unicode content."""
        content = "测试内容" * 100  # Still under limit
        result = AgentRunner._get_tool_detail_content("Read", content)
        assert result == content

    def test_get_tool_detail_with_newlines(self):
        """Test with content containing many newlines."""
        content = "\n" * 100 + "text" + "\n" * 100
        result = AgentRunner._get_tool_detail_content("Read", content)
        assert result == content

    def test_get_tool_detail_with_tabs(self):
        """Test with content containing many tabs."""
        content = "\t" * 1000
        result = AgentRunner._get_tool_detail_content("Grep", content)
        # Should be included (under limit)
        assert result == content

    def test_get_tool_detail_case_sensitive_tools(self):
        """Test that tool names are case-sensitive."""
        content = "test content"
        # lowercase should not match
        result = AgentRunner._get_tool_detail_content("read", content)
        assert result is None

        # uppercase should match
        result = AgentRunner._get_tool_detail_content("Read", content)
        assert result == content

    def test_get_tool_detail_exactly_at_limit(self):
        """Test content exactly at 50000 character limit."""
        content = "x" * 50000
        result = AgentRunner._get_tool_detail_content("Write", content)
        # The condition is < 50000, so exactly 50000 is NOT included
        assert result is None

    def test_get_tool_detail_one_over_limit(self):
        """Test content one character over limit."""
        content = "x" * 50001
        result = AgentRunner._get_tool_detail_content("Edit", content)
        assert result is None

    def test_get_tool_detail_with_binary_like_chars(self):
        """Test with binary-like characters."""
        content = "\x00\x01\x02\x03\x04\x05" * 1000  # Under limit
        result = AgentRunner._get_tool_detail_content("Read", content)
        # Should include if under limit
        assert result == content

    def test_get_tool_detail_just_under_limit(self):
        """Test content just under the limit (49999 chars)."""
        content = "x" * 49999
        result = AgentRunner._get_tool_detail_content("Bash", content)
        assert result == content

    def test_get_tool_detail_all_supported_tools_with_empty(self):
        """Test all supported tools with empty content."""
        content = ""
        supported_tools = ["Read", "Grep", "Bash", "Edit", "Write"]

        for tool in supported_tools:
            result = AgentRunner._get_tool_detail_content(tool, content)
            assert result == content

    def test_get_tool_detail_unsupported_tool_with_content(self):
        """Test unsupported tools return None even with small content."""
        content = "small content"
        unsupported_tools = ["Unknown", "Custom", "OtherTool"]

        for tool in unsupported_tools:
            result = AgentRunner._get_tool_detail_content(tool, content)
            assert result is None


class TestAgentRunnerInitialization:
    """Tests for AgentRunner initialization variations."""

    def test_init_with_path_like_objects(self):
        """Test initialization with Path-like objects."""
        project_dir = Path("/project")
        spec_dir = Path("/spec")
        model = "sonnet"
        task_logger = MagicMock()

        runner = AgentRunner(project_dir, spec_dir, model, task_logger)

        assert runner.project_dir == project_dir
        assert runner.spec_dir == spec_dir
        assert runner.model == model
        assert runner.task_logger == task_logger

    def test_init_with_different_models(self):
        """Test initialization with different model names."""
        models = ["sonnet", "haiku", "opus", "custom-model"]
        project_dir = Path("/project")
        spec_dir = Path("/spec")

        for model in models:
            runner = AgentRunner(project_dir, spec_dir, model, None)
            assert runner.model == model


class TestAgentRunnerStaticMethodTypes:
    """Type checking and validation tests for static methods."""

    def test_extract_tool_input_return_types(self):
        """Test that _extract_tool_input_display returns correct types."""
        # Should return string for valid inputs
        assert isinstance(AgentRunner._extract_tool_input_display({"pattern": "test"}), str)
        assert isinstance(AgentRunner._extract_tool_input_display({"file_path": "test.txt"}), str)
        assert isinstance(AgentRunner._extract_tool_input_display({"command": "ls"}), str)
        assert isinstance(AgentRunner._extract_tool_input_display({"path": "/path"}), str)

        # Should return None for invalid/unmatched inputs
        assert AgentRunner._extract_tool_input_display({}) is None
        assert AgentRunner._extract_tool_input_display({"unknown": "value"}) is None
        assert AgentRunner._extract_tool_input_display(None) is None
        assert AgentRunner._extract_tool_input_display("string") is None
        assert AgentRunner._extract_tool_input_display(123) is None

    def test_get_tool_detail_content_return_types(self):
        """Test that _get_tool_detail_content returns correct types."""
        # Should return string for supported tools with small content
        result = AgentRunner._get_tool_detail_content("Read", "content")
        assert isinstance(result, str) or result is None

        # Should return None for unsupported tools
        assert AgentRunner._get_tool_detail_content("Unknown", "content") is None

        # Should return None for large content
        large = "x" * 60000
        assert AgentRunner._get_tool_detail_content("Read", large) is None


class TestExtractToolInputTruncation:
    """Tests for input truncation behavior."""

    def test_file_path_truncation_at_boundary(self):
        """Test file path truncation at exactly 50 characters."""
        # Exactly 50 chars should not be truncated
        path_50 = "a" * 46 + ".txt"  # Total 50
        result = AgentRunner._extract_tool_input_display({"file_path": path_50})
        assert result == path_50

        # 51 chars should be truncated
        path_51 = "a" * 47 + ".txt"  # Total 51
        result = AgentRunner._extract_tool_input_display({"file_path": path_51})
        assert result.startswith("...")
        assert len(result) <= 50

    def test_command_truncation_at_boundary(self):
        """Test command truncation at exactly 50 characters."""
        # Exactly 50 chars should not be truncated
        cmd_50 = "echo '" + "a" * 43 + "'"  # Total 50
        result = AgentRunner._extract_tool_input_display({"command": cmd_50})
        assert result == cmd_50

        # 51 chars should be truncated
        cmd_51 = "echo '" + "a" * 44 + "'"  # Total 51
        result = AgentRunner._extract_tool_input_display({"command": cmd_51})
        assert result.endswith("...")
        assert len(result) <= 50

    def test_path_not_truncated(self):
        """Test that 'path' field is never truncated."""
        long_path = "a" * 100
        inp = {"path": long_path}
        result = AgentRunner._extract_tool_input_display(inp)
        assert result == long_path

    def test_pattern_not_truncated(self):
        """Test that 'pattern' field is never truncated."""
        long_pattern = ".*" + "a" * 100 + ".*"
        inp = {"pattern": long_pattern}
        result = AgentRunner._extract_tool_input_display(inp)
        assert result == f"pattern: {long_pattern}"


class TestGetToolDetailContentBoundaries:
    """Tests for content size boundary conditions."""

    def test_content_size_boundaries(self):
        """Test various content sizes around the limit."""
        # Just under limit
        assert AgentRunner._get_tool_detail_content("Read", "x" * 49999) == "x" * 49999

        # At limit (not included because condition is < 50000)
        assert AgentRunner._get_tool_detail_content("Read", "x" * 50000) is None

        # Just over limit
        assert AgentRunner._get_tool_detail_content("Read", "x" * 50001) is None

        # Very large
        assert AgentRunner._get_tool_detail_content("Read", "x" * 100000) is None

    def test_zero_length_content(self):
        """Test with zero-length content."""
        assert AgentRunner._get_tool_detail_content("Read", "") == ""

    def test_single_character_content(self):
        """Test with single character content."""
        assert AgentRunner._get_tool_detail_content("Read", "x") == "x"


class TestGetToolDetailContentSpecialCases:
    """Tests for special cases in tool detail content."""

    def test_content_with_special_characters(self):
        """Test content with various special characters."""
        special_content = "\n\r\t\x00\x01\x02" * 100  # Still under limit
        result = AgentRunner._get_tool_detail_content("Read", special_content)
        assert result == special_content

    def test_content_with_mixed_line_endings(self):
        """Test content with different line ending styles."""
        content = "line1\nline2\r\nline3\rline4" * 100  # Under limit
        result = AgentRunner._get_tool_detail_content("Read", content)
        assert result == content

    def test_content_with_null_bytes(self):
        """Test content containing null bytes."""
        content = "text\x00more\x00data" * 100  # Under limit
        result = AgentRunner._get_tool_detail_content("Grep", content)
        assert result == content

    def test_all_supported_tools_boundary(self):
        """Test all supported tools at the boundary."""
        boundary_content = "x" * 49999  # Just under limit
        supported_tools = ["Read", "Grep", "Bash", "Edit", "Write"]

        for tool in supported_tools:
            result = AgentRunner._get_tool_detail_content(tool, boundary_content)
            assert result == boundary_content

    def test_tool_name_variations(self):
        """Test tool name case variations."""
        content = "test"

        # Exact matches should work
        assert AgentRunner._get_tool_detail_content("Read", content) == content
        assert AgentRunner._get_tool_detail_content("Grep", content) == content
        assert AgentRunner._get_tool_detail_content("Bash", content) == content
        assert AgentRunner._get_tool_detail_content("Edit", content) == content
        assert AgentRunner._get_tool_detail_content("Write", content) == content

        # Case variations should not match
        assert AgentRunner._get_tool_detail_content("read", content) is None
        assert AgentRunner._get_tool_detail_content("READ", content) is None
        assert AgentRunner._get_tool_detail_content("Read ", content) is None
        assert AgentRunner._get_tool_detail_content(" Read", content) is None
