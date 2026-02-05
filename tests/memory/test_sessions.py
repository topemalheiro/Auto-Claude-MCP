"""
Tests for sessions module.
Comprehensive test coverage for session insights functions.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from memory.sessions import (
    save_session_insights,
    load_all_insights,
)


class TestSaveSessionInsights:
    """Tests for save_session_insights function."""

    def test_creates_session_file(self, temp_spec_dir, sample_insights):
        """Test creates session file with correct format."""
        save_session_insights(temp_spec_dir, 1, sample_insights)

        session_file = temp_spec_dir / "memory" / "session_insights" / "session_001.json"
        assert session_file.exists()

        with open(session_file, encoding="utf-8") as f:
            data = json.load(f)

        assert data["session_number"] == 1
        assert "timestamp" in data
        assert data["subtasks_completed"] == ["subtask-1", "subtask-2"]

    def test_adds_timestamp_to_session(self, temp_spec_dir, sample_insights):
        """Test adds timestamp to session data."""
        save_session_insights(temp_spec_dir, 1, sample_insights)

        session_file = temp_spec_dir / "memory" / "session_insights" / "session_001.json"
        with open(session_file, encoding="utf-8") as f:
            data = json.load(f)

        assert "timestamp" in data
        # Verify it's a valid ISO format timestamp
        assert "T" in data["timestamp"]
        assert "Z" in data["timestamp"] or "+" in data["timestamp"]

    def test_handles_missing_optional_fields(self, temp_spec_dir):
        """Test handles insights with missing optional fields."""
        minimal_insights = {
            "subtasks_completed": ["task-1"],
        }

        save_session_insights(temp_spec_dir, 1, minimal_insights)

        session_file = temp_spec_dir / "memory" / "session_insights" / "session_001.json"
        with open(session_file, encoding="utf-8") as f:
            data = json.load(f)

        assert data["subtasks_completed"] == ["task-1"]
        assert data["discoveries"] == {
            "files_understood": {},
            "patterns_found": [],
            "gotchas_encountered": [],
        }
        assert data["what_worked"] == []
        assert data["what_failed"] == []
        assert data["recommendations_for_next_session"] == []

    def test_saves_multiple_sessions(self, temp_spec_dir, sample_insights):
        """Test saving multiple sessions."""
        save_session_insights(temp_spec_dir, 1, sample_insights)
        save_session_insights(temp_spec_dir, 2, sample_insights)
        save_session_insights(temp_spec_dir, 3, sample_insights)

        insights_dir = temp_spec_dir / "memory" / "session_insights"
        session_files = sorted(insights_dir.glob("session_*.json"))

        assert len(session_files) == 3
        assert session_files[0].name == "session_001.json"
        assert session_files[1].name == "session_002.json"
        assert session_files[2].name == "session_003.json"

    def test_overwrites_existing_session(self, temp_spec_dir, sample_insights):
        """Test overwrites existing session file."""
        # Save initial session
        initial_insights = {"subtasks_completed": ["task-1"]}
        save_session_insights(temp_spec_dir, 1, initial_insights)

        # Overwrite with different data
        updated_insights = {"subtasks_completed": ["task-2", "task-3"]}
        save_session_insights(temp_spec_dir, 1, updated_insights)

        # Load and verify
        session_file = temp_spec_dir / "memory" / "session_insights" / "session_001.json"
        with open(session_file, encoding="utf-8") as f:
            data = json.load(f)

        assert data["subtasks_completed"] == ["task-2", "task-3"]

    def test_saves_to_graphiti_when_enabled(self, temp_spec_dir, sample_insights):
        """Test saves to Graphiti when enabled."""
        with patch(
            "memory.sessions.is_graphiti_memory_enabled", return_value=True
        ), patch("memory.sessions.save_to_graphiti_async", return_value=True) as mock_save:
            import asyncio

            mock_save.return_value = asyncio.sleep(0, result=True)

            save_session_insights(temp_spec_dir, 1, sample_insights)

            # Verify file was still created
            session_file = temp_spec_dir / "memory" / "session_insights" / "session_001.json"
            assert session_file.exists()

    def test_handles_graphiti_save_failure_gracefully(
        self, temp_spec_dir, sample_insights
    ):
        """Test continues if Graphiti save fails."""
        with patch(
            "memory.sessions.is_graphiti_memory_enabled", return_value=True
        ), patch("memory.sessions.run_async", side_effect=Exception("Graphiti failed")):
            # Should not raise exception
            save_session_insights(temp_spec_dir, 1, sample_insights)

            # File should still be created
            session_file = temp_spec_dir / "memory" / "session_insights" / "session_001.json"
            assert session_file.exists()

    def test_zero_pads_session_number(self, temp_spec_dir, sample_insights):
        """Test zero-pads session number in filename."""
        save_session_insights(temp_spec_dir, 1, sample_insights)
        save_session_insights(temp_spec_dir, 10, sample_insights)
        save_session_insights(temp_spec_dir, 100, sample_insights)

        insights_dir = temp_spec_dir / "memory" / "session_insights"
        files = [f.name for f in sorted(insights_dir.glob("session_*.json"))]

        assert "session_001.json" in files
        assert "session_010.json" in files
        assert "session_100.json" in files

    def test_preserves_unicode_content(self, temp_spec_dir):
        """Test handles Unicode characters in insights."""
        unicode_insights = {
            "subtasks_completed": ["任务-1"],
            "what_worked": ["成功的方法"],
            "what_failed": ["失败的方法"],
            "discoveries": {
                "files_understood": {
                    "src/测试.py": "测试文件",
                },
                "patterns_found": ["模式"],
                "gotchas_encountered": ["陷阱"],
            },
        }

        save_session_insights(temp_spec_dir, 1, unicode_insights)

        session_file = temp_spec_dir / "memory" / "session_insights" / "session_001.json"
        with open(session_file, encoding="utf-8") as f:
            data = json.load(f)

        assert data["what_worked"][0] == "成功的方法"
        assert data["discoveries"]["files_understood"]["src/测试.py"] == "测试文件"


class TestLoadAllInsights:
    """Tests for load_all_insights function."""

    def test_returns_empty_list_when_no_sessions(self, temp_spec_dir):
        """Test returns empty list when no session files exist."""
        insights = load_all_insights(temp_spec_dir)
        assert insights == []

    def test_loads_single_session(self, temp_spec_dir):
        """Test loads a single session."""
        # Create session file
        insights_dir = temp_spec_dir / "memory" / "session_insights"
        insights_dir.mkdir(parents=True, exist_ok=True)

        session_data = {
            "session_number": 1,
            "timestamp": "2024-01-01T00:00:00Z",
            "subtasks_completed": ["task-1"],
            "discoveries": {
                "files_understood": {},
                "patterns_found": [],
                "gotchas_encountered": [],
            },
            "what_worked": [],
            "what_failed": [],
            "recommendations_for_next_session": [],
        }

        session_file = insights_dir / "session_001.json"
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(session_data, f)

        # Load
        insights = load_all_insights(temp_spec_dir)

        assert len(insights) == 1
        assert insights[0]["session_number"] == 1

    def test_loads_multiple_sessions_in_order(self, temp_spec_dir):
        """Test loads multiple sessions in numerical order."""
        insights_dir = temp_spec_dir / "memory" / "session_insights"
        insights_dir.mkdir(parents=True, exist_ok=True)

        # Create sessions out of order
        for num in [3, 1, 2]:
            session_data = {
                "session_number": num,
                "timestamp": f"2024-01-0{num}T00:00:00Z",
                "subtasks_completed": [f"task-{num}"],
                "discoveries": {
                    "files_understood": {},
                    "patterns_found": [],
                    "gotchas_encountered": [],
                },
                "what_worked": [],
                "what_failed": [],
                "recommendations_for_next_session": [],
            }

            session_file = insights_dir / f"session_{num:03d}.json"
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(session_data, f)

        # Load
        insights = load_all_insights(temp_spec_dir)

        assert len(insights) == 3
        assert insights[0]["session_number"] == 1
        assert insights[1]["session_number"] == 2
        assert insights[2]["session_number"] == 3

    def test_skips_corrupted_session_files(self, temp_spec_dir):
        """Test skips corrupted session files."""
        insights_dir = temp_spec_dir / "memory" / "session_insights"
        insights_dir.mkdir(parents=True, exist_ok=True)

        # Valid session
        valid_session = {
            "session_number": 1,
            "timestamp": "2024-01-01T00:00:00Z",
            "subtasks_completed": [],
            "discoveries": {
                "files_understood": {},
                "patterns_found": [],
                "gotchas_encountered": [],
            },
            "what_worked": [],
            "what_failed": [],
            "recommendations_for_next_session": [],
        }

        with open(insights_dir / "session_001.json", "w", encoding="utf-8") as f:
            json.dump(valid_session, f)

        # Corrupted session
        with open(insights_dir / "session_002.json", "w", encoding="utf-8") as f:
            f.write("{invalid json")

        # Another valid session
        with open(insights_dir / "session_003.json", "w", encoding="utf-8") as f:
            json.dump({**valid_session, "session_number": 3}, f)

        # Load - should only return valid sessions
        insights = load_all_insights(temp_spec_dir)

        assert len(insights) == 2
        assert insights[0]["session_number"] == 1
        assert insights[1]["session_number"] == 3

    def test_handles_empty_session_insights_dir(self, temp_spec_dir):
        """Test handles empty session_insights directory."""
        insights_dir = temp_spec_dir / "memory" / "session_insights"
        insights_dir.mkdir(parents=True, exist_ok=True)

        insights = load_all_insights(temp_spec_dir)
        assert insights == []

    def test_handles_nonexistent_insights_dir(self, temp_spec_dir):
        """Test handles when session_insights directory doesn't exist."""
        # Don't create the directory
        insights = load_all_insights(temp_spec_dir)
        assert insights == []

    def test_skips_non_session_files(self, temp_spec_dir):
        """Test ignores non-session JSON files in the directory."""
        insights_dir = temp_spec_dir / "memory" / "session_insights"
        insights_dir.mkdir(parents=True, exist_ok=True)

        # Valid session
        valid_session = {
            "session_number": 1,
            "timestamp": "2024-01-01T00:00:00Z",
            "subtasks_completed": [],
            "discoveries": {
                "files_understood": {},
                "patterns_found": [],
                "gotchas_encountered": [],
            },
            "what_worked": [],
            "what_failed": [],
            "recommendations_for_next_session": [],
        }

        with open(insights_dir / "session_001.json", "w", encoding="utf-8") as f:
            json.dump(valid_session, f)

        # Other files that should be ignored
        with open(insights_dir / "other.json", "w") as f:
            json.dump({"not": "a session"}, f)

        with open(insights_dir / "notes.txt", "w") as f:
            f.write("Just notes")

        # Load - should only return session files
        insights = load_all_insights(temp_spec_dir)

        assert len(insights) == 1
        assert insights[0]["session_number"] == 1

    def test_handles_unicode_decode_errors(self, temp_spec_dir):
        """Test handles files with encoding issues."""
        insights_dir = temp_spec_dir / "memory" / "session_insights"
        insights_dir.mkdir(parents=True, exist_ok=True)

        # Valid session
        valid_session = {
            "session_number": 1,
            "timestamp": "2024-01-01T00:00:00Z",
            "subtasks_completed": [],
            "discoveries": {
                "files_understood": {},
                "patterns_found": [],
                "gotchas_encountered": [],
            },
            "what_worked": [],
            "what_failed": [],
            "recommendations_for_next_session": [],
        }

        with open(insights_dir / "session_001.json", "w", encoding="utf-8") as f:
            json.dump(valid_session, f)

        # File with invalid encoding
        with open(insights_dir / "session_002.json", "wb") as f:
            f.write(b"\xff\xfe invalid utf-8")

        # Load - should skip the corrupted file
        insights = load_all_insights(temp_spec_dir)

        assert len(insights) == 1
        assert insights[0]["session_number"] == 1

    def test_preserves_session_data(self, temp_spec_dir):
        """Test preserves all session data when loading."""
        insights_dir = temp_spec_dir / "memory" / "session_insights"
        insights_dir.mkdir(parents=True, exist_ok=True)

        session_data = {
            "session_number": 1,
            "timestamp": "2024-01-01T00:00:00Z",
            "subtasks_completed": ["task-1", "task-2"],
            "discoveries": {
                "files_understood": {"src/auth.py": "Auth handler"},
                "patterns_found": ["Use async"],
                "gotchas_encountered": ["Close connections"],
            },
            "what_worked": ["Approach A"],
            "what_failed": ["Approach B"],
            "recommendations_for_next_session": ["Try C"],
        }

        with open(insights_dir / "session_001.json", "w", encoding="utf-8") as f:
            json.dump(session_data, f)

        insights = load_all_insights(temp_spec_dir)

        assert len(insights) == 1
        loaded = insights[0]
        assert loaded["session_number"] == 1
        assert loaded["subtasks_completed"] == ["task-1", "task-2"]
        assert loaded["discoveries"]["files_understood"]["src/auth.py"] == "Auth handler"
        assert loaded["what_worked"] == ["Approach A"]
        assert loaded["what_failed"] == ["Approach B"]
        assert loaded["recommendations_for_next_session"] == ["Try C"]
