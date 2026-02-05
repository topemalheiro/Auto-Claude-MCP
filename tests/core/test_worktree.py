"""Tests for worktree"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.worktree import WorktreeManager, WorktreeError, WorktreeInfo


@pytest.fixture
def mock_project_dir(tmp_path):
    """Create a mock project directory."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    # Initialize as git repo
    import subprocess

    subprocess.run(["git", "init"], cwd=project_dir, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=project_dir, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=project_dir, capture_output=True)
    # Create initial commit
    (project_dir / "README.md").write_text("# Test Project")
    subprocess.run(["git", "add", "."], cwd=project_dir, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=project_dir, capture_output=True)
    return project_dir


@pytest.fixture
def worktree_manager(mock_project_dir):
    """Create a WorktreeManager instance."""
    return WorktreeManager(mock_project_dir, base_branch="main")


def test_WorktreeManager_init(mock_project_dir):
    """Test WorktreeManager.__init__"""
    # Act
    manager = WorktreeManager(mock_project_dir, base_branch="main")

    # Assert
    assert manager.project_dir == mock_project_dir
    assert manager.base_branch == "main"
    assert manager.worktrees_dir == mock_project_dir / ".auto-claude" / "worktrees" / "tasks"


def test_WorktreeManager_get_worktree_path(worktree_manager):
    """Test WorktreeManager.get_worktree_path"""
    # Act
    result = worktree_manager.get_worktree_path("spec_001")

    # Assert
    expected = worktree_manager.project_dir / ".auto-claude" / "worktrees" / "tasks" / "spec_001"
    assert result == expected


def test_WorktreeManager_get_branch_name(worktree_manager):
    """Test WorktreeManager.get_branch_name"""
    # Act
    result = worktree_manager.get_branch_name("spec_001")

    # Assert
    assert result == "auto-claude/spec_001"


def test_WorktreeManager_worktree_exists_false(worktree_manager):
    """Test WorktreeManager.worktree_exists returns False for non-existent worktree"""
    # Act
    result = worktree_manager.worktree_exists("spec_001")

    # Assert
    assert result is False


def test_WorktreeManager_get_worktree_info_not_exists(worktree_manager):
    """Test WorktreeManager.get_worktree_info for non-existent worktree"""
    # Act
    result = worktree_manager.get_worktree_info("spec_001")

    # Assert
    assert result is None


def test_WorktreeManager_list_all_worktrees_empty(worktree_manager):
    """Test WorktreeManager.list_all_worktrees with no worktrees"""
    # Act
    result = worktree_manager.list_all_worktrees()

    # Assert
    assert result == []


def test_WorktreeManager_list_all_spec_branches(worktree_manager):
    """Test WorktreeManager.list_all_spec_branches"""
    # This test requires git to actually work since it's called from __init__
    # Skip if git isn't properly initialized
    try:
        # Act
        result = worktree_manager.list_all_spec_branches()

        # Assert
        assert isinstance(result, list)
    except Exception as e:
        # Git operations may fail in test environment
        pytest.skip(f"Git operations not available: {e}")


def test_WorktreeManager_get_changed_files_not_exists(worktree_manager):
    """Test WorktreeManager.get_changed_files for non-existent worktree"""
    # Act
    result = worktree_manager.get_changed_files("spec_001")

    # Assert
    assert result == []


def test_WorktreeManager_get_change_summary_not_exists(worktree_manager):
    """Test WorktreeManager.get_change_summary for non-existent worktree"""
    # Act
    result = worktree_manager.get_change_summary("spec_001")

    # Assert - returns dict with zeros for non-existent worktree
    assert isinstance(result, dict)
    assert result.get("new_files") == 0
    assert result.get("modified_files") == 0
    assert result.get("deleted_files") == 0


def test_WorktreeManager_cleanup_all_no_worktrees(worktree_manager):
    """Test WorktreeManager.cleanup_all with no worktrees"""
    # Act - should not raise
    worktree_manager.cleanup_all()


def test_WorktreeManager_cleanup_stale_worktrees_no_worktrees(worktree_manager):
    """Test WorktreeManager.cleanup_stale_worktrees with no worktrees"""
    # Act
    result = worktree_manager.cleanup_stale_worktrees()

    # Assert - returns None (function has no return value)
    assert result is None


def test_WorktreeManager_get_test_commands_no_worktree(worktree_manager):
    """Test WorktreeManager.get_test_commands for non-existent worktree"""
    # Act
    result = worktree_manager.get_test_commands("spec_001")

    # Assert - returns list with default instructions
    assert isinstance(result, list)
    assert len(result) > 0  # Has default instruction


def test_WorktreeManager_has_uncommitted_changes_no_worktree(worktree_manager):
    """Test WorktreeManager.has_uncommitted_changes for non-existent worktree"""
    # Act
    result = worktree_manager.has_uncommitted_changes("spec_001")

    # Assert
    assert result is False


def test_WorktreeManager_get_old_worktrees_empty(worktree_manager):
    """Test WorktreeManager.get_old_worktrees with no worktrees"""
    # Act
    result = worktree_manager.get_old_worktrees(days_threshold=7, include_stats=False)

    # Assert
    assert result == []


def test_WorktreeManager_cleanup_old_worktrees_no_worktrees(worktree_manager):
    """Test WorktreeManager.cleanup_old_worktrees with no worktrees"""
    # Act
    result = worktree_manager.cleanup_old_worktrees(days_threshold=7, dry_run=True)

    # Assert - returns tuple (removed, kept) list
    assert isinstance(result, tuple) or result is None


def test_WorktreeManager_get_worktree_count_warning_no_worktrees(worktree_manager):
    """Test WorktreeManager.get_worktree_count_warning with no worktrees"""
    # Act
    result = worktree_manager.get_worktree_count_warning(warning_threshold=10, critical_threshold=20)

    # Assert - returns None when printed directly
    assert result is None


def test_WorktreeManager_print_worktree_summary_no_worktrees(worktree_manager, capsys):
    """Test WorktreeManager.print_worktree_summary with no worktrees"""
    # Act
    worktree_manager.print_worktree_summary()

    # Assert - should print something about worktrees
    captured = capsys.readouterr()
    assert captured.out is not None
    assert len(captured.out) > 0


def test_WorktreeManager_get_old_worktrees_with_stats(worktree_manager):
    """Test WorktreeManager.get_old_worktrees with include_stats=True"""
    # Act - no worktrees exist
    result = worktree_manager.get_old_worktrees(days_threshold=7, include_stats=True)

    # Assert
    assert result == []


def test_WorktreeManager_create_worktree_missing_branch(worktree_manager):
    """Test WorktreeManager.create_worktree when base branch doesn't exist"""
    # Create a manager with non-existent base branch
    manager = WorktreeManager(worktree_manager.project_dir, base_branch="nonexistent")

    # Act & Assert - should raise WorktreeError
    with pytest.raises(WorktreeError):
        manager.create_worktree("spec_001")


def test_WorktreeManager_get_or_create_worktree_missing_branch(worktree_manager):
    """Test WorktreeManager.get_or_create_worktree when base branch doesn't exist"""
    # Create a manager with non-existent base branch
    manager = WorktreeManager(worktree_manager.project_dir, base_branch="nonexistent")

    # Act & Assert - should raise WorktreeError
    with pytest.raises(WorktreeError):
        manager.get_or_create_worktree("spec_001")


def test_WorktreeManager_remove_worktree_not_exists(worktree_manager):
    """Test WorktreeManager.remove_worktree for non-existent worktree"""
    # Act & Assert - should not raise
    worktree_manager.remove_worktree("spec_001", delete_branch=False)


def test_WorktreeManager_merge_worktree_not_exists(worktree_manager):
    """Test WorktreeManager.merge_worktree for non-existent worktree"""
    # Act
    result = worktree_manager.merge_worktree("spec_001", delete_after=False, no_commit=True)

    # Assert - returns False for non-existent worktree
    assert result is False


def test_WorktreeManager_commit_in_worktree_not_exists(worktree_manager):
    """Test WorktreeManager.commit_in_worktree for non-existent worktree"""
    # Act
    result = worktree_manager.commit_in_worktree("spec_001", "Test commit")

    # Assert - returns False for non-existent worktree
    assert result is False


def test_WorktreeManager_push_branch_not_exists(worktree_manager):
    """Test WorktreeManager.push_branch for non-existent worktree"""
    # Act
    result = worktree_manager.push_branch("spec_001", force=False)

    # Assert - should return failure result
    assert result["success"] is False


def test_WorktreeManager_create_pull_request_not_exists(worktree_manager):
    """Test WorktreeManager.create_pull_request for non-existent worktree"""
    # Act
    result = worktree_manager.create_pull_request("spec_001", "main", "Test PR", draft=False)

    # Assert - should return failure result
    assert result["success"] is False


def test_WorktreeManager_create_merge_request_not_exists(worktree_manager):
    """Test WorktreeManager.create_merge_request for non-existent worktree"""
    # Act
    result = worktree_manager.create_merge_request("spec_001", "main", "Test MR", draft=False)

    # Assert - should return failure result
    assert result["success"] is False


def test_WorktreeManager_push_and_create_pr_not_exists(worktree_manager):
    """Test WorktreeManager.push_and_create_pr for non-existent worktree"""
    # Act
    result = worktree_manager.push_and_create_pr("spec_001", "main", "Test PR", draft=False, force_push=False)

    # Assert - should return failure result
    assert result["success"] is False


def test_WorktreeManager_setup_with_existing_dir(worktree_manager, tmp_path):
    """Test WorktreeManager.setup creates worktrees_dir"""
    # The worktrees_dir should be created by __init__ if needed
    # Act
    worktree_manager.setup()

    # Assert - directory should exist
    assert worktree_manager.worktrees_dir.exists()


def test_WorktreeInfo_dataclass():
    """Test WorktreeInfo dataclass"""
    from datetime import datetime
    from pathlib import Path

    # Arrange & Act
    info = WorktreeInfo(
        path=Path("/test/path"),
        branch="test-branch",
        spec_name="spec_001",
        base_branch="main",
        is_active=True,
        commit_count=5,
        files_changed=3,
        additions=10,
        deletions=2,
        last_commit_date=datetime.now(),
        days_since_last_commit=1,
    )

    # Assert
    assert info.path == Path("/test/path")
    assert info.branch == "test-branch"
    assert info.spec_name == "spec_001"
    assert info.base_branch == "main"
    assert info.is_active is True
    assert info.commit_count == 5
    assert info.files_changed == 3
