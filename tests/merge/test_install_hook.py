"""Comprehensive tests for merge/install_hook.py"""

import argparse
import shutil
import stat
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
import pytest

from merge.install_hook import (
    find_project_root,
    install_hook,
    uninstall_hook,
    main,
    HOOK_SCRIPT,
)


class TestFindProjectRoot:
    """Tests for find_project_root function"""

    def test_find_project_root_with_git_dir(self):
        """Test finding project root when .git exists in current directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            (project_path / ".git").mkdir()

            with patch("pathlib.Path.cwd", return_value=project_path):
                result = find_project_root()
                assert result == project_path

    def test_find_project_root_traverses_up(self):
        """Test finding project root by traversing up directories"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            nested_path = project_path / "src" / "nested"
            nested_path.mkdir(parents=True)

            # Create .git only at project root
            (project_path / ".git").mkdir()

            with patch("pathlib.Path.cwd", return_value=nested_path):
                result = find_project_root()
                assert result == project_path

    def test_find_project_root_no_git_dir(self):
        """Test when no .git directory is found (returns cwd)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            current_path = Path(tmpdir) / "some" / "path"
            current_path.mkdir(parents=True)

            with patch("pathlib.Path.cwd", return_value=current_path):
                result = find_project_root()
                assert result == current_path


class TestInstallHook:
    """Tests for install_hook function"""

    def test_install_hook_fresh_install(self):
        """Test installing hook to fresh project (no existing hook)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            git_dir = project_path / ".git"
            git_dir.mkdir()
            hooks_dir = git_dir / "hooks"
            hooks_dir.mkdir()

            result = install_hook(project_path)

            assert result is True
            hook_path = hooks_dir / "post-commit"
            assert hook_path.exists()
            content = hook_path.read_text()
            assert "FileTimelineTracker" in content
            # Check it's executable
            assert hook_path.stat().st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def test_install_hook_already_installed(self):
        """Test when hook is already installed"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            git_dir = project_path / ".git"
            git_dir.mkdir()
            hooks_dir = git_dir / "hooks"
            hooks_dir.mkdir()
            hook_path = hooks_dir / "post-commit"

            # Write hook that already has FileTimelineTracker
            hook_path.write_text("#!/bin/bash\n# FileTimelineTracker integration\nexit 0\n")

            result = install_hook(project_path)

            assert result is True
            # Hook should not be modified
            content = hook_path.read_text()
            assert "FileTimelineTracker" in content

    def test_install_hook_backup_existing(self):
        """Test backing up existing hook before installing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            git_dir = project_path / ".git"
            git_dir.mkdir()
            hooks_dir = git_dir / "hooks"
            hooks_dir.mkdir()
            hook_path = hooks_dir / "post-commit"

            # Write existing hook without FileTimelineTracker
            hook_path.write_text("#!/bin/bash\nExisting hook content\n")

            result = install_hook(project_path)

            assert result is True
            # Backup should be created
            backup_path = hooks_dir / "post-commit.backup"
            assert backup_path.exists()
            backup_content = backup_path.read_text()
            assert "Existing hook content" in backup_content
            # New hook should have FileTimelineTracker
            new_content = hook_path.read_text()
            assert "FileTimelineTracker" in new_content

    def test_install_hook_no_git_dir(self):
        """Test when .git directory doesn't exist"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            # Don't create .git directory

            result = install_hook(project_path)

            assert result is False

    def test_install_hook_worktree_git_file(self):
        """Test installing hook in worktree where .git is a file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create the actual git directory
            actual_git_dir = Path(tmpdir) / "actual_git"
            actual_git_dir.mkdir()
            hooks_dir = actual_git_dir / "hooks"
            hooks_dir.mkdir(parents=True)

            # Create worktree directory
            worktree_path = Path(tmpdir) / "worktree"
            worktree_path.mkdir()
            git_file = worktree_path / ".git"

            # Write gitdir reference
            git_file.write_text(f"gitdir: {actual_git_dir}\n")

            result = install_hook(worktree_path)

            assert result is True
            hook_path = hooks_dir / "post-commit"
            assert hook_path.exists()

    def test_install_hook_unparseable_git_file(self):
        """Test when .git file cannot be parsed"""
        with tempfile.TemporaryDirectory() as tmpdir:
            worktree_path = Path(tmpdir) / "worktree"
            worktree_path.mkdir()
            git_file = worktree_path / ".git"

            # Write invalid git file content
            git_file.write_text("Invalid git file content")

            result = install_hook(worktree_path)

            assert result is False


class TestUninstallHook:
    """Tests for uninstall_hook function"""

    def test_uninstall_hook_remove_entirely(self):
        """Test removing hook entirely when no backup exists"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            git_dir = project_path / ".git"
            git_dir.mkdir()
            hooks_dir = git_dir / "hooks"
            hooks_dir.mkdir()
            hook_path = hooks_dir / "post-commit"

            # Create hook with FileTimelineTracker
            hook_path.write_text("#!/bin/bash\n# FileTimelineTracker integration\nexit 0\n")

            result = uninstall_hook(project_path)

            assert result is True
            assert not hook_path.exists()

    def test_uninstall_hook_restore_from_backup(self):
        """Test restoring hook from backup"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            git_dir = project_path / ".git"
            git_dir.mkdir()
            hooks_dir = git_dir / "hooks"
            hooks_dir.mkdir()
            hook_path = hooks_dir / "post-commit"
            backup_path = hooks_dir / "post-commit.backup"

            # Create backup
            original_hook = "#!/bin/bash\nOriginal hook\n"
            backup_path.write_text(original_hook)

            # Create hook with FileTimelineTracker
            hook_path.write_text("#!/bin/bash\n# FileTimelineTracker\nexit 0\n")

            result = uninstall_hook(project_path)

            assert result is True
            # Should restore from backup
            assert hook_path.read_text() == original_hook
            assert not backup_path.exists()

    def test_uninstall_hook_no_hook_exists(self):
        """Test uninstalling when hook doesn't exist"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            git_dir = project_path / ".git"
            git_dir.mkdir()
            hooks_dir = git_dir / "hooks"
            hooks_dir.mkdir()

            result = uninstall_hook(project_path)

            assert result is True

    def test_uninstall_hook_no_tracker_integration(self):
        """Test when hook doesn't contain FileTimelineTracker integration"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            git_dir = project_path / ".git"
            git_dir.mkdir()
            hooks_dir = git_dir / "hooks"
            hooks_dir.mkdir()
            hook_path = hooks_dir / "post-commit"

            hook_path.write_text("#!/bin/bash\nSome other hook\n")

            result = uninstall_hook(project_path)

            assert result is True
            # Hook should not be removed
            assert hook_path.exists()

    def test_uninstall_hook_worktree_git_file(self):
        """Test uninstalling hook in worktree"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create actual git directory
            actual_git_dir = Path(tmpdir) / "actual_git"
            actual_git_dir.mkdir()
            hooks_dir = actual_git_dir / "hooks"
            hooks_dir.mkdir(parents=True)
            hook_path = hooks_dir / "post-commit"

            # Create hook with FileTimelineTracker
            hook_path.write_text("#!/bin/bash\n# FileTimelineTracker\n")

            # Create worktree
            worktree_path = Path(tmpdir) / "worktree"
            worktree_path.mkdir()
            git_file = worktree_path / ".git"
            git_file.write_text(f"gitdir: {actual_git_dir}\n")

            result = uninstall_hook(worktree_path)

            assert result is True
            assert not hook_path.exists()


class TestMain:
    """Tests for main function"""

    @patch("merge.install_hook.install_hook")
    @patch("merge.install_hook.find_project_root")
    def test_main_default_install(self, mock_find_root, mock_install):
        """Test main with default arguments (install)"""
        mock_find_root.return_value = Path("/test/project")
        mock_install.return_value = True

        with patch("sys.argv", ["install_hook"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("merge.install_hook.uninstall_hook")
    @patch("merge.install_hook.find_project_root")
    def test_main_with_uninstall_flag(self, mock_find_root, mock_uninstall):
        """Test main with --uninstall flag"""
        mock_find_root.return_value = Path("/test/project")
        mock_uninstall.return_value = True

        with patch("sys.argv", ["install_hook", "--uninstall"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("merge.install_hook.install_hook")
    def test_main_with_project_path(self, mock_install):
        """Test main with --project-path argument"""
        mock_install.return_value = True

        with patch("sys.argv", ["install_hook", "--project-path", "/custom/path"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
            # Should use provided path without calling find_project_root

    @patch("merge.install_hook.install_hook")
    @patch("merge.install_hook.find_project_root")
    def test_main_install_fails(self, mock_find_root, mock_install):
        """Test main when install fails"""
        mock_find_root.return_value = Path("/test/project")
        mock_install.return_value = False

        with patch("sys.argv", ["install_hook"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    @patch("merge.install_hook.uninstall_hook")
    @patch("merge.install_hook.find_project_root")
    def test_main_uninstall_fails(self, mock_find_root, mock_uninstall):
        """Test main when uninstall fails"""
        mock_find_root.return_value = Path("/test/project")
        mock_uninstall.return_value = False

        with patch("sys.argv", ["install_hook", "--uninstall"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    @patch("merge.install_hook.uninstall_hook")
    def test_main_with_all_arguments(self, mock_uninstall):
        """Test main with project path and uninstall together"""
        mock_uninstall.return_value = True

        with patch("sys.argv", ["install_hook", "--project-path", "/custom", "--uninstall"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0


class TestHookScriptConstant:
    """Tests for HOOK_SCRIPT constant"""

    def test_hook_script_contains_shebang(self):
        """Test that HOOK_SCRIPT starts with proper shebang"""
        assert HOOK_SCRIPT.startswith("#!/bin/bash")

    def test_hook_script_contains_timeline_tracker_reference(self):
        """Test that HOOK_SCRIPT contains FileTimelineTracker reference"""
        assert "FileTimelineTracker" in HOOK_SCRIPT

    def test_hook_script_checks_main_branch(self):
        """Test that HOOK_SCRIPT checks for main/master branch"""
        # HOOK_SCRIPT uses [[ "$BRANCH" == "main" ]] syntax
        assert 'BRANCH' in HOOK_SCRIPT
        assert "main" in HOOK_SCRIPT
        assert "master" in HOOK_SCRIPT

    def test_hook_script_checks_git_directory(self):
        """Test that HOOK_SCRIPT checks for .git directory"""
        # HOOK_SCRIPT uses [[ -d ".git" ]] syntax
        assert ".git" in HOOK_SCRIPT

    def test_hook_script_calls_python(self):
        """Test that HOOK_SCRIPT calls Python for notification"""
        assert "python" in HOOK_SCRIPT.lower()
        assert "tracker_cli" in HOOK_SCRIPT
        assert "notify-commit" in HOOK_SCRIPT
