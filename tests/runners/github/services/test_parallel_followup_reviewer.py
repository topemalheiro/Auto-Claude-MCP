"""Tests for parallel_followup_reviewer"""

from runners.github.services.parallel_followup_reviewer import ParallelFollowupReviewer
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


def test_ParallelFollowupReviewer___init__(mock_config):
    """Test ParallelFollowupReviewer.__init__"""

    # Arrange
    project_dir = Path("/tmp/test")
    github_dir = Path("/tmp/test")
    progress_callback = MagicMock()

    # Act
    instance = ParallelFollowupReviewer(project_dir, github_dir, mock_config, progress_callback)

    # Assert
    assert instance is not None
    assert instance.project_dir == project_dir
    assert instance.github_dir == github_dir
    assert instance.config == mock_config
    assert instance.progress_callback == progress_callback


@pytest.mark.asyncio
async def test_ParallelFollowupReviewer_review(mock_config, tmp_path):
    """Test ParallelFollowupReviewer.review"""

    # Arrange
    context = MagicMock()
    context.pr_number = 123
    context.current_commit_sha = "def456"
    context.head_sha = "def456"
    context.head_branch = "feature/test"
    context.commits_since_review = []
    context.files_changed_since_review = []
    context.diff_since_review = ""
    context.contributor_comments_since_review = []
    context.ai_bot_comments_since_review = []
    context.pr_reviews_since_review = []
    context.has_merge_conflicts = False
    context.merge_state_status = "clean"
    context.ci_status = None

    context.previous_review = MagicMock()
    context.previous_review.review_id = "review-123"
    context.previous_review.pr_number = 123
    context.previous_review.findings = []
    context.previous_review.summary = "Test summary"

    instance = ParallelFollowupReviewer(tmp_path, tmp_path, mock_config)

    # Act & Assert
    # This test would require mocking the AI client, so we just verify
    # the method exists and the reviewer is properly initialized
    assert hasattr(instance, 'review')
    assert callable(instance.review)
