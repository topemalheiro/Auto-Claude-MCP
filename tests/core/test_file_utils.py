"""Tests for file_utils"""

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from core.file_utils import atomic_write, write_json_atomic


class TestAtomicWrite:
    """Tests for atomic_write context manager"""

    def test_atomic_write_basic(self, tmp_path):
        """Test atomic_write context manager"""
        filepath = tmp_path / "test.txt"
        content = "Hello, world!"

        with atomic_write(filepath, "w") as f:
            f.write(content)

        assert filepath.exists()
        assert filepath.read_text() == content

    def test_atomic_write_creates_parent_dirs(self, tmp_path):
        """Test atomic_write creates parent directories"""
        filepath = tmp_path / "subdir" / "nested" / "test.txt"
        content = "Nested content"

        with atomic_write(filepath, "w") as f:
            f.write(content)

        assert filepath.exists()
        assert filepath.read_text() == content

    def test_atomic_write_binary(self, tmp_path):
        """Test atomic_write in binary mode"""
        filepath = tmp_path / "test.bin"
        content = b"\x00\x01\x02\x03"

        with atomic_write(filepath, "wb") as f:
            f.write(content)

        assert filepath.exists()
        assert filepath.read_bytes() == content

    def test_atomic_write_text_mode_default_encoding(self, tmp_path):
        """Test atomic_write uses utf-8 encoding by default"""
        filepath = tmp_path / "test.txt"
        content = "Hello 世界"

        with atomic_write(filepath, "w") as f:
            f.write(content)

        assert filepath.read_text(encoding="utf-8") == content

    def test_atomic_write_custom_encoding(self, tmp_path):
        """Test atomic_write with custom encoding"""
        filepath = tmp_path / "test.txt"
        content = "Hello 世界"

        with atomic_write(filepath, "w", encoding="utf-16") as f:
            f.write(content)

        assert filepath.read_text(encoding="utf-16") == content

    def test_atomic_write_wt_mode(self, tmp_path):
        """Test atomic_write with 'wt' mode"""
        filepath = tmp_path / "test.txt"
        content = "Text mode"

        with atomic_write(filepath, "wt") as f:
            f.write(content)

        assert filepath.read_text() == content

    def test_atomic_write_error_cleanup(self, tmp_path):
        """Test atomic_write cleans up temp file on error"""
        filepath = tmp_path / "test.txt"

        try:
            with atomic_write(filepath, "w") as f:
                f.write("Partial")
                raise ValueError("Test error")
        except ValueError:
            pass  # Expected test error (no-op)

        # File should not exist because write failed before completion
        assert not filepath.exists()

        # No .tmp files should remain
        tmp_files = list(tmp_path.glob("*.tmp*"))
        assert len(tmp_files) == 0

    def test_atomic_write_partial_cleanup_logs_warning(self, tmp_path, caplog):
        """Test atomic_write logs warning when cleanup fails"""
        filepath = tmp_path / "test.txt"

        # Simulate cleanup failure by making the temp file unreadable after write
        original_unlink = os.unlink

        def failing_unlink(path):
            if ".tmp." in str(path):
                raise OSError("Simulated cleanup failure")
            return original_unlink(path)

        with patch("os.unlink", side_effect=failing_unlink):
            try:
                with atomic_write(filepath, "w") as f:
                    f.write("Content")
                    raise ValueError("Test error during write")
            except ValueError:
                pass

        # Verify warning was logged about cleanup failure
        assert any("Failed to cleanup temp file" in record.message for record in caplog.records)

    def test_atomic_write_overwrites_existing(self, tmp_path):
        """Test atomic_write overwrites existing file"""
        filepath = tmp_path / "overwrite.txt"
        old_content = "Old content"
        new_content = "New content"

        # Write initial file
        filepath.write_text(old_content)
        assert filepath.read_text() == old_content

        # Overwrite
        with atomic_write(filepath, "w") as f:
            f.write(new_content)

        assert filepath.read_text() == new_content

    def test_atomic_write_returns_file_handle(self, tmp_path):
        """Test atomic_write yields file handle"""
        filepath = tmp_path / "test.txt"

        with atomic_write(filepath, "w") as f:
            assert hasattr(f, "write")
            f.write("Content")

    def test_atomic_write_pathlib_path(self, tmp_path):
        """Test atomic_write accepts pathlib.Path"""
        filepath = Path(tmp_path) / "test.txt"
        content = "Pathlib test"

        with atomic_write(filepath, "w") as f:
            f.write(content)

        assert filepath.read_text() == content

    def test_atomic_write_string_path(self, tmp_path):
        """Test atomic_write accepts string path"""
        filepath = os.path.join(tmp_path, "test.txt")
        content = "String path test"

        with atomic_write(filepath, "w") as f:
            f.write(content)

        assert Path(filepath).read_text() == content

    def test_atomic_write_binary_encoding_must_be_none(self, tmp_path):
        """Test that binary mode ignores encoding parameter"""
        filepath = tmp_path / "test.bin"
        content = b"\x00\x01"

        # Should not raise - encoding is ignored for binary mode
        with atomic_write(filepath, "wb", encoding="utf-8") as f:
            f.write(content)

        assert filepath.read_bytes() == content

    def test_atomic_write_multiple_writes(self, tmp_path):
        """Test atomic_write with multiple write operations"""
        filepath = tmp_path / "test.txt"

        with atomic_write(filepath, "w") as f:
            f.write("Line 1\n")
            f.write("Line 2\n")
            f.write("Line 3\n")

        content = filepath.read_text()
        assert content == "Line 1\nLine 2\nLine 3\n"

    def test_atomic_write_empty_file(self, tmp_path):
        """Test atomic_write creates empty file"""
        filepath = tmp_path / "empty.txt"

        with atomic_write(filepath, "w") as f:
            pass  # Write nothing

        assert filepath.exists()
        assert filepath.read_text() == ""

    def test_atomic_write_unicode_content(self, tmp_path):
        """Test atomic_write handles unicode content"""
        filepath = tmp_path / "unicode.txt"
        content = "Hello 世界 Привет мир مرحبا"

        with atomic_write(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        assert filepath.read_text(encoding="utf-8") == content

    def test_atomic_write_fdopen_failure_cleans_up(self, tmp_path):
        """Test atomic_write cleans up temp file when fdopen fails"""
        filepath = tmp_path / "test.txt"

        # Mock os.fdopen to raise an exception
        original_fdopen = os.fdopen

        def failing_fdopen(fd, mode, encoding=None):
            # Only fail for the temp file creation
            if fd > 0:  # file descriptors are positive
                raise IOError("Failed to fdopen")
            return original_fdopen(fd, mode, encoding=encoding)

        with patch("os.fdopen", side_effect=failing_fdopen):
            with pytest.raises(IOError, match="Failed to fdopen"):
                with atomic_write(filepath, "w") as f:
                    f.write("Content")

        # Verify no temp files remain
        tmp_files = list(tmp_path.glob("*.tmp*"))
        assert len(tmp_files) == 0


class TestWriteJsonAtomic:
    """Tests for write_json_atomic function"""

    def test_write_json_atomic_basic(self, tmp_path):
        """Test write_json_atomic"""
        filepath = tmp_path / "data.json"
        data = {"key": "value", "number": 42, "nested": {"a": 1}}

        write_json_atomic(filepath, data)

        assert filepath.exists()
        with open(filepath) as f:
            result = json.load(f)
        assert result == data

    def test_write_json_atomic_with_indent(self, tmp_path):
        """Test write_json_atomic with custom indent"""
        filepath = tmp_path / "formatted.json"
        data = {"key": "value", "number": 42}

        write_json_atomic(filepath, data, indent=4)

        content = filepath.read_text()
        assert "    \"key\"" in content  # 4 spaces indent
        assert "    \"number\"" in content

    def test_write_json_atomic_no_indent(self, tmp_path):
        """Test write_json_atomic with no indent"""
        filepath = tmp_path / "compact.json"
        data = {"key": "value", "nested": {"a": 1}}

        write_json_atomic(filepath, data, indent=None)

        content = filepath.read_text()
        # No newlines for compact JSON
        assert "\n" not in content
        assert json.loads(content) == data

    def test_write_json_atomic_ensure_ascii(self, tmp_path):
        """Test write_json_ascii with ensure_ascii"""
        filepath = tmp_path / "unicode.json"
        data = {"message": "Hello 世界"}

        write_json_atomic(filepath, data, ensure_ascii=True)

        content = filepath.read_text()
        assert "\\u4e16\\u754c" in content  # Escaped unicode
        # Verify it's valid JSON and decodes correctly
        assert json.loads(content) == data

    def test_write_json_atomic_ensure_ascii_false(self, tmp_path):
        """Test write_json_ascii with ensure_ascii=False"""
        filepath = tmp_path / "unicode.json"
        data = {"message": "Hello 世界"}

        write_json_atomic(filepath, data, ensure_ascii=False)

        # Explicitly read with UTF-8 encoding on all platforms
        content = filepath.read_text(encoding="utf-8")
        assert "世界" in content  # Raw unicode preserved
        assert "\\u4e16\\u754c" not in content

    def test_write_json_atomic_custom_encoding(self, tmp_path):
        """Test write_json_atomic with custom encoding"""
        filepath = tmp_path / "utf8.json"
        data = {"message": "Hello"}

        write_json_atomic(filepath, data, encoding="utf-8")

        assert filepath.exists()
        with open(filepath, encoding="utf-8") as f:
            result = json.load(f)
        assert result == data

    def test_write_json_atomic_overwrites_existing(self, tmp_path):
        """Test write_json_atomic overwrites existing file"""
        filepath = tmp_path / "overwrite.json"
        old_data = {"old": "data"}
        new_data = {"new": "data"}

        # Write initial file
        write_json_atomic(filepath, old_data)
        assert filepath.read_text() == json.dumps(old_data, indent=2)

        # Overwrite
        write_json_atomic(filepath, new_data)

        assert filepath.exists()
        with open(filepath) as f:
            result = json.load(f)
        assert result == new_data
        assert "old" not in result

    def test_write_json_atomic_unicode_keys(self, tmp_path):
        """Test write_json_atomic handles unicode keys"""
        filepath = tmp_path / "unicode_keys.json"
        data = {"名前": "値", "key": "value"}

        write_json_atomic(filepath, data)

        with open(filepath, encoding="utf-8") as f:
            result = json.load(f)
        assert result == data

    def test_write_json_atomic_complex_nested(self, tmp_path):
        """Test write_json_atomic with complex nested structure"""
        filepath = tmp_path / "complex.json"
        data = {
            "level1": {
                "level2": {
                    "level3": {
                        "array": [1, 2, 3],
                        "string": "test",
                        "boolean": True,
                        "null": None,
                    }
                }
            }
        }

        write_json_atomic(filepath, data)

        with open(filepath) as f:
            result = json.load(f)
        assert result == data

    def test_write_json_atomic_empty_dict(self, tmp_path):
        """Test write_json_atomic with empty dict"""
        filepath = tmp_path / "empty.json"
        data = {}

        write_json_atomic(filepath, data)

        assert filepath.read_text() == "{}"
        assert json.load(open(filepath)) == data

    def test_write_json_atomic_empty_list(self, tmp_path):
        """Test write_json_atomic with empty list"""
        filepath = tmp_path / "empty_list.json"
        data = []

        write_json_atomic(filepath, data)

        assert filepath.read_text() == "[]"
        assert json.load(open(filepath)) == data

    def test_write_json_atomic_large_data(self, tmp_path):
        """Test write_json_atomic with large data"""
        filepath = tmp_path / "large.json"
        data = {f"key_{i}": f"value_{i}" * 100 for i in range(1000)}

        write_json_atomic(filepath, data)

        with open(filepath) as f:
            result = json.load(f)
        assert result == data
        assert len(result) == 1000

    def test_write_json_atomic_special_characters(self, tmp_path):
        """Test write_json_atomic with special characters"""
        filepath = tmp_path / "special.json"
        data = {
            "quotes": 'He said "Hello"',
            "backslash": "path\\to\\file",
            "newline": "line1\nline2",
            "tab": "col1\tcol2",
            "unicode_escape": "\u0048\u0065\u006c\u006c\u006f",
        }

        write_json_atomic(filepath, data)

        with open(filepath) as f:
            result = json.load(f)
        assert result == data

    def test_write_json_atomic_numbers(self, tmp_path):
        """Test write_json_atomic with various number types"""
        filepath = tmp_path / "numbers.json"
        data = {
            "integer": 42,
            "negative": -10,
            "float": 3.14,
            "exponential": 1.5e10,
            "zero": 0,
        }

        write_json_atomic(filepath, data)

        with open(filepath) as f:
            result = json.load(f)
        assert result == data

    def test_write_json_atomic_boolean_and_null(self, tmp_path):
        """Test write_json_atomic with boolean and null values"""
        filepath = tmp_path / "bool_null.json"
        data = {"true": True, "false": False, "null": None}

        write_json_atomic(filepath, data)

        with open(filepath) as f:
            result = json.load(f)
        assert result == data

    def test_write_json_atomic_default_indent_2(self, tmp_path):
        """Test write_json_atomic uses indent=2 by default"""
        filepath = tmp_path / "default_indent.json"
        data = {"key": "value"}

        write_json_atomic(filepath, data)

        content = filepath.read_text()
        assert "  \"key\"" in content  # 2 spaces indent

    def test_write_json_atomic_creates_parent_dirs(self, tmp_path):
        """Test write_json_atomic creates parent directories"""
        filepath = tmp_path / "deep" / "nested" / "data.json"
        data = {"key": "value"}

        write_json_atomic(filepath, data)

        assert filepath.exists()
        with open(filepath) as f:
            result = json.load(f)
        assert result == data

    def test_write_json_atomic_pathlib_path(self, tmp_path):
        """Test write_json_atomic accepts pathlib.Path"""
        filepath = Path(tmp_path) / "pathlib.json"
        data = {"key": "value"}

        write_json_atomic(filepath, data)

        assert filepath.exists()

    def test_write_json_atomic_string_path(self, tmp_path):
        """Test write_json_atomic accepts string path"""
        filepath = os.path.join(tmp_path, "string.json")
        data = {"key": "value"}

        write_json_atomic(filepath, data)

        assert Path(filepath).exists()


class TestAtomicWriteEdgeCases:
    """Tests for edge cases and error scenarios in atomic_write."""

    def test_atomic_write_large_file(self, tmp_path):
        """Test atomic_write with large file content."""
        filepath = tmp_path / "large.txt"
        # Create a 1MB+ content
        content = "x" * (1024 * 1024 + 100)

        with atomic_write(filepath, "w") as f:
            f.write(content)

        assert filepath.exists()
        assert filepath.read_text() == content
        assert filepath.stat().st_size > 1024 * 1024

    def test_atomic_write_many_small_writes(self, tmp_path):
        """Test atomic_write with many small write operations."""
        filepath = tmp_path / "many_writes.txt"

        with atomic_write(filepath, "w") as f:
            for i in range(1000):
                f.write(f"Line {i}\n")

        content = filepath.read_text()
        lines = content.split("\n")
        # Last line might be empty due to trailing newline
        assert len([l for l in lines if l]) == 1000
        assert "Line 0" in content
        assert "Line 999" in content

    def test_atomic_write_permission_denied_parent(self, tmp_path):
        """Test atomic_write when parent directory is read-only."""
        import sys
        import stat

        # Skip on Windows - chmod doesn't prevent file creation
        if sys.platform == "win32":
            pytest.skip("Directory read-only doesn't prevent file creation on Windows")

        # Create a directory and make it read-only
        ro_dir = tmp_path / "readonly"
        ro_dir.mkdir()
        filepath = ro_dir / "test.txt"

        # Make directory read-only (skip on platforms where chmod may not work)
        try:
            ro_dir.chmod(stat.S_IRUSR | stat.S_IXUSR)
        except (OSError, AttributeError):
            # Skip test if chmod not supported
            pytest.skip("chmod not supported on this platform")

        try:
            with pytest.raises(PermissionError):
                with atomic_write(filepath, "w") as f:
                    f.write("test")
        finally:
            # Restore permissions for cleanup
            try:
                ro_dir.chmod(stat.S_IRWXU)
            except (OSError, AttributeError):
                pass

    def test_atomic_write_special_characters_filename(self, tmp_path):
        """Test atomic_write with special characters in filename."""
        # Test with various special characters (avoiding truly invalid ones)
        filepath = tmp_path / "file-with_special.chars[1].txt"
        content = "Special filename"

        with atomic_write(filepath, "w") as f:
            f.write(content)

        assert filepath.exists()
        assert filepath.read_text() == content

    def test_atomic_write_with_binary_null_bytes(self, tmp_path):
        """Test atomic_write with binary content including null bytes."""
        filepath = tmp_path / "null_bytes.bin"
        content = b"\x00\x01\x02\x00\x03\x00\x00"

        with atomic_write(filepath, "wb") as f:
            f.write(content)

        assert filepath.read_bytes() == content

    def test_atomic_write_replace_failure_preserves_original(self, tmp_path):
        """Test atomic_write preserves original when replace fails."""
        filepath = tmp_path / "existing.txt"
        original_content = "Original content"
        filepath.write_text(original_content)

        # Mock os.replace to fail but still allow temp file creation
        original_replace = os.replace

        def failing_replace(src, dst):
            # Only fail when replacing the actual file
            if "existing.txt" in str(dst):
                raise OSError("Simulated replace failure")
            return original_replace(src, dst)

        with patch("os.replace", side_effect=failing_replace):
            with pytest.raises(OSError, match="Simulated replace failure"):
                with atomic_write(filepath, "w") as f:
                    f.write("New content")

        # Original content should be preserved
        assert filepath.read_text() == original_content

    def test_atomic_write_context_manager_exit_properly(self, tmp_path):
        """Test atomic_write context manager exits cleanly."""
        filepath = tmp_path / "test.txt"

        # Normal exit
        with atomic_write(filepath, "w") as f:
            f.write("Content")

        assert filepath.exists()

        # Verify no resource leaks by checking file is closed
        with atomic_write(filepath, "w") as f:
            f.write("New content")
            assert not f.closed
        assert f.closed


class TestWriteJsonAtomicEdgeCases:
    """Tests for edge cases in write_json_atomic."""

    def test_write_json_atomic_large_data(self, tmp_path):
        """Test write_json_atomic with large nested data."""
        filepath = tmp_path / "large.json"
        # Create a large nested structure
        data = {
            f"key_{i}": {
                "nested": {
                    "deep": {
                        "array": list(range(100)),
                        "value": f"x" * 50
                    }
                } for j in range(10)
            } for i in range(100)
        }

        write_json_atomic(filepath, data)

        with open(filepath) as f:
            result = json.load(f)
        assert result == data
        assert len(result) == 100

    def test_write_json_atomic_unicode_various_scripts(self, tmp_path):
        """Test write_json_atomic with various Unicode scripts."""
        filepath = tmp_path / "unicode_all.json"
        data = {
            "latin": "Hello",
            "cyrillic": "Привет",
            "greek": "Γεια",
            "chinese": "你好",
            "japanese": "こんにちは",
            "arabic": "مرحبا",
            "hebrew": "שלום",
            "emoji": "👋🌍",
            "symbols": "©®™€£¥",
        }

        write_json_atomic(filepath, data, ensure_ascii=False)

        with open(filepath, encoding="utf-8") as f:
            result = json.load(f)
        assert result == data

    def test_write_json_atomic_deeply_nested(self, tmp_path):
        """Test write_json_atomic with deeply nested structure."""
        filepath = tmp_path / "deep.json"
        # Create deeply nested structure
        data = {"level": 0}
        current = data
        for i in range(1, 50):
            current["nested"] = {"level": i}
            current = current["nested"]

        write_json_atomic(filepath, data)

        with open(filepath) as f:
            result = json.load(f)
        assert result["level"] == 0

    def test_write_json_atomic_cyclic_reference_error(self, tmp_path):
        """Test write_json_atomic handles cyclic references gracefully."""
        filepath = tmp_path / "cyclic.json"
        data = {"key": "value"}
        data["self"] = data  # Create cyclic reference

        # This should raise a TypeError (circular reference)
        with pytest.raises((TypeError, ValueError)):
            write_json_atomic(filepath, data)

        # File should not exist due to write failure
        assert not filepath.exists()

    def test_write_json_atomic_nan_inf(self, tmp_path):
        """Test write_json_atomic with NaN and Infinity values."""
        filepath = tmp_path / "special_numbers.json"
        data = {
            "nan": float("nan"),
            "inf": float("inf"),
            "neg_inf": float("-inf"),
        }

        # Python's json.dumps allows NaN/Inf by default
        write_json_atomic(filepath, data)

        # File should exist and be readable
        assert filepath.exists()
        # NaN doesn't equal itself, so we just check the file exists and is valid
        content = filepath.read_text()
        assert "nan" in content.lower() or "nan" in content

    def test_write_json_atomic_array_with_types(self, tmp_path):
        """Test write_json_atomic with mixed type array."""
        filepath = tmp_path / "mixed_array.json"
        data = [
            "string",
            42,
            3.14,
            True,
            False,
            None,
            {"nested": "object"},
            [1, 2, 3],
        ]

        write_json_atomic(filepath, data)

        with open(filepath) as f:
            result = json.load(f)
        assert result == data
        assert len(result) == 8

    def test_write_json_atomic_very_long_strings(self, tmp_path):
        """Test write_json_atomic with very long string values."""
        filepath = tmp_path / "long_strings.json"
        data = {
            "long_string": "x" * 10000,
            "unicode_long": "世" * 5000,
        }

        write_json_atomic(filepath, data)

        with open(filepath, encoding="utf-8") as f:
            result = json.load(f)
        assert result["long_string"] == "x" * 10000
        assert result["unicode_long"] == "世" * 5000

    def test_write_json_atomic_dict_keys_various_types(self, tmp_path):
        """Test write_json_atomic with different key types."""
        filepath = tmp_path / "keys.json"
        # JSON only allows string keys
        data = {
            "string_key": "value1",
            "123": "numeric_string_key",
            "": "empty_string_key",
        }

        write_json_atomic(filepath, data)

        with open(filepath) as f:
            result = json.load(f)
        assert result == data

    def test_write_json_atomic_preserves_precision(self, tmp_path):
        """Test write_json_atomic preserves numeric precision."""
        filepath = tmp_path / "precision.json"
        data = {
            "float": 3.141592653589793,
            "large_int": 9007199254740992,  # 2^53
            "small_float": 0.000000001,
        }

        write_json_atomic(filepath, data)

        with open(filepath) as f:
            result = json.load(f)
        assert result["float"] == 3.141592653589793
        assert result["large_int"] == 9007199254740992
        assert result["small_float"] == 0.000000001

    def test_write_json_atomic_escape_sequences(self, tmp_path):
        """Test write_json_atomic properly escapes special characters."""
        filepath = tmp_path / "escaped.json"
        data = {
            "quote": 'Text with "quotes"',
            "backslash": "path\\to\\file",
            "newline": "line1\nline2",
            "tab": "col1\tcol2",
            "carriage": "line1\rline2",
            "backspace": "a\bc",
            "formfeed": "page\fp",
            "unicode_escape": "\u0048\u0065",
        }

        write_json_atomic(filepath, data)

        with open(filepath) as f:
            result = json.load(f)
        assert result == data
        assert result["quote"] == 'Text with "quotes"'
        assert result["backslash"] == "path\\to\\file"

    def test_write_json_atomic_surrogate_pairs(self, tmp_path):
        """Test write_json_atomic with Unicode surrogate pairs."""
        filepath = tmp_path / "surrogate.json"
        # Emoji and other characters outside BMP
        data = {
            "emoji": "😀🎉🚀",
            "chinese_ext": "𠀀𠀁𠀂",  # CJK Extension B
        }

        write_json_atomic(filepath, data, ensure_ascii=False)

        with open(filepath, encoding="utf-8") as f:
            result = json.load(f)
        assert result == data

    def test_write_json_atomic_empty_values(self, tmp_path):
        """Test write_json_atomic with various empty values."""
        filepath = tmp_path / "empty_values.json"
        data = {
            "empty_string": "",
            "empty_dict": {},
            "empty_list": [],
            "null_value": None,
            "false_value": False,
            "zero": 0,
            "zero_float": 0.0,
        }

        write_json_atomic(filepath, data)

        with open(filepath) as f:
            result = json.load(f)
        assert result == data

    def test_write_json_atomic_custom_indent_zero(self, tmp_path):
        """Test write_json_atomic with indent=0 (no indentation)."""
        filepath = tmp_path / "indent0.json"
        data = {"key": "value", "nested": {"a": 1}}

        write_json_atomic(filepath, data, indent=0)

        content = filepath.read_text()
        # With indent=0, should still be valid JSON but not pretty-printed
        assert json.loads(content) == data

    def test_write_json_atomic_inconsistent_indent(self, tmp_path):
        """Test write_json_atomic with various indent values."""
        filepath1 = tmp_path / "indent1.json"
        filepath2 = tmp_path / "indent4.json"
        filepath3 = tmp_path / "indent8.json"
        data = {"key": "value", "nested": {"a": 1, "b": 2}}

        write_json_atomic(filepath1, data, indent=1)
        write_json_atomic(filepath2, data, indent=4)
        write_json_atomic(filepath3, data, indent=8)

        # All should produce valid JSON
        for fp in [filepath1, filepath2, filepath3]:
            with open(fp) as f:
                assert json.load(f) == data

    def test_write_json_atomic_write_after_context_exit(self, tmp_path):
        """Test that file is properly closed after write_json_atomic."""
        filepath = tmp_path / "test.json"
        data = {"key": "value"}

        write_json_atomic(filepath, data)

        # File should be readable immediately (no file descriptor leaks)
        with open(filepath, "r") as f:
            result = json.load(f)
        assert result == data

        # Should be able to write again (no lock)
        write_json_atomic(filepath, {"new": "data"})
        with open(filepath) as f:
            result = json.load(f)
        assert result == {"new": "data"}
