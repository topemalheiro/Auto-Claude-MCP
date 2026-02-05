"""Tests for init.py - Project initialization utilities"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from init import (
    AUTO_CLAUDE_GITIGNORE_ENTRIES,
    _entry_exists_in_gitignore,
    _is_git_repo,
    _commit_gitignore,
    ensure_gitignore_entry,
    ensure_all_gitignore_entries,
    init_auto_claude_dir,
    get_auto_claude_dir,
    repair_gitignore,
)


class TestEntryExistsInGitignore:
    """Tests for _entry_exists_in_gitignore helper function"""

    def test_entry_exists_exact_match(self):
        """Test exact match of entry in gitignore"""
        lines = [".auto-claude/", "*.pyc", "node_modules/"]
        assert _entry_exists_in_gitignore(lines, ".auto-claude/")

    def test_entry_exists_without_trailing_slash(self):
        """Test entry exists without trailing slash in gitignore"""
        lines = [".auto-claude", "*.pyc"]
        assert _entry_exists_in_gitignore(lines, ".auto-claude/")

    def test_entry_exists_with_trailing_slash(self):
        """Test entry exists with trailing slash in gitignore"""
        lines = [".auto-claude/", "*.pyc"]
        assert _entry_exists_in_gitignore(lines, ".auto-claude")

    def test_entry_not_exists(self):
        """Test entry does not exist in gitignore"""
        lines = ["*.pyc", "node_modules/"]
        assert not _entry_exists_in_gitignore(lines, ".auto-claude/")

    def test_entry_exists_with_whitespace(self):
        """Test entry match with leading/trailing whitespace"""
        lines = ["  .auto-claude/  ", "*.pyc"]
        assert _entry_exists_in_gitignore(lines, ".auto-claude/")

    def test_entry_exists_case_sensitive(self):
        """Test entry matching is case sensitive"""
        lines = [".Auto-Claude/"]
        assert not _entry_exists_in_gitignore(lines, ".auto-claude/")


class TestEnsureGitignoreEntry:
    """Tests for ensure_gitignore_entry function"""

    def test_creates_new_gitignore(self, tmp_path):
        """Test creates new .gitignore with entry"""
        # Arrange
        entry = ".auto-claude/"

        # Act
        result = ensure_gitignore_entry(tmp_path, entry)

        # Assert
        assert result is True
        gitignore_path = tmp_path / ".gitignore"
        assert gitignore_path.exists()
        content = gitignore_path.read_text(encoding="utf-8")
        assert entry in content
        assert "# Auto Claude data directory" in content

    def test_entry_already_exists(self, tmp_path):
        """Test returns False when entry already exists"""
        # Arrange
        entry = ".auto-claude/"
        gitignore_path = tmp_path / ".gitignore"
        gitignore_path.write_text(f"{entry}\n", encoding="utf-8")

        # Act
        result = ensure_gitignore_entry(tmp_path, entry)

        # Assert
        assert result is False
        content = gitignore_path.read_text(encoding="utf-8")
        # Content should not have been modified (no comment added)
        assert content == f"{entry}\n"
        assert "# Auto Claude data directory" not in content

    def test_appends_to_existing_gitignore(self, tmp_path):
        """Test appends entry to existing .gitignore"""
        # Arrange
        entry = ".auto-claude/"
        gitignore_path = tmp_path / ".gitignore"
        gitignore_path.write_text("*.pyc\nnode_modules/\n", encoding="utf-8")

        # Act
        result = ensure_gitignore_entry(tmp_path, entry)

        # Assert
        assert result is True
        content = gitignore_path.read_text(encoding="utf-8")
        assert "*.pyc" in content
        assert "node_modules/" in content
        assert entry in content
        assert "# Auto Claude data directory" in content

    def test_adds_newline_if_missing(self, tmp_path):
        """Test adds newline before entry if file doesn't end with one"""
        # Arrange
        entry = ".auto-claude/"
        gitignore_path = tmp_path / ".gitignore"
        gitignore_path.write_text("*.pyc", encoding="utf-8")  # No trailing newline

        # Act
        result = ensure_gitignore_entry(tmp_path, entry)

        # Assert
        assert result is True
        content = gitignore_path.read_text(encoding="utf-8")
        assert content.endswith("\n")
        assert entry in content

    def test_custom_entry(self, tmp_path):
        """Test with custom entry"""
        # Arrange
        entry = ".custom-dir/"

        # Act
        result = ensure_gitignore_entry(tmp_path, entry)

        # Assert
        assert result is True
        gitignore_path = tmp_path / ".gitignore"
        content = gitignore_path.read_text(encoding="utf-8")
        assert entry in content


class TestIsGitRepo:
    """Tests for _is_git_repo function"""

    @patch("init.get_git_executable")
    @patch("subprocess.run")
    def test_is_git_repo_success(self, mock_run, mock_git, tmp_path):
        """Test returns True when inside git repo"""
        # Arrange
        mock_run.return_value = MagicMock(returncode=0, stdout="true\n")
        mock_git.return_value = "git"

        # Act
        result = _is_git_repo(tmp_path)

        # Assert
        assert result is True
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "rev-parse" in args
        assert "--is-inside-work-tree" in args

    @patch("init.get_git_executable")
    @patch("subprocess.run")
    def test_is_git_repo_failure(self, mock_run, mock_git, tmp_path):
        """Test returns False when not inside git repo"""
        # Arrange
        mock_run.return_value = MagicMock(returncode=128, stdout="", stderr="fatal: not a git repository")
        mock_git.return_value = "git"

        # Act
        result = _is_git_repo(tmp_path)

        # Assert
        assert result is False

    @patch("init.get_git_executable")
    @patch("subprocess.run")
    def test_is_git_repo_timeout(self, mock_run, mock_git, tmp_path):
        """Test returns False when subprocess times out"""
        # Arrange
        mock_run.side_effect = subprocess.TimeoutExpired("git", 10)
        mock_git.return_value = "git"

        # Act
        result = _is_git_repo(tmp_path)

        # Assert
        assert result is False

    @patch("init.get_git_executable")
    @patch("subprocess.run")
    def test_is_git_repo_exception(self, mock_run, mock_git, tmp_path):
        """Test returns False on any exception"""
        # Arrange
        mock_run.side_effect = OSError("Command failed")
        mock_git.return_value = "git"

        # Act
        result = _is_git_repo(tmp_path)

        # Assert
        assert result is False


class TestCommitGitignore:
    """Tests for _commit_gitignore function"""

    @patch("init._is_git_repo")
    @patch("init.get_git_executable")
    @patch("subprocess.run")
    def test_commit_success(self, mock_run, mock_git, mock_is_repo, tmp_path):
        """Test successful git commit"""
        # Arrange
        mock_is_repo.return_value = True
        mock_git.return_value = "git"
        mock_run.side_effect = [
            MagicMock(returncode=0),  # git add
            MagicMock(returncode=0),  # git commit
        ]

        # Act
        result = _commit_gitignore(tmp_path)

        # Assert
        assert result is True
        assert mock_run.call_count == 2

    @patch("init._is_git_repo")
    @patch("init.get_git_executable")
    @patch("subprocess.run")
    def test_commit_nothing_to_commit(self, mock_run, mock_git, mock_is_repo, tmp_path):
        """Test commit returns True when nothing to commit"""
        # Arrange
        mock_is_repo.return_value = True
        mock_git.return_value = "git"
        mock_run.side_effect = [
            MagicMock(returncode=0),  # git add
            MagicMock(
                returncode=1,
                stdout="",
                stderr="nothing to commit, working tree clean"
            ),  # git commit
        ]

        # Act
        result = _commit_gitignore(tmp_path)

        # Assert
        assert result is True

    @patch("init._is_git_repo")
    @patch("init.get_git_executable")
    @patch("subprocess.run")
    def test_commit_not_git_repo(self, mock_run, mock_git, mock_is_repo, tmp_path):
        """Test returns False when not a git repo"""
        # Arrange
        mock_is_repo.return_value = False
        mock_git.return_value = "git"

        # Act
        result = _commit_gitignore(tmp_path)

        # Assert
        assert result is False
        mock_run.assert_not_called()

    @patch("init._is_git_repo")
    @patch("init.get_git_executable")
    @patch("subprocess.run")
    def test_commit_add_fails(self, mock_run, mock_git, mock_is_repo, tmp_path):
        """Test returns False when git add fails"""
        # Arrange
        mock_is_repo.return_value = True
        mock_git.return_value = "git"
        mock_run.return_value = MagicMock(returncode=128)

        # Act
        result = _commit_gitignore(tmp_path)

        # Assert
        assert result is False

    @patch("init._is_git_repo")
    @patch("init.get_git_executable")
    @patch("subprocess.run")
    def test_commit_timeout(self, mock_run, mock_git, mock_is_repo, tmp_path):
        """Test returns False on timeout"""
        # Arrange
        mock_is_repo.return_value = True
        mock_git.return_value = "git"
        mock_run.side_effect = subprocess.TimeoutExpired("git", 30)

        # Act
        result = _commit_gitignore(tmp_path)

        # Assert
        assert result is False

    @patch("init._is_git_repo")
    @patch("init.get_git_executable")
    @patch("subprocess.run")
    def test_commit_uses_correct_env(self, mock_run, mock_git, mock_is_repo, tmp_path):
        """Test commit uses LC_ALL=C environment"""
        # Arrange
        mock_is_repo.return_value = True
        mock_git.return_value = "git"
        mock_run.side_effect = [
            MagicMock(returncode=0),
            MagicMock(returncode=0),
        ]

        # Act
        _commit_gitignore(tmp_path)

        # Assert
        for call in mock_run.call_args_list:
            env = call.kwargs.get("env", {})
            assert "LC_ALL" in env
            assert env["LC_ALL"] == "C"


class TestEnsureAllGitignoreEntries:
    """Tests for ensure_all_gitignore_entries function"""

    def test_creates_new_gitignore_with_all_entries(self, tmp_path):
        """Test creates new .gitignore with all AUTO_CLAUDE_GITIGNORE_ENTRIES"""
        # Act
        added = ensure_all_gitignore_entries(tmp_path, auto_commit=False)

        # Assert
        assert len(added) == len(AUTO_CLAUDE_GITIGNORE_ENTRIES)
        gitignore_path = tmp_path / ".gitignore"
        content = gitignore_path.read_text(encoding="utf-8")
        for entry in AUTO_CLAUDE_GITIGNORE_ENTRIES:
            assert entry in content

    def test_no_new_entries(self, tmp_path):
        """Test returns empty list when all entries exist"""
        # Arrange - create gitignore with all entries
        gitignore_path = tmp_path / ".gitignore"
        content = "# Auto Claude generated files\n"
        for entry in AUTO_CLAUDE_GITIGNORE_ENTRIES:
            content += f"{entry}\n"
        gitignore_path.write_text(content, encoding="utf-8")

        # Act
        added = ensure_all_gitignore_entries(tmp_path, auto_commit=False)

        # Assert
        assert added == []

    def test_adds_missing_entries(self, tmp_path):
        """Test only adds missing entries"""
        # Arrange - create gitignore with some entries
        gitignore_path = tmp_path / ".gitignore"
        existing_entries = AUTO_CLAUDE_GITIGNORE_ENTRIES[:2]
        content = "# Existing entries\n"
        for entry in existing_entries:
            content += f"{entry}\n"
        gitignore_path.write_text(content, encoding="utf-8")

        # Act
        added = ensure_all_gitignore_entries(tmp_path, auto_commit=False)

        # Assert
        expected_missing = AUTO_CLAUDE_GITIGNORE_ENTRIES[2:]
        assert len(added) == len(expected_missing)
        for entry in expected_missing:
            assert entry in added

    def test_preserves_existing_content(self, tmp_path):
        """Test preserves existing gitignore content"""
        # Arrange
        gitignore_path = tmp_path / ".gitignore"
        existing_content = "# My entries\n*.pyc\nnode_modules/\n"
        gitignore_path.write_text(existing_content, encoding="utf-8")

        # Act
        ensure_all_gitignore_entries(tmp_path, auto_commit=False)

        # Assert
        content = gitignore_path.read_text(encoding="utf-8")
        assert "*.pyc" in content
        assert "node_modules/" in content

    def test_with_auto_commit_success(self, tmp_path):
        """Test auto_commit=True calls _commit_gitignore"""
        # Arrange
        with patch("init._commit_gitignore", return_value=True) as mock_commit:
            # Act
            added = ensure_all_gitignore_entries(tmp_path, auto_commit=True)

            # Assert
            assert len(added) > 0
            mock_commit.assert_called_once_with(tmp_path)

    def test_with_auto_commit_failure(self, tmp_path, caplog):
        """Test auto_commit logs warning on failure"""
        # Arrange
        with patch("init._commit_gitignore", return_value=False):
            # Act
            ensure_all_gitignore_entries(tmp_path, auto_commit=True)

            # Assert - should log warning but not raise exception
            # The function should still complete successfully


class TestInitAutoClaudeDir:
    """Tests for init_auto_claude_dir function"""

    def test_creates_directory_and_gitignore(self, tmp_path):
        """Test creates .auto-claude directory and updates gitignore"""
        # Act
        auto_claude_dir, gitignore_updated = init_auto_claude_dir(tmp_path)

        # Assert
        assert auto_claude_dir.exists()
        assert auto_claude_dir == tmp_path / ".auto-claude"
        assert gitignore_updated is True  # First creation should update gitignore

    def test_existing_directory_no_gitignore_update(self, tmp_path):
        """Test existing directory doesn't update gitignore if marker exists"""
        # Arrange
        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir(parents=True, exist_ok=True)
        marker = auto_claude_dir / ".gitignore_checked"
        marker.touch()

        # Act
        auto_claude_dir_result, gitignore_updated = init_auto_claude_dir(tmp_path)

        # Assert
        assert auto_claude_dir_result == auto_claude_dir
        assert gitignore_updated is False

    def test_existing_directory_creates_marker(self, tmp_path):
        """Test creates .gitignore_checked marker on first run"""
        # Arrange
        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir(parents=True, exist_ok=True)
        marker = auto_claude_dir / ".gitignore_checked"

        # Act
        init_auto_claude_dir(tmp_path)

        # Assert
        assert marker.exists()

    def test_creates_parents_if_needed(self, tmp_path):
        """Test creates parent directories"""
        # Arrange
        nested_dir = tmp_path / "deep" / "nested" / "project"
        # Note: function uses the passed project_dir as base, doesn't create
        # parent dirs for project_dir itself

        # Act
        auto_claude_dir, _ = init_auto_claude_dir(nested_dir)

        # Assert
        assert auto_claude_dir.exists()

    def test_with_path_object(self, tmp_path):
        """Test works with Path object"""
        # Act
        auto_claude_dir, _ = init_auto_claude_dir(tmp_path)

        # Assert
        assert isinstance(auto_claude_dir, Path)

    def test_with_string_path(self, tmp_path):
        """Test works with string path"""
        # Act
        auto_claude_dir, _ = init_auto_claude_dir(str(tmp_path))

        # Assert
        assert isinstance(auto_claude_dir, Path)


class TestGetAutoClaudeDir:
    """Tests for get_auto_claude_dir function"""

    def test_ensure_exists_true(self, tmp_path):
        """Test with ensure_exists=True creates directory"""
        # Act
        result = get_auto_claude_dir(tmp_path, ensure_exists=True)

        # Assert
        assert result.exists()
        assert result == tmp_path / ".auto-claude"

    def test_ensure_exists_false(self, tmp_path):
        """Test with ensure_exists=False doesn't create directory"""
        # Act
        result = get_auto_claude_dir(tmp_path, ensure_exists=False)

        # Assert
        assert not result.exists()
        assert result == tmp_path / ".auto-claude"

    def test_returns_path_object(self, tmp_path):
        """Test always returns Path object"""
        # Act
        result = get_auto_claude_dir(tmp_path)

        # Assert
        assert isinstance(result, Path)


class TestRepairGitignore:
    """Tests for repair_gitignore function"""

    def test_adds_missing_entries(self, tmp_path):
        """Test adds all missing entries"""
        # Arrange
        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir(parents=True, exist_ok=True)
        marker = auto_claude_dir / ".gitignore_checked"
        marker.touch()  # Mark as checked

        # Act
        added = repair_gitignore(tmp_path)

        # Assert
        assert len(added) == len(AUTO_CLAUDE_GITIGNORE_ENTRIES)
        gitignore_path = tmp_path / ".gitignore"
        assert gitignore_path.exists()

    def test_removes_and_recreates_marker(self, tmp_path):
        """Test removes and recreates .gitignore_checked marker"""
        # Arrange
        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir(parents=True, exist_ok=True)
        marker = auto_claude_dir / ".gitignore_checked"
        marker.touch()

        # Modify marker to check it's recreated
        original_mtime = marker.stat().st_mtime

        import time
        time.sleep(0.01)  # Ensure different mtime

        # Act
        repair_gitignore(tmp_path)

        # Assert - marker should still exist
        assert marker.exists()

    def test_returns_empty_when_all_exist(self, tmp_path):
        """Test returns empty list when all entries exist"""
        # Arrange
        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir(parents=True, exist_ok=True)

        # Create gitignore with all entries
        gitignore_path = tmp_path / ".gitignore"
        content = "# Auto Claude generated files\n"
        for entry in AUTO_CLAUDE_GITIGNORE_ENTRIES:
            content += f"{entry}\n"
        gitignore_path.write_text(content, encoding="utf-8")

        # Act
        added = repair_gitignore(tmp_path)

        # Assert
        assert added == []

    def test_auto_commits_changes(self, tmp_path):
        """Test auto-commits gitignore changes"""
        # Arrange
        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir(parents=True, exist_ok=True)

        with patch("init._commit_gitignore", return_value=True) as mock_commit:
            # Act
            repair_gitignore(tmp_path)

            # Assert
            mock_commit.assert_called_once()

    def test_handles_nonexistent_auto_claude_dir(self, tmp_path):
        """Test handles case when .auto-claude doesn't exist"""
        # Arrange - don't create .auto-claude dir

        # Act - should not raise exception
        added = repair_gitignore(tmp_path)

        # Assert
        # Should still add entries
        gitignore_path = tmp_path / ".gitignore"
        assert gitignore_path.exists()


class TestConstants:
    """Tests for constants"""

    def test_auto_claude_gitignore_entries(self):
        """Test AUTO_CLAUDE_GITIGNORE_ENTRIES contains expected entries"""
        assert ".auto-claude/" in AUTO_CLAUDE_GITIGNORE_ENTRIES
        assert ".worktrees/" in AUTO_CLAUDE_GITIGNORE_ENTRIES
        assert ".security-key" in AUTO_CLAUDE_GITIGNORE_ENTRIES

    def test_auto_claude_gitignore_entries_no_duplicates(self):
        """Test AUTO_CLAUDE_GITIGNORE_ENTRIES has no duplicates"""
        assert len(AUTO_CLAUDE_GITIGNORE_ENTRIES) == len(set(AUTO_CLAUDE_GITIGNORE_ENTRIES))
