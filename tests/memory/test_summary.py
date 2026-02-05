"""
Tests for summary module.
Comprehensive test coverage for memory summary functions.
"""

import json
from pathlib import Path
from unittest.mock import patch
import pytest

from memory.summary import get_memory_summary
from memory.patterns import append_pattern, append_gotcha
from memory.codebase_map import update_codebase_map
from memory.sessions import save_session_insights


class TestGetMemorySummary:
    """Tests for get_memory_summary function."""

    def test_returns_empty_summary_for_new_spec(self, temp_spec_dir):
        """Test returns empty summary when no memory data exists."""
        summary = get_memory_summary(temp_spec_dir)

        assert summary["total_sessions"] == 0
        assert summary["total_files_mapped"] == 0
        assert summary["total_patterns"] == 0
        assert summary["total_gotchas"] == 0
        assert summary["recent_insights"] == []

    def test_counts_sessions(self, temp_spec_dir):
        """Test counts session files correctly."""
        # Create sessions
        for i in range(1, 4):
            save_session_insights(
                temp_spec_dir,
                i,
                {
                    "subtasks_completed": [f"task-{i}"],
                    "discoveries": {
                        "files_understood": {},
                        "patterns_found": [],
                        "gotchas_encountered": [],
                    },
                },
            )

        summary = get_memory_summary(temp_spec_dir)

        assert summary["total_sessions"] == 3

    def test_counts_codebase_map_entries(self, temp_spec_dir):
        """Test counts files in codebase map."""
        discoveries = {
            "src/api/auth.py": "JWT authentication",
            "src/models/user.py": "User model",
            "src/utils/helpers.py": "Utility functions",
        }
        update_codebase_map(temp_spec_dir, discoveries)

        summary = get_memory_summary(temp_spec_dir)

        assert summary["total_files_mapped"] == 3

    def test_counts_patterns(self, temp_spec_dir):
        """Test counts code patterns."""
        append_pattern(temp_spec_dir, "Pattern 1")
        append_pattern(temp_spec_dir, "Pattern 2")
        append_pattern(temp_spec_dir, "Pattern 3")

        summary = get_memory_summary(temp_spec_dir)

        assert summary["total_patterns"] == 3

    def test_counts_gotchas(self, temp_spec_dir):
        """Test counts gotchas."""
        append_gotcha(temp_spec_dir, "Gotcha 1")
        append_gotcha(temp_spec_dir, "Gotcha 2")

        summary = get_memory_summary(temp_spec_dir)

        assert summary["total_gotchas"] == 2

    def test_returns_recent_insights_less_than_three(self, temp_spec_dir):
        """Test returns all insights when less than 3 sessions."""
        # Create 2 sessions
        for i in range(1, 3):
            save_session_insights(
                temp_spec_dir,
                i,
                {
                    "subtasks_completed": [f"task-{i}"],
                    "discoveries": {
                        "files_understood": {},
                        "patterns_found": [],
                        "gotchas_encountered": [],
                    },
                },
            )

        summary = get_memory_summary(temp_spec_dir)

        assert len(summary["recent_insights"]) == 2
        assert summary["recent_insights"][0]["session_number"] == 1
        assert summary["recent_insights"][1]["session_number"] == 2

    def test_returns_last_three_insights_when_more_than_three(
        self, temp_spec_dir
    ):
        """Test returns only last 3 insights when more sessions exist."""
        # Create 5 sessions
        for i in range(1, 6):
            save_session_insights(
                temp_spec_dir,
                i,
                {
                    "subtasks_completed": [f"task-{i}"],
                    "discoveries": {
                        "files_understood": {},
                        "patterns_found": [],
                        "gotchas_encountered": [],
                    },
                },
            )

        summary = get_memory_summary(temp_spec_dir)

        assert summary["total_sessions"] == 5
        assert len(summary["recent_insights"]) == 3
        # Should return sessions 3, 4, 5 (the last 3)
        assert summary["recent_insights"][0]["session_number"] == 3
        assert summary["recent_insights"][1]["session_number"] == 4
        assert summary["recent_insights"][2]["session_number"] == 5

    def test_aggregates_all_counts(self, temp_spec_dir):
        """Test correctly aggregates all memory types."""
        # Add sessions
        save_session_insights(
            temp_spec_dir,
            1,
            {
                "subtasks_completed": ["task-1"],
                "discoveries": {
                    "files_understood": {},
                    "patterns_found": [],
                    "gotchas_encountered": [],
                },
            },
        )
        save_session_insights(
            temp_spec_dir,
            2,
            {
                "subtasks_completed": ["task-2"],
                "discoveries": {
                    "files_understood": {},
                    "patterns_found": [],
                    "gotchas_encountered": [],
                },
            },
        )

        # Add codebase map
        update_codebase_map(
            temp_spec_dir,
            {"src/api/auth.py": "Auth", "src/models/user.py": "User"},
        )

        # Add patterns
        append_pattern(temp_spec_dir, "Pattern 1")
        append_pattern(temp_spec_dir, "Pattern 2")

        # Add gotchas
        append_gotcha(temp_spec_dir, "Gotcha 1")
        append_gotcha(temp_spec_dir, "Gotcha 2")
        append_gotcha(temp_spec_dir, "Gotcha 3")

        summary = get_memory_summary(temp_spec_dir)

        assert summary["total_sessions"] == 2
        assert summary["total_files_mapped"] == 2
        assert summary["total_patterns"] == 2
        assert summary["total_gotchas"] == 3

    def test_excludes_metadata_from_file_count(self, temp_spec_dir):
        """Test excludes _metadata from codebase map file count."""
        discoveries = {
            "src/api/auth.py": "Auth",
            "src/models/user.py": "User",
        }
        update_codebase_map(temp_spec_dir, discoveries)

        # The metadata is added automatically
        map_file = temp_spec_dir / "memory" / "codebase_map.json"
        with open(map_file) as f:
            data = json.load(f)

        assert "_metadata" in data  # Metadata exists
        assert len([k for k in data.keys() if k != "_metadata"]) == 2  # 2 files

        summary = get_memory_summary(temp_spec_dir)
        assert summary["total_files_mapped"] == 2  # Should not count metadata

    def test_handles_deduplication_in_counts(self, temp_spec_dir):
        """Test counts are accurate even with duplicate adds."""
        # Add same pattern twice
        append_pattern(temp_spec_dir, "Same pattern")
        append_pattern(temp_spec_dir, "Same pattern")

        # Add same gotcha twice
        append_gotcha(temp_spec_dir, "Same gotcha")
        append_gotcha(temp_spec_dir, "Same gotcha")

        summary = get_memory_summary(temp_spec_dir)

        # Should only count unique entries (deduplication)
        assert summary["total_patterns"] == 1
        assert summary["total_gotchas"] == 1

    def test_returns_summary_with_correct_structure(self, temp_spec_dir):
        """Test summary has correct structure and types."""
        summary = get_memory_summary(temp_spec_dir)

        assert isinstance(summary, dict)
        assert "total_sessions" in summary
        assert "total_files_mapped" in summary
        assert "total_patterns" in summary
        assert "total_gotchas" in summary
        assert "recent_insights" in summary

        assert isinstance(summary["total_sessions"], int)
        assert isinstance(summary["total_files_mapped"], int)
        assert isinstance(summary["total_patterns"], int)
        assert isinstance(summary["total_gotchas"], int)
        assert isinstance(summary["recent_insights"], list)

    def test_recent_insights_preserves_session_data(self, temp_spec_dir):
        """Test recent insights include all session data."""
        save_session_insights(
            temp_spec_dir,
            1,
            {
                "subtasks_completed": ["task-1", "task-2"],
                "discoveries": {
                    "files_understood": {},
                    "patterns_found": [],
                    "gotchas_encountered": [],
                },
                "what_worked": ["Approach A"],
                "what_failed": [],
                "recommendations_for_next_session": [],
            },
        )

        summary = get_memory_summary(temp_spec_dir)

        assert len(summary["recent_insights"]) == 1
        insight = summary["recent_insights"][0]
        assert insight["session_number"] == 1
        assert insight["subtasks_completed"] == ["task-1", "task-2"]
        assert "timestamp" in insight
        assert insight["what_worked"] == ["Approach A"]
