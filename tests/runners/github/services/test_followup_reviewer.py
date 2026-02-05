"""Tests for followup_reviewer"""

from runners.github.services.followup_reviewer import FollowupReviewer
from runners.github.models import GitHubRunnerConfig
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock
import pytest


@pytest.fixture
def mock_config():
    """Create a mock GitHubRunnerConfig."""
    config = MagicMock(spec=GitHubRunnerConfig)
    config.repo = "test/repo"
    config.model = "sonnet"
    config.thinking_level = "medium"
    return config


def test_FollowupReviewer___init__(mock_config):
    """Test FollowupReviewer.__init__"""

    # Arrange
    project_dir = Path("/tmp/test")
    github_dir = Path("/tmp/test")
    progress_callback = MagicMock()
    use_ai = True

    # Act
    instance = FollowupReviewer(project_dir, github_dir, mock_config, progress_callback, use_ai)

    # Assert
    assert instance is not None
    assert instance.project_dir == project_dir
    assert instance.github_dir == github_dir
    assert instance.config == mock_config
    assert instance.progress_callback == progress_callback
    assert instance.use_ai == use_ai


@pytest.mark.asyncio
async def test_FollowupReviewer_review_followup(mock_config, tmp_path):
    """Test FollowupReviewer.review_followup"""

    # Arrange
    context = MagicMock()
    context.pr_number = 123
    context.previous_commit_sha = "abc123"
    context.current_commit_sha = "def456"
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

    instance = FollowupReviewer(tmp_path, tmp_path, mock_config, use_ai=False)

    # Act
    result = await instance.review_followup(context)

    # Assert
    assert result is not None
    assert result.pr_number == 123
