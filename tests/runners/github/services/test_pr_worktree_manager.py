"""Tests for pr_worktree_manager"""

from runners.github.services.pr_worktree_manager import PRWorktreeManager
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


def test_PRWorktreeManager___init__():
    """Test PRWorktreeManager.__init__"""

    # Arrange
    project_dir = Path("/tmp/test")
    worktree_dir = ".auto-claude/github/pr/worktrees"

    # Act
    instance = PRWorktreeManager(project_dir, worktree_dir)

    # Assert
    assert instance is not None
    assert instance.project_dir == project_dir
    assert instance.worktree_base_dir == project_dir / worktree_dir


def test_PRWorktreeManager_create_worktree(tmp_path):
    """Test PRWorktreeManager.create_worktree"""

    # Arrange
    instance = PRWorktreeManager(tmp_path, ".auto-claude/github/pr/worktrees")
    head_sha = "a" * 40  # Valid SHA
    pr_number = 123

    # Act & Assert
    # This test would require a git repository, so we just verify
    # the method exists and proper validation is done
    assert hasattr(instance, 'create_worktree')
    assert callable(instance.create_worktree)

    # Test that invalid SHA raises ValueError
    with pytest.raises(ValueError):
        instance.create_worktree("", pr_number)

    # Test that invalid pr_number raises ValueError
    with pytest.raises(ValueError):
        instance.create_worktree(head_sha, -1)


def test_PRWorktreeManager_remove_worktree(tmp_path):
    """Test PRWorktreeManager.remove_worktree"""

    # Arrange
    instance = PRWorktreeManager(tmp_path, ".auto-claude/github/pr/worktrees")
    worktree_path = tmp_path / "nonexistent_worktree"

    # Act
    # Should not raise for nonexistent worktree
    instance.remove_worktree(worktree_path)

    # Assert - no exception raised


def test_PRWorktreeManager_get_worktree_info(tmp_path):
    """Test PRWorktreeManager.get_worktree_info"""

    # Arrange
    instance = PRWorktreeManager(tmp_path, ".auto-claude/github/pr/worktrees")

    # Act
    result = instance.get_worktree_info()

    # Assert
    assert result is not None
    assert isinstance(result, list)


def test_PRWorktreeManager_get_registered_worktrees(tmp_path):
    """Test PRWorktreeManager.get_registered_worktrees"""

    # Arrange
    instance = PRWorktreeManager(tmp_path, ".auto-claude/github/pr/worktrees")

    # Act
    result = instance.get_registered_worktrees()

    # Assert
    assert result is not None
    assert isinstance(result, set)


def test_PRWorktreeManager_cleanup_worktrees(tmp_path):
    """Test PRWorktreeManager.cleanup_worktrees"""

    # Arrange
    instance = PRWorktreeManager(tmp_path, ".auto-claude/github/pr/worktrees")

    # Act
    result = instance.cleanup_worktrees()

    # Assert
    assert result is not None
    assert isinstance(result, dict)
    assert "total" in result
    assert "orphaned" in result
    assert "expired" in result
    assert "excess" in result


def test_PRWorktreeManager_cleanup_all_worktrees(tmp_path):
    """Test PRWorktreeManager.cleanup_all_worktrees"""

    # Arrange
    instance = PRWorktreeManager(tmp_path, ".auto-claude/github/pr/worktrees")

    # Act
    result = instance.cleanup_all_worktrees()

    # Assert
    assert result is not None
    assert isinstance(result, int)
    assert result >= 0
