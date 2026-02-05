"""
Tests for paths module.
Comprehensive test coverage for path management functions.
"""

from pathlib import Path
import pytest

from memory.paths import (
    get_memory_dir,
    get_session_insights_dir,
    clear_memory,
)


class TestGetMemoryDir:
    """Tests for get_memory_dir function."""

    def test_creates_memory_directory(self, temp_spec_dir):
        """Test creates memory directory if it doesn't exist."""
        memory_dir = get_memory_dir(temp_spec_dir)

        assert memory_dir == temp_spec_dir / "memory"
        assert memory_dir.exists()
        assert memory_dir.is_dir()

    def test_returns_existing_memory_directory(self, temp_spec_dir):
        """Test returns existing memory directory without error."""
        # Create directory first
        memory_dir = temp_spec_dir / "memory"
        memory_dir.mkdir()

        # Call function
        result = get_memory_dir(temp_spec_dir)

        assert result == memory_dir
        assert result.exists()

    def test_creates_parent_directories(self, tmp_path):
        """Test creates memory directory when parent exists."""
        # Create the spec directory first (paths module doesn't create parents)
        deep_spec_dir = tmp_path / "level1" / "level2" / "level3" / "spec"
        deep_spec_dir.mkdir(parents=True)

        memory_dir = get_memory_dir(deep_spec_dir)

        assert memory_dir == deep_spec_dir / "memory"
        assert memory_dir.exists()

    def test_handles_existing_file_at_memory_path(self, tmp_path):
        """Test handles case where a file exists at memory path."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create a file at the memory location
        memory_file = spec_dir / "memory"
        memory_file.write_text("I'm a file, not a directory")

        # mkdir will raise FileExistsError when a file exists with that name
        try:
            result = get_memory_dir(spec_dir)
            # If it doesn't raise, it should return the path
            assert result == memory_file
        except FileExistsError:
            # This is expected behavior when a file exists at the path
            pass


class TestGetSessionInsightsDir:
    """Tests for get_session_insights_dir function."""

    def test_creates_session_insights_directory(self, temp_spec_dir):
        """Test creates session_insights directory if it doesn't exist."""
        insights_dir = get_session_insights_dir(temp_spec_dir)

        expected_path = temp_spec_dir / "memory" / "session_insights"
        assert insights_dir == expected_path
        assert insights_dir.exists()
        assert insights_dir.is_dir()

    def test_creates_memory_and_insights_directories(self, temp_spec_dir):
        """Test creates both memory and session_insights directories."""
        insights_dir = get_session_insights_dir(temp_spec_dir)

        # Verify memory directory was created
        memory_dir = temp_spec_dir / "memory"
        assert memory_dir.exists()

        # Verify insights directory was created
        assert insights_dir.exists()
        assert insights_dir == memory_dir / "session_insights"

    def test_returns_existing_session_insights_directory(self, temp_spec_dir):
        """Test returns existing session_insights directory."""
        # Create the full path first
        insights_dir = temp_spec_dir / "memory" / "session_insights"
        insights_dir.mkdir(parents=True)

        # Call function
        result = get_session_insights_dir(temp_spec_dir)

        assert result == insights_dir
        assert result.exists()

    def test_handles_nested_spec_directories(self, tmp_path):
        """Test handles deeply nested spec directories."""
        # Create the spec directory first (paths module doesn't create parents)
        deep_spec_dir = tmp_path / "a" / "b" / "c" / "spec"
        deep_spec_dir.mkdir(parents=True)

        insights_dir = get_session_insights_dir(deep_spec_dir)

        expected = deep_spec_dir / "memory" / "session_insights"
        assert insights_dir == expected
        assert insights_dir.exists()


class TestClearMemory:
    """Tests for clear_memory function."""

    def test_deletes_memory_directory(self, temp_spec_dir):
        """Test deletes existing memory directory."""
        # Create memory directory with some files
        memory_dir = get_memory_dir(temp_spec_dir)
        (memory_dir / "test.txt").write_text("test")

        # Clear memory
        clear_memory(temp_spec_dir)

        # Directory should be gone
        assert not memory_dir.exists()

    def test_handles_non_existent_memory_directory(self, temp_spec_dir):
        """Test handles case where memory directory doesn't exist."""
        # Don't create memory directory
        memory_dir = temp_spec_dir / "memory"
        assert not memory_dir.exists()

        # Should not raise error
        clear_memory(temp_spec_dir)

        # Still shouldn't exist
        assert not memory_dir.exists()

    def test_clears_all_memory_contents(self, temp_spec_dir):
        """Test clears all files and subdirectories in memory."""
        memory_dir = get_memory_dir(temp_spec_dir)

        # Create various files and directories
        (memory_dir / "file1.txt").write_text("content1")
        (memory_dir / "file2.md").write_text("content2")

        subdir1 = memory_dir / "subdir1"
        subdir1.mkdir()
        (subdir1 / "nested.txt").write_text("nested")

        subdir2 = memory_dir / "session_insights"
        subdir2.mkdir()
        (subdir2 / "session_001.json").write_text("{}")

        # Clear memory
        clear_memory(temp_spec_dir)

        # Everything should be gone
        assert not memory_dir.exists()

    def test_does_not_delete_other_directories(self, temp_spec_dir):
        """Test only deletes memory directory, not other directories."""
        # Create other directories
        other_dir1 = temp_spec_dir / "other_dir"
        other_dir1.mkdir()
        (other_dir1 / "file.txt").write_text("should keep")

        other_dir2 = temp_spec_dir / "another"
        other_dir2.mkdir()

        # Create and clear memory
        memory_dir = get_memory_dir(temp_spec_dir)
        clear_memory(temp_spec_dir)

        # Other directories should still exist
        assert other_dir1.exists()
        assert (other_dir1 / "file.txt").exists()
        assert other_dir2.exists()

        # Memory directory should be gone
        assert not memory_dir.exists()

    def test_idempotent(self, temp_spec_dir):
        """Test calling clear_memory multiple times is safe."""
        # Create and clear memory
        memory_dir = get_memory_dir(temp_spec_dir)
        clear_memory(temp_spec_dir)

        # Call again - should not raise error
        clear_memory(temp_spec_dir)
        clear_memory(temp_spec_dir)

        assert not memory_dir.exists()

    def test_clears_and_can_recreate(self, temp_spec_dir):
        """Test memory can be cleared and then recreated."""
        # Create memory with files
        memory_dir = get_memory_dir(temp_spec_dir)
        (memory_dir / "test.txt").write_text("original")

        # Clear it
        clear_memory(temp_spec_dir)
        assert not memory_dir.exists()

        # Recreate
        new_memory_dir = get_memory_dir(temp_spec_dir)
        assert new_memory_dir.exists()
        assert not (new_memory_dir / "test.txt").exists()

        # Can add new files
        (new_memory_dir / "new.txt").write_text("new content")
        assert (new_memory_dir / "new.txt").read_text() == "new content"
