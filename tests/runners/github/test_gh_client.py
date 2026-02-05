"""Tests for gh_client"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from runners.github.gh_client import (
    GHClient,
    GHCommandError,
    GHCommandResult,
    GHTimeoutError,
    PRTooLargeError,
)


@pytest.fixture
def temp_project_dir(tmp_path: Path) -> Path:
    """Create a temporary project directory."""
    return tmp_path / "test_project"


@pytest.fixture
def mock_gh_executable():
    """Mock gh executable."""
    return "gh"


@pytest.fixture
def gh_client(temp_project_dir: Path, mock_gh_executable) -> GHClient:
    """Create a GHClient instance for testing."""
    return GHClient(
        project_dir=temp_project_dir,
        default_timeout=30.0,
        max_retries=3,
        enable_rate_limiting=False,  # Disable for faster tests
        repo=None,
    )


@pytest.mark.asyncio
async def test_GHClient___init__(temp_project_dir: Path):
    """Test GHClient.__init__"""
    client = GHClient(
        project_dir=temp_project_dir,
        default_timeout=30.0,
        max_retries=3,
        enable_rate_limiting=True,
        repo="owner/repo",
    )
    assert client.project_dir == temp_project_dir
    assert client.default_timeout == 30.0
    assert client.max_retries == 3
    assert client.enable_rate_limiting is True
    assert client.repo == "owner/repo"


@pytest.mark.asyncio
async def test_GHClient_run(gh_client: GHClient):
    """Test GHClient.run"""
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        # Mock successful subprocess execution
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(
            return_value=(b'{"result": "success"}', b"")
        )
        mock_subprocess.return_value = mock_proc

        result = await gh_client.run(["pr", "list"], timeout=10.0)

        assert isinstance(result, GHCommandResult)
        assert result.returncode == 0
        assert result.stdout == '{"result": "success"}'
        assert result.stderr == ""


@pytest.mark.asyncio
async def test_GHClient_pr_list(gh_client: GHClient):
    """Test GHClient.pr_list"""
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(
            return_value=(b'[{"number": 123, "title": "Test PR"}]', b"")
        )
        mock_subprocess.return_value = mock_proc

        result = await gh_client.pr_list(state="open", limit=10)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["number"] == 123
        assert result[0]["title"] == "Test PR"


@pytest.mark.asyncio
async def test_GHClient_pr_get(gh_client: GHClient):
    """Test GHClient.pr_get"""
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(
            return_value=(b'{"number": 123, "title": "Test PR"}', b"")
        )
        mock_subprocess.return_value = mock_proc

        result = await gh_client.pr_get(123)

        assert isinstance(result, dict)
        assert result["number"] == 123
        assert result["title"] == "Test PR"


@pytest.mark.asyncio
async def test_GHClient_pr_diff(gh_client: GHClient):
    """Test GHClient.pr_diff"""
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"diff --git a/file.py b/file.py", b""))
        mock_subprocess.return_value = mock_proc

        result = await gh_client.pr_diff(123)

        assert isinstance(result, str)
        assert result.startswith("diff --git")


@pytest.mark.asyncio
async def test_GHClient_pr_review(gh_client: GHClient):
    """Test GHClient.pr_review"""
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))
        mock_subprocess.return_value = mock_proc

        result = await gh_client.pr_review(123, body="LGTM", event="approve")

        assert result == 0


@pytest.mark.asyncio
async def test_GHClient_issue_list(gh_client: GHClient):
    """Test GHClient.issue_list"""
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(
            return_value=(b'[{"number": 42, "title": "Test Issue"}]', b"")
        )
        mock_subprocess.return_value = mock_proc

        result = await gh_client.issue_list(state="open", limit=10)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["number"] == 42


@pytest.mark.asyncio
async def test_GHClient_issue_get(gh_client: GHClient):
    """Test GHClient.issue_get"""
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(
            return_value=(b'{"number": 42, "title": "Test Issue"}', b"")
        )
        mock_subprocess.return_value = mock_proc

        result = await gh_client.issue_get(42)

        assert isinstance(result, dict)
        assert result["number"] == 42


@pytest.mark.asyncio
async def test_GHClient_issue_comment(gh_client: GHClient):
    """Test GHClient.issue_comment"""
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))
        mock_subprocess.return_value = mock_proc

        result = await gh_client.issue_comment(42, body="Test comment")

        assert result is None


@pytest.mark.asyncio
async def test_GHClient_issue_add_labels(gh_client: GHClient):
    """Test GHClient.issue_add_labels"""
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))
        mock_subprocess.return_value = mock_proc

        result = await gh_client.issue_add_labels(42, labels=["bug", "enhancement"])

        assert result is None


@pytest.mark.asyncio
async def test_GHClient_issue_add_labels_empty(gh_client: GHClient):
    """Test GHClient.issue_add_labels with empty labels"""
    result = await gh_client.issue_add_labels(42, labels=[])
    assert result is None


@pytest.mark.asyncio
async def test_GHClient_issue_remove_labels(gh_client: GHClient):
    """Test GHClient.issue_remove_labels"""
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))
        mock_subprocess.return_value = mock_proc

        result = await gh_client.issue_remove_labels(42, labels=["bug"])

        assert result is None


@pytest.mark.asyncio
async def test_GHClient_issue_remove_labels_empty(gh_client: GHClient):
    """Test GHClient.issue_remove_labels with empty labels"""
    result = await gh_client.issue_remove_labels(42, labels=[])
    assert result is None


@pytest.mark.asyncio
async def test_GHClient_api_get(gh_client: GHClient):
    """Test GHClient.api_get"""
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b'{"data": "value"}', b""))
        mock_subprocess.return_value = mock_proc

        result = await gh_client.api_get("/repos/owner/repo/issues")

        assert result == {"data": "value"}


@pytest.mark.asyncio
async def test_GHClient_pr_merge(gh_client: GHClient):
    """Test GHClient.pr_merge"""
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))
        mock_subprocess.return_value = mock_proc

        result = await gh_client.pr_merge(123, merge_method="squash")

        assert result is None


@pytest.mark.asyncio
async def test_GHClient_pr_comment(gh_client: GHClient):
    """Test GHClient.pr_comment"""
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))
        mock_subprocess.return_value = mock_proc

        result = await gh_client.pr_comment(123, body="Test comment")

        assert result is None


@pytest.mark.asyncio
async def test_GHClient_pr_get_assignees(gh_client: GHClient):
    """Test GHClient.pr_get_assignees"""
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(
            return_value=(b'{"assignees": [{"login": "user1"}, {"login": "user2"}]}', b"")
        )
        mock_subprocess.return_value = mock_proc

        result = await gh_client.pr_get_assignees(123)

        assert isinstance(result, list)
        assert result == ["user1", "user2"]


@pytest.mark.asyncio
async def test_GHClient_pr_assign(gh_client: GHClient):
    """Test GHClient.pr_assign"""
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))
        mock_subprocess.return_value = mock_proc

        result = await gh_client.pr_assign(123, assignees=["user1"])

        assert result is None


@pytest.mark.asyncio
async def test_GHClient_pr_assign_empty(gh_client: GHClient):
    """Test GHClient.pr_assign with empty assignees"""
    result = await gh_client.pr_assign(123, assignees=[])
    assert result is None


@pytest.mark.asyncio
async def test_GHClient_compare_commits(gh_client: GHClient):
    """Test GHClient.compare_commits"""
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(
            return_value=(b'{"commits": [], "files": []}', b"")
        )
        mock_subprocess.return_value = mock_proc

        result = await gh_client.compare_commits("abc123", "def456")

        assert isinstance(result, dict)
        assert "commits" in result
        assert "files" in result


@pytest.mark.asyncio
async def test_GHClient_get_comments_since(gh_client: GHClient):
    """Test GHClient.get_comments_since"""
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"[]", b""))
        mock_subprocess.return_value = mock_proc

        result = await gh_client.get_comments_since(123, "2025-01-01T00:00:00Z")

        assert isinstance(result, dict)
        assert "review_comments" in result
        assert "issue_comments" in result


@pytest.mark.asyncio
async def test_GHClient_get_reviews_since(gh_client: GHClient):
    """Test GHClient.get_reviews_since"""
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"[]", b""))
        mock_subprocess.return_value = mock_proc

        result = await gh_client.get_reviews_since(123, "2025-01-01T00:00:00Z")

        assert isinstance(result, list)


@pytest.mark.asyncio
async def test_GHClient_get_pr_head_sha(gh_client: GHClient):
    """Test GHClient.get_pr_head_sha"""
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(
            return_value=(b'{"commits": [{"oid": "abc123def456"}]}', b"")
        )
        mock_subprocess.return_value = mock_proc

        result = await gh_client.get_pr_head_sha(123)

        assert result == "abc123def456"


@pytest.mark.asyncio
async def test_GHClient_get_pr_head_sha_no_commits(gh_client: GHClient):
    """Test GHClient.get_pr_head_sha with no commits"""
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b'{"commits": []}', b""))
        mock_subprocess.return_value = mock_proc

        result = await gh_client.get_pr_head_sha(123)

        assert result is None


@pytest.mark.asyncio
async def test_GHClient_get_pr_checks(gh_client: GHClient):
    """Test GHClient.get_pr_checks"""
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(
            return_value=(b'[{"name": "test", "state": "SUCCESS"}]', b"")
        )
        mock_subprocess.return_value = mock_proc

        result = await gh_client.get_pr_checks(123)

        assert isinstance(result, dict)
        assert "checks" in result
        assert "passing" in result
        assert "failing" in result
        assert "pending" in result
        assert result["passing"] == 1


@pytest.mark.asyncio
async def test_GHClient_get_workflows_awaiting_approval(gh_client: GHClient):
    """Test GHClient.get_workflows_awaiting_approval"""
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        # First call for PR data
        mock_proc1 = AsyncMock()
        mock_proc1.returncode = 0
        mock_proc1.communicate = AsyncMock(
            return_value=(b'{"headRefOid": "abc123"}', b"")
        )

        # Second call for workflow runs
        mock_proc2 = AsyncMock()
        mock_proc2.returncode = 0
        mock_proc2.communicate = AsyncMock(return_value=(b'{"workflow_runs": []}', b""))

        mock_subprocess.side_effect = [mock_proc1, mock_proc2]

        result = await gh_client.get_workflows_awaiting_approval(123)

        assert isinstance(result, dict)
        assert "awaiting_approval" in result
        assert "workflow_runs" in result


@pytest.mark.asyncio
async def test_GHClient_approve_workflow_run(gh_client: GHClient):
    """Test GHClient.approve_workflow_run"""
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))
        mock_subprocess.return_value = mock_proc

        result = await gh_client.approve_workflow_run(12345)

        assert result is True


@pytest.mark.asyncio
async def test_GHClient_approve_workflow_run_failure(gh_client: GHClient):
    """Test GHClient.approve_workflow_run on failure"""
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        mock_proc = AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=(b"", b"Error"))
        mock_subprocess.return_value = mock_proc

        result = await gh_client.approve_workflow_run(12345)

        assert result is False


@pytest.mark.asyncio
async def test_GHClient_get_pr_checks_comprehensive(gh_client: GHClient):
    """Test GHClient.get_pr_checks_comprehensive"""
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        # Mock get_pr_checks response
        mock_proc1 = AsyncMock()
        mock_proc1.returncode = 0
        mock_proc1.communicate = AsyncMock(
            return_value=(b'[{"name": "test", "state": "SUCCESS"}]', b"")
        )

        # Mock get_workflows_awaiting_approval response
        mock_proc2 = AsyncMock()
        mock_proc2.returncode = 0
        mock_proc2.communicate = AsyncMock(
            return_value=(b'{"headRefOid": "abc123"}', b"")
        )

        # Mock workflow runs response
        mock_proc3 = AsyncMock()
        mock_proc3.returncode = 0
        mock_proc3.communicate = AsyncMock(return_value=(b'{"workflow_runs": []}', b""))

        mock_subprocess.side_effect = [mock_proc1, mock_proc2, mock_proc3]

        result = await gh_client.get_pr_checks_comprehensive(123)

        assert isinstance(result, dict)
        assert "checks" in result
        assert "awaiting_approval" in result


@pytest.mark.asyncio
async def test_GHClient_get_pr_files(gh_client: GHClient):
    """Test GHClient.get_pr_files"""
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(
            return_value=(b'[{"filename": "test.py", "status": "modified"}]', b"")
        )
        mock_subprocess.return_value = mock_proc

        result = await gh_client.get_pr_files(123)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["filename"] == "test.py"


@pytest.mark.asyncio
async def test_GHClient_get_pr_commits(gh_client: GHClient):
    """Test GHClient.get_pr_commits"""
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(
            return_value=(b'[{"sha": "abc123", "commit": {"message": "Test"}}]', b"")
        )
        mock_subprocess.return_value = mock_proc

        result = await gh_client.get_pr_commits(123)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["sha"] == "abc123"


@pytest.mark.asyncio
async def test_GHClient_get_pr_files_changed_since(gh_client: GHClient):
    """Test GHClient.get_pr_files_changed_since"""
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        # Mock get_pr_files
        mock_proc1 = AsyncMock()
        mock_proc1.returncode = 0
        mock_proc1.communicate = AsyncMock(
            return_value=(b'[{"filename": "test.py", "sha": "blob123", "status": "modified"}]', b"")
        )

        # Mock get_pr_commits
        mock_proc2 = AsyncMock()
        mock_proc2.returncode = 0
        mock_proc2.communicate = AsyncMock(
            return_value=(b'[{"sha": "abc123", "commit": {"message": "Test"}}]', b"")
        )

        mock_subprocess.side_effect = [mock_proc1, mock_proc2]

        files, commits = await gh_client.get_pr_files_changed_since(123, "abc000")

        assert isinstance(files, list)
        assert isinstance(commits, list)


@pytest.mark.asyncio
async def test_GHClient_pr_diff_too_large(gh_client: GHClient):
    """Test GHClient.pr_diff raises PRTooLargeError for large PRs"""
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        mock_proc = AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(
            return_value=(b"", b"diff exceeded the maximum number of lines")
        )
        mock_subprocess.return_value = mock_proc

        with pytest.raises(PRTooLargeError):
            await gh_client.pr_diff(123)


@pytest.mark.asyncio
async def test_GHClient_add_repo_flag():
    """Test GHClient._add_repo_flag"""
    client = GHClient(
        project_dir=Path("/tmp"),
        repo="owner/repo",
        enable_rate_limiting=False,
    )

    args = ["pr", "list"]
    result = client._add_repo_flag(args)

    assert result == ["pr", "list", "-R", "owner/repo"]


@pytest.mark.asyncio
async def test_GHClient_add_repo_flag_no_repo():
    """Test GHClient._add_repo_flag when repo is not set"""
    client = GHClient(
        project_dir=Path("/tmp"),
        repo=None,
        enable_rate_limiting=False,
    )

    args = ["pr", "list"]
    result = client._add_repo_flag(args)

    assert result == ["pr", "list"]
