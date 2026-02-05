"""Tests for timeline_git"""

from merge.timeline_git import TimelineGitHelper
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


@patch("subprocess.run")
def test_TimelineGitHelper___init__(mock_run):
    """Test TimelineGitHelper.__init__"""

    # Arrange & Act
    project_path = Path("/tmp/test")
    instance = TimelineGitHelper(project_path)

    # Assert
    assert instance is not None
    assert instance.project_path == project_path.resolve()


@patch("subprocess.run")
def test_TimelineGitHelper_get_current_main_commit(mock_run):
    """Test TimelineGitHelper.get_current_main_commit"""

    # Arrange
    instance = TimelineGitHelper(Path("/tmp/test"))
    mock_run.return_value.stdout = "abc123def"

    # Act
    result = instance.get_current_main_commit()

    # Assert
    assert result == "abc123def"


@patch("subprocess.run")
def test_TimelineGitHelper_get_file_content_at_commit(mock_run):
    """Test TimelineGitHelper.get_file_content_at_commit"""

    # Arrange
    instance = TimelineGitHelper(Path("/tmp/test"))
    mock_run.return_value.stdout = "file content"
    mock_run.return_value.returncode = 0

    file_path = "test.py"
    commit_hash = "abc123"

    # Act
    result = instance.get_file_content_at_commit(file_path, commit_hash)

    # Assert
    assert result == "file content"


@patch("subprocess.run")
def test_TimelineGitHelper_get_files_changed_in_commit(mock_run):
    """Test TimelineGitHelper.get_files_changed_in_commit"""

    # Arrange
    instance = TimelineGitHelper(Path("/tmp/test"))
    mock_run.return_value.stdout = "test.py\nmain.ts\n"

    commit_hash = "abc123"

    # Act
    result = instance.get_files_changed_in_commit(commit_hash)

    # Assert
    assert result is not None
    assert isinstance(result, list)
    assert "test.py" in result


@patch("subprocess.run")
def test_TimelineGitHelper_get_commit_info(mock_run):
    """Test TimelineGitHelper.get_commit_info"""

    # Arrange
    instance = TimelineGitHelper(Path("/tmp/test"))
    mock_run.return_value.stdout = "abc123 Author Name <author@email.com> 1234567890"

    commit_hash = "abc123"

    # Act
    result = instance.get_commit_info(commit_hash)

    # Assert
    assert result is not None
    assert isinstance(result, dict)


@patch("subprocess.run")
def test_TimelineGitHelper_get_worktree_file_content(mock_run):
    """Test TimelineGitHelper.get_worktree_file_content"""

    # Arrange
    instance = TimelineGitHelper(Path("/tmp/test"))

    task_id = "task_001"
    file_path = "test.py"

    with patch.object(Path, "exists", return_value=True):
        with patch.object(Path, "read_text", return_value="worktree content"):
            # Act
            result = instance.get_worktree_file_content(task_id, file_path)

            # Assert
            assert result == "worktree content"


@patch("subprocess.run")
def test_TimelineGitHelper_get_changed_files_in_worktree(mock_run):
    """Test TimelineGitHelper.get_changed_files_in_worktree"""

    # Arrange
    instance = TimelineGitHelper(Path("/tmp/test"))
    mock_run.return_value.stdout = "test.py\nmain.ts\n"

    task_id = "task_001"

    # Act
    result = instance.get_changed_files_in_worktree(task_id)

    # Assert
    assert result is not None
    assert isinstance(result, list)


@patch("subprocess.run")
def test_TimelineGitHelper_get_branch_point(mock_run):
    """Test TimelineGitHelper.get_branch_point"""

    # Arrange
    instance = TimelineGitHelper(Path("/tmp/test"))
    mock_run.return_value.stdout = "abc123\n"
    mock_run.return_value.returncode = 0

    worktree_path = Path("/tmp/test")

    # Act
    result = instance.get_branch_point(worktree_path)

    # Assert
    assert result == "abc123"


@patch("subprocess.run")
def test_TimelineGitHelper_count_commits_between(mock_run):
    """Test TimelineGitHelper.count_commits_between"""

    # Arrange
    instance = TimelineGitHelper(Path("/tmp/test"))
    mock_run.return_value.stdout = "5\n"
    mock_run.return_value.returncode = 0

    commit_a = "abc123"
    commit_b = "def456"

    # Act
    result = instance.count_commits_between(commit_a, commit_b)

    # Assert
    assert result == 5
