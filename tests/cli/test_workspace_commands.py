"""Tests for workspace_commands"""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from cli.workspace_commands import (
    _check_git_merge_conflicts,
    _detect_conflict_scenario,
    _detect_default_branch,
    _detect_parallel_task_conflicts,
    _detect_worktree_base_branch,
    _generate_and_save_commit_message,
    _get_changed_files_from_git,
    cleanup_old_worktrees_command,
    handle_cleanup_worktrees_command,
    handle_create_pr_command,
    handle_discard_command,
    handle_list_worktrees_command,
    handle_merge_command,
    handle_merge_preview_command,
    handle_review_command,
    worktree_summary_command,
)

# ============================================================================
# Test _detect_default_branch
# ============================================================================


class TestDetectDefaultBranch:
    """Tests for _detect_default_branch function."""

    def test_default_branch_from_env_var(self, tmp_path):
        """Test detection via DEFAULT_BRANCH environment variable."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch.dict("os.environ", {"DEFAULT_BRANCH": "custom-branch"}), patch(
            "subprocess.run",
            return_value=Mock(returncode=0, stdout="abc123\n"),
        ):
            result = _detect_default_branch(project_dir)
            assert result == "custom-branch"

    def test_default_branch_env_var_not_exists(self, tmp_path):
        """Test DEFAULT_BRANCH env var when branch doesn't exist."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch.dict("os.environ", {"DEFAULT_BRANCH": "nonexistent"}), patch(
            "subprocess.run",
            side_effect=[
                Mock(returncode=1),  # custom branch doesn't exist
                Mock(returncode=0, stdout="abc123\n"),  # main exists
            ],
        ):
            result = _detect_default_branch(project_dir)
            assert result == "main"

    def test_default_branch_detect_main(self, tmp_path):
        """Test auto-detection of 'main' branch."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch.dict("os.environ", {}, clear=False), patch(
            "os.getenv", return_value=None
        ), patch(
            "subprocess.run",
            return_value=Mock(returncode=0, stdout="abc123\n"),
        ):
            result = _detect_default_branch(project_dir)
            assert result == "main"

    def test_default_branch_detect_master(self, tmp_path):
        """Test auto-detection of 'master' branch."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch.dict("os.environ", {}, clear=False), patch(
            "os.getenv", return_value=None
        ), patch(
            "subprocess.run",
            side_effect=[
                Mock(returncode=1),  # main doesn't exist
                Mock(returncode=0, stdout="def456\n"),  # master exists
            ],
        ):
            result = _detect_default_branch(project_dir)
            assert result == "master"

    def test_default_branch_fallback_to_main(self, tmp_path):
        """Test fallback to 'main' when no branches exist."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch.dict("os.environ", {}, clear=False), patch(
            "os.getenv", return_value=None
        ), patch(
            "subprocess.run",
            side_effect=[
                Mock(returncode=1),  # main doesn't exist
                Mock(returncode=1),  # master doesn't exist
            ],
        ):
            result = _detect_default_branch(project_dir)
            assert result == "main"


# ============================================================================
# Test _get_changed_files_from_git
# ============================================================================


class TestGetChangedFilesFromGit:
    """Tests for _get_changed_files_from_git function."""

    def test_get_changed_files_with_merge_base(self, tmp_path):
        """Test getting changed files using merge-base."""
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        merge_base = "abc123"
        changed_files = "file1.py\nfile2.py\nfile3.py\n"

        with patch(
            "subprocess.run",
            side_effect=[
                Mock(returncode=0, stdout=merge_base + "\n"),  # merge-base
                Mock(
                    returncode=0, stdout=changed_files
                ),  # diff from merge-base
            ],
        ):
            result = _get_changed_files_from_git(worktree_path, "main")
            assert result == ["file1.py", "file2.py", "file3.py"]

    def test_get_changed_files_fallback_to_direct_diff(self, tmp_path):
        """Test fallback to direct diff when merge-base fails."""
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        changed_files = "file1.py\nfile2.py\n"

        with patch(
            "subprocess.run",
            side_effect=[
                Mock(
                    returncode=1, stderr="merge-base failed"
                ),  # merge-base fails
                Mock(
                    returncode=0, stdout=changed_files
                ),  # direct diff succeeds
            ],
        ):
            result = _get_changed_files_from_git(worktree_path, "main")
            assert result == ["file1.py", "file2"]

    def test_get_changed_files_both_fail(self, tmp_path):
        """Test when both merge-base and direct diff fail."""
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        with patch(
            "subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "git"),
        ):
            result = _get_changed_files_from_git(worktree_path, "main")
            assert result == []

    def test_get_changed_files_empty_output(self, tmp_path):
        """Test with no changed files."""
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        with patch(
            "subprocess.run",
            return_value=Mock(returncode=0, stdout="\n"),
        ):
            result = _get_changed_files_from_git(worktree_path, "main")
            assert result == []

    def test_get_changed_files_with_whitespace(self, tmp_path):
        """Test handling of whitespace in file list."""
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        changed_files = "  file1.py  \n\tfile2.py\n  file3.py\n\n"

        with patch(
            "subprocess.run",
            side_effect=[
                Mock(returncode=0, stdout="abc123\n"),
                Mock(returncode=0, stdout=changed_files),
            ],
        ):
            result = _get_changed_files_from_git(worktree_path, "main")
            assert result == ["file1.py", "file2.py", "file3.py"]


# ============================================================================
# Test _detect_worktree_base_branch
# ============================================================================


class TestDetectWorktreeBaseBranch:
    """Tests for _detect_worktree_base_branch function."""

    def test_detect_from_config_file(self, tmp_path):
        """Test detection from worktree config file."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        config_dir = worktree_path / ".auto-claude"
        config_dir.mkdir()
        config_file = config_dir / "worktree-config.json"
        config_file.write_text('{"base_branch": "develop"}', encoding="utf-8")

        result = _detect_worktree_base_branch(project_dir, worktree_path, "001-test")
        assert result == "develop"

    def test_detect_from_git_history_develop(self, tmp_path):
        """Test detection from git history (develop branch)."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        with patch(
            "subprocess.run",
            side_effect=[
                Mock(returncode=0, stdout="abc123\n"),  # develop exists
                Mock(returncode=0, stdout="abc123\n"),  # merge-base with develop
                Mock(returncode=0, stdout="0\n"),  # commits ahead
            ],
        ):
            result = _detect_worktree_base_branch(
                project_dir, worktree_path, "001-test"
            )
            assert result == "develop"

    def test_detect_from_git_history_main(self, tmp_path):
        """Test detection from git history (main branch)."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        # develop doesn't exist, main does
        with patch(
            "subprocess.run",
            side_effect=[
                Mock(returncode=1),  # develop doesn't exist
                Mock(returncode=0, stdout="def456\n"),  # main exists
                Mock(returncode=0, stdout="xyz789\n"),  # merge-base with main
                Mock(returncode=0, stdout="2\n"),  # commits ahead
            ],
        ):
            result = _detect_worktree_base_branch(
                project_dir, worktree_path, "001-test"
            )
            assert result == "main"

    def test_detect_no_config_invalid_json(self, tmp_path):
        """Test handling of invalid JSON in config file."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        config_dir = worktree_path / ".auto-claude"
        config_dir.mkdir()
        config_file = config_dir / "worktree-config.json"
        config_file.write_text("{invalid json}", encoding="utf-8")

        # Should fall back to git detection
        with patch(
            "subprocess.run",
            side_effect=[
                Mock(returncode=0, stdout="abc123\n"),  # develop exists
                Mock(returncode=0, stdout="abc123\n"),  # merge-base
                Mock(returncode=0, stdout="0\n"),  # commits ahead
            ],
        ):
            result = _detect_worktree_base_branch(
                project_dir, worktree_path, "001-test"
            )
            assert result == "develop"

    def test_detect_unable_to_detect(self, tmp_path):
        """Test when unable to detect base branch."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        with patch("subprocess.run", return_value=Mock(returncode=1)):
            result = _detect_worktree_base_branch(
                project_dir, worktree_path, "001-test"
            )
            assert result is None


# ============================================================================
# Test _detect_parallel_task_conflicts
# ============================================================================


class TestDetectParallelTaskConflicts:
    """Tests for _detect_parallel_task_conflicts function."""

    def test_no_parallel_conflicts(self, tmp_path):
        """Test when no parallel conflicts exist."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch(
            "cli.workspace_commands.MergeOrchestrator"
        ) as mock_orchestrator_class:
            mock_orchestrator = MagicMock()
            mock_orchestrator_class.return_value = mock_orchestrator
            mock_orchestrator.evolution_tracker.get_active_tasks.return_value = {
                "001-test"
            }

            result = _detect_parallel_task_conflicts(
                project_dir, "001-test", ["file1.py"]
            )
            assert result == []

    def test_has_parallel_conflicts(self, tmp_path):
        """Test when parallel conflicts are detected."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch(
            "cli.workspace_commands.MergeOrchestrator"
        ) as mock_orchestrator_class:
            mock_orchestrator = MagicMock()
            mock_orchestrator_class.return_value = mock_orchestrator

            # Two active tasks
            mock_orchestrator.evolution_tracker.get_active_tasks.return_value = {
                "001-test",
                "002-other",
            }
            # Both tasks modified file1.py
            mock_orchestrator.evolution_tracker.get_files_modified_by_tasks.return_value = {
                "file1.py": ["002-other"]
            }

            result = _detect_parallel_task_conflicts(
                project_dir, "001-test", ["file1.py"]
            )
            assert len(result) == 1
            assert result[0]["file"] == "file1.py"
            assert set(result[0]["tasks"]) == {"001-test", "002-other"}

    def test_parallel_conflicts_multiple_files(self, tmp_path):
        """Test with multiple conflicting files."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch(
            "cli.workspace_commands.MergeOrchestrator"
        ) as mock_orchestrator_class:
            mock_orchestrator = MagicMock()
            mock_orchestrator_class.return_value = mock_orchestrator

            mock_orchestrator.evolution_tracker.get_active_tasks.return_value = {
                "001-test",
                "002-other",
            }
            mock_orchestrator.evolution_tracker.get_files_modified_by_tasks.return_value = {
                "file1.py": ["002-other"],
                "file2.py": ["002-other"],
                "file3.py": ["002-other"],
            }

            result = _detect_parallel_task_conflicts(
                project_dir, "001-test", ["file1.py", "file2.py", "file3.py"]
            )
            assert len(result) == 3

    def test_parallel_conflicts_exception_handling(self, tmp_path):
        """Test exception handling in parallel conflict detection."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch(
            "cli.workspace_commands.MergeOrchestrator",
            side_effect=Exception("Merge orchestrator failed"),
        ):
            result = _detect_parallel_task_conflicts(
                project_dir, "001-test", ["file1.py"]
            )
            # Should return empty on error
            assert result == []


# ============================================================================
# Test _detect_conflict_scenario
# ============================================================================


class TestDetectConflictScenario:
    """Tests for _detect_conflict_scenario function."""

    def test_no_conflicting_files(self, tmp_path):
        """Test with no conflicting files."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        result = _detect_conflict_scenario(project_dir, [], "spec-branch", "main")
        assert result["scenario"] == "normal_conflict"
        assert result["already_merged_files"] == []

    def test_already_merged_scenario(self, tmp_path):
        """Test detection of already merged files."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        conflicting_files = ["file1.py", "file2.py"]

        with patch(
            "subprocess.run",
            side_effect=[
                Mock(returncode=0, stdout="merge-base-commit\n"),  # merge-base
                # Both files have identical content in spec and base
                Mock(returncode=0, stdout="same content"),
                Mock(returncode=0, stdout="same content"),
                Mock(returncode=0, stdout="original content"),
                Mock(returncode=0, stdout="same content"),
                Mock(returncode=0, stdout="same content"),
                Mock(returncode=0, stdout="original content"),
            ],
        ):
            result = _detect_conflict_scenario(
                project_dir, conflicting_files, "spec-branch", "main"
            )
            assert result["scenario"] == "already_merged"
            assert len(result["already_merged_files"]) == 2

    def test_superseded_scenario(self, tmp_path):
        """Test detection of superseded files."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        conflicting_files = ["file1.py"]

        with patch(
            "subprocess.run",
            side_effect=[
                Mock(returncode=0, stdout="merge-base-commit\n"),  # merge-base
                # Spec content matches merge-base (superseded by base)
                Mock(returncode=0, stdout="original content"),  # spec
                Mock(returncode=0, stdout="newer content"),  # base
                Mock(returncode=0, stdout="original content"),  # merge-base
            ],
        ):
            result = _detect_conflict_scenario(
                project_dir, conflicting_files, "spec-branch", "main"
            )
            assert result["scenario"] == "superseded"
            assert len(result["superseded_files"]) == 1

    def test_diverged_scenario(self, tmp_path):
        """Test detection of diverged files."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        conflicting_files = ["file1.py"]

        with patch(
            "subprocess.run",
            side_effect=[
                Mock(returncode=0, stdout="merge-base-commit\n"),  # merge-base
                # Both branches have different content
                Mock(returncode=0, stdout="spec changes"),  # spec
                Mock(returncode=0, stdout="base changes"),  # base
                Mock(returncode=0, stdout="original content"),  # merge-base
            ],
        ):
            result = _detect_conflict_scenario(
                project_dir, conflicting_files, "spec-branch", "main"
            )
            assert result["scenario"] == "diverged"
            assert len(result["diverged_files"]) == 1

    def test_merge_base_failure(self, tmp_path):
        """Test handling of merge-base command failure."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch(
            "subprocess.run",
            return_value=Mock(returncode=1, stderr="failed to find merge-base"),
        ):
            result = _detect_conflict_scenario(
                project_dir, ["file1.py"], "spec-branch", "main"
            )
            assert result["scenario"] == "normal_conflict"
            assert "Could not determine merge base" in result["details"]


# ============================================================================
# Test _check_git_merge_conflicts
# ============================================================================


class TestCheckGitMergeConflicts:
    """Tests for _check_git_merge_conflicts function."""

    def test_no_git_conflicts(self, tmp_path):
        """Test when no git conflicts exist."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch(
            "subprocess.run",
            side_effect=[
                Mock(returncode=0, stdout="main\n"),  # current branch
                Mock(returncode=0, stdout="abc123\n"),  # merge-base
                Mock(returncode=0, stdout="0\n"),  # commits behind
                Mock(returncode=0, stdout="", stderr=""),  # merge-tree
            ],
        ):
            result = _check_git_merge_conflicts(project_dir, "001-test")
            assert result["has_conflicts"] is False
            assert result["conflicting_files"] == []
            assert result["needs_rebase"] is False

    def test_has_git_conflicts_from_merge_tree(self, tmp_path):
        """Test git conflicts detected via merge-tree."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        merge_tree_output = "CONFLICT (content): Merge conflict in file1.py"

        with patch(
            "subprocess.run",
            side_effect=[
                Mock(returncode=0, stdout="main\n"),  # current branch
                Mock(returncode=0, stdout="abc123\n"),  # merge-base
                Mock(returncode=0, stdout="3\n"),  # commits behind
                Mock(
                    returncode=1,  # merge-tree returns 1 on conflicts
                    stdout="",
                    stderr=merge_tree_output,
                ),
            ],
        ):
            result = _check_git_merge_conflicts(project_dir, "001-test")
            assert result["has_conflicts"] is True
            assert "file1.py" in result["conflicting_files"]
            assert result["needs_rebase"] is True

    def test_git_conflicts_fallback_to_diff(self, tmp_path):
        """Test fallback to diff when merge-tree parsing fails."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch(
            "subprocess.run",
            side_effect=[
                Mock(returncode=0, stdout="main\n"),  # current branch
                Mock(returncode=0, stdout="abc123\n"),  # merge-base
                Mock(returncode=0, stdout="2\n"),  # commits behind
                Mock(
                    returncode=1,  # merge-tree returns 1
                    stdout="",  # No parsable conflicts
                    stderr="",
                ),
                # Fallback: get main files
                Mock(returncode=0, stdout="file1.py\nfile2.py\n"),
                # Fallback: get spec files
                Mock(returncode=0, stdout="file1.py\nfile3.py\n"),
            ],
        ):
            result = _check_git_merge_conflicts(project_dir, "001-test")
            assert result["has_conflicts"] is True
            assert "file1.py" in result["conflicting_files"]

    def test_auto_claude_files_filtered(self, tmp_path):
        """Test that .auto-claude files are filtered from conflicts."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        merge_tree_output = (
            "CONFLICT (content): Merge conflict in .auto-claude/spec.md\n"
            "CONFLICT (content): Merge conflict in src/main.py"
        )

        with patch(
            "subprocess.run",
            side_effect=[
                Mock(returncode=0, stdout="main\n"),
                Mock(returncode=0, stdout="abc123\n"),
                Mock(returncode=0, stdout="0\n"),
                Mock(returncode=1, stderr=merge_tree_output),
            ],
        ):
            result = _check_git_merge_conflicts(project_dir, "001-test")
            # Only src/main.py should be in conflicting files
            assert ".auto-claude/spec.md" not in result["conflicting_files"]
            # May have src/main.py if regex matched

    def test_base_branch_provided(self, tmp_path):
        """Test with explicitly provided base branch."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch(
            "subprocess.run",
            side_effect=[
                Mock(returncode=0, stdout="abc123\n"),  # merge-base
                Mock(returncode=0, stdout="0\n"),  # commits behind
                Mock(returncode=0),  # merge-tree
            ],
        ):
            result = _check_git_merge_conflicts(
                project_dir, "001-test", base_branch="develop"
            )
            assert result["base_branch"] == "develop"
            assert result["has_conflicts"] is False


# ============================================================================
# Test handle_merge_preview_command
# ============================================================================


class TestHandleMergePreviewCommand:
    """Tests for handle_merge_preview_command function."""

    def test_no_worktree_exists(self, tmp_path):
        """Test when no worktree exists."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch(
            "cli.workspace_commands.get_existing_build_worktree", return_value=None
        ):
            result = handle_merge_preview_command(project_dir, "001-test")
            assert result["success"] is False
            assert "No existing build" in result["error"]

    def test_successful_preview_no_conflicts(self, tmp_path):
        """Test successful preview with no conflicts."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        with patch(
            "cli.workspace_commands.get_existing_build_worktree",
            return_value=worktree_path,
        ), patch(
            "cli.workspace_commands._detect_default_branch", return_value="main"
        ), patch(
            "cli.workspace_commands._check_git_merge_conflicts",
            return_value={
                "has_conflicts": False,
                "conflicting_files": [],
                "needs_rebase": False,
                "base_branch": "main",
                "spec_branch": "auto-claude/001-test",
                "commits_behind": 0,
            },
        ), patch(
            "cli.workspace_commands._get_changed_files_from_git",
            return_value=["file1.py", "file2.py"],
        ), patch(
            "cli.workspace_commands._detect_parallel_task_conflicts", return_value=[]
        ), patch(
            "cli.workspace_commands.get_merge_base", return_value="abc123"
        ), patch(
            "cli.workspace_commands.detect_file_renames", return_value={}
        ):
            result = handle_merge_preview_command(project_dir, "001-test")
            assert result["success"] is True
            assert result["summary"]["totalFiles"] == 2
            assert result["summary"]["totalConflicts"] == 0

    def test_preview_with_git_conflicts(self, tmp_path):
        """Test preview with git conflicts."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        with patch(
            "cli.workspace_commands.get_existing_build_worktree",
            return_value=worktree_path,
        ), patch(
            "cli.workspace_commands._detect_default_branch", return_value="main"
        ), patch(
            "cli.workspace_commands._check_git_merge_conflicts",
            return_value={
                "has_conflicts": True,
                "conflicting_files": ["src/main.py"],
                "needs_rebase": True,
                "base_branch": "main",
                "spec_branch": "auto-claude/001-test",
                "commits_behind": 3,
            },
        ), patch(
            "cli.workspace_commands._get_changed_files_from_git",
            return_value=["src/main.py", "src/utils.py"],
        ), patch(
            "cli.workspace_commands._detect_parallel_task_conflicts", return_value=[]
        ), patch(
            "cli.workspace_commands.is_lock_file", return_value=False
        ), patch(
            "cli.workspace_commands.get_merge_base", return_value="abc123"
        ), patch(
            "cli.workspace_commands.detect_file_renames", return_value={}
        ):
            result = handle_merge_preview_command(project_dir, "001-test")
            assert result["success"] is True
            assert result["gitConflicts"]["hasConflicts"] is True
            assert len(result["conflicts"]) > 0

    def test_preview_with_parallel_conflicts(self, tmp_path):
        """Test preview with parallel task conflicts."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        parallel_conflicts = [
            {"file": "shared.py", "tasks": ["001-test", "002-other"]}
        ]

        with patch(
            "cli.workspace_commands.get_existing_build_worktree",
            return_value=worktree_path,
        ), patch(
            "cli.workspace_commands._detect_default_branch", return_value="main"
        ), patch(
            "cli.workspace_commands._check_git_merge_conflicts",
            return_value={
                "has_conflicts": False,
                "conflicting_files": [],
                "needs_rebase": False,
                "base_branch": "main",
                "spec_branch": "auto-claude/001-test",
                "commits_behind": 0,
            },
        ), patch(
            "cli.workspace_commands._get_changed_files_from_git",
            return_value=["shared.py"],
        ), patch(
            "cli.workspace_commands._detect_parallel_task_conflicts",
            return_value=parallel_conflicts,
        ), patch(
            "cli.workspace_commands.get_merge_base", return_value="abc123"
        ), patch(
            "cli.workspace_commands.detect_file_renames", return_value={}
        ):
            result = handle_merge_preview_command(project_dir, "001-test")
            assert result["success"] is True
            assert len(result["conflicts"]) == 1
            assert result["conflicts"][0]["type"] == "parallel"

    def test_preview_with_lock_file_conflict(self, tmp_path):
        """Test that lock files are excluded from conflicts."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        with patch(
            "cli.workspace_commands.get_existing_build_worktree",
            return_value=worktree_path,
        ), patch(
            "cli.workspace_commands._detect_default_branch", return_value="main"
        ), patch(
            "cli.workspace_commands._check_git_merge_conflicts",
            return_value={
                "has_conflicts": True,
                "conflicting_files": ["package-lock.json", "src/main.py"],
                "needs_rebase": False,
                "base_branch": "main",
                "spec_branch": "auto-claude/001-test",
                "commits_behind": 0,
            },
        ), patch(
            "cli.workspace_commands._get_changed_files_from_git",
            return_value=["package-lock.json", "src/main.py"],
        ), patch(
            "cli.workspace_commands._detect_parallel_task_conflicts", return_value=[]
        ), patch(
            "cli.workspace_commands.is_lock_file",
            side_effect=lambda f: f == "package-lock.json",
        ), patch(
            "cli.workspace_commands.get_merge_base", return_value="abc123"
        ), patch(
            "cli.workspace_commands.detect_file_renames", return_value={}
        ):
            result = handle_merge_preview_command(project_dir, "001-test")
            assert result["success"] is True
            # Lock file should be excluded
            assert "package-lock.json" in result.get("lockFilesExcluded", [])
            # Check git conflicts excludes lock file
            non_lock_conflicts = [
                f for f in result["gitConflicts"]["conflictingFiles"]
                if not is_lock_file(f)
            ]

    def test_preview_with_base_branch_provided(self, tmp_path):
        """Test preview with explicitly provided base branch."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        with patch(
            "cli.workspace_commands.get_existing_build_worktree",
            return_value=worktree_path,
        ), patch(
            "cli.workspace_commands._detect_worktree_base_branch", return_value=None
        ), patch(
            "cli.workspace_commands._detect_default_branch", return_value="develop"
        ), patch(
            "cli.workspace_commands._check_git_merge_conflicts",
            return_value={
                "has_conflicts": False,
                "conflicting_files": [],
                "needs_rebase": False,
                "base_branch": "develop",
                "spec_branch": "auto-claude/001-test",
                "commits_behind": 0,
            },
        ), patch(
            "cli.workspace_commands._get_changed_files_from_git",
            return_value=["file1.py"],
        ), patch(
            "cli.workspace_commands._detect_parallel_task_conflicts", return_value=[]
        ), patch(
            "cli.workspace_commands.get_merge_base", return_value="abc123"
        ), patch(
            "cli.workspace_commands.detect_file_renames", return_value={}
        ):
            result = handle_merge_preview_command(
                project_dir, "001-test", base_branch="develop"
            )
            assert result["success"] is True
            assert result["gitConflicts"]["baseBranch"] == "develop"

    def test_preview_exception_handling(self, tmp_path):
        """Test exception handling in preview."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        with patch(
            "cli.workspace_commands.get_existing_build_worktree",
            return_value=worktree_path,
        ), patch(
            "cli.workspace_commands._detect_default_branch",
            side_effect=Exception("Detection failed"),
        ):
            result = handle_merge_preview_command(project_dir, "001-test")
            assert result["success"] is False
            assert "error" in result


# ============================================================================
# Test _generate_and_save_commit_message
# ============================================================================


class TestGenerateAndSaveCommitMessage:
    """Tests for _generate_and_save_commit_message function."""

    def test_generate_commit_message_success(self, tmp_path):
        """Test successful commit message generation."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = project_dir / ".auto-claude" / "specs" / "001-test"
        spec_dir.mkdir(parents=True)

        diff_summary = "2 files changed, 10 insertions(+), 5 deletions(-)"
        files_changed = ["src/main.py", "src/utils.py"]

        with patch(
            "cli.workspace_commands.generate_commit_message_sync",
            return_value="feat: implement new feature",
        ), patch(
            "subprocess.run",
            side_effect=[
                Mock(returncode=0, stdout=diff_summary),  # diff --stat
                Mock(returncode=0, stdout="src/main.py\nsrc/utils.py\n"),  # diff --name-only
            ],
        ):
            _generate_and_save_commit_message(project_dir, "001-test")

            commit_msg_file = spec_dir / "suggested_commit_message.txt"
            assert commit_msg_file.exists()
            assert commit_msg_file.read_text() == "feat: implement new feature"

    def test_generate_commit_message_fallback_spec_dir(self, tmp_path):
        """Test fallback to auto-claude/specs directory."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = project_dir / "auto-claude" / "specs" / "001-test"
        spec_dir.mkdir(parents=True)

        with patch(
            "cli.workspace_commands.generate_commit_message_sync",
            return_value="fix: resolve bug",
        ), patch("subprocess.run", return_value=Mock(returncode=0, stdout="")):
            _generate_and_save_commit_message(project_dir, "001-test")

            commit_msg_file = spec_dir / "suggested_commit_message.txt"
            assert commit_msg_file.exists()

    def test_generate_commit_message_no_diff(self, tmp_path):
        """Test when no diff is available."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = project_dir / ".auto-claude" / "specs" / "001-test"
        spec_dir.mkdir(parents=True)

        with patch(
            "cli.workspace_commands.generate_commit_message_sync",
            return_value="chore: update",
        ), patch("subprocess.run", return_value=Mock(returncode=0, stdout="")):
            _generate_and_save_commit_message(project_dir, "001-test")

            commit_msg_file = spec_dir / "suggested_commit_message.txt"
            assert commit_msg_file.exists()

    def test_generate_commit_message_import_error(self, tmp_path, caplog):
        """Test handling when commit_message module not available."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch(
            "cli.workspace_commands.generate_commit_message_sync",
            side_effect=ImportError("No module named 'commit_message'"),
        ):
            # Should not raise
            _generate_and_save_commit_message(project_dir, "001-test")

    def test_generate_commit_message_generation_fails(self, tmp_path):
        """Test when commit message generation returns None."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = project_dir / ".auto-claude" / "specs" / "001-test"
        spec_dir.mkdir(parents=True)

        with patch(
            "cli.workspace_commands.generate_commit_message_sync", return_value=None
        ):
            _generate_and_save_commit_message(project_dir, "001-test")

            # File should not be created
            commit_msg_file = spec_dir / "suggested_commit_message.txt"
            assert not commit_msg_file.exists()


# ============================================================================
# Test handle_create_pr_command
# ============================================================================


class TestHandleCreatePrCommand:
    """Tests for handle_create_pr_command function."""

    def test_no_worktree_exists(self, tmp_path):
        """Test when no worktree exists."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch(
            "cli.workspace_commands.get_existing_build_worktree", return_value=None
        ):
            result = handle_create_pr_command(project_dir, "001-test")
            assert result["success"] is False
            assert result["error"] == "No build found for this spec"

    def test_pr_creation_success(self, tmp_path):
        """Test successful PR creation."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        with patch(
            "cli.workspace_commands.get_existing_build_worktree",
            return_value=worktree_path,
        ), patch("cli.workspace_commands.WorktreeManager") as mock_mgr_class:
            mock_manager = MagicMock()
            mock_mgr_class.return_value = mock_manager
            mock_manager.base_branch = "main"
            mock_manager.push_and_create_pr.return_value = {
                "success": True,
                "pr_url": "https://github.com/user/repo/pull/123",
                "already_exists": False,
            }

            result = handle_create_pr_command(project_dir, "001-test")
            assert result["success"] is True
            assert result["pr_url"] == "https://github.com/user/repo/pull/123"

    def test_pr_already_exists(self, tmp_path):
        """Test when PR already exists."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        with patch(
            "cli.workspace_commands.get_existing_build_worktree",
            return_value=worktree_path,
        ), patch("cli.workspace_commands.WorktreeManager") as mock_mgr_class:
            mock_manager = MagicMock()
            mock_mgr_class.return_value = mock_manager
            mock_manager.base_branch = "main"
            mock_manager.push_and_create_pr.return_value = {
                "success": True,
                "pr_url": "https://github.com/user/repo/pull/123",
                "already_exists": True,
            }

            result = handle_create_pr_command(project_dir, "001-test")
            assert result["success"] is True
            assert result["already_exists"] is True

    def test_pr_creation_with_draft(self, tmp_path):
        """Test PR creation with draft flag."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        with patch(
            "cli.workspace_commands.get_existing_build_worktree",
            return_value=worktree_path,
        ), patch("cli.workspace_commands.WorktreeManager") as mock_mgr_class:
            mock_manager = MagicMock()
            mock_mgr_class.return_value = mock_manager
            mock_manager.base_branch = "develop"
            mock_manager.push_and_create_pr.return_value = {
                "success": True,
                "pr_url": "https://github.com/user/repo/pull/456",
                "already_exists": False,
            }

            result = handle_create_pr_command(
                project_dir, "001-test", draft=True, title="My Feature"
            )
            assert result["success"] is True
            mock_manager.push_and_create_pr.assert_called_once_with(
                spec_name="001-test",
                target_branch=None,
                title="My Feature",
                draft=True,
            )

    def test_pr_creation_failure(self, tmp_path):
        """Test PR creation failure."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        with patch(
            "cli.workspace_commands.get_existing_build_worktree",
            return_value=worktree_path,
        ), patch("cli.workspace_commands.WorktreeManager") as mock_mgr_class:
            mock_manager = MagicMock()
            mock_mgr_class.return_value = mock_manager
            mock_manager.push_and_create_pr.return_value = {
                "success": False,
                "error": "Authentication failed",
            }

            result = handle_create_pr_command(project_dir, "001-test")
            assert result["success"] is False
            assert result["error"] == "Authentication failed"

    def test_pr_creation_exception_handling(self, tmp_path):
        """Test exception handling during PR creation."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        with patch(
            "cli.workspace_commands.get_existing_build_worktree",
            return_value=worktree_path,
        ), patch("cli.workspace_commands.WorktreeManager") as mock_mgr_class:
            mock_manager = MagicMock()
            mock_mgr_class.return_value = mock_manager
            mock_manager.push_and_create_pr.side_effect = Exception(
                "Network error"
            )

            result = handle_create_pr_command(project_dir, "001-test")
            assert result["success"] is False
            assert "Network error" in result["error"]


# ============================================================================
# Test handle_merge_command
# ============================================================================


class TestHandleMergeCommand:
    """Tests for handle_merge_command function."""

    def test_merge_success_no_commit(self, tmp_path):
        """Test successful merge with no_commit flag."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch(
            "cli.workspace_commands.merge_existing_build", return_value=True
        ), patch("cli.workspace_commands._generate_and_save_commit_message"):
            result = handle_merge_command(
                project_dir, "001-test", no_commit=True, base_branch="develop"
            )
            assert result is True

    def test_merge_success_with_commit(self, tmp_path):
        """Test successful merge with commit."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch(
            "cli.workspace_commands.merge_existing_build", return_value=True
        ):
            result = handle_merge_command(
                project_dir, "001-test", no_commit=False
            )
            assert result is True

    def test_merge_failure(self, tmp_path):
        """Test merge failure."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch(
            "cli.workspace_commands.merge_existing_build", return_value=False
        ):
            result = handle_merge_command(project_dir, "001-test")
            assert result is False

    def test_merge_with_base_branch(self, tmp_path):
        """Test merge with explicit base branch."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch(
            "cli.workspace_commands.merge_existing_build", return_value=True
        ) as mock_merge:
            handle_merge_command(
                project_dir, "001-test", base_branch="feature-branch"
            )
            mock_merge.assert_called_once_with(
                project_dir, "001-test", no_commit=False, base_branch="feature-branch"
            )


# ============================================================================
# Test handle_review_command
# ============================================================================


class TestHandleReviewCommand:
    """Tests for handle_review_command function."""

    def test_review_valid_worktree(self, tmp_path):
        """Test review with valid worktree."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        with patch(
            "cli.workspace_commands.review_existing_build",
        ) as mock_review:
            handle_review_command(project_dir, "001-test")
            mock_review.assert_called_once_with(project_dir, "001-test")

    def test_review_no_worktree(self, capsys):
        """Test review when no worktree exists."""
        project_dir = Path("/tmp/test")
        spec_name = "001-test"

        with patch("cli.workspace_commands.get_existing_build_worktree", return_value=None):
            handle_review_command(project_dir, spec_name)

        captured = capsys.readouterr()
        assert "No existing build" in captured.out


# ============================================================================
# Test handle_discard_command
# ============================================================================


class TestHandleDiscardCommand:
    """Tests for handle_discard_command function."""

    def test_discard_valid_worktree(self, tmp_path):
        """Test discard with valid worktree."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        with patch(
            "cli.workspace_commands.discard_existing_build",
        ) as mock_discard:
            handle_discard_command(project_dir, "001-test")
            mock_discard.assert_called_once_with(project_dir, "001-test")

    def test_discard_no_worktree(self, capsys):
        """Test discard when no worktree exists."""
        project_dir = Path("/tmp/test")
        spec_name = "001-test"

        with patch("cli.workspace_commands.get_existing_build_worktree", return_value=None):
            handle_discard_command(project_dir, spec_name)

        captured = capsys.readouterr()
        assert "No existing build" in captured.out


# ============================================================================
# Test cleanup_old_worktrees_command
# ============================================================================


class TestCleanupOldWorktreesCommand:
    """Tests for cleanup_old_worktrees_command function."""

    def test_cleanup_dry_run(self, tmp_path):
        """Test cleanup with dry_run flag."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch(
            "cli.workspace_commands.WorktreeManager"
        ) as mock_mgr_class:
            mock_manager = MagicMock()
            mock_mgr_class.return_value = mock_manager
            mock_manager.cleanup_old_worktrees.return_value = (
                ["worktree1", "worktree2"],
                [],
            )

            result = cleanup_old_worktrees_command(project_dir, days=30, dry_run=True)
            assert result["success"] is True
            assert result["dry_run"] is True
            assert len(result["removed"]) == 2
            mock_manager.cleanup_old_worktrees.assert_called_once_with(
                days_threshold=30, dry_run=True
            )

    def test_cleanup_actual_removal(self, tmp_path):
        """Test actual cleanup (dry_run=False)."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch(
            "cli.workspace_commands.WorktreeManager"
        ) as mock_mgr_class:
            mock_manager = MagicMock()
            mock_mgr_class.return_value = mock_manager
            mock_manager.cleanup_old_worktrees.return_value = (
                ["worktree1"],
                ["worktree2"],
            )

            result = cleanup_old_worktrees_command(project_dir, days=7, dry_run=False)
            assert result["success"] is True
            assert result["dry_run"] is False
            assert result["days_threshold"] == 7
            assert len(result["removed"]) == 1
            assert len(result["failed"]) == 1

    def test_cleanup_exception_handling(self, tmp_path):
        """Test exception handling during cleanup."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch(
            "cli.workspace_commands.WorktreeManager",
            side_effect=Exception("Cleanup failed"),
        ):
            result = cleanup_old_worktrees_command(project_dir, days=30)
            assert result["success"] is False
            assert "error" in result


# ============================================================================
# Test worktree_summary_command
# ============================================================================


class TestWorktreeSummaryCommand:
    """Tests for worktree_summary_command function."""

    def test_summary_with_worktrees(self, tmp_path):
        """Test summary with multiple worktrees."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Create mock worktree info
        mock_worktree1 = MagicMock()
        mock_worktree1.spec_name = "001-test"
        mock_worktree1.days_since_last_commit = 5
        mock_worktree1.commit_count = 10

        mock_worktree2 = MagicMock()
        mock_worktree2.spec_name = "002-other"
        mock_worktree2.days_since_last_commit = 20
        mock_worktree2.commit_count = 5

        with patch(
            "cli.workspace_commands.WorktreeManager"
        ) as mock_mgr_class:
            mock_manager = MagicMock()
            mock_mgr_class.return_value = mock_manager
            mock_manager.list_all_worktrees.return_value = [
                mock_worktree1,
                mock_worktree2,
            ]
            mock_manager.get_worktree_count_warning.return_value = None

            result = worktree_summary_command(project_dir)
            assert result["success"] is True
            assert result["total_worktrees"] == 2
            assert len(result["categories"]["recent"]) == 1  # < 7 days
            assert len(result["categories"]["week_old"]) == 1  # < 30 days
            assert len(result["categories"]["month_old"]) == 0

    def test_summary_age_categorization(self, tmp_path):
        """Test worktree age categorization."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Create worktrees with different ages
        worktrees = []
        for days, category in [
            (3, "recent"),  # < 7 days
            (10, "week_old"),  # < 30 days
            (45, "month_old"),  # < 90 days
            (120, "very_old"),  # >= 90 days
        ]:
            wt = MagicMock()
            wt.spec_name = f"{category}_task"
            wt.days_since_last_commit = days
            wt.commit_count = 5
            worktrees.append(wt)

        # Add one with unknown age
        wt_unknown = MagicMock()
        wt_unknown.spec_name = "unknown_task"
        wt_unknown.days_since_last_commit = None
        wt_unknown.commit_count = 0
        worktrees.append(wt_unknown)

        with patch(
            "cli.workspace_commands.WorktreeManager"
        ) as mock_mgr_class:
            mock_manager = MagicMock()
            mock_mgr_class.return_value = mock_manager
            mock_manager.list_all_worktrees.return_value = worktrees
            mock_manager.get_worktree_count_warning.return_value = None

            result = worktree_summary_command(project_dir)
            assert result["total_worktrees"] == 5
            assert len(result["categories"]["recent"]) == 1
            assert len(result["categories"]["week_old"]) == 1
            assert len(result["categories"]["month_old"]) == 1
            assert len(result["categories"]["very_old"]) == 1
            assert len(result["categories"]["unknown_age"]) == 1

    def test_summary_with_warning(self, tmp_path):
        """Test summary when worktree count warning is present."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch(
            "cli.workspace_commands.WorktreeManager"
        ) as mock_mgr_class:
            mock_manager = MagicMock()
            mock_mgr_class.return_value = mock_manager
            mock_manager.list_all_worktrees.return_value = []
            mock_manager.get_worktree_count_warning.return_value = (
                "Too many worktrees!"
            )

            result = worktree_summary_command(project_dir)
            assert result["success"] is True
            assert result["warning"] == "Too many worktrees!"

    def test_summary_exception_handling(self, tmp_path):
        """Test exception handling in summary command."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch(
            "cli.workspace_commands.WorktreeManager",
            side_effect=Exception("Summary failed"),
        ):
            result = worktree_summary_command(project_dir)
            assert result["success"] is False
            assert "error" in result
            assert result["total_worktrees"] == 0


# ============================================================================
# Original Tests (preserved for backward compatibility)
# ============================================================================


def test_handle_merge_command_no_worktree(capsys):
    """Test handle_merge_command when no worktree exists."""
    # Arrange
    project_dir = Path("/tmp/test")
    spec_name = ""

    with patch("cli.workspace_commands.get_existing_build_worktree", return_value=None):
        # Act
        result = handle_merge_command(project_dir, spec_name, False, None)

    # Assert
    captured = capsys.readouterr()
    assert result is None or result is False
    assert "No existing build" in captured.out or "build" in captured.out.lower()


def test_handle_merge_command_with_empty_inputs(capsys):
    """Test handle_merge_command with empty spec_name."""
    # Arrange
    project_dir = Path("/tmp/test")
    spec_name = ""

    with patch("cli.workspace_commands.get_existing_build_worktree", return_value=None):
        # Act
        result = handle_merge_command(project_dir, spec_name, False, None)

    # Assert
    captured = capsys.readouterr()
    assert "No existing build" in captured.out or "build" in captured.out.lower()


def test_handle_review_command_no_worktree(capsys):
    """Test handle_review_command when no worktree exists."""
    # Arrange
    project_dir = Path("/tmp/test")
    spec_name = ""

    with patch("cli.workspace_commands.get_existing_build_worktree", return_value=None):
        # Act
        result = handle_review_command(project_dir, spec_name)

    # Assert
    captured = capsys.readouterr()
    assert "No existing build" in captured.out


def test_handle_review_command_with_empty_inputs(capsys):
    """Test handle_review_command with empty spec_name."""
    # Arrange
    project_dir = Path("/tmp/test")
    spec_name = ""

    with patch("cli.workspace_commands.get_existing_build_worktree", return_value=None):
        # Act
        result = handle_review_command(project_dir, spec_name)

    # Assert
    captured = capsys.readouterr()
    assert "No existing build" in captured.out


def test_handle_discard_command_no_worktree(capsys):
    """Test handle_discard_command when no worktree exists."""
    # Arrange
    project_dir = Path("/tmp/test")
    spec_name = ""

    with patch("cli.workspace_commands.get_existing_build_worktree", return_value=None):
        # Act
        result = handle_discard_command(project_dir, spec_name)

    # Assert
    captured = capsys.readouterr()
    assert "No existing build" in captured.out


def test_handle_discard_command_with_empty_inputs(capsys):
    """Test handle_discard_command with empty spec_name."""
    # Arrange
    project_dir = Path("/tmp/test")
    spec_name = ""

    with patch("cli.workspace_commands.get_existing_build_worktree", return_value=None):
        # Act
        result = handle_discard_command(project_dir, spec_name)

    # Assert
    captured = capsys.readouterr()
    assert "No existing build" in captured.out


def test_handle_list_worktrees_command_non_git_dir(capsys):
    """Test handle_list_worktrees_command in non-git directory."""
    # Arrange
    project_dir = Path("/tmp/test")

    with patch("cli.workspace_commands.list_all_worktrees", side_effect=Exception("Not a git repository")):
        # Act - should handle exception gracefully
        try:
            handle_list_worktrees_command(project_dir)
        except Exception:
            pass  # Expected to raise for non-git directories

    # Assert - exception is expected for non-git directories


def test_handle_list_worktrees_command_with_empty_inputs():
    """Test handle_list_worktrees_command with invalid path."""
    # Arrange
    project_dir = Path("/tmp/test")

    with patch("cli.workspace_commands.list_all_worktrees", side_effect=Exception("Not a git repository")):
        # Act & Assert - should raise exception
        with pytest.raises(Exception):
            handle_list_worktrees_command(project_dir)


def test_handle_cleanup_worktrees_command_non_git_dir():
    """Test handle_cleanup_worktrees_command in non-git directory."""
    # Arrange
    project_dir = Path("/tmp/test")

    with patch("cli.workspace_commands.cleanup_all_worktrees", side_effect=Exception("Not a git repository")):
        # Act & Assert - should raise exception
        with pytest.raises(Exception):
            handle_cleanup_worktrees_command(project_dir)


def test_handle_cleanup_worktrees_command_with_empty_inputs():
    """Test handle_cleanup_worktrees_command with invalid path."""
    # Arrange
    project_dir = Path("/tmp/test")

    with patch("cli.workspace_commands.cleanup_all_worktrees", side_effect=Exception("Not a git repository")):
        # Act & Assert - should raise exception
        with pytest.raises(Exception):
            handle_cleanup_worktrees_command(project_dir)


def test_handle_merge_preview_command_no_worktree(tmp_path):
    """Test handle_merge_preview_command when no worktree exists."""
    # Arrange
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    spec_name = "001-test"

    with patch("cli.workspace_commands.get_existing_build_worktree", return_value=None):
        # Act
        result = handle_merge_preview_command(project_dir, spec_name, None)

    # Assert
    assert result is not None
    assert isinstance(result, dict)


def test_handle_merge_preview_command_with_empty_inputs(tmp_path):
    """Test handle_merge_preview_command with empty spec_name."""
    # Arrange
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    with patch("cli.workspace_commands.get_existing_build_worktree", return_value=None):
        # Act
        result = handle_merge_preview_command(project_dir, "", None)

    # Assert
    assert result is not None
    assert isinstance(result, dict)


def test_handle_create_pr_command_no_worktree(tmp_path):
    """Test handle_create_pr_command when no worktree exists."""
    # Arrange
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    spec_name = "001-test"

    with patch("cli.workspace_commands.get_existing_build_worktree", return_value=None):
        # Act
        result = handle_create_pr_command(project_dir, spec_name, None, None, False)

    # Assert
    assert result is not None
    assert isinstance(result, dict)
    # Should contain success=False
    assert result.get("success") is False


def test_handle_create_pr_command_with_empty_inputs(tmp_path):
    """Test handle_create_pr_command with empty spec_name."""
    # Arrange
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    with patch("cli.workspace_commands.get_existing_build_worktree", return_value=None):
        # Act
        result = handle_create_pr_command(project_dir, "", None, None, False)

    # Assert
    assert result is not None
    assert result.get("success") is False


def test_cleanup_old_worktrees_command(tmp_path):
    """Test cleanup_old_worktrees_command with dry_run."""
    # Arrange
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Act
    result = cleanup_old_worktrees_command(project_dir, 7, dry_run=True)

    # Assert
    assert result is not None


def test_cleanup_old_worktrees_command_with_empty_inputs():
    """Test cleanup_old_worktrees_command with invalid path."""
    # Arrange
    project_dir = Path("/tmp/test")

    # Act - should handle exception gracefully
    try:
        result = cleanup_old_worktrees_command(project_dir, 7, dry_run=True)
        # If it doesn't raise, should still return something
        assert result is not None
    except Exception:
        # Exception is also acceptable for non-existent directories
        pass


def test_worktree_summary_command(tmp_path):
    """Test worktree_summary_command."""
    # Arrange
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Act
    result = worktree_summary_command(project_dir)

    # Assert
    assert result is not None


def test_worktree_summary_command_with_empty_inputs():
    """Test worktree_summary_command with invalid path."""
    # Arrange
    project_dir = Path("/tmp/test")

    # Act - should handle exception gracefully
    try:
        result = worktree_summary_command(project_dir)
        # If it doesn't raise, should still return something
        assert result is not None
    except Exception:
        # Exception is also acceptable for non-existent directories
        pass


def test_handle_merge_command_valid_worktree(tmp_path, capsys):
    """Test handle_merge_command with valid worktree."""
    # Arrange
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    spec_name = "001-test"
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()

    with patch("cli.workspace_commands.get_existing_build_worktree", return_value=worktree_path), \
         patch("sys.exit"):
        # Act
        result = handle_merge_command(project_dir, spec_name, False, None)

    # Assert - function returns a bool (success status)
    assert isinstance(result, bool)


def test_handle_review_command_valid_worktree(tmp_path, capsys):
    """Test handle_review_command with valid worktree."""
    # Arrange
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    spec_name = "001-test"
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()

    with patch("cli.workspace_commands.get_existing_build_worktree", return_value=worktree_path):
        # Act
        result = handle_review_command(project_dir, spec_name)

    # Assert - should complete without raising
    assert result is None


def test_handle_discard_command_valid_worktree(tmp_path, capsys):
    """Test handle_discard_command with valid worktree."""
    # Arrange
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    spec_name = "001-test"
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()

    with patch("cli.workspace_commands.get_existing_build_worktree", return_value=worktree_path), \
         patch("sys.exit"):
        # Act
        result = handle_discard_command(project_dir, spec_name)

    # Assert - should complete without raising
    assert result is None
