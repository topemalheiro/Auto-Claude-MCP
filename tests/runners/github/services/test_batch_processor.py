"""Tests for batch_processor"""

from runners.github.services.batch_processor import BatchProcessor
from runners.github.models import GitHubRunnerConfig
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
import pytest
import sys


# Check if batch_issues module is available
BATCH_ISSUES_AVAILABLE = False
try:
    from runners.github.batch_issues import IssueBatcher
    BATCH_ISSUES_AVAILABLE = True
except ImportError:
    pass


@pytest.fixture
def mock_config():
    """Create a mock GitHubRunnerConfig."""
    config = MagicMock(spec=GitHubRunnerConfig)
    config.repo = "test/repo"
    return config


def test_BatchProcessor___init__(mock_config):
    """Test BatchProcessor.__init__"""

    # Arrange
    project_dir = Path("/tmp/test")
    github_dir = Path("/tmp/test")
    progress_callback = MagicMock()

    # Act
    instance = BatchProcessor(project_dir, github_dir, mock_config, progress_callback)

    # Assert
    assert instance is not None
    assert instance.project_dir == project_dir
    assert instance.github_dir == github_dir
    assert instance.config == mock_config
    assert instance.progress_callback == progress_callback


@pytest.mark.skipif(not BATCH_ISSUES_AVAILABLE, reason="batch_issues module not available")
@pytest.mark.asyncio
async def test_BatchProcessor_batch_and_fix_issues(mock_config, tmp_path):
    """Test BatchProcessor.batch_and_fix_issues"""

    # Arrange
    issues = []
    fetch_issue_callback = AsyncMock()
    instance = BatchProcessor(tmp_path, tmp_path, mock_config)

    # Act
    result = await instance.batch_and_fix_issues(issues, fetch_issue_callback)

    # Assert
    assert result is not None
    assert isinstance(result, list)


@pytest.mark.skipif(not BATCH_ISSUES_AVAILABLE, reason="batch_issues module not available")
@pytest.mark.asyncio
async def test_BatchProcessor_analyze_issues_preview(mock_config, tmp_path):
    """Test BatchProcessor.analyze_issues_preview"""

    # Arrange
    issues = []
    max_issues = 200
    instance = BatchProcessor(tmp_path, tmp_path, mock_config)

    # Act
    result = await instance.analyze_issues_preview(issues, max_issues)

    # Assert
    assert result is not None
    assert isinstance(result, dict)
    assert "success" in result


@pytest.mark.skipif(not BATCH_ISSUES_AVAILABLE, reason="batch_issues module not available")
@pytest.mark.asyncio
async def test_BatchProcessor_approve_and_execute_batches(mock_config, tmp_path):
    """Test BatchProcessor.approve_and_execute_batches"""

    # Arrange
    approved_batches = []
    instance = BatchProcessor(tmp_path, tmp_path, mock_config)

    # Act
    result = await instance.approve_and_execute_batches(approved_batches)

    # Assert
    assert result is not None
    assert isinstance(result, list)


@pytest.mark.skipif(not BATCH_ISSUES_AVAILABLE, reason="batch_issues module not available")
@pytest.mark.asyncio
async def test_BatchProcessor_get_batch_status(mock_config, tmp_path):
    """Test BatchProcessor.get_batch_status"""

    # Arrange
    instance = BatchProcessor(tmp_path, tmp_path, mock_config)

    # Act
    result = await instance.get_batch_status()

    # Assert
    assert result is not None
    assert isinstance(result, dict)
    assert "total_batches" in result


@pytest.mark.skipif(not BATCH_ISSUES_AVAILABLE, reason="batch_issues module not available")
@pytest.mark.asyncio
async def test_BatchProcessor_process_pending_batches(mock_config, tmp_path):
    """Test BatchProcessor.process_pending_batches"""

    # Arrange
    instance = BatchProcessor(tmp_path, tmp_path, mock_config)

    # Act
    result = await instance.process_pending_batches()

    # Assert
    assert result is not None
    assert isinstance(result, int)
