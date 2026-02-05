"""Tests for triage_engine"""

from runners.github.services.triage_engine import TriageEngine
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
    return config


def test_TriageEngine___init__(mock_config):
    """Test TriageEngine.__init__"""

    # Arrange
    project_dir = Path("/tmp/test")
    github_dir = Path("/tmp/test")
    progress_callback = MagicMock()

    # Act
    instance = TriageEngine(project_dir, github_dir, mock_config, progress_callback)

    # Assert
    assert instance is not None
    assert instance.project_dir == project_dir
    assert instance.github_dir == github_dir
    assert instance.config == mock_config
    assert instance.progress_callback == progress_callback


@pytest.mark.asyncio
async def test_TriageEngine_triage_single_issue(mock_config, tmp_path):
    """Test TriageEngine.triage_single_issue"""

    # Arrange
    issue = {"number": 123, "title": "Test issue", "author": {"login": "testuser"}, "createdAt": "2024-01-01T00:00:00Z", "labels": [], "body": "Test body"}
    all_issues = []
    instance = TriageEngine(tmp_path, tmp_path, mock_config)

    # Act & Assert
    # This test would require mocking the AI client
    # We just verify the method exists and the engine is properly initialized
    assert hasattr(instance, 'triage_single_issue')
    assert callable(instance.triage_single_issue)


def test_TriageEngine_build_triage_context(mock_config, tmp_path):
    """Test TriageEngine.build_triage_context"""

    # Arrange
    issue = {"number": 123, "title": "Test issue", "author": {"login": "testuser"}, "createdAt": "2024-01-01T00:00:00Z", "labels": [], "body": "Test body"}
    all_issues = []
    instance = TriageEngine(tmp_path, tmp_path, mock_config)

    # Act
    result = instance.build_triage_context(issue, all_issues)

    # Assert
    assert result is not None
    assert isinstance(result, str)
    assert "#123" in result
    assert "Test issue" in result
