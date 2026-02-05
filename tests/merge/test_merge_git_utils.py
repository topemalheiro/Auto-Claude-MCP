"""Comprehensive tests for merge/git_utils.py"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock, mock_open
import pytest

from merge.git_utils import find_worktree, get_file_from_branch


class TestFindWorktree:
    """Tests for find_worktree function"""

    @patch("merge.git_utils.Path.exists")
    @patch("merge.git_utils.Path.iterdir")
    def test_find_worktree_in_new_path(self, mock_iterdir, mock_exists):
        """Test finding worktree in new .auto-claude/worktrees/tasks path"""
        project_dir = Path("/tmp/test_project")
        task_id = "task-001-feature"

        # Always return True for exists check
        mock_exists.return_value = True

        # Mock worktree entries
        entry1 = MagicMock()
        entry1.is_dir.return_value = True
        entry1.name = "task-001-feature-branch1"

        entry2 = MagicMock()
        entry2.is_dir.return_value = True
        entry2.name = "task-002-other-branch"

        mock_iterdir.return_value = [entry1, entry2]

        result = find_worktree(project_dir, task_id)

        assert result == entry1

    @patch("merge.git_utils.Path.exists")
    @patch("merge.git_utils.Path.iterdir")
    def test_find_worktree_not_found(self, mock_iterdir, mock_exists):
        """Test when worktree is not found"""
        project_dir = Path("/tmp/test_project")
        task_id = "nonexistent-task"

        mock_exists.return_value = True
        mock_iterdir.return_value = []

        result = find_worktree(project_dir, task_id)

        assert result is None

    @patch("merge.git_utils.Path.exists")
    def test_find_worktree_no_worktrees_dir(self, mock_exists):
        """Test when worktrees directories don't exist"""
        project_dir = Path("/tmp/test_project")
        task_id = "task-001"

        mock_exists.return_value = False

        result = find_worktree(project_dir, task_id)

        assert result is None

    @patch("merge.git_utils.Path.exists")
    @patch("merge.git_utils.Path.iterdir")
    def test_find_worktree_task_id_not_in_name(self, mock_iterdir, mock_exists):
        """Test when task_id is not contained in any directory name"""
        project_dir = Path("/tmp/test_project")
        task_id = "task-001"

        mock_exists.return_value = True

        entry = MagicMock()
        entry.is_dir.return_value = True
        entry.name = "some-other-worktree"

        mock_iterdir.return_value = [entry]

        result = find_worktree(project_dir, task_id)

        assert result is None

    @patch("merge.git_utils.Path.exists")
    @patch("merge.git_utils.Path.iterdir")
    def test_find_worktree_multiple_matches(self, mock_iterdir, mock_exists):
        """Test when multiple directories contain the task_id (returns first)"""
        project_dir = Path("/tmp/test_project")
        task_id = "task-001"

        mock_exists.return_value = True

        entry1 = MagicMock()
        entry1.is_dir.return_value = True
        entry1.name = "task-001-feature"

        entry2 = MagicMock()
        entry2.is_dir.return_value = True
        entry2.name = "task-001-bugfix"

        mock_iterdir.return_value = [entry1, entry2]

        result = find_worktree(project_dir, task_id)

        # Should return the first match
        assert result == entry1

    @patch("merge.git_utils.Path.exists")
    @patch("merge.git_utils.Path.iterdir")
    def test_find_worktree_with_non_directory_entries(self, mock_iterdir, mock_exists):
        """Test that non-directory entries are skipped"""
        project_dir = Path("/tmp/test_project")
        task_id = "task-001"

        mock_exists.return_value = True

        file_entry = MagicMock()
        file_entry.is_dir.return_value = False
        file_entry.name = "task-001-file.txt"

        dir_entry = MagicMock()
        dir_entry.is_dir.return_value = True
        dir_entry.name = "task-001-directory"

        mock_iterdir.return_value = [file_entry, dir_entry]

        result = find_worktree(project_dir, task_id)

        # Should return the directory, not the file
        assert result == dir_entry

    @patch("merge.git_utils.Path.exists")
    @patch("merge.git_utils.Path.iterdir")
    def test_find_worktree_partial_match(self, mock_iterdir, mock_exists):
        """Test partial string matching of task_id in directory name"""
        project_dir = Path("/tmp/test_project")
        task_id = "feature"

        mock_exists.return_value = True

        entry = MagicMock()
        entry.is_dir.return_value = True
        entry.name = "task-001-feature-branch"

        mock_iterdir.return_value = [entry]

        result = find_worktree(project_dir, task_id)

        assert result == entry


class TestGetFileFromBranch:
    """Tests for get_file_from_branch function"""

    @patch("subprocess.run")
    def test_get_file_from_branch_success(self, mock_run):
        """Test successfully getting file content from branch"""
        project_dir = Path("/tmp/test_project")
        file_path = "src/main.py"
        branch = "feature-branch"
        expected_content = "def hello():\n    print('world')"

        mock_run.return_value = MagicMock(
            stdout=expected_content,
            returncode=0
        )

        result = get_file_from_branch(project_dir, file_path, branch)

        assert result == expected_content
        mock_run.assert_called_once_with(
            ["git", "show", f"{branch}:{file_path}"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            check=True,
        )

    @patch("subprocess.run")
    def test_get_file_from_branch_file_not_exists(self, mock_run):
        """Test when file doesn't exist on branch (CalledProcessError)"""
        project_dir = Path("/tmp/test_project")
        file_path = "nonexistent.py"
        branch = "main"

        mock_run.side_effect = subprocess.CalledProcessError(
            1, "git", stderr="fatal: invalid path"
        )

        result = get_file_from_branch(project_dir, file_path, branch)

        assert result is None

    @patch("subprocess.run")
    def test_get_file_from_branch_empty_file(self, mock_run):
        """Test getting an empty file"""
        project_dir = Path("/tmp/test_project")
        file_path = "empty.txt"
        branch = "main"

        mock_run.return_value = MagicMock(
            stdout="",
            returncode=0
        )

        result = get_file_from_branch(project_dir, file_path, branch)

        assert result == ""

    @patch("subprocess.run")
    def test_get_file_from_branch_with_special_characters(self, mock_run):
        """Test file path with special characters"""
        project_dir = Path("/tmp/test_project")
        file_path = "src/path with spaces/file.py"
        branch = "feature"
        expected_content = "# content"

        mock_run.return_value = MagicMock(
            stdout=expected_content,
            returncode=0
        )

        result = get_file_from_branch(project_dir, file_path, branch)

        assert result == expected_content

    @patch("subprocess.run")
    def test_get_file_from_branch_binary_file(self, mock_run):
        """Test handling binary file content"""
        project_dir = Path("/tmp/test_project")
        file_path = "image.png"
        branch = "main"
        binary_content = b'\x89PNG\r\n\x1a\n\x00\x00\x00'

        mock_run.return_value = MagicMock(
            stdout=binary_content.decode('latin1'),
            returncode=0
        )

        result = get_file_from_branch(project_dir, file_path, branch)

        # Binary content comes through as text
        assert result is not None

    @patch("subprocess.run")
    def test_get_file_from_branch_multiline_content(self, mock_run):
        """Test getting file with multiline content"""
        project_dir = Path("/tmp/test_project")
        file_path = "config.ini"
        branch = "main"
        content = "[section1]\nkey1=value1\n\n[section2]\nkey2=value2"

        mock_run.return_value = MagicMock(
            stdout=content,
            returncode=0
        )

        result = get_file_from_branch(project_dir, file_path, branch)

        assert result == content
        assert "\n" in result

    @patch("subprocess.run")
    def test_get_file_from_branch_unicode_content(self, mock_run):
        """Test getting file with unicode content"""
        project_dir = Path("/tmp/test_project")
        file_path = "README.md"
        branch = "main"
        content = "# Hello World\n\nBonjour le monde\n\nHola mundo"

        mock_run.return_value = MagicMock(
            stdout=content,
            returncode=0
        )

        result = get_file_from_branch(project_dir, file_path, branch)

        assert result == content
        assert "monde" in result

    @patch("subprocess.run")
    def test_get_file_from_branch_trailing_newline(self, mock_run):
        """Test getting file with trailing newline"""
        project_dir = Path("/tmp/test_project")
        file_path = "data.txt"
        branch = "main"
        content = "line1\nline2\n"

        mock_run.return_value = MagicMock(
            stdout=content,
            returncode=0
        )

        result = get_file_from_branch(project_dir, file_path, branch)

        assert result == "line1\nline2\n"
        assert result.endswith("\n")

    @patch("subprocess.run")
    def test_get_file_from_branch_permission_error(self, mock_run):
        """Test when git command fails with permission error"""
        project_dir = Path("/tmp/test_project")
        file_path = "secret.py"
        branch = "main"

        mock_run.side_effect = subprocess.CalledProcessError(
            128, "git", stderr="fatal: permission denied"
        )

        result = get_file_from_branch(project_dir, file_path, branch)

        assert result is None
