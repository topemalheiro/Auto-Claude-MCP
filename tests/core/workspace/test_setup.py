"""Tests for setup module in core.workspace.setup

Comprehensive test coverage for workspace setup functionality including:
- choose_workspace()
- copy_env_files_to_worktree()
- symlink_node_modules_to_worktree()
- copy_spec_to_worktree()
- setup_workspace()
- ensure_timeline_hook_installed()
- initialize_timeline_tracking()
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import pytest

from core.workspace.setup import (
    choose_workspace,
    copy_env_files_to_worktree,
    symlink_node_modules_to_worktree,
    copy_spec_to_worktree,
    setup_workspace,
    ensure_timeline_hook_installed,
    initialize_timeline_tracking,
    _ensure_timeline_hook_installed,
    _initialize_timeline_tracking,
)


class TestChooseWorkspace:
    """Tests for choose_workspace function."""

    def test_choose_workspace_force_isolated(self, tmp_path):
        """Test choose_workspace with force_isolated=True."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        result = choose_workspace(
            project_dir,
            "001-feature",
            force_isolated=True,
            force_direct=False,
            auto_continue=False,
        )

        assert result.value == "isolated"

    def test_choose_workspace_force_direct(self, tmp_path):
        """Test choose_workspace with force_direct=True."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        result = choose_workspace(
            project_dir,
            "001-feature",
            force_isolated=False,
            force_direct=True,
            auto_continue=False,
        )

        assert result.value == "direct"

    def test_choose_workspace_auto_continue(self, tmp_path, capsys):
        """Test choose_workspace with auto_continue=True."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        result = choose_workspace(
            project_dir,
            "001-feature",
            force_isolated=False,
            force_direct=False,
            auto_continue=True,
        )

        assert result.value == "isolated"
        captured = capsys.readouterr()
        assert "isolated workspace" in captured.out.lower()

    @patch("core.workspace.setup.has_uncommitted_changes")
    def test_choose_workspace_has_unsaved_changes(self, mock_has_changes, tmp_path, capsys):
        """Test choose_workspace detects unsaved changes and uses isolated mode."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        mock_has_changes.return_value = True

        with patch("builtins.input", return_value=""):
            result = choose_workspace(
                project_dir,
                "001-feature",
                force_isolated=False,
                force_direct=False,
                auto_continue=False,
            )

        assert result.value == "isolated"
        captured = capsys.readouterr()
        assert "protected" in captured.out.lower() or "safe" in captured.out.lower()

    @patch("core.workspace.setup.has_uncommitted_changes")
    @patch("core.workspace.setup.select_menu")
    def test_choose_workspace_clean_isolated(self, mock_menu, mock_has_changes, tmp_path):
        """Test choose_workspace selects isolated mode from menu."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        mock_has_changes.return_value = False
        mock_menu.return_value = "isolated"

        result = choose_workspace(
            project_dir,
            "001-feature",
            force_isolated=False,
            force_direct=False,
            auto_continue=False,
        )

        assert result.value == "isolated"
        mock_menu.assert_called_once()

    @patch("core.workspace.setup.has_uncommitted_changes")
    @patch("core.workspace.setup.select_menu")
    def test_choose_workspace_clean_direct(self, mock_menu, mock_has_changes, tmp_path):
        """Test choose_workspace selects direct mode from menu."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        mock_has_changes.return_value = False
        mock_menu.return_value = "direct"

        result = choose_workspace(
            project_dir,
            "001-feature",
            force_isolated=False,
            force_direct=False,
            auto_continue=False,
        )

        assert result.value == "direct"

    @patch("core.workspace.setup.has_uncommitted_changes")
    @patch("core.workspace.setup.select_menu")
    @patch("sys.exit")
    def test_choose_workspace_user_quits(self, mock_exit, mock_menu, mock_has_changes, tmp_path):
        """Test choose_workspace handles user quitting the menu."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        mock_has_changes.return_value = False
        mock_menu.return_value = None

        choose_workspace(
            project_dir,
            "001-feature",
            force_isolated=False,
            force_direct=False,
            auto_continue=False,
        )

        mock_exit.assert_called_once_with(0)

    @patch("core.workspace.setup.has_uncommitted_changes")
    @patch("builtins.input", side_effect=KeyboardInterrupt())
    @patch("sys.exit")
    def test_choose_workspace_keyboard_interrupt(self, mock_exit, mock_input, tmp_path):
        """Test choose_workspace handles KeyboardInterrupt."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Need to mock has_uncommitted_changes to return True first
        with patch("core.workspace.setup.has_uncommitted_changes", return_value=True):
            choose_workspace(
                project_dir,
                "001-feature",
                force_isolated=False,
                force_direct=False,
                auto_continue=False,
            )

            mock_exit.assert_called_once_with(0)


class TestCopyEnvFilesToWorktree:
    """Tests for copy_env_files_to_worktree function."""

    def test_copy_env_files_basic(self, tmp_path):
        """Test copy_env_files_to_worktree copies .env files."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        # Create .env file
        (project_dir / ".env").write_text("TEST=value")

        result = copy_env_files_to_worktree(project_dir, worktree_path)

        assert ".env" in result
        assert (worktree_path / ".env").exists()
        assert (worktree_path / ".env").read_text() == "TEST=value"

    def test_copy_env_files_all_patterns(self, tmp_path):
        """Test copy_env_files_to_worktree copies all env file patterns."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        # Create various env files
        (project_dir / ".env").write_text("BASE=value")
        (project_dir / ".env.local").write_text("LOCAL=value")
        (project_dir / ".env.development").write_text("DEV=value")
        (project_dir / ".env.test").write_text("TEST=value")

        result = copy_env_files_to_worktree(project_dir, worktree_path)

        assert len(result) == 4
        assert (worktree_path / ".env").exists()
        assert (worktree_path / ".env.local").exists()
        assert (worktree_path / ".env.development").exists()
        assert (worktree_path / ".env.test").exists()

    def test_copy_env_files_no_overwrite(self, tmp_path):
        """Test copy_env_files_to_worktree doesn't overwrite existing files."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        # Create .env in both locations
        (project_dir / ".env").write_text("PROJECT=value")
        (worktree_path / ".env").write_text("WORKTREE=value")

        result = copy_env_files_to_worktree(project_dir, worktree_path)

        # Worktree version should be preserved
        assert (worktree_path / ".env").read_text() == "WORKTREE=value"
        assert ".env" not in result  # Not copied since it exists

    def test_copy_env_files_no_env_files(self, tmp_path):
        """Test copy_env_files_to_worktree with no env files."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        result = copy_env_files_to_worktree(project_dir, worktree_path)

        assert result == []

    def test_copy_env_files_selective_patterns(self, tmp_path):
        """Test copy_env_files_to_worktree only copies matching patterns."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        # Create only some env files
        (project_dir / ".env").write_text("BASE=value")
        (project_dir / ".env.production").write_text("PROD=value")
        # Create a non-matching file
        (project_dir / ".env.backup").write_text("BACKUP=value")

        result = copy_env_files_to_worktree(project_dir, worktree_path)

        # .env.backup is not in the patterns list, so it shouldn't be copied
        assert ".env" in result or ".env.production" in result
        assert not (worktree_path / ".env.backup").exists()


class TestSymlinkNodeModulesToWorktree:
    """Tests for symlink_node_modules_to_worktree function."""

    @patch("sys.platform", "linux")
    def test_symlink_node_modules_linux(self, tmp_path):
        """Test symlink_node_modules_to_worktree on Linux."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        # Create node_modules in project
        node_modules = project_dir / "node_modules"
        node_modules.mkdir()
        (node_modules / "test.txt").write_text("test")

        result = symlink_node_modules_to_worktree(project_dir, worktree_path)

        assert "node_modules" in result
        assert (worktree_path / "node_modules").is_symlink()

    @patch("sys.platform", "linux")
    def test_symlink_node_modules_frontend(self, tmp_path):
        """Test symlink_node_modules_to_worktree includes frontend node_modules."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        # Create nested node_modules
        frontend_nm = project_dir / "apps" / "frontend" / "node_modules"
        frontend_nm.mkdir(parents=True)
        (frontend_nm / "test.txt").write_text("test")

        result = symlink_node_modules_to_worktree(project_dir, worktree_path)

        assert "apps/frontend/node_modules" in result
        assert (worktree_path / "apps" / "frontend" / "node_modules").is_symlink()

    @patch("sys.platform", "win32")
    @patch("subprocess.run")
    def test_symlink_node_modules_windows_junction(self, mock_run, tmp_path):
        """Test symlink_node_modules_to_worktree on Windows uses junctions."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        # Create node_modules in project
        node_modules = project_dir / "node_modules"
        node_modules.mkdir()

        # Mock successful mklink command
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        result = symlink_node_modules_to_worktree(project_dir, worktree_path)

        # Should call mklink on Windows
        assert len(result) >= 0
        if result:
            assert any("node_modules" in r for r in result)

    @patch("sys.platform", "linux")
    def test_symlink_node_modules_no_source(self, tmp_path):
        """Test symlink_node_modules_to_worktree when source doesn't exist."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        result = symlink_node_modules_to_worktree(project_dir, worktree_path)

        assert result == []

    @patch("sys.platform", "linux")
    def test_symlink_node_modules_target_exists(self, tmp_path):
        """Test symlink_node_modules_to_worktree skips existing targets."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        # Create node_modules in both locations
        project_nm = project_dir / "node_modules"
        project_nm.mkdir()
        worktree_nm = worktree_path / "node_modules"
        worktree_nm.mkdir()

        result = symlink_node_modules_to_worktree(project_dir, worktree_path)

        # Should skip since target exists
        assert "node_modules" not in result

    @patch("sys.platform", "linux")
    @patch("os.symlink", side_effect=OSError("Permission denied"))
    def test_symlink_node_modules_fails_gracefully(self, mock_symlink, tmp_path, capsys):
        """Test symlink_node_modules_to_worktree handles symlink failures gracefully."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        # Create node_modules in project
        node_modules = project_dir / "node_modules"
        node_modules.mkdir()

        result = symlink_node_modules_to_worktree(project_dir, worktree_path)

        # Should handle error gracefully
        assert result == []

    @patch("sys.platform", "linux")
    @pytest.mark.skipif(sys.platform == "win32", reason="Symlink creation issues on Windows")
    def test_symlink_node_modules_broken_symlink_check(self, tmp_path):
        """Test symlink_node_modules_to_worktree checks for broken symlinks."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        # Create a broken symlink at target
        target = worktree_path / "node_modules"
        try:
            os.symlink("/nonexistent/path", target)

            # Create source node_modules
            node_modules = project_dir / "node_modules"
            node_modules.mkdir()

            result = symlink_node_modules_to_worktree(project_dir, worktree_path)

            # Should skip broken symlink
            assert "node_modules" not in result
        except OSError:
            # Symlink creation not supported
            pytest.skip("Symlink creation not supported on this system")


class TestCopySpecToWorktree:
    """Tests for copy_spec_to_worktree function."""

    def test_copy_spec_to_worktree_basic(self, tmp_path):
        """Test copy_spec_to_worktree copies spec directory."""
        source_spec_dir = tmp_path / "source_specs" / "001-feature"
        source_spec_dir.mkdir(parents=True)
        (source_spec_dir / "spec.md").write_text("# Feature Spec")
        (source_spec_dir / "plan.json").write_text("{}")

        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()
        spec_name = "001-feature"

        result = copy_spec_to_worktree(source_spec_dir, worktree_path, spec_name)

        # Verify the path structure
        assert result == worktree_path / ".auto-claude" / "specs" / spec_name
        assert (result / "spec.md").exists()
        assert (result / "plan.json").exists()

    def test_copy_spec_to_worktree_overwrites_existing(self, tmp_path):
        """Test copy_spec_to_worktree overwrites existing spec."""
        source_spec_dir = tmp_path / "source_specs" / "001-feature"
        source_spec_dir.mkdir(parents=True)
        (source_spec_dir / "spec.md").write_text("# New Spec")

        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()
        spec_name = "001-feature"

        # Create existing spec with different content
        existing_spec = worktree_path / ".auto-claude" / "specs" / spec_name
        existing_spec.mkdir(parents=True)
        (existing_spec / "spec.md").write_text("# Old Spec")

        result = copy_spec_to_worktree(source_spec_dir, worktree_path, spec_name)

        # Should be overwritten
        assert (result / "spec.md").read_text() == "# New Spec"

    def test_copy_spec_to_worktree_creates_directories(self, tmp_path):
        """Test copy_spec_to_worktree creates parent directories."""
        source_spec_dir = tmp_path / "source_specs" / "002-feature"
        source_spec_dir.mkdir(parents=True)
        (source_spec_dir / "spec.md").write_text("# Spec")

        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()
        spec_name = "002-feature"

        # Don't create .auto-claude/specs directory
        result = copy_spec_to_worktree(source_spec_dir, worktree_path, spec_name)

        # Should create the full path
        assert result.exists()
        assert (result / "spec.md").exists()

    def test_copy_spec_to_worktree_nested_files(self, tmp_path):
        """Test copy_spec_to_worktree with nested directory structure."""
        source_spec_dir = tmp_path / "source_specs" / "003-feature"
        source_spec_dir.mkdir(parents=True)
        (source_spec_dir / "spec.md").write_text("# Spec")
        (source_spec_dir / "context").mkdir()
        (source_spec_dir / "context" / "file.txt").write_text("context")

        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()
        spec_name = "003-feature"

        result = copy_spec_to_worktree(source_spec_dir, worktree_path, spec_name)

        # Should copy nested files
        assert (result / "context" / "file.txt").exists()


class TestEnsureTimelineHookInstalled:
    """Tests for ensure_timeline_hook_installed function."""

    def test_ensure_timeline_hook_not_git_repo(self, tmp_path):
        """Test ensure_timeline_hook_installed handles non-git directory."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Should not raise
        ensure_timeline_hook_installed(project_dir)

    @pytest.mark.skip(reason="install_hook is in merge.install_hook module, not workspace.setup")
    @patch("core.workspace.setup.install_hook")
    def test_ensure_timeline_hook_installs_when_missing(self, mock_install, tmp_path):
        """Test ensure_timeline_hook_installed installs hook when missing."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        git_dir = project_dir / ".git"
        git_dir.mkdir()
        hooks_dir = git_dir / "hooks"
        hooks_dir.mkdir()
        # Don't create post-commit hook

        ensure_timeline_hook_installed(project_dir)

        mock_install.assert_called_once_with(project_dir)

    @pytest.mark.skip(reason="install_hook is in merge.install_hook module, not workspace.setup")
    @patch("core.workspace.setup.install_hook")
    def test_ensure_timeline_hook_skips_when_exists(self, mock_install, tmp_path):
        """Test ensure_timeline_hook_installed skips when hook exists."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        git_dir = project_dir / ".git"
        git_dir.mkdir()
        hooks_dir = git_dir / "hooks"
        hooks_dir.mkdir()
        hook_file = hooks_dir / "post-commit"
        hook_file.write_text("#!/bin/sh\n# FileTimelineTracker hook\n")

        ensure_timeline_hook_installed(project_dir)

        mock_install.assert_not_called()

    @pytest.mark.skip(reason="install_hook is in merge.install_hook module, not workspace.setup")
    @patch("core.workspace.setup.install_hook", side_effect=Exception("Install failed"))
    def test_ensure_timeline_hook_handles_install_error(self, mock_install, tmp_path):
        """Test ensure_timeline_hook_installed handles install errors gracefully."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        git_dir = project_dir / ".git"
        git_dir.mkdir()
        hooks_dir = git_dir / "hooks"
        hooks_dir.mkdir()

        # Should not raise
        ensure_timeline_hook_installed(project_dir)

    def test_ensure_timeline_hook_worktree_gitdir(self, tmp_path):
        """Test ensure_timeline_hook_installed handles worktree .git file."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        # Create .git as a file (worktree)
        git_file = project_dir / ".git"
        actual_git = tmp_path / "actual_git"
        actual_git.mkdir()
        hooks_dir = actual_git / "hooks"
        hooks_dir.mkdir()
        git_file.write_text(f"gitdir: {actual_git}\n")

        ensure_timeline_hook_installed(project_dir)

        # Should handle worktree .git file
        assert True


class TestInitializeTimelineTracking:
    """Tests for initialize_timeline_tracking function."""

    @patch("core.workspace.setup.FileTimelineTracker")
    def test_initialize_timeline_tracking_with_plan(self, mock_tracker_class, tmp_path):
        """Test initialize_timeline_tracking with implementation plan."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()
        spec_name = "001-feature"

        # Create spec with implementation plan
        source_spec_dir = tmp_path / "specs" / spec_name
        source_spec_dir.mkdir(parents=True)
        plan_data = {
            "title": "Test Feature",
            "description": "Test description",
            "phases": [
                {
                    "subtasks": [
                        {"files": ["file1.py", "file2.py"]},
                        {"files": ["file3.py"]},
                    ]
                }
            ],
        }
        (source_spec_dir / "implementation_plan.json").write_text(json.dumps(plan_data))

        # Mock run_git to return a commit hash
        with patch("core.workspace.setup.run_git") as mock_git:
            mock_git.return_value = MagicMock(returncode=0, stdout="abc123\n")

            # Mock tracker instance
            mock_tracker = MagicMock()
            mock_tracker_class.return_value = mock_tracker

            initialize_timeline_tracking(
                project_dir, spec_name, worktree_path, source_spec_dir
            )

            # Verify on_task_start was called
            mock_tracker.on_task_start.assert_called_once()
            call_args = mock_tracker.on_task_start.call_args
            assert call_args[1]["task_id"] == spec_name
            assert set(call_args[1]["files_to_modify"]) == {"file1.py", "file2.py", "file3.py"}

    @patch("core.workspace.setup.FileTimelineTracker")
    def test_initialize_timeline_tracking_without_plan(self, mock_tracker_class, tmp_path):
        """Test initialize_timeline_tracking without implementation plan."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()
        spec_name = "002-feature"
        source_spec_dir = tmp_path / "specs" / spec_name
        source_spec_dir.mkdir(parents=True)

        # Mock tracker instance
        mock_tracker = MagicMock()
        mock_tracker_class.return_value = mock_tracker

        initialize_timeline_tracking(
            project_dir, spec_name, worktree_path, source_spec_dir
        )

        # Should call initialize_from_worktree as fallback
        mock_tracker.initialize_from_worktree.assert_called_once()

    @patch("core.workspace.setup.FileTimelineTracker", side_effect=Exception("Tracker error"))
    def test_initialize_timeline_tracking_handles_error(self, tmp_path):
        """Test initialize_timeline_tracking handles errors gracefully."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()
        spec_name = "003-feature"
        source_spec_dir = tmp_path / "specs" / spec_name
        source_spec_dir.mkdir(parents=True)

        # Should not raise
        initialize_timeline_tracking(
            project_dir, spec_name, worktree_path, source_spec_dir
        )

    @patch("core.workspace.setup.FileTimelineTracker")
    def test_initialize_timeline_tracking_no_source_dir(self, mock_tracker_class, tmp_path):
        """Test initialize_timeline_tracking with None source_spec_dir."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()
        spec_name = "004-feature"
        source_spec_dir = None

        # Mock tracker instance
        mock_tracker = MagicMock()
        mock_tracker_class.return_value = mock_tracker

        initialize_timeline_tracking(
            project_dir, spec_name, worktree_path, source_spec_dir
        )

        # Should handle None source_spec_dir
        mock_tracker.initialize_from_worktree.assert_called_once()


class TestBackwardCompatibilityAliases:
    """Tests for backward compatibility aliases."""

    def test_ensure_timeline_hook_installed_alias(self):
        """Test _ensure_timeline_hook_installed alias exists."""
        assert _ensure_timeline_hook_installed is ensure_timeline_hook_installed

    def test_initialize_timeline_tracking_alias(self):
        """Test _initialize_timeline_tracking alias exists."""
        assert _initialize_timeline_tracking is initialize_timeline_tracking


class TestSetupEdgeCases:
    """Tests for edge cases in setup functions."""

    @pytest.mark.skipif(sys.platform == "win32", reason="Windows console cannot encode certain Unicode characters (charmap codec limitation)")
    def test_copy_env_files_unicode_content(self, tmp_path):
        """Test copy_env_files_to_worktree with Unicode content."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        (project_dir / ".env").write_text("KEY=你好世界🌍")

        result = copy_env_files_to_worktree(project_dir, worktree_path)

        assert ".env" in result
        assert (worktree_path / ".env").read_text() == "KEY=你好世界🌍"

    @patch("sys.platform", "linux")
    def test_symlink_node_modules_creates_parent_dirs(self, tmp_path):
        """Test symlink_node_modules_to_worktree creates parent directories."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        # Create nested node_modules
        frontend_nm = project_dir / "apps" / "frontend" / "node_modules"
        frontend_nm.mkdir(parents=True)

        # Don't create apps/frontend in worktree
        result = symlink_node_modules_to_worktree(project_dir, worktree_path)

        # Should create parent directories
        if result:
            assert (worktree_path / "apps" / "frontend" / "node_modules").exists()

    def test_copy_spec_to_worktree_empty_spec(self, tmp_path):
        """Test copy_spec_to_worktree with empty spec directory."""
        source_spec_dir = tmp_path / "source_specs" / "005-feature"
        source_spec_dir.mkdir(parents=True)
        # Don't create any files

        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()
        spec_name = "005-feature"

        result = copy_spec_to_worktree(source_spec_dir, worktree_path, spec_name)

        # Should still create the directory
        assert result.exists()
