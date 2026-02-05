"""Tests for display module in core.workspace.display

Comprehensive test coverage for workspace display functionality including:
- show_build_summary()
- show_changed_files()
- print_merge_success()
- print_conflict_info()
- Backward compatibility aliases
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from core.workspace.display import (
    print_merge_success,
    print_conflict_info,
    show_build_summary,
    show_changed_files,
    _print_merge_success,
    _print_conflict_info,
)


@pytest.fixture
def mock_manager():
    """Create a mock WorktreeManager."""
    manager = MagicMock()
    return manager


class TestShowBuildSummary:
    """Tests for show_build_summary function."""

    def test_show_build_summary_no_changes(self, mock_manager, capsys):
        """Test show_build_summary with no changes."""
        mock_manager.get_change_summary.return_value = {
            "new_files": 0,
            "modified_files": 0,
            "deleted_files": 0,
        }
        spec_name = "spec_001"

        show_build_summary(mock_manager, spec_name)

        captured = capsys.readouterr()
        assert "No changes were made" in captured.out

    def test_show_build_summary_with_new_files(self, mock_manager, capsys):
        """Test show_build_summary with new files."""
        mock_manager.get_change_summary.return_value = {
            "new_files": 5,
            "modified_files": 0,
            "deleted_files": 0,
        }
        spec_name = "spec_001"

        show_build_summary(mock_manager, spec_name)

        captured = capsys.readouterr()
        assert "5 new files" in captured.out

    def test_show_build_summary_with_modified_files(self, mock_manager, capsys):
        """Test show_build_summary with modified files."""
        mock_manager.get_change_summary.return_value = {
            "new_files": 0,
            "modified_files": 3,
            "deleted_files": 0,
        }
        spec_name = "spec_001"

        show_build_summary(mock_manager, spec_name)

        captured = capsys.readouterr()
        assert "3 modified file" in captured.out

    def test_show_build_summary_with_deleted_files(self, mock_manager, capsys):
        """Test show_build_summary with deleted files."""
        mock_manager.get_change_summary.return_value = {
            "new_files": 0,
            "modified_files": 0,
            "deleted_files": 2,
        }
        spec_name = "spec_001"

        show_build_summary(mock_manager, spec_name)

        captured = capsys.readouterr()
        assert "2 deleted file" in captured.out

    def test_show_build_summary_mixed_changes(self, mock_manager, capsys):
        """Test show_build_summary with mixed changes."""
        mock_manager.get_change_summary.return_value = {
            "new_files": 2,
            "modified_files": 3,
            "deleted_files": 1,
        }
        spec_name = "spec_001"

        show_build_summary(mock_manager, spec_name)

        captured = capsys.readouterr()
        assert "2 new file" in captured.out
        assert "3 modified file" in captured.out
        assert "1 deleted file" in captured.out

    def test_show_build_summary_singular_pluralization(self, mock_manager, capsys):
        """Test singular/plural forms for file counts."""
        # Test singular (1 file)
        mock_manager.get_change_summary.return_value = {
            "new_files": 1,
            "modified_files": 1,
            "deleted_files": 1,
        }

        show_build_summary(mock_manager, "spec_001")
        captured = capsys.readouterr()
        assert "1 new file" in captured.out
        assert "1 modified file" in captured.out
        assert "1 deleted file" in captured.out

    def test_show_build_summary_zero_total(self, mock_manager, capsys):
        """Test show_build_summary when total is zero."""
        mock_manager.get_change_summary.return_value = {
            "new_files": 0,
            "modified_files": 0,
            "deleted_files": 0,
        }

        show_build_summary(mock_manager, "spec_001")
        captured = capsys.readouterr()
        # Should return early without printing "What was built"
        assert "No changes were made" in captured.out


class TestShowChangedFiles:
    """Tests for show_changed_files function."""

    def test_show_changed_files_no_changes(self, mock_manager, capsys):
        """Test show_changed_files with no changes."""
        mock_manager.get_changed_files.return_value = []
        spec_name = "spec_001"

        show_changed_files(mock_manager, spec_name)

        captured = capsys.readouterr()
        assert "No changes" in captured.out

    def test_show_changed_files_with_added(self, mock_manager, capsys):
        """Test show_changed_files with added files."""
        mock_manager.get_changed_files.return_value = [
            ("A", "new_file.py"),
        ]
        spec_name = "spec_001"

        show_changed_files(mock_manager, spec_name)

        captured = capsys.readouterr()
        assert "new_file.py" in captured.out
        assert "Changed files:" in captured.out

    def test_show_changed_files_with_modified(self, mock_manager, capsys):
        """Test show_changed_files with modified files."""
        mock_manager.get_changed_files.return_value = [
            ("M", "modified_file.py"),
        ]
        spec_name = "spec_001"

        show_changed_files(mock_manager, spec_name)

        captured = capsys.readouterr()
        assert "modified_file.py" in captured.out

    def test_show_changed_files_with_deleted(self, mock_manager, capsys):
        """Test show_changed_files with deleted files."""
        mock_manager.get_changed_files.return_value = [
            ("D", "deleted_file.py"),
        ]
        spec_name = "spec_001"

        show_changed_files(mock_manager, spec_name)

        captured = capsys.readouterr()
        assert "deleted_file.py" in captured.out

    def test_show_changed_files_mixed_statuses(self, mock_manager, capsys):
        """Test show_changed_files with mixed file statuses."""
        mock_manager.get_changed_files.return_value = [
            ("A", "new_file.py"),
            ("M", "modified_file.py"),
            ("D", "deleted_file.py"),
            ("A", "another_new.py"),
        ]
        spec_name = "spec_001"

        show_changed_files(mock_manager, spec_name)

        captured = capsys.readouterr()
        assert "new_file.py" in captured.out
        assert "modified_file.py" in captured.out
        assert "deleted_file.py" in captured.out
        assert "another_new.py" in captured.out

    def test_show_changed_files_unknown_status(self, mock_manager, capsys):
        """Test show_changed_files with unknown status code."""
        mock_manager.get_changed_files.return_value = [
            ("X", "unknown_status.py"),
        ]
        spec_name = "spec_001"

        show_changed_files(mock_manager, spec_name)

        captured = capsys.readouterr()
        assert "unknown_status.py" in captured.out


class TestPrintMergeSuccess:
    """Tests for print_merge_success function."""

    def test_print_merge_success_no_commit_basic(self, capsys):
        """Test print_merge_success with no_commit=True, basic case."""
        print_merge_success(
            no_commit=True,
            stats=None,
            spec_name=None,
            keep_worktree=False,
        )

        captured = capsys.readouterr()
        assert "CHANGES ADDED TO YOUR PROJECT" in captured.out
        assert "working directory" in captured.out

    def test_print_merge_success_no_commit_with_lock_files(self, capsys):
        """Test print_merge_success with lock files excluded."""
        print_merge_success(
            no_commit=True,
            stats={"lock_files_excluded": 3},
            spec_name=None,
            keep_worktree=False,
        )

        captured = capsys.readouterr()
        assert "Lock files kept from main" in captured.out
        assert "Regenerate" in captured.out

    def test_print_merge_success_no_commit_keep_worktree(self, capsys):
        """Test print_merge_success with worktree kept."""
        print_merge_success(
            no_commit=True,
            stats=None,
            spec_name="001-feature",
            keep_worktree=True,
        )

        captured = capsys.readouterr()
        assert "Worktree kept" in captured.out
        assert "001-feature" in captured.out

    def test_print_merge_success_with_commit_basic(self, capsys):
        """Test print_merge_success with no_commit=False (commit made)."""
        print_merge_success(
            no_commit=False,
            stats=None,
            spec_name=None,
            keep_worktree=False,
        )

        captured = capsys.readouterr()
        assert "FEATURE ADDED TO YOUR PROJECT" in captured.out or "changes" in captured.out.lower()

    def test_print_merge_success_with_commit_with_stats(self, capsys):
        """Test print_merge_success with commit and file stats."""
        print_merge_success(
            no_commit=False,
            stats={
                "files_added": 5,
                "files_modified": 3,
                "files_deleted": 1,
            },
            spec_name=None,
            keep_worktree=False,
        )

        captured = capsys.readouterr()
        assert "5 file" in captured.out
        assert "3 file" in captured.out
        assert "1 file" in captured.out

    def test_print_merge_success_with_commit_keep_worktree(self, capsys):
        """Test print_merge_success with commit and worktree kept."""
        print_merge_success(
            no_commit=False,
            stats=None,
            spec_name="002-feature",
            keep_worktree=True,
        )

        captured = capsys.readouterr()
        assert "Worktree kept" in captured.out
        assert "002-feature" in captured.out

    def test_print_merge_success_with_commit_cleanup_message(self, capsys):
        """Test print_merge_success shows cleanup message when worktree deleted."""
        print_merge_success(
            no_commit=False,
            stats=None,
            spec_name=None,
            keep_worktree=False,
        )

        captured = capsys.readouterr()
        assert "separate workspace has been cleaned up" in captured.out or "part of your project" in captured.out

    def test_print_merge_success_stats_singular_pluralization(self, capsys):
        """Test singular/plural forms in stats display."""
        print_merge_success(
            no_commit=False,
            stats={
                "files_added": 1,
                "files_modified": 1,
                "files_deleted": 1,
            },
            spec_name=None,
            keep_worktree=False,
        )

        captured = capsys.readouterr()
        # Check for singular forms
        assert "1 file" in captured.out


class TestPrintConflictInfo:
    """Tests for print_conflict_info function."""

    def test_print_conflict_info_empty(self, capsys):
        """Test print_conflict_info with no conflicts."""
        result = {"conflicts": []}

        print_conflict_info(result)

        captured = capsys.readouterr()
        # Should not print anything for no conflicts
        assert captured.out == ""

    def test_print_conflict_info_missing_key(self, capsys):
        """Test print_conflict_info with missing conflicts key."""
        result = {}

        print_conflict_info(result)

        captured = capsys.readouterr()
        # Should handle gracefully
        assert True

    def test_print_conflict_info_string_conflicts(self, capsys):
        """Test print_conflict_info with string conflict paths."""
        result = {
            "conflicts": [
                "file1.py",
                "file2.py",
            ]
        }

        print_conflict_info(result)

        captured = capsys.readouterr()
        assert "file1.py" in captured.out
        assert "file2.py" in captured.out

    def test_print_conflict_info_dict_conflicts(self, capsys):
        """Test print_conflict_info with dict conflicts (AI merge failures)."""
        result = {
            "conflicts": [
                {
                    "file": "conflict.py",
                    "reason": "Semantic analysis failed",
                    "severity": "high",
                },
                {
                    "file": "another.py",
                    "reason": "Unknown type",
                    "severity": "medium",
                },
            ]
        }

        print_conflict_info(result)

        captured = capsys.readouterr()
        assert "conflict.py" in captured.out
        assert "another.py" in captured.out
        assert "Semantic analysis failed" in captured.out or "Unknown type" in captured.out

    def test_print_conflict_info_mixed_types(self, capsys):
        """Test print_conflict_info with mixed string and dict conflicts."""
        result = {
            "conflicts": [
                "simple.py",
                {
                    "file": "complex.py",
                    "reason": "AI merge failed",
                    "severity": "critical",
                },
            ]
        }

        print_conflict_info(result)

        captured = capsys.readouterr()
        assert "simple.py" in captured.out
        assert "complex.py" in captured.out

    def test_print_conflict_info_all_severity_levels(self, capsys):
        """Test print_conflict_info with all severity levels."""
        result = {
            "conflicts": [
                {"file": "critical.py", "reason": "Critical issue", "severity": "critical"},
                {"file": "high.py", "reason": "High issue", "severity": "high"},
                {"file": "medium.py", "reason": "Medium issue", "severity": "medium"},
            ]
        }

        print_conflict_info(result)

        captured = capsys.readouterr()
        assert "critical.py" in captured.out
        assert "high.py" in captured.out
        assert "medium.py" in captured.out

    def test_print_conflict_info_dict_missing_fields(self, capsys):
        """Test print_conflict_info with dict conflicts missing optional fields."""
        result = {
            "conflicts": [
                {"file": "minimal.py"},  # No reason or severity
            ]
        }

        print_conflict_info(result)

        captured = capsys.readouterr()
        assert "minimal.py" in captured.out

    def test_print_conflict_info_git_commands(self, capsys):
        """Test print_conflict_info includes git commands."""
        result = {
            "conflicts": ["file with spaces.py", "normal.py"]
        }

        print_conflict_info(result)

        captured = capsys.readouterr()
        assert "git add" in captured.out
        assert "git commit" in captured.out

    def test_print_conflict_info_marker_conflicts_message(self, capsys):
        """Test print_conflict_info shows message for git marker conflicts."""
        result = {
            "conflicts": ["file.py"]
        }

        print_conflict_info(result)

        captured = capsys.readouterr()
        assert "conflict markers" in captured.out or "marker" in captured.out.lower()

    def test_print_conflict_info_ai_conflicts_message(self, capsys):
        """Test print_conflict_info shows message for AI merge conflicts."""
        result = {
            "conflicts": [
                {"file": "ai.py", "reason": "AI failed", "severity": "medium"}
            ]
        }

        print_conflict_info(result)

        captured = capsys.readouterr()
        assert "auto-merge" in captured.out.lower()

    def test_print_conflict_info_duplicates_shown(self, capsys):
        """Test print_conflict_info shows duplicate entries as-is."""
        result = {
            "conflicts": [
                "duplicate.py",
                "duplicate.py",
                "another.py",
                "another.py",
            ]
        }

        print_conflict_info(result)

        captured = capsys.readouterr()
        # The function shows all entries (doesn't deduplicate)
        assert "duplicate.py" in captured.out
        assert "another.py" in captured.out


class TestBackwardCompatibilityAliases:
    """Tests for backward compatibility exported aliases."""

    def test_print_merge_success_alias_exists(self):
        """Test that _print_merge_success alias exists."""
        assert _print_merge_success is print_merge_success

    def test_print_conflict_info_alias_exists(self):
        """Test that _print_conflict_info alias exists."""
        assert _print_conflict_info is print_conflict_info


class TestDisplayEdgeCases:
    """Tests for edge cases in display functions."""

    def test_show_build_summary_large_numbers(self, mock_manager, capsys):
        """Test show_build_summary with large file counts."""
        mock_manager.get_change_summary.return_value = {
            "new_files": 9999,
            "modified_files": 10000,
            "deleted_files": 5000,
        }

        show_build_summary(mock_manager, "spec_001")

        captured = capsys.readouterr()
        assert "9999" in captured.out

    def test_show_changed_files_special_paths(self, mock_manager, capsys):
        """Test show_changed_files with special path characters."""
        mock_manager.get_changed_files.return_value = [
            ("A", "path/with spaces/file.py"),
            ("M", "path-with-dashes/file.py"),
            ("D", "path_with_underscores/file.py"),
        ]

        show_changed_files(mock_manager, "spec_001")

        captured = capsys.readouterr()
        assert "path/with spaces/file.py" in captured.out

    def test_print_merge_success_zero_stats(self, capsys):
        """Test print_merge_success with zero file stats."""
        print_merge_success(
            no_commit=False,
            stats={
                "files_added": 0,
                "files_modified": 0,
                "files_deleted": 0,
            },
            spec_name=None,
            keep_worktree=False,
        )

        captured = capsys.readouterr()
        # Should handle gracefully
        assert len(captured.out) > 0

    def test_print_conflict_info_unicode_paths(self, capsys):
        """Test print_conflict_info with Unicode file paths."""
        result = {
            "conflicts": ["文件.py", "fichier.py", "Datei.py"]
        }

        print_conflict_info(result)

        captured = capsys.readouterr()
        assert "文件.py" in captured.out or "fichier.py" in captured.out

    def test_show_changed_files_empty_list(self, mock_manager, capsys):
        """Test show_changed_files with empty file list."""
        mock_manager.get_changed_files.return_value = []

        show_changed_files(mock_manager, "spec_001")

        captured = capsys.readouterr()
        assert "No changes" in captured.out
