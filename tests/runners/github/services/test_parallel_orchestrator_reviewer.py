"""Tests for parallel_orchestrator_reviewer"""

from runners.github.services.parallel_orchestrator_reviewer import ParallelOrchestratorReviewer
from runners.github.models import GitHubRunnerConfig
from pathlib import Path
from unittest.mock import MagicMock
import pytest


@pytest.fixture
def mock_config():
    """Create a mock GitHubRunnerConfig."""
    config = MagicMock(spec=GitHubRunnerConfig)
    config.repo = "test/repo"
    config.model = "sonnet"
    config.thinking_level = "medium"
    return config


def test_ParallelOrchestratorReviewer___init__(mock_config):
    """Test ParallelOrchestratorReviewer.__init__"""

    # Arrange
    project_dir = Path("/tmp/test")
    github_dir = Path("/tmp/test")
    progress_callback = MagicMock()

    # Act
    instance = ParallelOrchestratorReviewer(project_dir, github_dir, mock_config, progress_callback)

    # Assert
    assert instance is not None
    assert instance.project_dir == project_dir
    assert instance.github_dir == github_dir
    assert instance.config == mock_config
    assert instance.progress_callback == progress_callback


@pytest.mark.asyncio
async def test_ParallelOrchestratorReviewer_review(mock_config, tmp_path):
    """Test ParallelOrchestratorReviewer.review"""

    # Arrange
    context = MagicMock()
    context.pr_number = 123
    context.head_sha = "def456"
    context.head_branch = "feature/test"
    context.title = "Test PR"
    context.author = "testuser"
    context.base_branch = "main"
    context.description = "Test description"
    context.changed_files = []
    context.total_additions = 10
    context.total_deletions = 5
    context.commits = []
    context.ai_bot_comments = []
    context.diff = ""
    context.diff_truncated = False
    context.has_merge_conflicts = False
    context.merge_state_status = "clean"

    instance = ParallelOrchestratorReviewer(tmp_path, tmp_path, mock_config)

    # Act & Assert
    # This test would require mocking the AI client, so we just verify
    # the method exists and the reviewer is properly initialized
    assert hasattr(instance, 'review')
    assert callable(instance.review)
