"""
Tests for GitLab Client
========================

Tests for runners.gitlab.glab_client - GitLab API client wrapper
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import urllib.request
import urllib.error
from datetime import datetime, timezone

import pytest

from runners.gitlab.glab_client import (
    GitLabClient,
    GitLabConfig,
    encode_project_path,
    validate_endpoint,
    load_gitlab_config,
)


@pytest.fixture
def temp_project_dir(tmp_path: Path) -> Path:
    """Create a temporary project directory."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir


@pytest.fixture
def mock_gitlab_config() -> GitLabConfig:
    """Create a mock GitLabConfig."""
    return GitLabConfig(
        token="test_token",
        project="group/subgroup/project",
        instance_url="https://gitlab.example.com",
    )


@pytest.fixture
def gitlab_client(temp_project_dir: Path, mock_gitlab_config: GitLabConfig) -> GitLabClient:
    """Create a GitLabClient instance for testing."""
    return GitLabClient(
        project_dir=temp_project_dir,
        config=mock_gitlab_config,
        default_timeout=30.0,
    )


def test_encode_project_path():
    """Test encode_project_path."""
    result = encode_project_path("group/subgroup/project")
    assert result == "group%2Fsubgroup%2Fproject"

    result = encode_project_path("simple-project")
    assert result == "simple-project"


def test_validate_endpoint_valid():
    """Test validate_endpoint with valid endpoints."""
    # Should not raise
    validate_endpoint("/projects/123")
    validate_endpoint("/user")
    validate_endpoint("/users/456")
    validate_endpoint("/groups/789")
    validate_endpoint("/merge_requests/1")
    validate_endpoint("/issues/2")


def test_validate_endpoint_empty():
    """Test validate_endpoint with empty endpoint."""
    with pytest.raises(ValueError, match="cannot be empty"):
        validate_endpoint("")


def test_validate_endpoint_no_slash():
    """Test validate_endpoint without leading slash."""
    with pytest.raises(ValueError, match="must start with /"):
        validate_endpoint("projects/123")


def test_validate_endpoint_path_traversal():
    """Test validate_endpoint with path traversal."""
    with pytest.raises(ValueError, match="path traversal"):
        validate_endpoint("/projects/../../etc/passwd")


def test_validate_endpoint_null_byte():
    """Test validate_endpoint with null byte."""
    with pytest.raises(ValueError, match="null byte"):
        validate_endpoint("/projects/123\x00")


def test_validate_endpoint_invalid_pattern():
    """Test validate_endpoint with invalid pattern."""
    with pytest.raises(ValueError, match="does not match known GitLab API patterns"):
        validate_endpoint("/invalid/endpoint")


def test_GitLabClient___init__(temp_project_dir: Path, mock_gitlab_config: GitLabConfig):
    """Test GitLabClient initialization."""
    client = GitLabClient(
        project_dir=temp_project_dir,
        config=mock_gitlab_config,
        default_timeout=45.0,
    )

    assert client.project_dir == temp_project_dir
    assert client.config == mock_gitlab_config
    assert client.default_timeout == 45.0


def test_GitLabClient_ApiUrl(gitlab_client: GitLabClient):
    """Test _api_url method."""
    result = gitlab_client._api_url("/projects/123")
    assert result == "https://gitlab.example.com/api/v4/projects/123"

    # Test without leading slash
    result = gitlab_client._api_url("projects/123")
    assert result == "https://gitlab.example.com/api/v4/projects/123"

    # Test with trailing slash in instance URL
    gitlab_client.config.instance_url = "https://gitlab.example.com/"
    result = gitlab_client._api_url("/projects/123")
    assert result == "https://gitlab.example.com/api/v4/projects/123"


@patch("urllib.request.urlopen")
def test_GitLabClient_Fetch_Success(mock_urlopen, gitlab_client: GitLabClient):
    """Test _fetch with successful response."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = b'{"id": 123, "name": "test"}'
    mock_urlopen.return_value.__enter__.return_value = mock_response

    result = gitlab_client._fetch("/projects/123")

    assert result["id"] == 123
    assert result["name"] == "test"


@patch("urllib.request.urlopen")
def test_GitLabClient_Fetch_204_No_Content(mock_urlopen, gitlab_client: GitLabClient):
    """Test _fetch with 204 No Content response."""
    mock_response = MagicMock()
    mock_response.status = 204
    mock_urlopen.return_value.__enter__.return_value = mock_response

    result = gitlab_client._fetch("/projects/123", method="DELETE")

    assert result is None


@patch("urllib.request.urlopen")
def test_GitLabClient_Fetch_InvalidJSON(mock_urlopen, gitlab_client: GitLabClient):
    """Test _fetch with invalid JSON response."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = b"not json"
    mock_urlopen.return_value.__enter__.return_value = mock_response

    with pytest.raises(Exception, match="Invalid JSON response"):
        gitlab_client._fetch("/projects/123")


@patch("urllib.request.urlopen")
def test_GitLabClient_Fetch_RateLimit_WithRetryAfter(mock_urlopen, gitlab_client: GitLabClient):
    """Test _fetch with rate limiting and Retry-After header."""
    from email.message import Message

    # First call returns 429 with Retry-After header
    mock_error_response = MagicMock()
    mock_error_response.code = 429
    mock_error_response.headers = Message()
    mock_error_response.headers["Retry-After"] = "2"
    mock_error_response.read.return_value = b"Rate limited"

    # Second call succeeds - need context manager
    mock_success_response = MagicMock()
    mock_success_response.status = 200
    mock_success_response.read.return_value = b'{"id": 123}'
    mock_success_response.__enter__ = MagicMock(return_value=mock_success_response)
    mock_success_response.__exit__ = MagicMock(return_value=False)

    # Create the HTTPError with proper headers
    http_error = urllib.error.HTTPError(
        url="https://gitlab.example.com/api/v4/projects/123",
        code=429,
        msg="Rate limited",
        hdrs=mock_error_response.headers,
        fp=None,
    )

    mock_urlopen.side_effect = [http_error, mock_success_response]

    with patch("time.sleep") as mock_sleep:
        result = gitlab_client._fetch("/projects/123", max_retries=2)
        mock_sleep.assert_called_once_with(2)

    assert result["id"] == 123


@patch("urllib.request.urlopen")
def test_GitLabClient_Fetch_RateLimit_HTTPDate_RetryAfter(mock_urlopen, gitlab_client: GitLabClient):
    """Test _fetch with HTTP-date Retry-After header."""
    from email.message import Message

    # First call returns 429 with Retry-After as HTTP-date
    future_time = datetime.now(timezone.utc).replace(second=30)
    retry_after = future_time.strftime("%a, %d %b %Y %H:%M:%S GMT")

    mock_error_response = MagicMock()
    mock_error_response.code = 429
    mock_error_response.headers = Message()
    mock_error_response.headers["Retry-After"] = retry_after
    mock_error_response.read.return_value = b"Rate limited"

    mock_success_response = MagicMock()
    mock_success_response.status = 200
    mock_success_response.read.return_value = b'{"id": 123}'
    mock_success_response.__enter__ = MagicMock(return_value=mock_success_response)
    mock_success_response.__exit__ = MagicMock(return_value=False)

    # Create the HTTPError with proper headers
    http_error = urllib.error.HTTPError(
        url="https://gitlab.example.com/api/v4/projects/123",
        code=429,
        msg="Rate limited",
        hdrs=mock_error_response.headers,
        fp=None,
    )

    mock_urlopen.side_effect = [http_error, mock_success_response]

    with patch("time.sleep") as mock_sleep:
        result = gitlab_client._fetch("/projects/123", max_retries=2)
        # Should sleep at least 1 second
        assert mock_sleep.call_count == 1
        sleep_arg = mock_sleep.call_args[0][0]
        assert sleep_arg >= 1

    assert result["id"] == 123


@patch("urllib.request.urlopen")
def test_GitLabClient_Fetch_MaxRetries_Exceeded(mock_urlopen, gitlab_client: GitLabClient):
    """Test _fetch when max retries exceeded."""
    from email.message import Message

    mock_error_response = MagicMock()
    mock_error_response.code = 429
    mock_error_response.headers = Message()
    mock_error_response.read.return_value = b"Rate limited"

    mock_urlopen.side_effect = urllib.error.HTTPError(
        url="https://gitlab.example.com/api/v4/projects/123",
        code=429,
        msg="Rate limited",
        hdrs=mock_error_response.headers,
        fp=None,
    )

    with pytest.raises(Exception, match="GitLab API error 429"):
        gitlab_client._fetch("/projects/123", max_retries=2)


@patch("urllib.request.urlopen")
def test_GitLabClient_Fetch_HTTPError_Not429(mock_urlopen, gitlab_client: GitLabClient):
    """Test _fetch with non-429 HTTP error."""
    mock_error_response = MagicMock()
    mock_error_response.code = 404
    mock_error_response.read.return_value = b"Not found"

    mock_urlopen.side_effect = urllib.error.HTTPError(
        url="https://gitlab.example.com/api/v4/projects/999",
        code=404,
        msg="Not Found",
        hdrs={},
        fp=None,
    )

    with pytest.raises(Exception, match="GitLab API error 404"):
        gitlab_client._fetch("/projects/999")


@patch("urllib.request.urlopen")
def test_GitLabClient_Fetch_POST_Method(mock_urlopen, gitlab_client: GitLabClient):
    """Test _fetch with POST method."""
    mock_response = MagicMock()
    mock_response.status = 201
    mock_response.read.return_value = b'{"id": 456, "created": true}'
    mock_urlopen.return_value.__enter__.return_value = mock_response

    result = gitlab_client._fetch(
        "/projects/123/notes",
        method="POST",
        data={"body": "Test comment"},
    )

    assert result["id"] == 456
    assert result["created"] is True


@patch("urllib.request.urlopen")
def test_GitLabClient_GetMR(mock_urlopen, gitlab_client: GitLabClient):
    """Test get_mr method."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = b'{"iid": 1, "title": "Test MR"}'
    mock_urlopen.return_value.__enter__.return_value = mock_response

    result = gitlab_client.get_mr(1)

    assert result["iid"] == 1
    assert result["title"] == "Test MR"


@patch("urllib.request.urlopen")
def test_GitLabClient_GetMRChanges(mock_urlopen, gitlab_client: GitLabClient):
    """Test get_mr_changes method."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = b'''
    {
        "changes": [
            {
                "old_path": "file1.py",
                "new_path": "file1.py",
                "diff": "@@ -1,1 +1,2 @@\\n-old\\n+new"
            }
        ]
    }
    '''
    mock_urlopen.return_value.__enter__.return_value = mock_response

    result = gitlab_client.get_mr_changes(1)

    assert "changes" in result
    assert len(result["changes"]) == 1
    assert result["changes"][0]["old_path"] == "file1.py"


@patch("urllib.request.urlopen")
def test_GitLabClient_GetMRDiff(mock_urlopen, gitlab_client: GitLabClient):
    """Test get_mr_diff method."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = b'''
    {
        "changes": [
            {
                "diff": "@@ -1,1 +1,2 @@\\n-old\\n+new"
            },
            {
                "diff": "@@ -10,1 +10,1 @@\\n-old2\\n+new2"
            }
        ]
    }
    '''
    mock_urlopen.return_value.__enter__.return_value = mock_response

    result = gitlab_client.get_mr_diff(1)

    assert "@@ -1,1 +1,2 @@" in result
    assert "@@ -10,1 +10,1 @@" in result


@patch("urllib.request.urlopen")
def test_GitLabClient_GetMRCommits(mock_urlopen, gitlab_client: GitLabClient):
    """Test get_mr_commits method."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = b'''
    [
        {"id": "abc123", "short_id": "abc123", "title": "Commit 1"},
        {"id": "def456", "short_id": "def456", "title": "Commit 2"}
    ]
    '''
    mock_urlopen.return_value.__enter__.return_value = mock_response

    result = gitlab_client.get_mr_commits(1)

    assert len(result) == 2
    assert result[0]["id"] == "abc123"
    assert result[1]["id"] == "def456"


@patch("urllib.request.urlopen")
def test_GitLabClient_GetCurrentUser(mock_urlopen, gitlab_client: GitLabClient):
    """Test get_current_user method."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = b'{"id": 123, "username": "testuser"}'
    mock_urlopen.return_value.__enter__.return_value = mock_response

    result = gitlab_client.get_current_user()

    assert result["id"] == 123
    assert result["username"] == "testuser"


@patch("urllib.request.urlopen")
def test_GitLabClient_PostMRNote(mock_urlopen, gitlab_client: GitLabClient):
    """Test post_mr_note method."""
    mock_response = MagicMock()
    mock_response.status = 201
    mock_response.read.return_value = b'{"id": 789, "body": "Test comment"}'
    mock_urlopen.return_value.__enter__.return_value = mock_response

    result = gitlab_client.post_mr_note(1, "Test comment")

    assert result["id"] == 789
    assert result["body"] == "Test comment"


@patch("urllib.request.urlopen")
def test_GitLabClient_ApproveMR(mock_urlopen, gitlab_client: GitLabClient):
    """Test approve_mr method."""
    mock_response = MagicMock()
    mock_response.status = 201
    mock_response.read.return_value = b'{"approved": true}'
    mock_urlopen.return_value.__enter__.return_value = mock_response

    result = gitlab_client.approve_mr(1)

    assert result["approved"] is True


@patch("urllib.request.urlopen")
def test_GitLabClient_MergeMR(mock_urlopen, gitlab_client: GitLabClient):
    """Test merge_mr method."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = b'{"merged": true}'
    mock_urlopen.return_value.__enter__.return_value = mock_response

    result = gitlab_client.merge_mr(1)

    assert result["merged"] is True


@patch("urllib.request.urlopen")
def test_GitLabClient_MergeMR_Squash(mock_urlopen, gitlab_client: GitLabClient):
    """Test merge_mr method with squash."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = b'{"merged": true, "squash": true}'
    mock_urlopen.return_value.__enter__.return_value = mock_response

    result = gitlab_client.merge_mr(1, squash=True)

    assert result["merged"] is True
    assert result["squash"] is True


@patch("urllib.request.urlopen")
def test_GitLabClient_AssignMR(mock_urlopen, gitlab_client: GitLabClient):
    """Test assign_mr method."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = b'{"assignees": [{"id": 1}, {"id": 2}]}'
    mock_urlopen.return_value.__enter__.return_value = mock_response

    result = gitlab_client.assign_mr(1, [1, 2])

    assert len(result["assignees"]) == 2


def test_LoadGitlabConfig_NotFound(temp_project_dir: Path):
    """Test load_gitlab_config when config file doesn't exist."""
    result = load_gitlab_config(temp_project_dir)
    assert result is None


def test_LoadGitlabConfig_Success(temp_project_dir: Path):
    """Test load_gitlab_config with valid config file."""
    import json

    gitlab_dir = temp_project_dir / ".auto-claude" / "gitlab"
    gitlab_dir.mkdir(parents=True, exist_ok=True)

    config_data = {
        "token": "test_token",
        "project": "group/project",
        "instance_url": "https://gitlab.example.com",
    }

    config_file = gitlab_dir / "config.json"
    config_file.write_text(json.dumps(config_data))

    result = load_gitlab_config(temp_project_dir)

    assert result is not None
    assert result.token == "test_token"
    assert result.project == "group/project"
    assert result.instance_url == "https://gitlab.example.com"


def test_LoadGitlabConfig_DefaultInstanceURL(temp_project_dir: Path):
    """Test load_gitlab_config defaults instance_url to gitlab.com."""
    import json

    gitlab_dir = temp_project_dir / ".auto-claude" / "gitlab"
    gitlab_dir.mkdir(parents=True, exist_ok=True)

    config_data = {
        "token": "test_token",
        "project": "group/project",
    }

    config_file = gitlab_dir / "config.json"
    config_file.write_text(json.dumps(config_data))

    result = load_gitlab_config(temp_project_dir)

    assert result is not None
    assert result.instance_url == "https://gitlab.com"


def test_LoadGitlabConfig_MissingFields(temp_project_dir: Path):
    """Test load_gitlab_config with missing required fields."""
    import json

    gitlab_dir = temp_project_dir / ".auto-claude" / "gitlab"
    gitlab_dir.mkdir(parents=True, exist_ok=True)

    # Missing token
    config_data = {
        "project": "group/project",
    }

    config_file = gitlab_dir / "config.json"
    config_file.write_text(json.dumps(config_data))

    result = load_gitlab_config(temp_project_dir)
    assert result is None


def test_LoadGitlabConfig_InvalidJSON(temp_project_dir: Path):
    """Test load_gitlab_config with invalid JSON."""
    gitlab_dir = temp_project_dir / ".auto-claude" / "gitlab"
    gitlab_dir.mkdir(parents=True, exist_ok=True)

    config_file = gitlab_dir / "config.json"
    config_file.write_text("invalid json")

    result = load_gitlab_config(temp_project_dir)
    assert result is None


def test_GitLabConfig():
    """Test GitLabConfig dataclass."""
    config = GitLabConfig(
        token="test_token",
        project="group/project",
        instance_url="https://gitlab.example.com",
    )

    assert config.token == "test_token"
    assert config.project == "group/project"
    assert config.instance_url == "https://gitlab.example.com"
