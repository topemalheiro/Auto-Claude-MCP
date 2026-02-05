"""Tests for cleanup_pr_worktrees"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from runners.github.cleanup_pr_worktrees import (
    cleanup_worktrees,
    find_project_root,
    list_worktrees,
    main,
    show_stats,
)


@pytest.fixture
def mock_worktree_manager():
    """Create a mock PRWorktreeManager."""
    manager = MagicMock()
    manager.get_worktree_info.return_value = []
    manager.get_registered_worktrees.return_value = []
    return manager


def test_find_project_root(tmp_path):
    """Test find_project_root"""
    # Create a .git directory in temp path
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    # Change to temp directory
    original_cwd = Path.cwd()
    try:
        import os
        os.chdir(tmp_path)

        result = find_project_root()
        assert result == tmp_path
    finally:
        os.chdir(original_cwd)


def test_find_project_root_not_in_repo():
    """Test find_project_root when not in a git repository"""
    original_cwd = Path.cwd()
    try:
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            with pytest.raises(RuntimeError, match="Not in a git repository"):
                find_project_root()
    finally:
        os.chdir(original_cwd)


def test_list_worktrees(mock_worktree_manager, capsys):
    """Test list_worktrees"""
    # Setup mock with no worktrees
    mock_worktree_manager.get_worktree_info.return_value = []

    list_worktrees(mock_worktree_manager)

    captured = capsys.readouterr()
    assert "No PR review worktrees found" in captured.out


def test_list_worktrees_with_data(mock_worktree_manager, capsys):
    """Test list_worktrees with worktree data"""
    from runners.github.services.pr_worktree_manager import WorktreeInfo

    # Setup mock with worktrees
    worktree = WorktreeInfo(
        path=Path("/tmp/test-wt"),
        pr_number=123,
        age_days=5.0,
    )
    mock_worktree_manager.get_worktree_info.return_value = [worktree]

    list_worktrees(mock_worktree_manager)

    captured = capsys.readouterr()
    assert "Found 1 PR review worktrees" in captured.out
    assert "#123" in captured.out


def test_show_stats(mock_worktree_manager, capsys):
    """Test show_stats"""
    show_stats(mock_worktree_manager)

    captured = capsys.readouterr()
    assert "PR Worktree Statistics" in captured.out
    assert "Total worktrees:      0" in captured.out  # Note extra spacing


def test_show_stats_with_worktrees(mock_worktree_manager, capsys):
    """Test show_stats with worktree data"""
    from runners.github.services.pr_worktree_manager import WorktreeInfo

    # Setup mock with worktrees
    worktree = WorktreeInfo(
        path=Path("/tmp/test-wt"),
        pr_number=123,
        age_days=5.0,
    )
    mock_worktree_manager.get_worktree_info.return_value = [worktree]

    show_stats(mock_worktree_manager)

    captured = capsys.readouterr()
    assert "Total worktrees:      1" in captured.out


def test_cleanup_worktrees(mock_worktree_manager, capsys):
    """Test cleanup_worktrees"""
    cleanup_worktrees(mock_worktree_manager, force=False)

    captured = capsys.readouterr()
    assert "Running PR worktree cleanup" in captured.out


def test_cleanup_worktrees_force(mock_worktree_manager, capsys):
    """Test cleanup_worktrees with force flag"""
    mock_worktree_manager.remove_worktree.return_value = True

    cleanup_worktrees(mock_worktree_manager, force=True)

    captured = capsys.readouterr()
    assert "Force cleanup" in captured.out


@patch("runners.github.cleanup_pr_worktrees.find_project_root")
@patch("runners.github.cleanup_pr_worktrees.PRWorktreeManager")
def test_main(mock_manager_class, mock_find_root, capsys):
    """Test main function"""
    # Setup mocks
    mock_root = Path("/tmp/test")
    mock_find_root.return_value = mock_root

    mock_manager = MagicMock()
    mock_manager_class.return_value = mock_manager
    mock_manager.get_worktree_info.return_value = []

    # Simulate command line args
    with patch("sys.argv", ["cleanup_pr_worktrees.py", "--list"]):
        main()

    captured = capsys.readouterr()
    # Should call list_worktrees
    assert mock_manager.get_worktree_info.called


@patch("runners.github.cleanup_pr_worktrees.find_project_root")
@patch("runners.github.cleanup_pr_worktrees.PRWorktreeManager")
@patch("runners.github.cleanup_pr_worktrees.show_stats")
def test_main_stats(mock_show_stats, mock_manager_class, mock_find_root):
    """Test main with --stats flag"""
    # Setup mocks
    mock_root = Path("/tmp/test")
    mock_find_root.return_value = mock_root

    mock_manager = MagicMock()
    mock_manager_class.return_value = mock_manager

    with patch("sys.argv", ["cleanup_pr_worktrees.py", "--stats"]):
        main()

    assert mock_show_stats.called
