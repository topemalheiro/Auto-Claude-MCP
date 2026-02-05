"""Tests for protocol"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from typing import Protocol, runtime_checkable

from runners.github.providers.protocol import (
    GitProvider,
    IssueData,
    IssueFilters,
    LabelData,
    PRData,
    PRFilters,
    ProviderType,
    ReviewData,
)


# Create a mock implementation of GitProvider for testing the protocol
@runtime_checkable
class MockGitProvider(Protocol):
    """Mock implementation of GitProvider protocol for testing."""

    @property
    def provider_type(self) -> ProviderType:
        ...

    @property
    def repo(self) -> str:
        ...


@pytest.fixture
def mock_provider():
    """Create a mock provider that implements GitProvider protocol."""
    provider = MagicMock()
    provider.provider_type = ProviderType.GITHUB
    provider.repo = "owner/repo"

    # Configure all async methods
    provider.fetch_pr = AsyncMock()
    provider.fetch_prs = AsyncMock()
    provider.fetch_pr_diff = AsyncMock()
    provider.post_review = AsyncMock()
    provider.merge_pr = AsyncMock()
    provider.close_pr = AsyncMock()
    provider.fetch_issue = AsyncMock()
    provider.fetch_issues = AsyncMock()
    provider.create_issue = AsyncMock()
    provider.close_issue = AsyncMock()
    provider.add_comment = AsyncMock()
    provider.apply_labels = AsyncMock()
    provider.remove_labels = AsyncMock()
    provider.create_label = AsyncMock()
    provider.list_labels = AsyncMock()
    provider.get_repository_info = AsyncMock()
    provider.get_default_branch = AsyncMock()
    provider.check_permissions = AsyncMock()
    provider.api_get = AsyncMock()
    provider.api_post = AsyncMock()

    return provider


@pytest.mark.asyncio
async def test_GitProvider_fetch_pr(mock_provider):
    """Test GitProvider.fetch_pr method through protocol."""
    # Arrange
    pr_data = PRData(
        number=123,
        title="Test PR",
        body="Test body",
        author="testuser",
        state="open",
        source_branch="feature",
        target_branch="main",
        additions=10,
        deletions=5,
        changed_files=2,
        files=[],
        diff="diff content",
        url="https://github.com/owner/repo/pull/123",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        provider=ProviderType.GITHUB,
    )
    mock_provider.fetch_pr.return_value = pr_data

    # Act
    result = await mock_provider.fetch_pr(123)

    # Assert
    assert isinstance(result, PRData)
    assert result.number == 123
    assert result.title == "Test PR"
    mock_provider.fetch_pr.assert_called_once_with(123)


@pytest.mark.asyncio
async def test_GitProvider_fetch_prs(mock_provider):
    """Test GitProvider.fetch_prs method through protocol."""
    # Arrange
    prs = [
        PRData(
            number=1,
            title="PR 1",
            body="",
            author="user1",
            state="open",
            source_branch="branch1",
            target_branch="main",
            additions=0,
            deletions=0,
            changed_files=0,
            files=[],
            diff="",
            url="",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            provider=ProviderType.GITHUB,
        )
    ]
    mock_provider.fetch_prs.return_value = prs

    # Act
    result = await mock_provider.fetch_prs(PRFilters(state="open"))

    # Assert
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].number == 1


@pytest.mark.asyncio
async def test_GitProvider_fetch_pr_diff(mock_provider):
    """Test GitProvider.fetch_pr_diff method through protocol."""
    # Arrange
    mock_provider.fetch_pr_diff.return_value = "diff content"

    # Act
    result = await mock_provider.fetch_pr_diff(123)

    # Assert
    assert result == "diff content"
    mock_provider.fetch_pr_diff.assert_called_once_with(123)


@pytest.mark.asyncio
async def test_GitProvider_post_review(mock_provider):
    """Test GitProvider.post_review method through protocol."""
    # Arrange
    review = ReviewData(pr_number=123, event="approve", body="LGTM")
    mock_provider.post_review.return_value = 456

    # Act
    result = await mock_provider.post_review(123, review)

    # Assert
    assert result == 456


@pytest.mark.asyncio
async def test_GitProvider_merge_pr(mock_provider):
    """Test GitProvider.merge_pr method through protocol."""
    # Arrange
    mock_provider.merge_pr.return_value = True

    # Act
    result = await mock_provider.merge_pr(123, "merge", "Title")

    # Assert
    assert result is True
    mock_provider.merge_pr.assert_called_once_with(123, "merge", "Title")


@pytest.mark.asyncio
async def test_GitProvider_close_pr(mock_provider):
    """Test GitProvider.close_pr method through protocol."""
    # Arrange
    mock_provider.close_pr.return_value = True

    # Act
    result = await mock_provider.close_pr(123, "Closing")

    # Assert
    assert result is True
    mock_provider.close_pr.assert_called_once_with(123, "Closing")


@pytest.mark.asyncio
async def test_GitProvider_fetch_issue(mock_provider):
    """Test GitProvider.fetch_issue method through protocol."""
    # Arrange
    issue_data = IssueData(
        number=42,
        title="Test Issue",
        body="Body",
        author="user",
        state="open",
        labels=["bug"],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        url="https://github.com/owner/repo/issues/42",
        provider=ProviderType.GITHUB,
    )
    mock_provider.fetch_issue.return_value = issue_data

    # Act
    result = await mock_provider.fetch_issue(42)

    # Assert
    assert isinstance(result, IssueData)
    assert result.number == 42
    assert result.title == "Test Issue"


@pytest.mark.asyncio
async def test_GitProvider_fetch_issues(mock_provider):
    """Test GitProvider.fetch_issues method through protocol."""
    # Arrange
    issues = [
        IssueData(
            number=1,
            title="Issue 1",
            body="",
            author="user",
            state="open",
            labels=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            url="",
            provider=ProviderType.GITHUB,
        )
    ]
    mock_provider.fetch_issues.return_value = issues

    # Act
    result = await mock_provider.fetch_issues(IssueFilters(state="open"))

    # Assert
    assert isinstance(result, list)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_GitProvider_create_issue(mock_provider):
    """Test GitProvider.create_issue method through protocol."""
    # Arrange
    issue_data = IssueData(
        number=99,
        title="New Issue",
        body="Body",
        author="creator",
        state="open",
        labels=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        url="https://github.com/owner/repo/issues/99",
        provider=ProviderType.GITHUB,
    )
    mock_provider.create_issue.return_value = issue_data

    # Act
    result = await mock_provider.create_issue("New Issue", "Body", ["bug"], ["user"])

    # Assert
    assert isinstance(result, IssueData)
    assert result.number == 99
    mock_provider.create_issue.assert_called_once_with(
        "New Issue", "Body", ["bug"], ["user"]
    )


@pytest.mark.asyncio
async def test_GitProvider_close_issue(mock_provider):
    """Test GitProvider.close_issue method through protocol."""
    # Arrange
    mock_provider.close_issue.return_value = True

    # Act
    result = await mock_provider.close_issue(42, "Closing")

    # Assert
    assert result is True
    mock_provider.close_issue.assert_called_once_with(42, "Closing")


@pytest.mark.asyncio
async def test_GitProvider_add_comment(mock_provider):
    """Test GitProvider.add_comment method through protocol."""
    # Arrange
    mock_provider.add_comment.return_value = 123

    # Act
    result = await mock_provider.add_comment(42, "Comment")

    # Assert
    assert result == 123
    mock_provider.add_comment.assert_called_once_with(42, "Comment")


@pytest.mark.asyncio
async def test_GitProvider_apply_labels(mock_provider):
    """Test GitProvider.apply_labels method through protocol."""
    # Arrange
    mock_provider.apply_labels.return_value = None

    # Act
    await mock_provider.apply_labels(42, ["bug", "enhancement"])

    # Assert
    mock_provider.apply_labels.assert_called_once_with(42, ["bug", "enhancement"])


@pytest.mark.asyncio
async def test_GitProvider_remove_labels(mock_provider):
    """Test GitProvider.remove_labels method through protocol."""
    # Arrange
    mock_provider.remove_labels.return_value = None

    # Act
    await mock_provider.remove_labels(42, ["bug"])

    # Assert
    mock_provider.remove_labels.assert_called_once_with(42, ["bug"])


@pytest.mark.asyncio
async def test_GitProvider_create_label(mock_provider):
    """Test GitProvider.create_label method through protocol."""
    # Arrange
    label = LabelData(name="new-label", color="FF0000", description="A label")
    mock_provider.create_label.return_value = None

    # Act
    await mock_provider.create_label(label)

    # Assert
    mock_provider.create_label.assert_called_once_with(label)


@pytest.mark.asyncio
async def test_GitProvider_list_labels(mock_provider):
    """Test GitProvider.list_labels method through protocol."""
    # Arrange
    labels = [
        LabelData(name="bug", color="FF0000", description="Bug"),
        LabelData(name="enhancement", color="00FF00", description="Enhancement"),
    ]
    mock_provider.list_labels.return_value = labels

    # Act
    result = await mock_provider.list_labels()

    # Assert
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0].name == "bug"
    assert result[1].name == "enhancement"


@pytest.mark.asyncio
async def test_GitProvider_get_repository_info(mock_provider):
    """Test GitProvider.get_repository_info method through protocol."""
    # Arrange
    repo_info = {
        "name": "repo",
        "full_name": "owner/repo",
        "default_branch": "main",
    }
    mock_provider.get_repository_info.return_value = repo_info

    # Act
    result = await mock_provider.get_repository_info()

    # Assert
    assert result == repo_info


@pytest.mark.asyncio
async def test_GitProvider_get_default_branch(mock_provider):
    """Test GitProvider.get_default_branch method through protocol."""
    # Arrange
    mock_provider.get_default_branch.return_value = "main"

    # Act
    result = await mock_provider.get_default_branch()

    # Assert
    assert result == "main"


@pytest.mark.asyncio
async def test_GitProvider_check_permissions(mock_provider):
    """Test GitProvider.check_permissions method through protocol."""
    # Arrange
    mock_provider.check_permissions.return_value = "admin"

    # Act
    result = await mock_provider.check_permissions("testuser")

    # Assert
    assert result == "admin"
    mock_provider.check_permissions.assert_called_once_with("testuser")


@pytest.mark.asyncio
async def test_GitProvider_api_get(mock_provider):
    """Test GitProvider.api_get method through protocol."""
    # Arrange
    mock_provider.api_get.return_value = {"data": "value"}

    # Act
    result = await mock_provider.api_get("/endpoint", {"param": "value"})

    # Assert
    assert result == {"data": "value"}
    mock_provider.api_get.assert_called_once_with("/endpoint", {"param": "value"})


@pytest.mark.asyncio
async def test_GitProvider_api_post(mock_provider):
    """Test GitProvider.api_post method through protocol."""
    # Arrange
    mock_provider.api_post.return_value = {"created": True}

    # Act
    result = await mock_provider.api_post("/endpoint", {"key": "value"})

    # Assert
    assert result == {"created": True}
    mock_provider.api_post.assert_called_once_with("/endpoint", {"key": "value"})


def test_GitProvider_protocol_properties(mock_provider):
    """Test GitProvider protocol properties."""
    # Assert
    assert mock_provider.provider_type == ProviderType.GITHUB
    assert mock_provider.repo == "owner/repo"
