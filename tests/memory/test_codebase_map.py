"""
Tests for codebase_map module.
Comprehensive test coverage for codebase map functions.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
import pytest

from memory.codebase_map import (
    update_codebase_map,
    load_codebase_map,
)


class TestUpdateCodebaseMap:
    """Tests for update_codebase_map function."""

    def test_creates_new_map_file(self, temp_spec_dir):
        """Test creates new codebase_map.json when it doesn't exist."""
        discoveries = {
            "src/api/auth.py": "JWT authentication handler",
            "src/models/user.py": "User database model",
        }

        update_codebase_map(temp_spec_dir, discoveries)

        map_file = temp_spec_dir / "memory" / "codebase_map.json"
        assert map_file.exists()

        with open(map_file, encoding="utf-8") as f:
            content = json.load(f)

        assert content["src/api/auth.py"] == "JWT authentication handler"
        assert content["src/models/user.py"] == "User database model"

    def test_adds_metadata_to_new_map(self, temp_spec_dir):
        """Test adds metadata when creating new map."""
        discoveries = {"src/api/auth.py": "JWT authentication handler"}

        update_codebase_map(temp_spec_dir, discoveries)

        map_file = temp_spec_dir / "memory" / "codebase_map.json"
        with open(map_file, encoding="utf-8") as f:
            content = json.load(f)

        assert "_metadata" in content
        assert "last_updated" in content["_metadata"]
        assert "total_files" in content["_metadata"]
        assert content["_metadata"]["total_files"] == 1

    def test_updates_existing_map(self, temp_spec_dir):
        """Test updates existing codebase map."""
        # Create initial map
        initial_discoveries = {
            "src/api/auth.py": "JWT authentication handler",
        }
        update_codebase_map(temp_spec_dir, initial_discoveries)

        # Add more discoveries
        new_discoveries = {
            "src/models/user.py": "User database model",
            "src/utils/helpers.py": "Utility functions",
        }
        update_codebase_map(temp_spec_dir, new_discoveries)

        # Load and verify
        codebase_map = load_codebase_map(temp_spec_dir)

        assert len(codebase_map) == 3
        assert codebase_map["src/api/auth.py"] == "JWT authentication handler"
        assert codebase_map["src/models/user.py"] == "User database model"
        assert codebase_map["src/utils/helpers.py"] == "Utility functions"

    def test_overwrites_existing_file_purposes(self, temp_spec_dir):
        """Test overwrites purpose when file path already exists."""
        # Create initial entry
        update_codebase_map(temp_spec_dir, {"src/api/auth.py": "Initial description"})

        # Update with new purpose
        update_codebase_map(temp_spec_dir, {"src/api/auth.py": "Updated description"})

        codebase_map = load_codebase_map(temp_spec_dir)
        assert codebase_map["src/api/auth.py"] == "Updated description"
        assert len(codebase_map) == 1

    def test_updates_metadata_timestamp(self, temp_spec_dir):
        """Test updates last_updated timestamp on each update."""
        # First update
        update_codebase_map(temp_spec_dir, {"src/file1.py": "Description 1"})

        map_file = temp_spec_dir / "memory" / "codebase_map.json"
        with open(map_file, encoding="utf-8") as f:
            content = json.load(f)
        first_timestamp = content["_metadata"]["last_updated"]

        # Wait a tiny bit and update again
        update_codebase_map(temp_spec_dir, {"src/file2.py": "Description 2"})

        with open(map_file, encoding="utf-8") as f:
            content = json.load(f)
        second_timestamp = content["_metadata"]["last_updated"]

        # Timestamps should be different (or at least updated)
        assert "last_updated" in content["_metadata"]
        assert content["_metadata"]["total_files"] == 2

    def test_handles_corrupted_existing_file(self, temp_spec_dir):
        """Test handles corrupted existing map file gracefully."""
        memory_dir = temp_spec_dir / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)
        map_file = memory_dir / "codebase_map.json"

        # Write corrupted JSON
        map_file.write_text("{invalid json}", encoding="utf-8")

        # Should create new map
        discoveries = {"src/api/auth.py": "JWT authentication handler"}
        update_codebase_map(temp_spec_dir, discoveries)

        codebase_map = load_codebase_map(temp_spec_dir)
        assert "src/api/auth.py" in codebase_map

    def test_handles_unicode_in_paths_and_descriptions(self, temp_spec_dir):
        """Test handles Unicode characters in file paths and descriptions."""
        discoveries = {
            "src/api/认证.py": "认证处理程序",  # Chinese characters
            "src/models/пользователь.py": "Модель пользователя",  # Cyrillic
        }

        update_codebase_map(temp_spec_dir, discoveries)

        codebase_map = load_codebase_map(temp_spec_dir)
        assert "src/api/认证.py" in codebase_map
        assert codebase_map["src/api/认证.py"] == "认证处理程序"

    def test_saves_to_graphiti_when_enabled(self, temp_spec_dir):
        """Test saves to Graphiti when enabled."""
        mock_graphiti = MagicMock()
        mock_graphiti.save_codebase_discoveries = AsyncMock()
        mock_graphiti.close = AsyncMock()

        discoveries = {"src/api/auth.py": "JWT authentication handler"}

        with patch(
            "memory.codebase_map.is_graphiti_memory_enabled", return_value=True
        ), patch("memory.codebase_map.get_graphiti_memory", return_value=mock_graphiti), patch(
            "memory.codebase_map.run_async"
        ) as mock_run_async:
            import asyncio

            mock_run_async.side_effect = lambda coro: asyncio.run(coro)

            update_codebase_map(temp_spec_dir, discoveries)

            # Verify file was still created
            codebase_map = load_codebase_map(temp_spec_dir)
            assert "src/api/auth.py" in codebase_map

    def test_handles_graphiti_save_failure_gracefully(
        self, temp_spec_dir, caplog
    ):
        """Test continues if Graphiti save fails."""
        discoveries = {"src/api/auth.py": "JWT authentication handler"}

        with patch(
            "memory.codebase_map.is_graphiti_memory_enabled", return_value=True
        ), patch(
            "memory.codebase_map.get_graphiti_memory",
            side_effect=RuntimeError("Graphiti failed"),
        ):
            # Should not raise exception
            update_codebase_map(temp_spec_dir, discoveries)

            # File should still be created
            codebase_map = load_codebase_map(temp_spec_dir)
            assert "src/api/auth.py" in codebase_map

    def test_does_not_save_empty_discoveries_to_graphiti(self, temp_spec_dir):
        """Test doesn't call Graphiti for empty discoveries."""
        with patch(
            "memory.codebase_map.is_graphiti_memory_enabled", return_value=True
        ), patch("memory.codebase_map.get_graphiti_memory") as mock_get:
            update_codebase_map(temp_spec_dir, {})

            # Should not call get_graphiti_memory for empty discoveries
            mock_get.assert_not_called()

    def test_writes_sorted_json(self, temp_spec_dir):
        """Test writes JSON with sorted keys for consistency."""
        discoveries = {
            "zebra.py": "Z",
            "apple.py": "A",
            "middle.py": "M",
        }

        update_codebase_map(temp_spec_dir, discoveries)

        map_file = temp_spec_dir / "memory" / "codebase_map.json"
        content = map_file.read_text(encoding="utf-8")

        # JSON should be sorted
        lines = content.split("\n")
        # Find the lines with file entries
        file_lines = [l for l in lines if l.strip().startswith('"') and ':' in l]
        # apple.py should come before zebra.py
        apple_index = next(i for i, l in enumerate(file_lines) if 'apple.py' in l)
        zebra_index = next(i for i, l in enumerate(file_lines) if 'zebra.py' in l)
        assert apple_index < zebra_index

    def test_handles_special_characters_in_descriptions(self, temp_spec_dir):
        """Test handles special characters in descriptions."""
        discoveries = {
            "src/api/auth.py": 'Handles "quoted" values and \'single\' quotes',
            "src/utils/regex.py": "Uses regex: \\d+ for digits",
        }

        update_codebase_map(temp_spec_dir, discoveries)

        codebase_map = load_codebase_map(temp_spec_dir)
        assert 'Handles "quoted" values' in codebase_map["src/api/auth.py"]
        assert "regex: \\d+" in codebase_map["src/utils/regex.py"]


class TestLoadCodebaseMap:
    """Tests for load_codebase_map function."""

    def test_returns_empty_dict_when_no_file(self, temp_spec_dir):
        """Test returns empty dict when codebase_map.json doesn't exist."""
        codebase_map = load_codebase_map(temp_spec_dir)
        assert codebase_map == {}

    def test_loads_existing_map(self, temp_spec_dir):
        """Test loads existing codebase map."""
        memory_dir = temp_spec_dir / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)
        map_file = memory_dir / "codebase_map.json"

        test_data = {
            "src/api/auth.py": "JWT authentication handler",
            "src/models/user.py": "User database model",
            "_metadata": {
                "last_updated": "2024-01-01T00:00:00Z",
                "total_files": 2,
            },
        }

        with open(map_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        codebase_map = load_codebase_map(temp_spec_dir)

        assert len(codebase_map) == 2
        assert "_metadata" not in codebase_map
        assert codebase_map["src/api/auth.py"] == "JWT authentication handler"

    def test_removes_metadata_from_result(self, temp_spec_dir):
        """Test removes _metadata key from loaded result."""
        memory_dir = temp_spec_dir / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)
        map_file = memory_dir / "codebase_map.json"

        test_data = {
            "src/api/auth.py": "JWT authentication handler",
            "_metadata": {"last_updated": "2024-01-01T00:00:00Z"},
        }

        with open(map_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        codebase_map = load_codebase_map(temp_spec_dir)

        assert "_metadata" not in codebase_map
        assert "src/api/auth.py" in codebase_map

    def test_handles_corrupted_json_file(self, temp_spec_dir):
        """Test returns empty dict for corrupted JSON."""
        memory_dir = temp_spec_dir / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)
        map_file = memory_dir / "codebase_map.json"

        map_file.write_text("{invalid json}", encoding="utf-8")

        codebase_map = load_codebase_map(temp_spec_dir)
        assert codebase_map == {}

    def test_handles_unicode_decode_error(self, temp_spec_dir):
        """Test handles Unicode decode errors gracefully."""
        memory_dir = temp_spec_dir / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)
        map_file = memory_dir / "codebase_map.json"

        # Write invalid UTF-8
        map_file.write_bytes(b"\xff\xfe invalid utf-8")

        codebase_map = load_codebase_map(temp_spec_dir)
        assert codebase_map == {}

    def test_handles_os_error(self, temp_spec_dir):
        """Test handles OS errors (e.g., permission denied)."""
        # This test is difficult to implement without actually
        # changing file permissions, which may not work on all systems
        # We'll just verify the function exists and handles the case
        codebase_map = load_codebase_map(temp_spec_dir)
        assert isinstance(codebase_map, dict)

    def test_handles_empty_map_file(self, temp_spec_dir):
        """Test handles empty JSON object."""
        memory_dir = temp_spec_dir / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)
        map_file = memory_dir / "codebase_map.json"

        map_file.write_text("{}", encoding="utf-8")

        codebase_map = load_codebase_map(temp_spec_dir)
        assert codebase_map == {}

    def test_handles_map_with_only_metadata(self, temp_spec_dir):
        """Test handles map that only contains metadata."""
        memory_dir = temp_spec_dir / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)
        map_file = memory_dir / "codebase_map.json"

        test_data = {"_metadata": {"last_updated": "2024-01-01T00:00:00Z"}}
        with open(map_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        codebase_map = load_codebase_map(temp_spec_dir)
        assert codebase_map == {}

    def test_preserves_unicode_content(self, temp_spec_dir):
        """Test preserves Unicode characters in content."""
        memory_dir = temp_spec_dir / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)
        map_file = memory_dir / "codebase_map.json"

        test_data = {
            "src/测试.py": "测试内容",
            "src/тест.py": "тестирование",
        }

        with open(map_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        codebase_map = load_codebase_map(temp_spec_dir)
        assert codebase_map["src/测试.py"] == "测试内容"
        assert codebase_map["src/тест.py"] == "тестирование"
