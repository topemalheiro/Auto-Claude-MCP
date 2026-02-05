"""Tests for debug module"""

import asyncio
import os
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.debug import (
    Colors,
    _format_value,
    _get_debug_enabled,
    _get_debug_level,
    _get_log_file,
    debug,
    debug_async_timer,
    debug_detailed,
    debug_env_status,
    debug_error,
    debug_info,
    debug_section,
    debug_success,
    debug_timer,
    debug_verbose,
    debug_warning,
    get_debug_level,
    is_debug_enabled,
)


class TestDebugEnvironment:
    """Tests for debug environment variable handling."""

    def test_is_debug_enabled_true_values(self, monkeypatch):
        """Test is_debug_enabled with various true values."""
        for value in ["true", "True", "TRUE", "1", "yes", "Yes", "on", "On"]:
            monkeypatch.setenv("DEBUG", value)
            assert is_debug_enabled() is True

    def test_is_debug_enabled_false_values(self, monkeypatch):
        """Test is_debug_enabled with various false values."""
        for value in ["false", "False", "0", "no", "off", "", "random"]:
            monkeypatch.setenv("DEBUG", value)
            assert is_debug_enabled() is False

    def test_is_debug_enabled_no_env_var(self, monkeypatch):
        """Test is_debug_enabled when DEBUG is not set."""
        monkeypatch.delenv("DEBUG", raising=False)
        assert is_debug_enabled() is False

    def test_get_debug_level_valid_values(self, monkeypatch):
        """Test get_debug_level with valid numeric values."""
        for level in [1, 2, 3]:
            monkeypatch.setenv("DEBUG_LEVEL", str(level))
            assert get_debug_level() == level

    def test_get_debug_level_clamping(self, monkeypatch):
        """Test get_debug_level clamps values to 1-3 range."""
        monkeypatch.setenv("DEBUG_LEVEL", "0")
        assert get_debug_level() == 1

        monkeypatch.setenv("DEBUG_LEVEL", "-1")
        assert get_debug_level() == 1

        monkeypatch.setenv("DEBUG_LEVEL", "10")
        assert get_debug_level() == 3

    def test_get_debug_level_invalid_value(self, monkeypatch):
        """Test get_debug_level defaults to 1 with invalid value."""
        monkeypatch.setenv("DEBUG_LEVEL", "invalid")
        assert get_debug_level() == 1

    def test_get_debug_level_no_env_var(self, monkeypatch):
        """Test get_debug_level defaults to 1 when not set."""
        monkeypatch.delenv("DEBUG_LEVEL", raising=False)
        assert get_debug_level() == 1

    def test_get_log_file_with_path(self, monkeypatch, tmp_path):
        """Test _get_log_file returns Path when set."""
        log_file = tmp_path / "debug.log"
        monkeypatch.setenv("DEBUG_LOG_FILE", str(log_file))
        assert _get_log_file() == log_file

    def test_get_log_file_not_set(self, monkeypatch):
        """Test _get_log_file returns None when not set."""
        monkeypatch.delenv("DEBUG_LOG_FILE", raising=False)
        assert _get_log_file() is None


class TestFormatValue:
    """Tests for _format_value utility function."""

    def test_format_value_none(self):
        """Test formatting None value."""
        assert _format_value(None) == "None"

    def test_format_value_dict(self):
        """Test formatting dictionary."""
        result = _format_value({"key": "value", "number": 42})
        assert '"key": "value"' in result
        assert '"number": 42' in result

    def test_format_value_list(self):
        """Test formatting list."""
        result = _format_value([1, 2, 3])
        assert "[\n  1,\n  2,\n  3\n]" == result

    def test_format_value_long_dict_truncation(self):
        """Test that long values are truncated."""
        long_dict = {f"key{i}": f"value{i}" * 100 for i in range(10)}
        result = _format_value(long_dict, max_length=100)
        assert result.endswith("...")

    def test_format_value_long_string_truncation(self):
        """Test that long strings are truncated."""
        long_string = "x" * 300
        result = _format_value(long_string, max_length=100)
        assert result.endswith("...")
        assert len(result) == 103  # 100 + "..."

    def test_format_value_non_serializable_object(self):
        """Test formatting objects that can't be JSON serialized."""
        class CustomObject:
            def __str__(self):
                return "CustomObject()"

        obj = CustomObject()
        result = _format_value(obj)
        assert "CustomObject()" in result

    def test_format_value_simple_types(self):
        """Test formatting simple types."""
        assert _format_value(42) == "42"
        assert _format_value(3.14) == "3.14"
        assert _format_value("hello") == "hello"
        assert _format_value(True) == "True"


class TestDebugLogging:
    """Tests for debug logging functions."""

    def test_debug_not_enabled_no_output(self, monkeypatch, capsys):
        """Test debug produces no output when disabled."""
        monkeypatch.setenv("DEBUG", "false")
        debug("test_module", "Test message")

        captured = capsys.readouterr()
        assert captured.err == ""

    def test_debug_enabled_basic_output(self, monkeypatch, capsys):
        """Test debug produces output when enabled."""
        monkeypatch.setenv("DEBUG", "true")
        debug("test_module", "Test message")

        captured = capsys.readouterr()
        assert "[DEBUG]" in captured.err
        assert "[test_module]" in captured.err
        assert "Test message" in captured.err

    def test_debug_with_level_filtering(self, monkeypatch, capsys):
        """Test debug level filtering."""
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("DEBUG_LEVEL", "1")

        # Level 1 should print
        debug("module", "message", level=1)
        captured = capsys.readouterr()
        assert "message" in captured.err

        # Level 2 should not print at DEBUG_LEVEL=1
        debug("module", "detailed", level=2)
        captured = capsys.readouterr()
        assert "detailed" not in captured.err

    def test_debug_with_kwargs(self, monkeypatch, capsys):
        """Test debug with keyword arguments."""
        monkeypatch.setenv("DEBUG", "true")
        debug("test_module", "Test message", task_id="123", status="active")

        captured = capsys.readouterr()
        assert "task_id" in captured.err
        assert "123" in captured.err
        assert "status" in captured.err
        assert "active" in captured.err

    def test_debug_with_multiline_value(self, monkeypatch, capsys):
        """Test debug with multi-line dictionary value."""
        monkeypatch.setenv("DEBUG", "true")
        debug("test_module", "Complex data", data={"key1": "value1", "key2": "value2"})

        captured = capsys.readouterr()
        # Multi-line values format with "data" on one line, then indented content
        assert "data" in captured.err
        assert "key1" in captured.err
        assert "value1" in captured.err
        assert "key2" in captured.err
        assert "value2" in captured.err

    def test_debug_detailed_convenience(self, monkeypatch, capsys):
        """Test debug_detailed convenience function."""
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("DEBUG_LEVEL", "2")

        debug_detailed("agent", "Processing complete", items_processed=100)

        captured = capsys.readouterr()
        assert "[DEBUG]" in captured.err
        assert "Processing complete" in captured.err
        assert "items_processed" in captured.err

    def test_debug_verbose_convenience(self, monkeypatch, capsys):
        """Test debug_verbose convenience function."""
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("DEBUG_LEVEL", "3")

        debug_verbose("client", "Full payload", payload={"large": "data"})

        captured = capsys.readouterr()
        assert "[DEBUG]" in captured.err
        assert "Full payload" in captured.err

    def test_debug_success(self, monkeypatch, capsys):
        """Test debug_success output."""
        monkeypatch.setenv("DEBUG", "true")
        debug_success("runner", "Task completed successfully")

        captured = capsys.readouterr()
        assert "[OK]" in captured.err
        assert "Task completed successfully" in captured.err

    def test_debug_info(self, monkeypatch, capsys):
        """Test debug_info output."""
        monkeypatch.setenv("DEBUG", "true")
        debug_info("config", "Loading configuration")

        captured = capsys.readouterr()
        assert "[INFO]" in captured.err
        assert "Loading configuration" in captured.err

    def test_debug_error(self, monkeypatch, capsys):
        """Test debug_error output."""
        monkeypatch.setenv("DEBUG", "true")
        debug_error("agent", "Failed to process", error_code=500)

        captured = capsys.readouterr()
        assert "[ERROR]" in captured.err
        assert "Failed to process" in captured.err

    def test_debug_warning(self, monkeypatch, capsys):
        """Test debug_warning output."""
        monkeypatch.setenv("DEBUG", "true")
        debug_warning("config", "Deprecated setting used")

        captured = capsys.readouterr()
        assert "[WARN]" in captured.err
        assert "Deprecated setting used" in captured.err

    def test_debug_section(self, monkeypatch, capsys):
        """Test debug_section formatting."""
        monkeypatch.setenv("DEBUG", "true")
        debug_section("test_module", "Section Title")

        captured = capsys.readouterr()
        assert "Section Title" in captured.err
        assert "test_module" in captured.err
        assert "─" in captured.err  # Separator characters


class TestDebugDecorators:
    """Tests for debug decorator functions."""

    def test_debug_timer_disabled(self, monkeypatch, capsys):
        """Test debug_timer doesn't time when debug disabled."""
        monkeypatch.setenv("DEBUG", "false")

        @debug_timer("test_module")
        def test_func():
            return 42

        result = test_func()
        assert result == 42

        captured = capsys.readouterr()
        assert "Starting" not in captured.err

    def test_debug_timer_success(self, monkeypatch, capsys):
        """Test debug_timer times successful execution."""
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("DEBUG_LEVEL", "2")

        @debug_timer("test_module")
        def test_func():
            return 42

        result = test_func()
        assert result == 42

        captured = capsys.readouterr()
        assert "Starting test_func()" in captured.err
        assert "Completed test_func()" in captured.err
        assert "elapsed_ms" in captured.err

    def test_debug_timer_exception(self, monkeypatch, capsys):
        """Test debug_timer logs exceptions."""
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("DEBUG_LEVEL", "2")

        @debug_timer("test_module")
        def failing_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            failing_func()

        captured = capsys.readouterr()
        assert "Starting failing_func()" in captured.err
        assert "Failed failing_func()" in captured.err
        assert "Test error" in captured.err

    def test_debug_timer_preserves_function_name(self, monkeypatch):
        """Test debug_timer preserves function metadata."""
        monkeypatch.setenv("DEBUG", "false")

        @debug_timer("test_module")
        def my_function():
            pass

        assert my_function.__name__ == "my_function"

    @pytest.mark.asyncio
    async def test_debug_async_timer_disabled(self, monkeypatch, capsys):
        """Test debug_async_timer doesn't time when debug disabled."""
        monkeypatch.setenv("DEBUG", "false")

        @debug_async_timer("test_module")
        async def test_func():
            return 42

        result = await test_func()
        assert result == 42

        captured = capsys.readouterr()
        assert "Starting" not in captured.err

    @pytest.mark.asyncio
    async def test_debug_async_timer_success(self, monkeypatch, capsys):
        """Test debug_async_timer times successful async execution."""
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("DEBUG_LEVEL", "2")

        @debug_async_timer("test_module")
        async def test_func():
            return 42

        result = await test_func()
        assert result == 42

        captured = capsys.readouterr()
        assert "Starting test_func()" in captured.err
        assert "Completed test_func()" in captured.err
        assert "elapsed_ms" in captured.err

    @pytest.mark.asyncio
    async def test_debug_async_timer_exception(self, monkeypatch, capsys):
        """Test debug_async_timer logs async exceptions."""
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("DEBUG_LEVEL", "2")

        @debug_async_timer("test_module")
        async def failing_func():
            raise ValueError("Async error")

        with pytest.raises(ValueError, match="Async error"):
            await failing_func()

        captured = capsys.readouterr()
        assert "Starting failing_func()" in captured.err
        assert "Failed failing_func()" in captured.err
        assert "Async error" in captured.err

    def test_debug_async_timer_preserves_function_name(self, monkeypatch):
        """Test debug_async_timer preserves function metadata."""
        monkeypatch.setenv("DEBUG", "false")

        @debug_async_timer("test_module")
        async def my_async_function():
            pass

        assert my_async_function.__name__ == "my_async_function"


class TestDebugFileLogging:
    """Tests for file logging functionality."""

    def test_write_log_to_file(self, monkeypatch, tmp_path):
        """Test that logs are written to file when configured."""
        log_file = tmp_path / "test_debug.log"
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("DEBUG_LOG_FILE", str(log_file))

        debug("test_module", "Test message to file")

        # Give time for file write
        assert log_file.exists()
        content = log_file.read_text(encoding="utf-8")
        assert "Test message to file" in content
        # ANSI codes should be stripped
        assert "\033" not in content

    def test_write_log_creates_directories(self, monkeypatch, tmp_path):
        """Test that log file directories are created."""
        log_file = tmp_path / "nested" / "dir" / "debug.log"
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("DEBUG_LOG_FILE", str(log_file))

        debug("test_module", "Test")

        assert log_file.exists()
        assert log_file.parent.is_dir()

    def test_write_log_file_failure_silent(self, monkeypatch, tmp_path):
        """Test that file logging failures are silent."""
        # Use an invalid path that can't be created
        log_file = Path("/invalid/path/that/cannot/be/created/debug.log")
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("DEBUG_LOG_FILE", str(log_file))

        # Should not raise exception
        debug("test_module", "Test message")


class TestDebugEnvStatus:
    """Tests for debug_env_status function."""

    def test_debug_env_status_disabled(self, monkeypatch, capsys):
        """Test debug_env_status does nothing when debug disabled."""
        monkeypatch.setenv("DEBUG", "false")
        debug_env_status()

        captured = capsys.readouterr()
        assert captured.err == ""

    def test_debug_env_status_enabled(self, monkeypatch, capsys):
        """Test debug_env_status prints status when enabled."""
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("DEBUG_LEVEL", "2")

        debug_env_status()

        captured = capsys.readouterr()
        assert "Debug Mode Enabled" in captured.err
        assert "DEBUG" in captured.err
        assert "DEBUG_LEVEL" in captured.err


class TestColors:
    """Tests for Colors class."""

    def test_color_codes_defined(self):
        """Test that all color codes are defined."""
        assert hasattr(Colors, "RESET")
        assert hasattr(Colors, "BOLD")
        assert hasattr(Colors, "DIM")
        assert hasattr(Colors, "DEBUG")
        assert hasattr(Colors, "SUCCESS")
        assert hasattr(Colors, "WARNING")
        assert hasattr(Colors, "ERROR")

    def test_color_codes_are_strings(self):
        """Test that color codes are strings."""
        for attr in dir(Colors):
            if not attr.startswith("_"):
                value = getattr(Colors, attr)
                if isinstance(value, str):
                    assert value.startswith("\033[")


class TestDebugIntegration:
    """Integration tests for debug functionality."""

    def test_full_debug_workflow(self, monkeypatch, tmp_path, capsys):
        """Test complete debug workflow with file and console output."""
        log_file = tmp_path / "workflow.log"
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("DEBUG_LEVEL", "3")
        monkeypatch.setenv("DEBUG_LOG_FILE", str(log_file))

        # Test various debug calls
        debug_section("workflow", "Integration Test")
        debug("workflow", "Starting process", step=1)
        debug_detailed("workflow", "Processing data", count=100)
        debug_verbose("workflow", "Detailed info", debug_data="verbose")
        debug_success("workflow", "Step complete")
        debug_info("workflow", "Additional info")
        debug_warning("workflow", "Minor issue")
        debug_error("workflow", "Critical error", code=500)

        # Check console output
        captured = capsys.readouterr()
        assert "Integration Test" in captured.err
        assert "Starting process" in captured.err
        assert "Step complete" in captured.err

        # Check file output
        assert log_file.exists()
        file_content = log_file.read_text(encoding="utf-8")
        assert "Integration Test" in file_content
        assert "Starting process" in file_content

    def test_multiple_debug_levels_same_module(self, monkeypatch, capsys):
        """Test multiple debug levels in same module."""
        monkeypatch.setenv("DEBUG", "true")

        # At level 1, only level 1 messages should appear
        monkeypatch.setenv("DEBUG_LEVEL", "1")
        debug("test", "level 1", level=1)
        debug("test", "level 2", level=2)
        debug("test", "level 3", level=3)

        captured = capsys.readouterr()
        assert "level 1" in captured.err
        assert "level 2" not in captured.err
        assert "level 3" not in captured.err

        # At level 3, all should appear
        monkeypatch.setenv("DEBUG_LEVEL", "3")
        debug("test", "level 1", level=1)
        debug("test", "level 2", level=2)
        debug("test", "level 3", level=3)

        captured = capsys.readouterr()
        assert "level 1" in captured.err
        assert "level 2" in captured.err
        assert "level 3" in captured.err


class TestDebugEdgeCases:
    """Tests for edge cases and error handling."""

    def test_format_value_dict_json_error(self):
        """Test _format_value handles JSON serialization errors for dicts."""
        # Object that can't be JSON serialized even with default=str
        class Unserializable:
            pass

        # Create a dict with an unserializable value
        # This will trigger the exception handler at lines 91-92
        bad_dict = {"key": Unserializable()}

        # Should not raise, should fall back to str representation
        result = _format_value(bad_dict, max_length=200)
        assert isinstance(result, str)
        assert "key" in result

    def test_debug_functions_with_kwargs(self, monkeypatch, capsys):
        """Test debug_success/info/warning/error with kwargs to hit kwargs branches."""
        monkeypatch.setenv("DEBUG", "true")

        # These tests cover the kwargs branches (lines 180-182, 195-197, 210-212, 225-227)
        debug_success("module", "Success", key="value")
        captured = capsys.readouterr()
        assert "key" in captured.err

        debug_info("module", "Info", data="test")
        captured = capsys.readouterr()
        assert "data" in captured.err

        debug_warning("module", "Warning", warning="test")
        captured = capsys.readouterr()
        assert "warning" in captured.err

        debug_error("module", "Error", error="test")
        captured = capsys.readouterr()
        assert "error" in captured.err

    def test_all_debug_types_when_disabled(self, monkeypatch, capsys):
        """Test that all debug functions respect disabled state (early returns)."""
        monkeypatch.setenv("DEBUG", "false")

        debug("module", "test")
        debug_detailed("module", "test")
        debug_verbose("module", "test")
        debug_success("module", "test")
        debug_info("module", "test")
        debug_warning("module", "test")
        debug_error("module", "test")
        debug_section("module", "test")

        captured = capsys.readouterr()
        # Should be empty due to early returns
        assert captured.err == ""


class TestDebugEnvironmentEdgeCases:
    """Tests for environment variable edge cases."""

    def test_get_debug_enabled_case_insensitive(self, monkeypatch):
        """Test that DEBUG is case-insensitive."""
        for value in ["TRUE", "tRuE", "TrUe", "1", "YES", "yes", "Yes", "ON", "on", "On"]:
            monkeypatch.setenv("DEBUG", value)
            assert _get_debug_enabled() is True

    def test_get_debug_enabled_whitespace_values(self, monkeypatch):
        """Test DEBUG with whitespace handling."""
        # These should NOT be treated as true (exact match required)
        for value in [" true", "true ", " true ", " 1", "1 "]:
            monkeypatch.setenv("DEBUG", value)
            assert _get_debug_enabled() is False

    def test_get_debug_level_float_string(self, monkeypatch):
        """Test get_debug_level with float string."""
        monkeypatch.setenv("DEBUG_LEVEL", "2.5")
        # int("2.5") raises ValueError, should default to 1
        assert get_debug_level() == 1

    def test_get_debug_level_negative_zero(self, monkeypatch):
        """Test get_debug_level with -0."""
        monkeypatch.setenv("DEBUG_LEVEL", "-0")
        assert get_debug_level() == 1  # -0 is 0, which gets clamped to 1

    def test_get_debug_level_large_number(self, monkeypatch):
        """Test get_debug_level with very large number."""
        monkeypatch.setenv("DEBUG_LEVEL", "999999")
        assert get_debug_level() == 3  # Clamped to max

    def test_get_log_file_relative_path(self, monkeypatch, tmp_path):
        """Test _get_log_file with relative path."""
        # Change to temp directory
        import os as os_module
        original_cwd = os_module.getcwd()
        try:
            os_module.chdir(tmp_path)
            monkeypatch.setenv("DEBUG_LOG_FILE", "relative.log")
            result = _get_log_file()
            # Should return a Path object
            assert isinstance(result, Path)
            assert str(result) == "relative.log" or result.name == "relative.log"
        finally:
            os_module.chdir(original_cwd)

    def test_get_log_file_empty_string(self, monkeypatch):
        """Test _get_log_file with empty string."""
        monkeypatch.setenv("DEBUG_LOG_FILE", "")
        # Empty string is falsy, should return None
        assert _get_log_file() is None


class TestFormatValueEdgeCases:
    """Tests for _format_value edge cases."""

    def test_format_value_empty_dict(self):
        """Test formatting empty dictionary."""
        result = _format_value({})
        assert "{}" in result or result == "{}"

    def test_format_value_empty_list(self):
        """Test formatting empty list."""
        result = _format_value([])
        assert "[]" in result or result == "[]"

    def test_format_value_nested_structures(self):
        """Test formatting deeply nested structures."""
        data = {"a": {"b": {"c": {"d": "value"}}}}
        result = _format_value(data)
        assert "a" in result
        assert "value" in result

    def test_format_value_dict_with_none_values(self):
        """Test formatting dict with None values."""
        result = _format_value({"key": None, "other": "value"})
        # JSON serializes None as "null"
        assert "null" in result or "None" in result
        assert "value" in result

    def test_format_value_list_with_mixed_types(self):
        """Test formatting list with mixed types."""
        result = _format_value([1, "two", None, True, 3.14])
        assert "1" in result
        assert "two" in result
        # JSON serializes None as "null" and True as "true"
        assert "null" in result or "None" in result

    def test_format_value_very_long_single_line(self):
        """Test formatting value that produces very long single line."""
        long_string = "x" * 400
        result = _format_value(long_string, max_length=100)
        assert result.endswith("...")
        assert len(result) <= 103  # 100 + "..."

    def test_format_value_zero_max_length(self):
        """Test formatting with zero max length."""
        result = _format_value("hello", max_length=0)
        assert result == "..." or len(result) <= 3

    def test_format_value_datetime_object(self):
        """Test formatting datetime object."""
        from datetime import datetime
        dt = datetime(2024, 1, 1, 12, 0, 0)
        result = _format_value(dt)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_format_value_custom_object_with_str(self):
        """Test formatting custom object with __str__ method."""
        class CustomClass:
            def __str__(self):
                return "CustomClass()"

        obj = CustomClass()
        result = _format_value(obj)
        assert "CustomClass()" in result

    def test_format_value_bytes(self):
        """Test formatting bytes object."""
        data = b"hello"
        result = _format_value(data)
        assert isinstance(result, str)

    def test_format_value_set(self):
        """Test formatting set (becomes list-like in JSON)."""
        data = {1, 2, 3}
        result = _format_value(data)
        assert isinstance(result, str)


class TestDebugLoggingAdvanced:
    """Tests for advanced debug logging scenarios."""

    def test_debug_with_very_long_module_name(self, monkeypatch, capsys):
        """Test debug with very long module name."""
        monkeypatch.setenv("DEBUG", "true")
        long_module = "a" * 200
        debug(long_module, "test")

        captured = capsys.readouterr()
        assert long_module in captured.err
        assert "test" in captured.err

    def test_debug_with_very_long_message(self, monkeypatch, capsys):
        """Test debug with very long message."""
        monkeypatch.setenv("DEBUG", "true")
        long_message = "x" * 500
        debug("module", long_message)

        captured = capsys.readouterr()
        assert long_message in captured.err

    def test_debug_with_many_kwargs(self, monkeypatch, capsys):
        """Test debug with many keyword arguments."""
        monkeypatch.setenv("DEBUG", "true")
        debug("module", "test", **{f"key{i}": f"value{i}" for i in range(20)})

        captured = capsys.readouterr()
        for i in range(20):
            assert f"key{i}" in captured.err
            assert f"value{i}" in captured.err

    def test_debug_with_newline_in_message(self, monkeypatch, capsys):
        """Test debug with newline in message."""
        monkeypatch.setenv("DEBUG", "true")
        debug("module", "Line 1\nLine 2\nLine 3")

        captured = capsys.readouterr()
        assert "Line 1" in captured.err
        assert "Line 2" in captured.err
        assert "Line 3" in captured.err

    def test_debug_with_special_characters(self, monkeypatch, capsys):
        """Test debug with special characters in message."""
        monkeypatch.setenv("DEBUG", "true")
        debug("module", "Special: \t\n\r\x00")

        captured = capsys.readouterr()
        assert "Special:" in captured.err

    def test_debug_detailed_level_filtering_edge(self, monkeypatch, capsys):
        """Test debug_detailed at exact level boundary."""
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("DEBUG_LEVEL", "2")

        # Level 2 should show at DEBUG_LEVEL=2
        debug("module", "exact", level=2)
        captured = capsys.readouterr()
        assert "exact" in captured.err

        # Level 3 should not show at DEBUG_LEVEL=2
        debug("module", "above", level=3)
        captured = capsys.readouterr()
        assert "above" not in captured.err

    def test_debug_verbose_max_level(self, monkeypatch, capsys):
        """Test debug_verbose at maximum level."""
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("DEBUG_LEVEL", "3")

        debug_verbose("module", "verbose message")
        captured = capsys.readouterr()
        assert "verbose message" in captured.err

    def test_debug_success_error_with_exception(self, monkeypatch, capsys):
        """Test debug_error with exception object."""
        monkeypatch.setenv("DEBUG", "true")
        try:
            raise ValueError("Test exception")
        except ValueError as e:
            debug_error("module", "Error occurred", exception=e)

        captured = capsys.readouterr()
        assert "Error occurred" in captured.err
        assert "Test exception" in captured.err

    def test_debug_section_very_long_title(self, monkeypatch, capsys):
        """Test debug_section with very long title."""
        monkeypatch.setenv("DEBUG", "true")
        long_title = "x" * 100
        debug_section("module", long_title)

        captured = capsys.readouterr()
        assert long_title in captured.err or long_title[:58] in captured.err

    def test_multiple_quick_debug_calls(self, monkeypatch, capsys):
        """Test multiple rapid debug calls."""
        monkeypatch.setenv("DEBUG", "true")

        for i in range(10):
            debug("module", f"message {i}")

        captured = capsys.readouterr()
        for i in range(10):
            assert f"message {i}" in captured.err


class TestDebugDecoratorsAdvanced:
    """Tests for advanced decorator scenarios."""

    def test_debug_timer_with_args_kwargs(self, monkeypatch, capsys):
        """Test debug_timer with function arguments."""
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("DEBUG_LEVEL", "2")

        @debug_timer("test_module")
        def func_with_args(a, b, c=None):
            return a + b + (c or 0)

        result = func_with_args(1, 2, c=3)
        assert result == 6

        captured = capsys.readouterr()
        assert "Starting func_with_args()" in captured.err
        assert "Completed func_with_args()" in captured.err

    def test_debug_timer_returns_none(self, monkeypatch, capsys):
        """Test debug_timer with function returning None."""
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("DEBUG_LEVEL", "2")

        @debug_timer("test_module")
        def void_func():
            pass

        result = void_func()
        assert result is None

        captured = capsys.readouterr()
        assert "Completed void_func()" in captured.err

    def test_debug_timer_nested_calls(self, monkeypatch, capsys):
        """Test debug_timer with nested function calls."""
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("DEBUG_LEVEL", "2")

        @debug_timer("module")
        def outer():
            return inner()

        @debug_timer("module")
        def inner():
            return "result"

        result = outer()
        assert result == "result"

        captured = capsys.readouterr()
        assert "Starting outer()" in captured.err
        assert "Starting inner()" in captured.err

    def test_debug_async_timer_with_args(self, monkeypatch, capsys):
        """Test debug_async_timer with async function arguments."""
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("DEBUG_LEVEL", "2")

        @debug_async_timer("test_module")
        async def async_func(a, b):
            await asyncio.sleep(0.001)
            return a + b

        result = asyncio.run(async_func(10, 20))
        assert result == 30

        captured = capsys.readouterr()
        assert "Starting async_func()" in captured.err
        assert "Completed async_func()" in captured.err

    @pytest.mark.asyncio
    async def test_debug_async_timer_await_multiple(self, monkeypatch, capsys):
        """Test debug_async_timer with multiple awaits."""
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("DEBUG_LEVEL", "2")

        @debug_async_timer("test_module")
        async def multi_await_func():
            await asyncio.sleep(0.001)
            await asyncio.sleep(0.001)
            return "done"

        result = await multi_await_func()
        assert result == "done"

        captured = capsys.readouterr()
        assert "Completed multi_await_func()" in captured.err


class TestDebugFileLoggingAdvanced:
    """Tests for advanced file logging scenarios."""

    def test_write_log_append_mode(self, monkeypatch, tmp_path):
        """Test that log file appends rather than overwrites."""
        log_file = tmp_path / "append_test.log"
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("DEBUG_LOG_FILE", str(log_file))

        debug("module", "First message")
        debug("module", "Second message")

        content = log_file.read_text(encoding="utf-8")
        assert "First message" in content
        assert "Second message" in content

    def test_write_log_multiple_modules(self, monkeypatch, tmp_path):
        """Test logging multiple modules to same file."""
        log_file = tmp_path / "multi_module.log"
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("DEBUG_LOG_FILE", str(log_file))

        debug("module1", "Message 1")
        debug("module2", "Message 2")
        debug("module3", "Message 3")

        content = log_file.read_text(encoding="utf-8")
        assert "module1" in content
        assert "module2" in content
        assert "module3" in content

    def test_write_log_all_debug_levels_to_file(self, monkeypatch, tmp_path):
        """Test that all debug levels write to file."""
        log_file = tmp_path / "all_levels.log"
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("DEBUG_LEVEL", "3")
        monkeypatch.setenv("DEBUG_LOG_FILE", str(log_file))

        debug("module", "level1", level=1)
        debug("module", "level2", level=2)
        debug("module", "level3", level=3)
        debug_success("module", "success")
        debug_info("module", "info")
        debug_warning("module", "warning")
        debug_error("module", "error")

        content = log_file.read_text(encoding="utf-8")
        assert "level1" in content
        assert "level2" in content
        assert "level3" in content
        assert "[OK]" in content
        assert "[INFO]" in content
        assert "[WARN]" in content
        assert "[ERROR]" in content

    def test_write_log_unicode_content(self, monkeypatch, tmp_path):
        """Test file logging with Unicode content."""
        log_file = tmp_path / "unicode.log"
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("DEBUG_LOG_FILE", str(log_file))

        debug("module", "Unicode: 你好 مرحبا שלום")

        content = log_file.read_text(encoding="utf-8")
        assert "你好" in content
        assert "مرحبا" in content
        assert "שלום" in content
        # ANSI codes should be stripped
        assert "\033" not in content

    def test_write_log_concurrent_writes(self, monkeypatch, tmp_path):
        """Test concurrent writes to log file."""
        log_file = tmp_path / "concurrent.log"
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("DEBUG_LOG_FILE", str(log_file))

        # Make multiple debug calls
        for i in range(50):
            debug("module", f"Concurrent message {i}")

        content = log_file.read_text(encoding="utf-8")
        # All messages should be present
        for i in range(50):
            assert f"Concurrent message {i}" in content


class TestDebugEnvStatusEdgeCases:
    """Tests for debug_env_status edge cases."""

    def test_debug_env_status_with_log_file(self, monkeypatch, capsys, tmp_path):
        """Test debug_env_status includes log file info."""
        log_file = tmp_path / "test.log"
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("DEBUG_LEVEL", "2")
        monkeypatch.setenv("DEBUG_LOG_FILE", str(log_file))

        debug_env_status()

        captured = capsys.readouterr()
        assert "Debug Mode Enabled" in captured.err
        assert "DEBUG_LOG_FILE" in captured.err

    def test_debug_env_status_level_3(self, monkeypatch, capsys):
        """Test debug_env_status at max level."""
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("DEBUG_LEVEL", "3")

        debug_env_status()

        captured = capsys.readouterr()
        assert "DEBUG_LEVEL" in captured.err
        assert "3" in captured.err

    def test_debug_env_status_level_1(self, monkeypatch, capsys):
        """Test debug_env_status at min level."""
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("DEBUG_LEVEL", "1")

        debug_env_status()

        captured = capsys.readouterr()
        assert "DEBUG_LEVEL" in captured.err
        assert "1" in captured.err


class TestDebugIntegrationAdvanced:
    """Advanced integration tests."""

    def test_debug_workflow_with_level_changes(self, monkeypatch, tmp_path, capsys):
        """Test debug workflow with changing debug levels."""
        log_file = tmp_path / "dynamic.log"
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("DEBUG_LOG_FILE", str(log_file))

        # Start at level 1
        monkeypatch.setenv("DEBUG_LEVEL", "1")
        debug("test", "level1-only")

        # Increase to level 2
        monkeypatch.setenv("DEBUG_LEVEL", "2")
        debug_detailed("test", "level2-enabled")

        # Increase to level 3
        monkeypatch.setenv("DEBUG_LEVEL", "3")
        debug_verbose("test", "level3-enabled")

        captured = capsys.readouterr()
        content = log_file.read_text(encoding="utf-8")

        assert "level1-only" in captured.err
        assert "level2-enabled" in captured.err
        assert "level3-enabled" in captured.err

    def test_debug_with_all_special_kwarg_values(self, monkeypatch, capsys):
        """Test debug with various special kwarg values."""
        monkeypatch.setenv("DEBUG", "true")

        debug("module", "test",
              none_val=None,
              empty_str="",
              zero=0,
              false_val=False,
              special_chars="\t\n\r")

        captured = capsys.readouterr()
        assert "none_val" in captured.err
        assert "empty_str" in captured.err
        assert "zero" in captured.err
        assert "false_val" in captured.err
        assert "special_chars" in captured.err

    def test_debug_format_value_dict_unjsonable_key(self, monkeypatch, capsys):
        """Test debug with dict that has un-JSON-serializable key."""
        monkeypatch.setenv("DEBUG", "true")

        # Dict with non-string key (will fail JSON serialization)
        bad_dict = {123: "value"}  # JSON requires string keys
        debug("module", "test", data=bad_dict)

        captured = capsys.readouterr()
        # Should handle gracefully and produce some output
        assert "test" in captured.err
