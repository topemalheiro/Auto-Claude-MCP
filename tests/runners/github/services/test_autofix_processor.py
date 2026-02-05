"""Tests for autofix_processor"""

from runners.github.services.autofix_processor import AutoFixProcessor
from runners.github.models import GitHubRunnerConfig
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
import pytest


@pytest.fixture
def mock_config():
    """Create a mock GitHubRunnerConfig."""
    config = MagicMock(spec=GitHubRunnerConfig)
    config.repo = "test/repo"
    config.auto_fix_enabled = True
    config.auto_fix_labels = ["auto-fix", "automated-fix"]
    return config


@pytest.fixture
def mock_permission_checker():
    """Create a mock permission checker."""
    checker = MagicMock()
    checker.verify_automation_trigger = AsyncMock(
        return_value=MagicMock(allowed=True, username="testuser", role="admin")
    )
    return checker


def test_AutoFixProcessor___init__(mock_config, mock_permission_checker):
    """Test AutoFixProcessor.__init__"""

    # Arrange
    github_dir = Path("/tmp/test")
    progress_callback = MagicMock()

    # Act
    instance = AutoFixProcessor(github_dir, mock_config, mock_permission_checker, progress_callback)

    # Assert
    assert instance is not None
    assert instance.github_dir == github_dir
    assert instance.config == mock_config
    assert instance.permission_checker == mock_permission_checker
    assert instance.progress_callback == progress_callback


@pytest.mark.asyncio
async def test_AutoFixProcessor_process_issue(mock_config, mock_permission_checker, tmp_path):
    """Test AutoFixProcessor.process_issue"""

    # Arrange
    issue_number = 123
    issue = {"number": 123, "title": "Test issue"}
    trigger_label = "auto-fix"
    instance = AutoFixProcessor(tmp_path, mock_config, mock_permission_checker)

    # Act
    result = await instance.process_issue(issue_number, issue, trigger_label)

    # Assert
    assert result is not None
    assert result.issue_number == issue_number


@pytest.mark.asyncio
async def test_AutoFixProcessor_get_queue(mock_config, mock_permission_checker, tmp_path):
    """Test AutoFixProcessor.get_queue"""

    # Arrange
    instance = AutoFixProcessor(tmp_path, mock_config, mock_permission_checker)
    # Create issues directory
    issues_dir = tmp_path / "issues"
    issues_dir.mkdir(parents=True)

    # Act
    result = await instance.get_queue()

    # Assert
    assert result is not None
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_AutoFixProcessor_check_labeled_issues(mock_config, mock_permission_checker, tmp_path):
    """Test AutoFixProcessor_check_labeled_issues"""

    # Arrange
    all_issues = [
        {
            "number": 1,
            "title": "Test issue",
            "labels": [{"name": "auto-fix"}],
        }
    ]
    instance = AutoFixProcessor(tmp_path, mock_config, mock_permission_checker)

    # Act
    result = await instance.check_labeled_issues(all_issues, verify_permissions=False)

    # Assert
    assert result is not None
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["issue_number"] == 1
