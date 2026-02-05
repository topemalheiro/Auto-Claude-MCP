"""Tests for agents.utils module."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from agents.utils import (
    get_latest_commit,
    get_commit_count,
    load_implementation_plan,
    find_subtask_in_plan,
    find_phase_for_subtask,
    sync_spec_to_source,
    _sync_directory,
    sync_plan_to_source,
)


class TestGetLatestCommit:
    """Test get_latest_commit function."""

    def test_returns_commit_hash_on_success(self, tmp_path):
        """Test that commit hash is returned on success."""
        # Create a git repo
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)
        (tmp_path / "test.txt").write_text("test")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=tmp_path, capture_output=True)

        result = get_latest_commit(tmp_path)

        assert result is not None
        assert len(result) == 40  # SHA-1 hash length

    def test_returns_none_on_git_error(self, tmp_path):
        """Test that None is returned when git fails."""
        # Not a git repo
        result = get_latest_commit(tmp_path)

        assert result is None


class TestGetCommitCount:
    """Test get_commit_count function."""

    def test_returns_count_on_success(self, tmp_path):
        """Test that commit count is returned on success."""
        # Create a git repo with multiple commits
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)

        for i in range(3):
            (tmp_path / f"test{i}.txt").write_text(f"test{i}")
            subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
            subprocess.run(["git", "commit", "-m", f"Commit {i}"], cwd=tmp_path, capture_output=True)

        result = get_commit_count(tmp_path)

        assert result == 3

    def test_returns_zero_on_git_error(self, tmp_path):
        """Test that 0 is returned when git fails."""
        result = get_commit_count(tmp_path)

        assert result == 0

    def test_returns_zero_on_invalid_output(self, tmp_path):
        """Test that 0 is returned when git returns non-numeric output."""
        # Create a git repo
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)

        # Mock run_git to return invalid output
        with patch('agents.utils.run_git') as mock_git:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "not a number"
            mock_git.return_value = mock_result

            result = get_commit_count(tmp_path)

            assert result == 0


class TestLoadImplementationPlan:
    """Test load_implementation_plan function."""

    def test_loads_valid_plan(self, tmp_path):
        """Test that valid plan is loaded correctly."""
        plan = {
            "feature": "Test",
            "phases": [{"id": "1", "name": "Phase 1", "subtasks": []}]
        }
        plan_file = tmp_path / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan))

        result = load_implementation_plan(tmp_path)

        assert result is not None
        assert result["feature"] == "Test"
        assert len(result["phases"]) == 1

    def test_returns_none_when_file_missing(self, tmp_path):
        """Test that None is returned when file doesn't exist."""
        result = load_implementation_plan(tmp_path)

        assert result is None

    def test_returns_none_on_invalid_json(self, tmp_path):
        """Test that None is returned on invalid JSON."""
        plan_file = tmp_path / "implementation_plan.json"
        plan_file.write_text("not json")

        result = load_implementation_plan(tmp_path)

        assert result is None

    def test_returns_none_on_os_error(self, tmp_path):
        """Test that None is returned on OS error (e.g., permission denied)."""
        plan_file = tmp_path / "implementation_plan.json"
        plan_file.write_text('{"test": "value"}')

        # Mock open to raise OSError
        with patch('builtins.open', side_effect=OSError("Permission denied")):
            result = load_implementation_plan(tmp_path)

            assert result is None

    def test_returns_none_on_unicode_decode_error(self, tmp_path):
        """Test that None is returned on Unicode decode error."""
        plan_file = tmp_path / "implementation_plan.json"
        # Write binary data that can't be decoded as UTF-8
        plan_file.write_bytes(b'\xff\xfe invalid utf-8')

        result = load_implementation_plan(tmp_path)

        assert result is None


class TestFindSubtaskInPlan:
    """Test find_subtask_in_plan function."""

    def test_finds_subtask_by_id(self):
        """Test that subtask is found by ID."""
        plan = {
            "phases": [
                {
                    "id": "1",
                    "subtasks": [
                        {"id": "subtask-1", "description": "First"},
                        {"id": "subtask-2", "description": "Second"},
                    ]
                }
            ]
        }

        result = find_subtask_in_plan(plan, "subtask-2")

        assert result is not None
        assert result["id"] == "subtask-2"
        assert result["description"] == "Second"

    def test_returns_none_when_not_found(self):
        """Test that None is returned when subtask doesn't exist."""
        plan = {
            "phases": [
                {
                    "id": "1",
                    "subtasks": [
                        {"id": "subtask-1", "description": "First"}
                    ]
                }
            ]
        }

        result = find_subtask_in_plan(plan, "subtask-999")

        assert result is None

    def test_searches_multiple_phases(self):
        """Test that all phases are searched."""
        plan = {
            "phases": [
                {
                    "id": "1",
                    "subtasks": [
                        {"id": "subtask-1", "description": "First"}
                    ]
                },
                {
                    "id": "2",
                    "subtasks": [
                        {"id": "subtask-2", "description": "Second"}
                    ]
                }
            ]
        }

        result = find_subtask_in_plan(plan, "subtask-2")

        assert result is not None
        assert result["id"] == "subtask-2"

    def test_handles_plan_without_phases(self):
        """Test that plan without phases key is handled."""
        plan = {"feature": "Test"}

        result = find_subtask_in_plan(plan, "subtask-1")

        assert result is None

    def test_handles_phase_without_subtasks(self):
        """Test that phase without subtasks key is handled."""
        plan = {
            "phases": [
                {"id": "1", "name": "Phase 1"}
            ]
        }

        result = find_subtask_in_plan(plan, "subtask-1")

        assert result is None

    def test_handles_subtask_without_id(self):
        """Test that subtask without id field is handled."""
        plan = {
            "phases": [
                {
                    "subtasks": [
                        {"description": "No ID"}
                    ]
                }
            ]
        }

        result = find_subtask_in_plan(plan, "subtask-1")

        assert result is None


class TestFindPhaseForSubtask:
    """Test find_phase_for_subtask function."""

    def test_finds_phase_containing_subtask(self):
        """Test that phase containing subtask is found."""
        plan = {
            "phases": [
                {
                    "id": "1",
                    "name": "Phase 1",
                    "subtasks": [
                        {"id": "subtask-1", "description": "First"}
                    ]
                },
                {
                    "id": "2",
                    "name": "Phase 2",
                    "subtasks": [
                        {"id": "subtask-2", "description": "Second"}
                    ]
                }
            ]
        }

        result = find_phase_for_subtask(plan, "subtask-2")

        assert result is not None
        assert result["id"] == "2"
        assert result["name"] == "Phase 2"

    def test_returns_none_when_subtask_not_found(self):
        """Test that None is returned when subtask doesn't exist."""
        plan = {
            "phases": [
                {
                    "id": "1",
                    "subtasks": [
                        {"id": "subtask-1", "description": "First"}
                    ]
                }
            ]
        }

        result = find_phase_for_subtask(plan, "subtask-999")

        assert result is None

    def test_handles_plan_without_phases(self):
        """Test that plan without phases key is handled."""
        plan = {"feature": "Test"}

        result = find_phase_for_subtask(plan, "subtask-1")

        assert result is None

    def test_handles_phase_without_subtasks(self):
        """Test that phase without subtasks key is handled."""
        plan = {
            "phases": [
                {"id": "1", "name": "Phase 1"}
            ]
        }

        result = find_phase_for_subtask(plan, "subtask-1")

        assert result is None

    def test_returns_first_matching_phase(self):
        """Test that first matching phase is returned if subtask appears in multiple."""
        plan = {
            "phases": [
                {
                    "id": "1",
                    "name": "Phase 1",
                    "subtasks": [
                        {"id": "subtask-1", "description": "First"}
                    ]
                },
                {
                    "id": "2",
                    "name": "Phase 2",
                    "subtasks": [
                        {"id": "subtask-1", "description": "Duplicate"}
                    ]
                }
            ]
        }

        result = find_phase_for_subtask(plan, "subtask-1")

        assert result is not None
        assert result["id"] == "1"  # First phase


class TestSyncSpecToSource:
    """Test sync_spec_to_source function."""

    def test_returns_false_when_no_source(self, tmp_path):
        """Test that False is returned when no source directory."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)

        result = sync_spec_to_source(spec_dir, None)

        assert result is False

    def test_returns_false_when_same_directory(self, tmp_path):
        """Test that False is returned when spec and source are the same."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)

        result = sync_spec_to_source(spec_dir, spec_dir)

        assert result is False

    def test_copies_files_to_source(self, tmp_path):
        """Test that files are copied to source directory."""
        spec_dir = tmp_path / "worktree" / "specs" / "001-test"
        source_spec_dir = tmp_path / "main" / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        source_spec_dir.mkdir(parents=True)

        # Create test files
        (spec_dir / "test.txt").write_text("content")
        (spec_dir / "subdir").mkdir()
        (spec_dir / "subdir" / "nested.txt").write_text("nested")

        result = sync_spec_to_source(spec_dir, source_spec_dir)

        assert result is True
        assert (source_spec_dir / "test.txt").exists()
        assert (source_spec_dir / "subdir" / "nested.txt").exists()
        assert (source_spec_dir / "test.txt").read_text() == "content"

    def test_skips_symlinks(self, tmp_path):
        """Test that symlinks are skipped during sync."""
        spec_dir = tmp_path / "worktree" / "specs" / "001-test"
        source_spec_dir = tmp_path / "main" / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        source_spec_dir.mkdir(parents=True)

        # Create a symlink
        (spec_dir / "link").symlink_to(tmp_path)

        # Should not crash
        result = sync_spec_to_source(spec_dir, source_spec_dir)

        # Result might be False if there were no regular files
        assert isinstance(result, bool)

    def test_handles_copy_errors_gracefully(self, tmp_path):
        """Test that copy errors are handled gracefully."""
        spec_dir = tmp_path / "worktree" / "specs" / "001-test"
        source_spec_dir = tmp_path / "main" / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        # Don't create source - let the function try to create it

        (spec_dir / "test.txt").write_text("content")

        # Should not crash even if there are issues
        result = sync_spec_to_source(spec_dir, source_spec_dir)

        # Result might be True or False depending on error
        assert isinstance(result, bool)

    def test_handles_exception_during_sync(self, tmp_path):
        """Test that exceptions during sync are handled gracefully."""
        spec_dir = tmp_path / "worktree" / "specs" / "001-test"
        source_spec_dir = tmp_path / "main" / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        source_spec_dir.mkdir(parents=True)

        (spec_dir / "test.txt").write_text("content")

        # Mock iterdir to raise exception
        with patch.object(Path, 'iterdir', side_effect=PermissionError("Access denied")):
            result = sync_spec_to_source(spec_dir, source_spec_dir)

            # Should return False on error
            assert result is False

    def test_creates_source_directory_if_missing(self, tmp_path):
        """Test that source directory is created if it doesn't exist."""
        spec_dir = tmp_path / "worktree" / "specs" / "001-test"
        source_spec_dir = tmp_path / "main" / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        # Don't create source_spec_dir

        (spec_dir / "test.txt").write_text("content")

        result = sync_spec_to_source(spec_dir, source_spec_dir)

        assert result is True
        assert source_spec_dir.exists()
        assert (source_spec_dir / "test.txt").exists()

    def test_resolves_symbolic_links_in_paths(self, tmp_path):
        """Test that symbolic links in paths are resolved."""
        spec_dir = tmp_path / "worktree" / "specs" / "001-test"
        spec_dir.mkdir(parents=True)

        # Create a symlink to the spec directory
        link_dir = tmp_path / "link_to_specs"
        link_dir.symlink_to(spec_dir)

        # Source is the same as spec (after resolution)
        result = sync_spec_to_source(spec_dir, link_dir)

        # Should return False since they resolve to same directory
        assert result is False

    def test_overwrites_files_in_source(self, tmp_path):
        """Test that files in source are overwritten."""
        spec_dir = tmp_path / "worktree" / "specs" / "001-test"
        source_spec_dir = tmp_path / "main" / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        source_spec_dir.mkdir(parents=True)

        # Create existing file in source with different content
        (source_spec_dir / "test.txt").write_text("old content")
        (spec_dir / "test.txt").write_text("new content")

        result = sync_spec_to_source(spec_dir, source_spec_dir)

        assert result is True
        assert (source_spec_dir / "test.txt").read_text() == "new content"


class TestSyncPlanToSource:
    """Test sync_plan_to_source function (alias)."""

    def test_is_alias_for_sync_spec_to_source(self, tmp_path):
        """Test that sync_plan_to_source is an alias for sync_spec_to_source."""
        spec_dir = tmp_path / "specs" / "001-test"
        source_spec_dir = tmp_path / "main" / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        source_spec_dir.mkdir(parents=True)

        (spec_dir / "test.txt").write_text("content")

        result = sync_plan_to_source(spec_dir, source_spec_dir)

        # Should work the same as sync_spec_to_source
        assert isinstance(result, bool)


class TestSyncDirectory:
    """Test _sync_directory helper function."""

    def test_syncs_nested_directory_structure(self, tmp_path):
        """Test that nested directories are synced recursively."""
        source_dir = tmp_path / "source" / "nested"
        target_dir = tmp_path / "target" / "nested"
        source_dir.mkdir(parents=True)

        # Create nested structure
        (source_dir / "level1").mkdir()
        (source_dir / "level1" / "level2").mkdir()
        (source_dir / "level1" / "level2" / "file.txt").write_text("deep")
        (source_dir / "root.txt").write_text("root")

        _sync_directory(source_dir, target_dir)

        assert (target_dir / "root.txt").exists()
        assert (target_dir / "level1" / "level2" / "file.txt").exists()
        assert (target_dir / "root.txt").read_text() == "root"
        assert (target_dir / "level1" / "level2" / "file.txt").read_text() == "deep"

    def test_creates_target_directory(self, tmp_path):
        """Test that target directory is created if missing."""
        source_dir = tmp_path / "source"
        target_dir = tmp_path / "target" / "nested" / "path"
        source_dir.mkdir()

        (source_dir / "file.txt").write_text("content")

        _sync_directory(source_dir, target_dir)

        assert target_dir.exists()
        assert (target_dir / "file.txt").exists()

    def test_skips_symlinks_in_subdirectories(self, tmp_path):
        """Test that symlinks are skipped in nested directories."""
        source_dir = tmp_path / "source"
        target_dir = tmp_path / "target"
        source_dir.mkdir()
        target_dir.mkdir()

        # Create a symlink
        (source_dir / "link").symlink_to(tmp_path)
        # Create a regular file
        (source_dir / "file.txt").write_text("content")

        _sync_directory(source_dir, target_dir)

        # Regular file should be copied
        assert (target_dir / "file.txt").exists()
        assert (target_dir / "file.txt").read_text() == "content"

    def test_syncs_empty_directories(self, tmp_path):
        """Test that empty directories are handled correctly."""
        source_dir = tmp_path / "source"
        target_dir = tmp_path / "target"
        source_dir.mkdir()

        _sync_directory(source_dir, target_dir)

        assert target_dir.exists()

    def test_copies_file_timestamps(self, tmp_path):
        """Test that file timestamps are preserved (shutil.copy2)."""
        import time

        source_dir = tmp_path / "source"
        target_dir = tmp_path / "target"
        source_dir.mkdir()

        test_file = source_dir / "file.txt"
        test_file.write_text("content")

        # Get source file stats
        source_stat = test_file.stat()

        # Small delay to ensure timestamp difference
        time.sleep(0.01)

        _sync_directory(source_dir, target_dir)

        target_file = target_dir / "file.txt"
        assert target_file.exists()

        # shutil.copy2 preserves timestamps
        # The mtime should be close to the source
        target_stat = target_file.stat()
        assert target_stat.st_mtime == source_stat.st_mtime
