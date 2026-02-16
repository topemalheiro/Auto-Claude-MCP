"""
Tests for MCP GitHub Service and Tools
=======================================

Tests GitHubService (repo detection, issue listing, PR review, triage, auto-fix)
and the github tool wrappers.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Setup: add backend to path and pre-mock SDK
_backend = Path(__file__).parent.parent / "apps" / "backend"
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

if "claude_agent_sdk" not in sys.modules:
    sys.modules["claude_agent_sdk"] = MagicMock()
    sys.modules["claude_agent_sdk.types"] = MagicMock()

import pytest

from mcp_server.services.github_service import GitHubService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def project_dir(tmp_path):
    """Create a temp project dir with .auto-claude/github structure."""
    github_dir = tmp_path / ".auto-claude" / "github"
    github_dir.mkdir(parents=True)
    return tmp_path


@pytest.fixture
def service(project_dir):
    return GitHubService(project_dir)


# ---------------------------------------------------------------------------
# _detect_repo
# ---------------------------------------------------------------------------


class TestDetectRepo:
    """Tests for _detect_repo() - parses git remote to owner/repo."""

    def test_ssh_remote(self, service):
        """SSH remote git@github.com:owner/repo.git is parsed correctly."""
        mock_result = MagicMock(returncode=0, stdout="git@github.com:owner/repo.git\n")
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = service._detect_repo()

        assert result == "owner/repo"
        mock_run.assert_called_once()
        args = mock_run.call_args
        assert args[0][0] == ["git", "remote", "get-url", "origin"]

    def test_ssh_remote_no_dot_git(self, service):
        """SSH remote without .git suffix works."""
        mock_result = MagicMock(returncode=0, stdout="git@github.com:owner/repo\n")
        with patch("subprocess.run", return_value=mock_result):
            result = service._detect_repo()

        assert result == "owner/repo"

    def test_https_remote(self, service):
        """HTTPS remote https://github.com/owner/repo.git is parsed correctly."""
        mock_result = MagicMock(
            returncode=0, stdout="https://github.com/owner/repo.git\n"
        )
        with patch("subprocess.run", return_value=mock_result):
            result = service._detect_repo()

        assert result == "owner/repo"

    def test_https_remote_no_dot_git(self, service):
        """HTTPS remote without .git suffix works."""
        mock_result = MagicMock(
            returncode=0, stdout="https://github.com/owner/repo\n"
        )
        with patch("subprocess.run", return_value=mock_result):
            result = service._detect_repo()

        assert result == "owner/repo"

    def test_non_github_remote_returns_none(self, service):
        """Non-GitHub remote (e.g. GitLab) returns None."""
        mock_result = MagicMock(
            returncode=0, stdout="https://gitlab.com/owner/repo.git\n"
        )
        with patch("subprocess.run", return_value=mock_result):
            result = service._detect_repo()

        assert result is None

    def test_git_command_fails_returns_none(self, service):
        """If git command returns non-zero, returns None."""
        mock_result = MagicMock(returncode=1, stdout="", stderr="not a git repo")
        with patch("subprocess.run", return_value=mock_result):
            result = service._detect_repo()

        assert result is None

    def test_exception_returns_none(self, service):
        """If subprocess raises, returns None."""
        with patch("subprocess.run", side_effect=OSError("git not found")):
            result = service._detect_repo()

        assert result is None


# ---------------------------------------------------------------------------
# _get_repo
# ---------------------------------------------------------------------------


class TestGetRepo:
    """Tests for _get_repo() - resolves repo from explicit arg or auto-detect."""

    def test_explicit_repo_returned_directly(self, service):
        """When repo is provided, it is returned without auto-detection."""
        result = service._get_repo("my-org/my-repo")
        assert result == "my-org/my-repo"

    def test_auto_detects_when_no_repo_provided(self, service):
        """When repo is None, falls back to _detect_repo."""
        with patch.object(service, "_detect_repo", return_value="detected/repo"):
            result = service._get_repo(None)

        assert result == "detected/repo"

    def test_raises_when_no_repo_and_no_detection(self, service):
        """When repo is None and detection fails, raises ValueError."""
        with patch.object(service, "_detect_repo", return_value=None):
            with pytest.raises(ValueError, match="Could not detect repository"):
                service._get_repo(None)


# ---------------------------------------------------------------------------
# list_issues
# ---------------------------------------------------------------------------


class TestListIssues:
    """Tests for list_issues() - calls gh CLI to list GitHub issues."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_list_issues_success(self, service):
        """Successful gh issue list returns parsed JSON."""
        issues_json = '[{"number": 1, "title": "Bug"}]'
        mock_result = MagicMock(returncode=0, stdout=issues_json)
        with patch.object(service, "_get_repo", return_value="owner/repo"):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                result = await service.list_issues(state="open", limit=10)

        assert result["success"] is True
        assert result["count"] == 1
        assert result["issues"][0]["number"] == 1

        # Verify gh CLI was called with correct args
        cmd = mock_run.call_args[0][0]
        assert "gh" in cmd
        assert "issue" in cmd
        assert "list" in cmd
        assert "--repo" in cmd
        assert "owner/repo" in cmd
        assert "--state" in cmd
        assert "open" in cmd

    @pytest.mark.asyncio(loop_scope="function")
    async def test_list_issues_gh_failure(self, service):
        """When gh CLI fails, returns error dict."""
        mock_result = MagicMock(
            returncode=1, stdout="", stderr="authentication required"
        )
        with patch.object(service, "_get_repo", return_value="owner/repo"):
            with patch("subprocess.run", return_value=mock_result):
                result = await service.list_issues()

        assert "error" in result
        assert "gh CLI failed" in result["error"]

    @pytest.mark.asyncio(loop_scope="function")
    async def test_list_issues_exception(self, service):
        """When an exception occurs, returns error dict."""
        with patch.object(
            service, "_get_repo", side_effect=ValueError("no repo")
        ):
            result = await service.list_issues()

        assert "error" in result
        assert "no repo" in result["error"]

    @pytest.mark.asyncio(loop_scope="function")
    async def test_list_issues_with_explicit_repo(self, service):
        """Repo argument is forwarded to _get_repo."""
        issues_json = "[]"
        mock_result = MagicMock(returncode=0, stdout=issues_json)
        with patch.object(
            service, "_get_repo", return_value="explicit/repo"
        ) as mock_get:
            with patch("subprocess.run", return_value=mock_result):
                await service.list_issues(repo="explicit/repo")

        mock_get.assert_called_once_with("explicit/repo")


# ---------------------------------------------------------------------------
# review_pr
# ---------------------------------------------------------------------------


class TestReviewPR:
    """Tests for review_pr() - wraps GitHubOrchestrator.review_pr."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_review_pr_success(self, service):
        """Successful review returns serialized result."""
        mock_orchestrator = MagicMock()
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"verdict": "approve", "findings": []}
        mock_orchestrator.review_pr = AsyncMock(return_value=mock_result)

        with patch.object(service, "_get_repo", return_value="owner/repo"):
            with patch.object(service, "_create_config") as mock_config:
                with patch.dict(
                    "sys.modules",
                    {
                        "runners.github.orchestrator": MagicMock(
                            GitHubOrchestrator=MagicMock(
                                return_value=mock_orchestrator
                            )
                        )
                    },
                ):
                    result = await service.review_pr(42)

        assert result["success"] is True
        assert result["data"]["verdict"] == "approve"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_review_pr_import_error(self, service):
        """When GitHubOrchestrator is not available, returns error."""
        with patch.object(service, "_get_repo", return_value="owner/repo"):
            with patch.dict("sys.modules", {"runners.github.orchestrator": None}):
                result = await service.review_pr(42)

        assert "error" in result
        assert "not available" in result["error"]

    @pytest.mark.asyncio(loop_scope="function")
    async def test_review_pr_get_repo_error(self, service):
        """When _get_repo raises inside the method, returns error dict."""
        # The import of GitHubOrchestrator happens first in the try block,
        # so we need to provide a valid module, then let _get_repo fail.
        mock_orch_mod = MagicMock()

        with patch.dict("sys.modules", {"runners.github.orchestrator": mock_orch_mod}):
            with patch.object(
                service, "_get_repo", side_effect=ValueError("no repo")
            ):
                result = await service.review_pr(42)

        assert "error" in result
        assert "no repo" in result["error"]


# ---------------------------------------------------------------------------
# get_review
# ---------------------------------------------------------------------------


class TestGetReview:
    """Tests for get_review() - loads saved review from disk."""

    def test_get_review_found(self, service):
        """When a review exists on disk, returns it."""
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"verdict": "approve"}

        with patch.dict(
            "sys.modules",
            {
                "runners.github.models": MagicMock(
                    PRReviewResult=MagicMock(
                        load=MagicMock(return_value=mock_result)
                    )
                )
            },
        ):
            result = service.get_review(42)

        assert result["success"] is True
        assert result["data"]["verdict"] == "approve"

    def test_get_review_not_found(self, service):
        """When no review exists, returns error."""
        with patch.dict(
            "sys.modules",
            {
                "runners.github.models": MagicMock(
                    PRReviewResult=MagicMock(
                        load=MagicMock(return_value=None)
                    )
                )
            },
        ):
            result = service.get_review(42)

        assert "error" in result
        assert "No review found" in result["error"]

    def test_get_review_import_error(self, service):
        """When models module is unavailable, returns error."""
        with patch.dict("sys.modules", {"runners.github.models": None}):
            result = service.get_review(42)

        assert "error" in result


# ---------------------------------------------------------------------------
# auto_fix_issue
# ---------------------------------------------------------------------------


class TestAutoFixIssue:
    """Tests for auto_fix_issue() - wraps GitHubOrchestrator.auto_fix_issue."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_auto_fix_success(self, service):
        """Successful auto-fix returns serialized state."""
        mock_orchestrator = MagicMock()
        mock_state = MagicMock()
        mock_state.to_dict.return_value = {"status": "completed"}
        mock_orchestrator.auto_fix_issue = AsyncMock(return_value=mock_state)

        with patch.object(service, "_get_repo", return_value="owner/repo"):
            with patch.object(service, "_create_config") as mock_config:
                mock_config.return_value = MagicMock()
                with patch.dict(
                    "sys.modules",
                    {
                        "runners.github.orchestrator": MagicMock(
                            GitHubOrchestrator=MagicMock(
                                return_value=mock_orchestrator
                            )
                        )
                    },
                ):
                    result = await service.auto_fix_issue(10)

        assert result["success"] is True

    @pytest.mark.asyncio(loop_scope="function")
    async def test_auto_fix_exception(self, service):
        """When auto_fix_issue raises, returns error."""
        with patch.object(
            service, "_get_repo", side_effect=ValueError("fail")
        ):
            result = await service.auto_fix_issue(10)

        assert "error" in result


# ---------------------------------------------------------------------------
# triage_issues
# ---------------------------------------------------------------------------


class TestTriageIssues:
    """Tests for triage_issues() - wraps GitHubOrchestrator.triage_issues."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_triage_success(self, service):
        """Successful triage returns list of serialized results."""
        mock_orchestrator = MagicMock()
        mock_triage_result = MagicMock()
        mock_triage_result.to_dict.return_value = {"issue": 1, "category": "bug"}
        mock_orchestrator.triage_issues = AsyncMock(
            return_value=[mock_triage_result]
        )

        with patch.object(service, "_get_repo", return_value="owner/repo"):
            with patch.object(service, "_create_config") as mock_config:
                mock_config.return_value = MagicMock()
                with patch.dict(
                    "sys.modules",
                    {
                        "runners.github.orchestrator": MagicMock(
                            GitHubOrchestrator=MagicMock(
                                return_value=mock_orchestrator
                            )
                        )
                    },
                ):
                    result = await service.triage_issues([1, 2])

        assert result["success"] is True
        assert result["count"] == 1

    @pytest.mark.asyncio(loop_scope="function")
    async def test_triage_exception(self, service):
        """When triage raises, returns error dict."""
        with patch.object(
            service, "_get_repo", side_effect=ValueError("fail")
        ):
            result = await service.triage_issues([1])

        assert "error" in result


# ---------------------------------------------------------------------------
# _create_config
# ---------------------------------------------------------------------------


class TestCreateConfig:
    """Tests for _create_config() - builds GitHubRunnerConfig."""

    def test_creates_config_with_env_token(self, service):
        """Uses GITHUB_TOKEN from environment if set."""
        mock_config_cls = MagicMock()
        mock_config_cls.return_value = MagicMock()

        with patch.dict("os.environ", {"GITHUB_TOKEN": "test-token"}):
            with patch.dict(
                "sys.modules",
                {
                    "runners.github.models": MagicMock(
                        GitHubRunnerConfig=mock_config_cls
                    )
                },
            ):
                config = service._create_config("owner/repo", "sonnet")

        mock_config_cls.assert_called_once()
        call_kwargs = mock_config_cls.call_args[1]
        assert call_kwargs["token"] == "test-token"
        assert call_kwargs["repo"] == "owner/repo"
        assert call_kwargs["model"] == "sonnet"

    def test_falls_back_to_gh_cli_token(self, service):
        """When GITHUB_TOKEN is empty, tries gh auth token."""
        mock_config_cls = MagicMock()
        mock_config_cls.return_value = MagicMock()
        mock_gh_result = MagicMock(returncode=0, stdout="gh-cli-token\n")

        with patch.dict("os.environ", {"GITHUB_TOKEN": ""}, clear=False):
            with patch("subprocess.run", return_value=mock_gh_result):
                with patch.dict(
                    "sys.modules",
                    {
                        "runners.github.models": MagicMock(
                            GitHubRunnerConfig=mock_config_cls
                        )
                    },
                ):
                    config = service._create_config("owner/repo")

        call_kwargs = mock_config_cls.call_args[1]
        assert call_kwargs["token"] == "gh-cli-token"
