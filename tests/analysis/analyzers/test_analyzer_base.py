"""Tests for analysis.analyzers.base module"""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from analysis.analyzers.base import (
    BaseAnalyzer,
    SKIP_DIRS,
    SERVICE_INDICATORS,
    SERVICE_ROOT_FILES,
)


class TestBaseAnalyzer:
    """Test BaseAnalyzer class."""

    def test_init_with_path(self, tmp_path):
        """Test BaseAnalyzer initialization with a path."""
        analyzer = BaseAnalyzer(tmp_path)
        assert analyzer.path == tmp_path.resolve()

    def test_init_resolves_path(self, tmp_path):
        """Test that BaseAnalyzer resolves the path to absolute."""
        # Create a subdirectory to test relative path resolution
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        # Initialize with relative-style path
        relative_path = tmp_path / "subdir" / ".."
        analyzer = BaseAnalyzer(relative_path)

        # Should resolve to absolute path
        assert analyzer.path.is_absolute()
        assert analyzer.path == tmp_path.resolve()

    def test_init_with_string_path_converted(self, tmp_path):
        """Test BaseAnalyzer initialization with string path (converted to Path)."""
        # BaseAnalyzer expects Path type, but Python will accept string in __init__
        # The type hint says Path, so we need to convert string to Path
        analyzer = BaseAnalyzer(Path(str(tmp_path)))
        assert analyzer.path == tmp_path.resolve()


class TestBaseAnalyzerExists:
    """Test BaseAnalyzer._exists method."""

    def test_exists_file_exists(self, tmp_path):
        """Test _exists returns True for existing file."""
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        analyzer = BaseAnalyzer(tmp_path)
        assert analyzer._exists("test.txt") is True

    def test_exists_directory_exists(self, tmp_path):
        """Test _exists returns True for existing directory."""
        # Create a subdirectory
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        analyzer = BaseAnalyzer(tmp_path)
        assert analyzer._exists("subdir") is True

    def test_exists_not_exists(self, tmp_path):
        """Test _exists returns False for non-existent path."""
        analyzer = BaseAnalyzer(tmp_path)
        assert analyzer._exists("nonexistent.txt") is False

    def test_exists_nested_path(self, tmp_path):
        """Test _exists with nested relative path."""
        # Create nested structure
        nested = tmp_path / "level1" / "level2"
        nested.mkdir(parents=True)
        (nested / "file.txt").write_text("content")

        analyzer = BaseAnalyzer(tmp_path)
        assert analyzer._exists("level1/level2/file.txt") is True
        assert analyzer._exists("level1/level2") is True
        assert analyzer._exists("level1/level3") is False


class TestBaseAnalyzerReadFile:
    """Test BaseAnalyzer._read_file method."""

    def test_read_file_success(self, tmp_path):
        """Test _read_file reads file content successfully."""
        test_file = tmp_path / "test.txt"
        content = "Hello, World!"
        test_file.write_text(content, encoding="utf-8")

        analyzer = BaseAnalyzer(tmp_path)
        result = analyzer._read_file("test.txt")

        assert result == content

    def test_read_file_empty_file(self, tmp_path):
        """Test _read_file with empty file."""
        test_file = tmp_path / "empty.txt"
        test_file.write_text("", encoding="utf-8")

        analyzer = BaseAnalyzer(tmp_path)
        result = analyzer._read_file("empty.txt")

        assert result == ""

    def test_read_file_not_exists(self, tmp_path):
        """Test _read_file returns empty string for non-existent file."""
        analyzer = BaseAnalyzer(tmp_path)
        result = analyzer._read_file("nonexistent.txt")

        assert result == ""

    def test_read_file_with_newlines(self, tmp_path):
        """Test _read_file preserves newlines."""
        test_file = tmp_path / "lines.txt"
        content = "Line 1\nLine 2\nLine 3"
        test_file.write_text(content, encoding="utf-8")

        analyzer = BaseAnalyzer(tmp_path)
        result = analyzer._read_file("lines.txt")

        assert result == content

    def test_read_file_unicode_content(self, tmp_path):
        """Test _read_file with Unicode characters."""
        test_file = tmp_path / "unicode.txt"
        content = "Hello 世界 \u00E9 \u00F1"
        test_file.write_text(content, encoding="utf-8")

        analyzer = BaseAnalyzer(tmp_path)
        result = analyzer._read_file("unicode.txt")

        assert result == content

    def test_read_file_with_oserror(self, tmp_path):
        """Test _read_file handles OSError gracefully."""
        analyzer = BaseAnalyzer(tmp_path)

        # Mock read_text to raise OSError
        with patch.object(Path, "read_text", side_effect=OSError("Permission denied")):
            result = analyzer._read_file("test.txt")
            assert result == ""

    def test_read_file_with_unicode_decode_error(self, tmp_path):
        """Test _read_file handles UnicodeDecodeError gracefully."""
        test_file = tmp_path / "binary.bin"
        # Write binary content that will fail UTF-8 decoding
        test_file.write_bytes(b"\xff\xfe\x00\x01")

        analyzer = BaseAnalyzer(tmp_path)
        result = analyzer._read_file("binary.bin")

        # Should return empty string on decode error
        assert result == ""


class TestBaseAnalyzerReadJson:
    """Test BaseAnalyzer._read_json method."""

    def test_read_json_success(self, tmp_path):
        """Test _read_json parses valid JSON successfully."""
        test_file = tmp_path / "test.json"
        data = {"key": "value", "number": 42}
        test_file.write_text(json.dumps(data), encoding="utf-8")

        analyzer = BaseAnalyzer(tmp_path)
        result = analyzer._read_json("test.json")

        assert result == data

    def test_read_json_empty_file(self, tmp_path):
        """Test _read_json with empty file returns None."""
        test_file = tmp_path / "empty.json"
        test_file.write_text("", encoding="utf-8")

        analyzer = BaseAnalyzer(tmp_path)
        result = analyzer._read_json("empty.json")

        assert result is None

    def test_read_json_not_exists(self, tmp_path):
        """Test _read_json with non-existent file returns None."""
        analyzer = BaseAnalyzer(tmp_path)
        result = analyzer._read_json("nonexistent.json")

        assert result is None

    def test_read_json_invalid_json(self, tmp_path):
        """Test _read_json with invalid JSON returns None."""
        test_file = tmp_path / "invalid.json"
        test_file.write_text("{ invalid json }", encoding="utf-8")

        analyzer = BaseAnalyzer(tmp_path)
        result = analyzer._read_json("invalid.json")

        assert result is None

    def test_read_json_empty_object(self, tmp_path):
        """Test _read_json with empty JSON object."""
        test_file = tmp_path / "empty_obj.json"
        test_file.write_text("{}", encoding="utf-8")

        analyzer = BaseAnalyzer(tmp_path)
        result = analyzer._read_json("empty_obj.json")

        assert result == {}

    def test_read_json_nested_structure(self, tmp_path):
        """Test _read_json with nested JSON structure."""
        test_file = tmp_path / "nested.json"
        data = {
            "level1": {
                "level2": {
                    "level3": ["item1", "item2"]
                }
            }
        }
        test_file.write_text(json.dumps(data), encoding="utf-8")

        analyzer = BaseAnalyzer(tmp_path)
        result = analyzer._read_json("nested.json")

        assert result == data

    def test_read_json_array(self, tmp_path):
        """Test _read_json with JSON array at root."""
        test_file = tmp_path / "array.json"
        data = [1, 2, 3, {"key": "value"}]
        test_file.write_text(json.dumps(data), encoding="utf-8")

        analyzer = BaseAnalyzer(tmp_path)
        result = analyzer._read_json("array.json")

        assert result == data

    def test_read_json_null_values(self, tmp_path):
        """Test _read_json with null values."""
        test_file = tmp_path / "nulls.json"
        data = {"key": None, "another": "value"}
        test_file.write_text(json.dumps(data), encoding="utf-8")

        analyzer = BaseAnalyzer(tmp_path)
        result = analyzer._read_json("nulls.json")

        assert result == data

    def test_read_json_special_characters(self, tmp_path):
        """Test _read_json with special characters."""
        test_file = tmp_path / "special.json"
        data = {"key": "Line 1\nLine 2", "tab": "col1\tcol2"}
        test_file.write_text(json.dumps(data), encoding="utf-8")

        analyzer = BaseAnalyzer(tmp_path)
        result = analyzer._read_json("special.json")

        assert result == data


class TestBaseAnalyzerInferEnvVarType:
    """Test BaseAnalyzer._infer_env_var_type method."""

    def test_infer_env_var_type_empty_string(self):
        """Test _infer_env_var_type with empty string returns 'string'."""
        analyzer = BaseAnalyzer(Path("/tmp"))
        assert analyzer._infer_env_var_type("") == "string"

    def test_infer_env_var_type_boolean_true(self):
        """Test _infer_env_var_type detects boolean true values."""
        analyzer = BaseAnalyzer(Path("/tmp"))
        for value in ["true", "TRUE", "True", "1", "yes", "YES", "Yes"]:
            assert analyzer._infer_env_var_type(value) == "boolean"

    def test_infer_env_var_type_boolean_false(self):
        """Test _infer_env_var_type detects boolean false values."""
        analyzer = BaseAnalyzer(Path("/tmp"))
        for value in ["false", "FALSE", "False", "0", "no", "NO", "No"]:
            assert analyzer._infer_env_var_type(value) == "boolean"

    def test_infer_env_var_type_number_integer(self):
        """Test _infer_env_var_type detects integer numbers."""
        analyzer = BaseAnalyzer(Path("/tmp"))
        assert analyzer._infer_env_var_type("42") == "number"
        # Note: "0" and "1" are detected as boolean first
        assert analyzer._infer_env_var_type("0") == "boolean"
        assert analyzer._infer_env_var_type("1") == "boolean"
        # Numbers other than 0 and 1 are detected as numbers
        assert analyzer._infer_env_var_type("123456789") == "number"

    def test_infer_env_var_type_url_http(self):
        """Test _infer_env_var_type detects HTTP URLs."""
        analyzer = BaseAnalyzer(Path("/tmp"))
        assert analyzer._infer_env_var_type("http://example.com") == "url"
        assert analyzer._infer_env_var_type("http://localhost:3000") == "url"

    def test_infer_env_var_type_url_https(self):
        """Test _infer_env_var_type detects HTTPS URLs."""
        analyzer = BaseAnalyzer(Path("/tmp"))
        assert analyzer._infer_env_var_type("https://example.com") == "url"
        assert analyzer._infer_env_var_type("https://api.example.com/v1") == "url"

    def test_infer_env_var_type_database_urls(self):
        """Test _infer_env_var_type detects database URLs."""
        analyzer = BaseAnalyzer(Path("/tmp"))
        assert analyzer._infer_env_var_type("postgres://localhost/db") == "url"
        assert analyzer._infer_env_var_type("postgresql://localhost/db") == "url"
        assert analyzer._infer_env_var_type("mysql://localhost/db") == "url"
        assert analyzer._infer_env_var_type("mongodb://localhost/db") == "url"
        assert analyzer._infer_env_var_type("redis://localhost:6379") == "url"

    def test_infer_env_var_type_email(self):
        """Test _infer_env_var_type detects email addresses."""
        analyzer = BaseAnalyzer(Path("/tmp"))
        assert analyzer._infer_env_var_type("user@example.com") == "email"
        assert analyzer._infer_env_var_type("admin@test.co.uk") == "email"
        assert analyzer._infer_env_var_type("user+tag@example.org") == "email"

    def test_infer_env_var_type_not_email(self):
        """Test _infer_env_var_type doesn't misidentify non-emails."""
        analyzer = BaseAnalyzer(Path("/tmp"))
        # Missing dot
        assert analyzer._infer_env_var_type("user@localhost") != "email"
        # Missing @
        assert analyzer._infer_env_var_type("userexample.com") != "email"

    def test_infer_env_var_type_path_unix(self):
        """Test _infer_env_var_type detects Unix paths."""
        analyzer = BaseAnalyzer(Path("/tmp"))
        assert analyzer._infer_env_var_type("/usr/local/bin") == "path"
        assert analyzer._infer_env_var_type("./relative/path") == "path"
        assert analyzer._infer_env_var_type("../parent") == "path"

    def test_infer_env_var_type_path_windows(self):
        """Test _infer_env_var_type detects Windows paths."""
        analyzer = BaseAnalyzer(Path("/tmp"))
        assert analyzer._infer_env_var_type("C:\\Users\\test") == "path"
        assert analyzer._infer_env_var_type("\\\\server\\share") == "path"
        assert analyzer._infer_env_var_type(".\\relative") == "path"

    def test_infer_env_var_type_string_default(self):
        """Test _infer_env_var_type defaults to 'string' for unknown types."""
        analyzer = BaseAnalyzer(Path("/tmp"))
        assert analyzer._infer_env_var_type("plain text") == "string"
        assert analyzer._infer_env_var_type("API_KEY") == "string"
        assert analyzer._infer_env_var_type("my-variable") == "string"
        assert analyzer._infer_env_var_type("random_token_123abc") == "string"

    def test_infer_env_var_type_float_not_detected(self):
        """Test _infer_env_var_type doesn't detect floats (by design)."""
        analyzer = BaseAnalyzer(Path("/tmp"))
        # isdigit() returns False for floats with decimal point
        assert analyzer._infer_env_var_type("3.14") == "string"
        assert analyzer._infer_env_var_type("0.5") == "string"

    def test_infer_env_var_type_negative_numbers(self):
        """Test _infer_env_var_type handles negative numbers."""
        analyzer = BaseAnalyzer(Path("/tmp"))
        # Negative sign is not a digit, so it should be 'string'
        assert analyzer._infer_env_var_type("-42") == "string"

    def test_infer_env_var_type_mixed_case_boolean(self):
        """Test _infer_env_var_type handles mixed case booleans."""
        analyzer = BaseAnalyzer(Path("/tmp"))
        assert analyzer._infer_env_var_type("tRuE") == "boolean"
        assert analyzer._infer_env_var_type("FaLsE") == "boolean"

    def test_infer_env_var_type_url_with_port(self):
        """Test _infer_env_var_type detects URLs with ports."""
        analyzer = BaseAnalyzer(Path("/tmp"))
        assert analyzer._infer_env_var_type("https://example.com:8080") == "url"
        assert analyzer._infer_env_var_type("postgres://localhost:5432/db") == "url"


class TestModuleConstants:
    """Test module-level constants."""

    def test_skip_dirs_is_set(self):
        """Test SKIP_DIRS is a set with expected values."""
        assert isinstance(SKIP_DIRS, set)
        assert "node_modules" in SKIP_DIRS
        assert ".git" in SKIP_DIRS
        assert "__pycache__" in SKIP_DIRS
        assert ".venv" in SKIP_DIRS
        assert "venv" in SKIP_DIRS
        assert "dist" in SKIP_DIRS
        assert "build" in SKIP_DIRS
        assert ".pytest_cache" in SKIP_DIRS
        assert ".worktrees" in SKIP_DIRS
        assert ".auto-claude" in SKIP_DIRS

    def test_service_indicators_is_set(self):
        """Test SERVICE_INDICATORS is a set with expected values."""
        assert isinstance(SERVICE_INDICATORS, set)
        assert "backend" in SERVICE_INDICATORS
        assert "frontend" in SERVICE_INDICATORS
        assert "api" in SERVICE_INDICATORS
        assert "server" in SERVICE_INDICATORS
        assert "client" in SERVICE_INDICATORS

    def test_service_root_files_is_set(self):
        """Test SERVICE_ROOT_FILES is a set with expected values."""
        assert isinstance(SERVICE_ROOT_FILES, set)
        assert "package.json" in SERVICE_ROOT_FILES
        assert "requirements.txt" in SERVICE_ROOT_FILES
        assert "pyproject.toml" in SERVICE_ROOT_FILES
        assert "Cargo.toml" in SERVICE_ROOT_FILES
        assert "Dockerfile" in SERVICE_ROOT_FILES

    def test_skip_dirs_is_not_empty(self):
        """Test SKIP_DIRS is not empty."""
        assert len(SKIP_DIRS) > 0

    def test_service_indicators_is_not_empty(self):
        """Test SERVICE_INDICATORS is not empty."""
        assert len(SERVICE_INDICATORS) > 0

    def test_service_root_files_is_not_empty(self):
        """Test SERVICE_ROOT_FILES is not empty."""
        assert len(SERVICE_ROOT_FILES) > 0


class TestBaseAnalyzerEdgeCases:
    """Test edge cases and error handling."""

    def test_exists_with_symlink_to_file(self, tmp_path):
        """Test _exists with symlink to existing file."""
        # Create original file
        original = tmp_path / "original.txt"
        original.write_text("content")

        # Create symlink
        symlink = tmp_path / "link.txt"
        symlink.symlink_to(original)

        analyzer = BaseAnalyzer(tmp_path)
        assert analyzer._exists("link.txt") is True

    def test_exists_with_broken_symlink(self, tmp_path):
        """Test _exists with broken symlink."""
        # Create symlink to non-existent file
        symlink = tmp_path / "broken.txt"
        symlink.symlink_to(tmp_path / "nonexistent.txt")

        analyzer = BaseAnalyzer(tmp_path)
        # exists() returns False for broken symlinks
        assert analyzer._exists("broken.txt") is False

    def test_read_file_large_file(self, tmp_path):
        """Test _read_file with large file."""
        large_content = "x" * 1_000_000  # 1MB
        test_file = tmp_path / "large.txt"
        test_file.write_text(large_content, encoding="utf-8")

        analyzer = BaseAnalyzer(tmp_path)
        result = analyzer._read_file("large.txt")

        assert result == large_content

    def test_read_json_malformed_json_trailing_comma(self, tmp_path):
        """Test _read_json with JSON having trailing comma."""
        test_file = tmp_path / "trailing.json"
        test_file.write_text('{"key": "value",}', encoding="utf-8")

        analyzer = BaseAnalyzer(tmp_path)
        result = analyzer._read_json("trailing.json")

        # Should return None for invalid JSON
        assert result is None

    def test_read_json_comments_not_allowed(self, tmp_path):
        """Test _read_json with JSON comments (not standard JSON)."""
        test_file = tmp_path / "comments.json"
        test_file.write_text('{"key": "value"} // comment', encoding="utf-8")

        analyzer = BaseAnalyzer(tmp_path)
        result = analyzer._read_json("comments.json")

        # Should return None for invalid JSON
        assert result is None

    def test_infer_env_var_type_unicode_string(self):
        """Test _infer_env_var_type with Unicode string."""
        analyzer = BaseAnalyzer(Path("/tmp"))
        assert analyzer._infer_env_var_type("Hello 世界") == "string"

    def test_infer_env_var_type_whitespace_only(self):
        """Test _infer_env_var_type with whitespace."""
        analyzer = BaseAnalyzer(Path("/tmp"))
        # Whitespace is not empty, so it should be 'string'
        assert analyzer._infer_env_var_type("   ") == "string"
        assert analyzer._infer_env_var_type("\t\n") == "string"
