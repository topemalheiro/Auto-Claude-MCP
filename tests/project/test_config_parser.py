"""Comprehensive tests for config_parser module."""

import json
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from project.config_parser import ConfigParser


@pytest.fixture
def temp_project_dir(tmp_path: Path) -> Path:
    """Create a temporary project directory for testing."""
    return tmp_path


@pytest.fixture
def config_parser(temp_project_dir: Path) -> ConfigParser:
    """Create a ConfigParser instance for testing."""
    return ConfigParser(temp_project_dir)


class TestConfigParserInit:
    """Tests for ConfigParser.__init__"""

    def test_init_with_path(self, temp_project_dir: Path):
        """Test initialization with a project directory path."""
        parser = ConfigParser(temp_project_dir)
        assert parser.project_dir == temp_project_dir.resolve()

    def test_init_resolves_path(self, tmp_path: Path):
        """Test that project_dir is resolved to absolute path."""
        relative_path = tmp_path.name
        parser = ConfigParser(Path(relative_path))
        assert parser.project_dir.is_absolute()

    def test_init_with_string(self, tmp_path: Path):
        """Test initialization with a string path."""
        parser = ConfigParser(str(tmp_path))
        assert isinstance(parser.project_dir, Path)
        assert parser.project_dir.is_absolute()


class TestReadJson:
    """Tests for ConfigParser.read_json"""

    def test_read_json_valid_file(self, config_parser: ConfigParser, tmp_path: Path):
        """Test reading a valid JSON file."""
        test_file = tmp_path / "test.json"
        test_data = {"key": "value", "number": 123}
        test_file.write_text(json.dumps(test_data))

        result = config_parser.read_json("test.json")
        assert result == test_data

    def test_read_json_nonexistent_file(self, config_parser: ConfigParser):
        """Test reading a non-existent JSON file returns None."""
        result = config_parser.read_json("nonexistent.json")
        assert result is None

    def test_read_json_invalid_json(self, config_parser: ConfigParser, tmp_path: Path):
        """Test reading an invalid JSON file returns None."""
        test_file = tmp_path / "invalid.json"
        test_file.write_text("{invalid json content")

        result = config_parser.read_json("invalid.json")
        assert result is None

    def test_read_json_empty_file(self, config_parser: ConfigParser, tmp_path: Path):
        """Test reading an empty JSON file."""
        test_file = tmp_path / "empty.json"
        test_file.write_text("{}")

        result = config_parser.read_json("empty.json")
        assert result == {}

    def test_read_json_nested_structure(self, config_parser: ConfigParser, tmp_path: Path):
        """Test reading a JSON file with nested structure."""
        test_file = tmp_path / "nested.json"
        test_data = {
            "level1": {
                "level2": {
                    "level3": "deep value"
                },
                "array": [1, 2, 3]
            }
        }
        test_file.write_text(json.dumps(test_data))

        result = config_parser.read_json("nested.json")
        assert result == test_data


class TestReadToml:
    """Tests for ConfigParser.read_toml"""

    def test_read_toml_valid_file(self, config_parser: ConfigParser, tmp_path: Path):
        """Test reading a valid TOML file."""
        test_file = tmp_path / "test.toml"
        test_file.write_text("""
[section]
key = "value"
number = 123
""")

        result = config_parser.read_toml("test.toml")
        assert result is not None
        assert "section" in result
        assert result["section"]["key"] == "value"
        assert result["section"]["number"] == 123

    def test_read_toml_nonexistent_file(self, config_parser: ConfigParser):
        """Test reading a non-existent TOML file returns None."""
        result = config_parser.read_toml("nonexistent.toml")
        assert result is None

    def test_read_toml_invalid_toml(self, config_parser: ConfigParser, tmp_path: Path):
        """Test reading an invalid TOML file returns None."""
        test_file = tmp_path / "invalid.toml"
        test_file.write_text("[invalid")

        result = config_parser.read_toml("invalid.toml")
        assert result is None

    def test_read_toml_empty_file(self, config_parser: ConfigParser, tmp_path: Path):
        """Test reading an empty TOML file."""
        test_file = tmp_path / "empty.toml"
        test_file.write_text("")

        result = config_parser.read_toml("empty.toml")
        assert result is not None
        assert result == {}

    def test_read_toml_array_section(self, config_parser: ConfigParser, tmp_path: Path):
        """Test reading a TOML file with array section."""
        test_file = tmp_path / "array.toml"
        test_file.write_text("""
[[items]]
name = "first"

[[items]]
name = "second"
""")

        result = config_parser.read_toml("array.toml")
        assert result is not None
        assert "items" in result
        assert len(result["items"]) == 2
        assert result["items"][0]["name"] == "first"
        assert result["items"][1]["name"] == "second"


class TestReadText:
    """Tests for ConfigParser.read_text"""

    def test_read_text_valid_file(self, config_parser: ConfigParser, tmp_path: Path):
        """Test reading a valid text file."""
        test_file = tmp_path / "test.txt"
        test_content = "This is a test file\nWith multiple lines"
        test_file.write_text(test_content)

        result = config_parser.read_text("test.txt")
        assert result == test_content

    def test_read_text_nonexistent_file(self, config_parser: ConfigParser):
        """Test reading a non-existent text file returns None."""
        result = config_parser.read_text("nonexistent.txt")
        assert result is None

    def test_read_text_empty_file(self, config_parser: ConfigParser, tmp_path: Path):
        """Test reading an empty text file."""
        test_file = tmp_path / "empty.txt"
        test_file.write_text("")

        result = config_parser.read_text("empty.txt")
        assert result == ""

    def test_read_text_unicode_content(self, config_parser: ConfigParser, tmp_path: Path):
        """Test reading a text file with unicode content."""
        test_file = tmp_path / "unicode.txt"
        test_content = "Hello 世界\nHello 🌍\nTab\tseparated"
        test_file.write_text(test_content)

        result = config_parser.read_text("unicode.txt")
        assert result == test_content

    def test_read_text_os_error_returns_none(self, config_parser: ConfigParser, tmp_path: Path):
        """Test that OSError is handled gracefully."""
        # Create a directory instead of a file
        test_dir = tmp_path / "directory"
        test_dir.mkdir()

        result = config_parser.read_text("directory")
        assert result is None


class TestFileExists:
    """Tests for ConfigParser.file_exists"""

    def test_file_exists_single_file(self, config_parser: ConfigParser, tmp_path: Path):
        """Test checking if a single file exists."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        result = config_parser.file_exists("test.txt")
        assert result is True

    def test_file_exists_nonexistent_file(self, config_parser: ConfigParser):
        """Test checking if a non-existent file exists."""
        result = config_parser.file_exists("nonexistent.txt")
        assert result is False

    def test_file_exists_multiple_paths(self, config_parser: ConfigParser, tmp_path: Path):
        """Test checking if any of multiple paths exist."""
        (tmp_path / "file1.txt").write_text("content")
        # file2.txt doesn't exist

        result = config_parser.file_exists("file1.txt", "file2.txt")
        assert result is True

    def test_file_exists_none_exist(self, config_parser: ConfigParser):
        """Test checking when none of the paths exist."""
        result = config_parser.file_exists("file1.txt", "file2.txt", "file3.txt")
        assert result is False

    def test_file_exists_glob_pattern(self, config_parser: ConfigParser, tmp_path: Path):
        """Test checking files using glob pattern."""
        (tmp_path / "test1.json").write_text("{}")
        (tmp_path / "test2.json").write_text("{}")

        result = config_parser.file_exists("*.json")
        assert result is True

    def test_file_exists_nested_glob(self, config_parser: ConfigParser, tmp_path: Path):
        """Test checking files using nested glob pattern."""
        nested = tmp_path / "subdir"
        nested.mkdir()
        (nested / "test.py").write_text("print('hello')")

        result = config_parser.file_exists("**/*.py")
        assert result is True

    def test_file_exists_glob_no_match(self, config_parser: ConfigParser):
        """Test glob pattern that matches nothing."""
        result = config_parser.file_exists("*.nonexistent")
        assert result is False

    def test_file_exists_mixed_patterns(self, config_parser: ConfigParser, tmp_path: Path):
        """Test mixing regular paths and glob patterns."""
        (tmp_path / "package.json").write_text("{}")

        result = config_parser.file_exists("*.json", "requirements.txt", "Gemfile")
        assert result is True


class TestGlobFiles:
    """Tests for ConfigParser.glob_files"""

    def test_glob_files_json_files(self, config_parser: ConfigParser, tmp_path: Path):
        """Test globbing JSON files."""
        (tmp_path / "test1.json").write_text("{}")
        (tmp_path / "test2.json").write_text("{}")
        (tmp_path / "test.txt").write_text("text")

        result = config_parser.glob_files("*.json")
        assert len(result) == 2
        assert all(p.suffix == ".json" for p in result)

    def test_glob_files_nested_pattern(self, config_parser: ConfigParser, tmp_path: Path):
        """Test globbing with nested pattern."""
        nested = tmp_path / "src"
        nested.mkdir()
        (nested / "main.py").write_text("print('main')")
        (tmp_path / "root.py").write_text("print('root')")

        result = config_parser.glob_files("**/*.py")
        assert len(result) == 2

    def test_glob_files_no_matches(self, config_parser: ConfigParser):
        """Test globbing pattern with no matches."""
        result = config_parser.glob_files("*.nonexistent")
        assert result == []

    def test_glob_files_returns_paths(self, config_parser: ConfigParser, tmp_path: Path):
        """Test that glob_files returns Path objects."""
        (tmp_path / "test.json").write_text("{}")

        result = config_parser.glob_files("*.json")
        assert all(isinstance(p, Path) for p in result)

    def test_glob_files_multiple_extensions(self, config_parser: ConfigParser, tmp_path: Path):
        """Test globbing files with different extensions."""
        (tmp_path / "test.py").write_text("")
        (tmp_path / "test.txt").write_text("")
        (tmp_path / "test.md").write_text("")

        result = config_parser.glob_files("test.*")
        assert len(result) == 3


class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_read_json_with_large_file(self, config_parser: ConfigParser, tmp_path: Path):
        """Test reading a large JSON file."""
        test_file = tmp_path / "large.json"
        large_data = {f"key_{i}": f"value_{i}" for i in range(1000)}
        test_file.write_text(json.dumps(large_data))

        result = config_parser.read_json("large.json")
        assert len(result) == 1000
        assert result["key_0"] == "value_0"
        assert result["key_999"] == "value_999"

    def test_read_toml_with_special_characters(self, config_parser: ConfigParser, tmp_path: Path):
        """Test reading TOML with special characters."""
        test_file = tmp_path / "special.toml"
        test_file.write_text(r"""
key = "value with \"quotes\""
path = "C:\\Users\\test"
special = "Line1\nLine2\tTab"
""")

        result = config_parser.read_toml("special.toml")
        assert result is not None
        assert "quotes" in result["key"]
        assert "Users" in result["path"]

    def test_file_exists_with_directory(self, config_parser: ConfigParser, tmp_path: Path):
        """Test file_exists with a directory path."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()

        result = config_parser.file_exists("test_dir")
        assert result is True

    def test_read_text_binary_file(self, config_parser: ConfigParser, tmp_path: Path):
        """Test reading text file handles encoding gracefully."""
        test_file = tmp_path / "binary.bin"
        test_file.write_bytes(b"\x00\x01\x02\x03\xff\xfe")

        # Should raise an error or handle gracefully
        try:
            result = config_parser.read_text("binary.bin")
            # If it returns something, it shouldn't crash
            assert isinstance(result, (str, None))
        except UnicodeDecodeError:
            # This is acceptable behavior for binary files
            pass
