"""Tests for github_provider"""

import pytest
from datetime import datetime, timezone
from unittest.mock import ANY, AsyncMock, MagicMock, patch

from runners.github.providers.github_provider import GitHubProvider
from runners.github.providers.protocol import (
    IssueData,
    IssueFilters,
    LabelData,
    PRData,
    PRFilters,
    ProviderType,
    ReviewData,
)


@pytest.fixture
def mock_gh_client():
    """Create a mock GHClient."""
    client = MagicMock()
    client.pr_get = AsyncMock()
    client.pr_list = AsyncMock()
    client.pr_diff = AsyncMock()
    client.pr_review = AsyncMock()
    client.issue_get = AsyncMock()
    client.issue_list = AsyncMock()
    client.issue_comment = AsyncMock()
    client.issue_add_labels = AsyncMock()
    client.issue_remove_labels = AsyncMock()
    client.api_get = AsyncMock()
    client.api_post = AsyncMock()
    client._run_gh_command = AsyncMock()
    return client


@pytest.fixture
def provider(mock_gh_client):
    """Create a GitHubProvider instance with mocked client."""
    with patch("runners.github.providers.github_provider.GHClient", return_value=mock_gh_client):
        provider = GitHubProvider(_repo="owner/repo", _project_dir="/tmp/test")
        provider._gh_client = mock_gh_client
        return provider


@pytest.mark.asyncio
async def test_GitHubProvider___post_init__(provider):
    """Test GitHubProvider.__post_init__ initialization."""
    assert provider._repo == "owner/repo"
    assert provider.provider_type == ProviderType.GITHUB
    assert provider.repo == "owner/repo"
    assert provider.gh_client is not None


@pytest.mark.asyncio
async def test_GitHubProvider_fetch_pr(provider, mock_gh_client):
    """Test GitHubProvider.fetch_pr"""
    # Arrange
    mock_pr_data = {
        "number": 123,
        "title": "Test PR",
        "body": "Test body",
        "author": {"login": "testuser"},
        "state": "open",
        "headRefName": "feature-branch",
        "baseRefName": "main",
        "additions": 10,
        "deletions": 5,
        "changedFiles": 2,
        "files": [{"path": "test.txt"}],
        "url": "https://github.com/owner/repo/pull/123",
        "createdAt": "2024-01-01T00:00:00Z",
        "updatedAt": "2024-01-02T00:00:00Z",
        "labels": [{"name": "bug"}],
        "reviewRequests": [],
        "isDraft": False,
        "mergeable": "MERGEABLE",
    }
    mock_gh_client.pr_get.return_value = mock_pr_data
    mock_gh_client.pr_diff.return_value = "diff content"

    # Act
    result = await provider.fetch_pr(123)

    # Assert
    assert isinstance(result, PRData)
    assert result.number == 123
    assert result.title == "Test PR"
    assert result.author == "testuser"
    assert result.source_branch == "feature-branch"
    assert result.target_branch == "main"
    mock_gh_client.pr_get.assert_called_once_with(123, json_fields=ANY)
    mock_gh_client.pr_diff.assert_called_once_with(123)


@pytest.mark.asyncio
async def test_GitHubProvider_fetch_prs(provider, mock_gh_client):
    """Test GitHubProvider.fetch_prs"""
    # Arrange
    mock_prs_data = [
        {
            "number": 1,
            "title": "PR 1",
            "author": {"login": "user1"},
            "state": "open",
            "headRefName": "branch1",
            "baseRefName": "main",
            "labels": [{"name": "bug"}],
            "url": "https://github.com/owner/repo/pull/1",
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-02T00:00:00Z",
        }
    ]
    mock_gh_client.pr_list.return_value = mock_prs_data

    # Act
    result = await provider.fetch_prs(PRFilters(state="open"))

    # Assert
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].number == 1
    assert result[0].title == "PR 1"


@pytest.mark.asyncio
async def test_GitHubProvider_fetch_pr_diff(provider, mock_gh_client):
    """Test GitHubProvider.fetch_pr_diff"""
    # Arrange
    mock_gh_client.pr_diff.return_value = "diff content here"

    # Act
    result = await provider.fetch_pr_diff(123)

    # Assert
    assert result == "diff content here"
    mock_gh_client.pr_diff.assert_called_once_with(123)


@pytest.mark.asyncio
async def test_GitHubProvider_post_review(provider, mock_gh_client):
    """Test GitHubProvider.post_review"""
    # Arrange
    review = ReviewData(pr_number=123, event="approve", body="LGTM")
    mock_gh_client.pr_review.return_value = 456

    # Act
    result = await provider.post_review(123, review)

    # Assert
    assert result == 456
    mock_gh_client.pr_review.assert_called_once_with(
        pr_number=123, body="LGTM", event="APPROVE"
    )


@pytest.mark.asyncio
async def test_GitHubProvider_merge_pr(provider, mock_gh_client):
    """Test GitHubProvider.merge_pr"""
    # Arrange
    mock_gh_client._run_gh_command.return_value = ""

    # Act
    result = await provider.merge_pr(123, "squash", "My title")

    # Assert
    assert result is True
    mock_gh_client._run_gh_command.assert_called_once()
    call_args = mock_gh_client._run_gh_command.call_args[0][0]
    assert call_args[0] == "pr"
    assert call_args[1] == "merge"
    assert call_args[2] == "123"
    assert "--squash" in call_args
    assert "--subject" in call_args
    assert "My title" in call_args


@pytest.mark.asyncio
async def test_GitHubProvider_close_pr(provider, mock_gh_client):
    """Test GitHubProvider.close_pr"""
    # Arrange
    mock_gh_client._run_gh_command.return_value = ""

    # Act
    result = await provider.close_pr(123, "Closing this")

    # Assert
    assert result is True
    mock_gh_client.issue_comment.assert_called_once_with(123, "Closing this")
    mock_gh_client._run_gh_command.assert_called()


@pytest.mark.asyncio
async def test_GitHubProvider_fetch_issue(provider, mock_gh_client):
    """Test GitHubProvider.fetch_issue"""
    # Arrange
    mock_issue_data = {
        "number": 42,
        "title": "Test Issue",
        "body": "Issue body",
        "author": {"login": "testuser"},
        "state": "open",
        "labels": [{"name": "bug"}],
        "createdAt": "2024-01-01T00:00:00Z",
        "updatedAt": "2024-01-02T00:00:00Z",
        "url": "https://github.com/owner/repo/issues/42",
        "assignees": [{"login": "assignee1"}],
        "milestone": None,
    }
    mock_gh_client.issue_get.return_value = mock_issue_data

    # Act
    result = await provider.fetch_issue(42)

    # Assert
    assert isinstance(result, IssueData)
    assert result.number == 42
    assert result.title == "Test Issue"
    assert result.author == "testuser"
    assert result.labels == ["bug"]


@pytest.mark.asyncio
async def test_GitHubProvider_fetch_issues(provider, mock_gh_client):
    """Test GitHubProvider.fetch_issues"""
    # Arrange
    mock_issues_data = [
        {
            "number": 1,
            "title": "Issue 1",
            "body": "Body 1",
            "author": {"login": "user1"},
            "state": "open",
            "labels": [{"name": "bug"}],
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-02T00:00:00Z",
            "url": "https://github.com/owner/repo/issues/1",
            "assignees": [],
            "milestone": None,
        }
    ]
    mock_gh_client.issue_list.return_value = mock_issues_data

    # Act
    result = await provider.fetch_issues(IssueFilters(state="open"))

    # Assert
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].number == 1
    assert result[0].title == "Issue 1"


@pytest.mark.asyncio
async def test_GitHubProvider_create_issue(provider, mock_gh_client):
    """Test GitHubProvider.create_issue"""
    # Arrange
    mock_gh_client._run_gh_command.return_value = "https://github.com/owner/repo/issues/99"
    mock_issue_data = {
        "number": 99,
        "title": "New Issue",
        "body": "New body",
        "author": {"login": "creator"},
        "state": "open",
        "labels": [],
        "createdAt": "2024-01-01T00:00:00Z",
        "updatedAt": "2024-01-01T00:00:00Z",
        "url": "https://github.com/owner/repo/issues/99",
        "assignees": [],
        "milestone": None,
    }
    mock_gh_client.issue_get.return_value = mock_issue_data

    # Act
    result = await provider.create_issue("New Issue", "New body", ["bug"], ["user1"])

    # Assert
    assert isinstance(result, IssueData)
    assert result.number == 99
    assert result.title == "New Issue"
    mock_gh_client._run_gh_command.assert_called_once()
    call_args = mock_gh_client._run_gh_command.call_args[0][0]
    assert "issue" in call_args
    assert "create" in call_args


@pytest.mark.asyncio
async def test_GitHubProvider_close_issue(provider, mock_gh_client):
    """Test GitHubProvider.close_issue"""
    # Arrange
    mock_gh_client._run_gh_command.return_value = ""

    # Act
    result = await provider.close_issue(42, "Closing issue")

    # Assert
    assert result is True
    mock_gh_client.issue_comment.assert_called_once_with(42, "Closing issue")
    mock_gh_client._run_gh_command.assert_called()


@pytest.mark.asyncio
async def test_GitHubProvider_add_comment(provider, mock_gh_client):
    """Test GitHubProvider.add_comment"""
    # Arrange
    mock_gh_client.issue_comment.return_value = None

    # Act
    result = await provider.add_comment(42, "My comment")

    # Assert
    assert result == 0  # gh CLI doesn't return comment ID
    mock_gh_client.issue_comment.assert_called_once_with(42, "My comment")


@pytest.mark.asyncio
async def test_GitHubProvider_apply_labels(provider, mock_gh_client):
    """Test GitHubProvider.apply_labels"""
    # Arrange
    mock_gh_client.issue_add_labels.return_value = None

    # Act
    await provider.apply_labels(42, ["bug", "enhancement"])

    # Assert
    mock_gh_client.issue_add_labels.assert_called_once_with(42, ["bug", "enhancement"])


@pytest.mark.asyncio
async def test_GitHubProvider_remove_labels(provider, mock_gh_client):
    """Test GitHubProvider.remove_labels"""
    # Arrange
    mock_gh_client.issue_remove_labels.return_value = None

    # Act
    await provider.remove_labels(42, ["bug"])

    # Assert
    mock_gh_client.issue_remove_labels.assert_called_once_with(42, ["bug"])


@pytest.mark.asyncio
async def test_GitHubProvider_create_label(provider, mock_gh_client):
    """Test GitHubProvider.create_label"""
    # Arrange
    label = LabelData(name="new-label", color="FF0000", description="A new label")
    mock_gh_client._run_gh_command.return_value = ""

    # Act
    await provider.create_label(label)

    # Assert
    mock_gh_client._run_gh_command.assert_called_once()
    call_args = mock_gh_client._run_gh_command.call_args[0][0]
    assert "label" in call_args
    assert "create" in call_args
    assert "new-label" in call_args
    assert "--color" in call_args or "--color" in " ".join(call_args)


@pytest.mark.asyncio
async def test_GitHubProvider_list_labels(provider, mock_gh_client):
    """Test GitHubProvider.list_labels"""
    # Arrange
    mock_labels_json = '[{"name": "bug", "color": "FF0000", "description": "Bug report"}]'
    mock_gh_client._run_gh_command.return_value = mock_labels_json

    # Act
    result = await provider.list_labels()

    # Assert
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].name == "bug"
    assert result[0].color == "FF0000"
    assert result[0].description == "Bug report"


@pytest.mark.asyncio
async def test_GitHubProvider_get_repository_info(provider, mock_gh_client):
    """Test GitHubProvider.get_repository_info"""
    # Arrange
    mock_repo_info = {
        "name": "repo",
        "full_name": "owner/repo",
        "default_branch": "main",
        "private": False,
    }
    mock_gh_client.api_get.return_value = mock_repo_info

    # Act
    result = await provider.get_repository_info()

    # Assert
    assert result == mock_repo_info
    mock_gh_client.api_get.assert_called_once_with("/repos/owner/repo")


@pytest.mark.asyncio
async def test_GitHubProvider_get_default_branch(provider, mock_gh_client):
    """Test GitHubProvider.get_default_branch"""
    # Arrange
    mock_gh_client.api_get.return_value = {"default_branch": "develop"}

    # Act
    result = await provider.get_default_branch()

    # Assert
    assert result == "develop"


@pytest.mark.asyncio
async def test_GitHubProvider_check_permissions(provider, mock_gh_client):
    """Test GitHubProvider.check_permissions"""
    # Arrange
    mock_gh_client.api_get.return_value = {"permission": "admin"}

    # Act
    result = await provider.check_permissions("testuser")

    # Assert
    assert result == "admin"
    mock_gh_client.api_get.assert_called_once_with(
        "/repos/owner/repo/collaborators/testuser/permission"
    )


@pytest.mark.asyncio
async def test_GitHubProvider_api_get(provider, mock_gh_client):
    """Test GitHubProvider.api_get"""
    # Arrange
    mock_gh_client.api_get.return_value = {"data": "value"}

    # Act
    result = await provider.api_get("/test/endpoint", {"param": "value"})

    # Assert
    assert result == {"data": "value"}
    mock_gh_client.api_get.assert_called_once_with("/test/endpoint", {"param": "value"})


@pytest.mark.asyncio
async def test_GitHubProvider_api_post(provider, mock_gh_client):
    """Test GitHubProvider.api_post"""
    # Arrange
    mock_gh_client.api_post.return_value = {"created": True}

    # Act
    result = await provider.api_post("/test/endpoint", {"key": "value"})

    # Assert
    assert result == {"created": True}
    mock_gh_client.api_post.assert_called_once_with("/test/endpoint", {"key": "value"})
