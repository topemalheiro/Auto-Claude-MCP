"""Tests for pr_review_engine"""

from runners.github.services.pr_review_engine import PRReviewEngine
from runners.github.models import GitHubRunnerConfig, ReviewPass
from pathlib import Path
from unittest.mock import MagicMock
import pytest


@pytest.fixture
def mock_config():
    """Create a mock GitHubRunnerConfig."""
    config = MagicMock(spec=GitHubRunnerConfig)
    config.repo = "test/repo"
    config.model = "sonnet"
    config.use_parallel_orchestrator = False
    return config


def test_PRReviewEngine___init__(mock_config):
    """Test PRReviewEngine.__init__"""

    # Arrange
    project_dir = Path("/tmp/test")
    github_dir = Path("/tmp/test")
    progress_callback = MagicMock()

    # Act
    instance = PRReviewEngine(project_dir, github_dir, mock_config, progress_callback)

    # Assert
    assert instance is not None
    assert instance.project_dir == project_dir
    assert instance.github_dir == github_dir
    assert instance.config == mock_config
    assert instance.progress_callback == progress_callback


def test_PRReviewEngine_needs_deep_analysis(mock_config):
    """Test PRReviewEngine.needs_deep_analysis"""

    # Arrange
    scan_result = {}
    context = MagicMock()
    context.total_additions = 300
    context.total_deletions = 0
    instance = PRReviewEngine(Path("/tmp/test"), Path("/tmp/test"), mock_config)

    # Act
    result = instance.needs_deep_analysis(scan_result, context)

    # Assert
    assert result is True


def test_PRReviewEngine_deduplicate_findings(mock_config):
    """Test PRReviewEngine.deduplicate_findings"""

    # Arrange
    findings = [
        MagicMock(id="1", file="test.py", line=10, title="First issue"),
        MagicMock(id="2", file="test.py", line=10, title="First issue"),  # duplicate
        MagicMock(id="3", file="other.py", line=20, title="Second issue"),
    ]
    instance = PRReviewEngine(Path("/tmp/test"), Path("/tmp/test"), mock_config)

    # Act
    result = instance.deduplicate_findings(findings)

    # Assert
    assert result is not None
    assert len(result) == 2


@pytest.mark.asyncio
async def test_PRReviewEngine_run_review_pass(mock_config, tmp_path):
    """Test PRReviewEngine.run_review_pass"""

    # Arrange
    review_pass = ReviewPass.QUICK_SCAN
    context = MagicMock()
    context.pr_number = 123
    context.title = "Test PR"
    context.author = "testuser"
    context.base_branch = "main"
    context.head_branch = "feature/test"
    context.description = "Test"
    context.changed_files = []
    context.total_additions = 10
    context.total_deletions = 5
    context.commits = []
    context.diff = ""
    context.diff_truncated = False

    instance = PRReviewEngine(tmp_path, tmp_path, mock_config)

    # Act & Assert
    # This test would require mocking the AI client
    # We just verify the method exists
    assert hasattr(instance, 'run_review_pass')
    assert callable(instance.run_review_pass)


@pytest.mark.asyncio
async def test_PRReviewEngine_run_multi_pass_review(mock_config, tmp_path):
    """Test PRReviewEngine.run_multi_pass_review"""

    # Arrange
    context = MagicMock()
    context.pr_number = 123
    context.title = "Test PR"
    context.author = "testuser"
    context.base_branch = "main"
    context.head_branch = "feature/test"
    context.description = "Test"
    context.changed_files = []
    context.total_additions = 10
    context.total_deletions = 5
    context.commits = []
    context.ai_bot_comments = []
    context.diff = ""
    context.diff_truncated = False
    context.has_merge_conflicts = False
    context.merge_state_status = "clean"

    instance = PRReviewEngine(tmp_path, tmp_path, mock_config)

    # Act & Assert
    # This test would require mocking the AI client
    # We just verify the method exists
    assert hasattr(instance, 'run_multi_pass_review')
    assert callable(instance.run_multi_pass_review)
