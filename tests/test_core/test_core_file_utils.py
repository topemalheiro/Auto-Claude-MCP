"""
Tests for core.file_utils module
=================================

Comprehensive tests for atomic file write utilities including:
- atomic_write context manager (text and binary modes)
- write_json_atomic for JSON serialization
- Error handling and cleanup
- Cross-platform compatibility
"""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.file_utils import atomic_write, write_json_atomic


# ============================================================================
# atomic_write tests (text mode)
# ============================================================================


class TestAtomicWriteText:
    """Tests for atomic_write in text mode."""

    def test_atomic_write_basic(self, tmp_path):
        """Test atomic_write basic functionality."""
        test_file = tmp_path / "test.txt"

        with atomic_write(test_file, mode="w") as f:
            f.write("Hello, world!")

        # File should be written
        assert test_file.exists()
        assert test_file.read_text() == "Hello, world!"

    def test_atomic_write_creates_parent_dirs(self, tmp_path):
        """Test atomic_write creates parent directories."""
        test_file = tmp_path / "nested" / "dirs" / "test.txt"

        with atomic_write(test_file, mode="w") as f:
            f.write("Content")

        assert test_file.exists()
        assert test_file.parent.exists()

    def test_atomic_write_default_encoding(self, tmp_path):
        """Test atomic_write uses UTF-8 encoding by default."""
        test_file = tmp_path / "test.txt"

        with atomic_write(test_file, mode="w") as f:
            f.write("Hello 世界")

        assert test_file.read_text(encoding="utf-8") == "Hello 世界"

    def test_atomic_write_custom_encoding(self, tmp_path):
        """Test atomic_write with custom encoding."""
        test_file = tmp_path / "test.txt"

        with atomic_write(test_file, mode="w", encoding="latin-1") as f:
            f.write("Hello")

        # File should be readable with specified encoding
        assert test_file.read_text(encoding="latin-1") == "Hello"

    def test_atomic_write_overwrites_existing(self, tmp_path):
        """Test atomic_write overwrites existing file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Old content")

        with atomic_write(test_file, mode="w") as f:
            f.write("New content")

        assert test_file.read_text() == "New content"

    def test_atomic_write_exception_cleanup(self, tmp_path):
        """Test atomic_write cleans up temp file on exception."""
        test_file = tmp_path / "test.txt"

        with pytest.raises(ValueError):
            with atomic_write(test_file, mode="w") as f:
                f.write("Partial")
                raise ValueError("Test exception")

        # Target file should not exist
        assert not test_file.exists()

        # No .tmp files should remain
        tmp_files = list(tmp_path.glob("*.tmp*"))
        assert len(tmp_files) == 0

    def test_atomic_write_text_mode_explicit(self, tmp_path):
        """Test atomic_write with mode='wt' (explicit text mode)."""
        test_file = tmp_path / "test.txt"

        with atomic_write(test_file, mode="wt") as f:
            f.write("Text content")

        assert test_file.read_text() == "Text content"

    def test_atomic_write_multiple_lines(self, tmp_path):
        """Test atomic_write with multiple lines."""
        test_file = tmp_path / "test.txt"

        with atomic_write(test_file, mode="w") as f:
            f.write("Line 1\n")
            f.write("Line 2\n")
            f.write("Line 3\n")

        content = test_file.read_text()
        assert "Line 1" in content
        assert "Line 2" in content
        assert "Line 3" in content


# ============================================================================
# atomic_write tests (binary mode)
# ============================================================================


class TestAtomicWriteBinary:
    """Tests for atomic_write in binary mode."""

    def test_atomic_write_binary_basic(self, tmp_path):
        """Test atomic_write in binary mode."""
        test_file = tmp_path / "test.bin"

        with atomic_write(test_file, mode="wb") as f:
            f.write(b"\x00\x01\x02\x03\x04")

        assert test_file.exists()
        assert test_file.read_bytes() == b"\x00\x01\x02\x03\x04"

    def test_atomic_write_binary_encoding_none(self, tmp_path):
        """Test atomic_write binary mode ignores encoding parameter."""
        test_file = tmp_path / "test.bin"

        # This should work - binary mode should require encoding=None
        with atomic_write(test_file, mode="wb", encoding=None) as f:
            f.write(b"Binary data")

        assert test_file.read_bytes() == b"Binary data"

    def test_atomic_write_binary_large_file(self, tmp_path):
        """Test atomic_write with large binary data."""
        test_file = tmp_path / "large.bin"
        large_data = b"\x00" * (10 * 1024 * 1024)  # 10 MB

        with atomic_write(test_file, mode="wb") as f:
            f.write(large_data)

        assert test_file.stat().st_size == len(large_data)

    def test_atomic_write_binary_exception_cleanup(self, tmp_path):
        """Test atomic_write cleans up temp file on exception in binary mode."""
        test_file = tmp_path / "test.bin"

        with pytest.raises(ValueError):
            with atomic_write(test_file, mode="wb") as f:
                f.write(b"Partial")
                raise ValueError("Test exception")

        assert not test_file.exists()


# ============================================================================
# atomic_write tests with Path objects
# ============================================================================


class TestAtomicWritePathObjects:
    """Tests for atomic_write with Path objects."""

    def test_atomic_write_with_path_object(self, tmp_path):
        """Test atomic_write accepts pathlib.Path objects."""
        test_file = tmp_path / "test.txt"

        with atomic_write(test_file, mode="w") as f:
            f.write("Content")

        assert test_file.exists()

    def test_atomic_write_with_string_path(self, tmp_path):
        """Test atomic_write accepts string paths."""
        test_file = str(tmp_path / "test.txt")

        with atomic_write(test_file, mode="w") as f:
            f.write("Content")

        assert Path(test_file).exists()


# ============================================================================
# atomic_write edge cases
# ============================================================================


class TestAtomicWriteEdgeCases:
    """Tests for atomic_write edge cases."""

    def test_atomic_write_empty_file(self, tmp_path):
        """Test atomic_write with empty content."""
        test_file = tmp_path / "empty.txt"

        with atomic_write(test_file, mode="w") as f:
            f.write("")

        assert test_file.exists()
        assert test_file.read_text() == ""

    def test_atomic_write_unicode_emoji(self, tmp_path):
        """Test atomic_write with Unicode emoji."""
        test_file = tmp_path / "emoji.txt"

        with atomic_write(test_file, mode="w", encoding="utf-8") as f:
            f.write("Hello 🌍 🚀 👋")

        assert test_file.read_text(encoding="utf-8") == "Hello 🌍 🚀 👋"

    def test_atomic_write_context_manager_exit(self, tmp_path):
        """Test atomic_write context manager properly closes file."""
        test_file = tmp_path / "test.txt"

        with atomic_write(test_file, mode="w") as f:
            f.write("Content")
            # File should be open
            assert not f.closed

        # File should be closed after context
        assert f.closed

    def test_atomic_write_temp_file_naming(self, tmp_path):
        """Test atomic_write creates temp file with correct naming."""
        test_file = tmp_path / "target.txt"

        with atomic_write(test_file, mode="w") as f:
            # File should be open and writable
            f.write("Content")

        # After completion, target should exist
        assert test_file.exists()

    def test_atomic_write_cleanup_failure_logged(self, tmp_path, caplog):
        """Test atomic_write logs cleanup failures."""
        test_file = tmp_path / "test.txt"

        def mock_unlink(path):
            raise OSError("Permission denied")

        with patch("os.unlink", side_effect=mock_unlink):
            with pytest.raises(ValueError):
                with atomic_write(test_file, mode="w") as f:
                    raise ValueError("Test exception")

        # Check that warning was logged
        assert any("Failed to cleanup temp file" in record.message for record in caplog.records)


# ============================================================================
# write_json_atomic tests
# ============================================================================


class TestWriteJsonAtomic:
    """Tests for write_json_atomic function."""

    def test_write_json_atomic_basic(self, tmp_path):
        """Test write_json_atomic basic functionality."""
        test_file = tmp_path / "test.json"
        data = {"key": "value", "number": 42}

        write_json_atomic(test_file, data)

        assert test_file.exists()
        with open(test_file) as f:
            result = json.load(f)
        assert result == data

    def test_write_json_atomic_nested(self, tmp_path):
        """Test write_json_atomic with nested structures."""
        test_file = tmp_path / "nested.json"
        data = {
            "user": {
                "name": "Alice",
                "age": 30,
                "address": {
                    "city": "Wonderland",
                    "zip": "12345"
                }
            },
            "tags": ["admin", "user"]
        }

        write_json_atomic(test_file, data)

        with open(test_file) as f:
            result = json.load(f)
        assert result == data

    def test_write_json_atomic_list(self, tmp_path):
        """Test write_json_atomic with list data."""
        test_file = tmp_path / "list.json"
        data = [1, 2, 3, "four", {"five": 5}]

        write_json_atomic(test_file, data)

        with open(test_file) as f:
            result = json.load(f)
        assert result == data

    def test_write_json_atomic_custom_indent(self, tmp_path):
        """Test write_json_atomic with custom indent."""
        test_file = tmp_path / "custom.json"
        data = {"key": "value"}

        write_json_atomic(test_file, data, indent=4)

        content = test_file.read_text()
        assert "    " in content  # 4 spaces indent

    def test_write_json_atomic_no_indent(self, tmp_path):
        """Test write_json_atomic with indent=None."""
        test_file = tmp_path / "compact.json"
        data = {"key": "value"}

        write_json_atomic(test_file, data, indent=None)

        content = test_file.read_text()
        # Should be compact (no newlines except trailing)
        assert "\n" not in content.strip()

    def test_write_json_atomic_unicode(self, tmp_path):
        """Test write_json_atomic with Unicode characters."""
        test_file = tmp_path / "unicode.json"
        data = {"message": "Hello 世界 🌍"}

        write_json_atomic(test_file, data, ensure_ascii=False)

        with open(test_file, encoding="utf-8") as f:
            result = json.load(f)
        assert result == data

    def test_write_json_atomic_ensure_ascii(self, tmp_path):
        """Test write_json_ascii with ensure_ascii=True."""
        test_file = tmp_path / "ascii.json"
        data = {"message": "Hello 世界"}

        write_json_atomic(test_file, data, ensure_ascii=True)

        content = test_file.read_text()
        # Unicode should be escaped
        assert "\\u" in content

    def test_write_json_atomic_special_characters(self, tmp_path):
        """Test write_json_atomic with special characters."""
        test_file = tmp_path / "special.json"
        data = {
            "newline": "line1\nline2",
            "tab": "col1\tcol2",
            "quote": 'He said "hello"',
            "backslash": "path\\to\\file"
        }

        write_json_atomic(test_file, data)

        with open(test_file) as f:
            result = json.load(f)
        assert result == data

    def test_write_json_atomic_custom_encoding(self, tmp_path):
        """Test write_json_atomic with custom encoding."""
        test_file = tmp_path / "encoded.json"
        data = {"key": "value"}

        write_json_atomic(test_file, data, encoding="latin-1")

        # Should be readable with specified encoding
        with open(test_file, encoding="latin-1") as f:
            result = json.load(f)
        assert result == data

    def test_write_json_atomic_overwrites_existing(self, tmp_path):
        """Test write_json_atomic overwrites existing file."""
        test_file = tmp_path / "overwrite.json"
        old_data = {"old": "data"}
        new_data = {"new": "data"}

        # Write old data
        write_json_atomic(test_file, old_data)
        assert json.loads(test_file.read_text()) == old_data

        # Write new data
        write_json_atomic(test_file, new_data)
        assert json.loads(test_file.read_text()) == new_data

    def test_write_json_atomic_empty_dict(self, tmp_path):
        """Test write_json_atomic with empty dictionary."""
        test_file = tmp_path / "empty.json"

        write_json_atomic(test_file, {})

        with open(test_file) as f:
            result = json.load(f)
        assert result == {}

    def test_write_json_atomic_none_values(self, tmp_path):
        """Test write_json_atomic with None values."""
        test_file = tmp_path / "nulls.json"
        data = {
            "null_key": None,
            "string": "value",
            "number": 0
        }

        write_json_atomic(test_file, data)

        with open(test_file) as f:
            result = json.load(f)
        assert result == data

    def test_write_json_atomic_large_data(self, tmp_path):
        """Test write_json_atomic with large data structure."""
        test_file = tmp_path / "large.json"
        data = {f"key_{i}": f"value_{i}" * 100 for i in range(1000)}

        write_json_atomic(test_file, data)

        with open(test_file) as f:
            result = json.load(f)
        assert result == data


# ============================================================================
# Cross-platform compatibility tests
# ============================================================================


class TestCrossPlatformCompatibility:
    """Tests for cross-platform file handling."""

    def test_atomic_write_windows_style_paths(self, tmp_path):
        """Test atomic_write handles Windows-style paths correctly."""
        # On Unix, create with forward slashes
        test_file = tmp_path / "subdir" / "test.txt"
        test_file.parent.mkdir(parents=True, exist_ok=True)

        with atomic_write(str(test_file), mode="w") as f:
            f.write("Windows compatible")

        assert test_file.exists()

    def test_atomic_write_long_paths(self, tmp_path):
        """Test atomic_write with long directory paths."""
        # Create a deeply nested path
        deep_dir = tmp_path
        for i in range(10):
            deep_dir = deep_dir / f"level{i}"

        test_file = deep_dir / "test.txt"

        with atomic_write(test_file, mode="w") as f:
            f.write("Deep file")

        assert test_file.exists()

    def test_write_json_atomic_path_object(self, tmp_path):
        """Test write_json_atomic accepts Path objects."""
        test_file = tmp_path / "path_obj.json"
        data = {"test": "data"}

        write_json_atomic(test_file, data)

        assert test_file.exists()
