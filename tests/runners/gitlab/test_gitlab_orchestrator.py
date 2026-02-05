"""
Tests for GitLab Orchestrator
==============================

Tests for runners.gitlab.orchestrator - GitLab MR review orchestration
"""

from collections.abc import Callable
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

import pytest

from runners.gitlab.models import (
    GitLabRunnerConfig,
    MergeVerdict,
    MRContext,
    MRReviewFinding,
    MRReviewResult,
    ReviewCategory,
    ReviewSeverity,
)
from runners.gitlab.orchestrator import GitLabOrchestrator, ProgressCallback


@pytest.fixture
def temp_project_dir(tmp_path: Path) -> Path:
    """Create a temporary project directory."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir


@pytest.fixture
def mock_gitlab_config() -> GitLabRunnerConfig:
    """Create a mock GitLabRunnerConfig."""
    return GitLabRunnerConfig(
        token="test_token",
        project="group/project",
        instance_url="https://gitlab.example.com",
        model="claude-sonnet-4-5-20250929",
        thinking_level="medium",
    )


@pytest.fixture
def progress_callbacks() -> list[ProgressCallback]:
    """Fixture to collect progress callbacks."""
    callbacks = []

    def collector(callback: ProgressCallback) -> None:
        callbacks.append(callback)

    return collector


@pytest.fixture
def orchestrator(
    temp_project_dir: Path, mock_gitlab_config: GitLabRunnerConfig
) -> GitLabOrchestrator:
    """Create a GitLabOrchestrator instance for testing."""
    with patch("runners.gitlab.orchestrator.GitLabClient"), patch(
        "runners.gitlab.orchestrator.MRReviewEngine"
    ):
        return GitLabOrchestrator(
            project_dir=temp_project_dir,
            config=mock_gitlab_config,
            progress_callback=None,
        )


@pytest.mark.asyncio
async def test_GitLabOrchestrator___init__(
    temp_project_dir: Path, mock_gitlab_config: GitLabRunnerConfig
):
    """Test GitLabOrchestrator initialization."""
    with patch("runners.gitlab.orchestrator.GitLabClient"), patch(
        "runners.gitlab.orchestrator.MRReviewEngine"
    ):
        orchestrator = GitLabOrchestrator(
            project_dir=temp_project_dir,
            config=mock_gitlab_config,
            progress_callback=None,
        )

        assert orchestrator.project_dir == temp_project_dir
        assert orchestrator.config == mock_gitlab_config
        assert orchestrator.gitlab_dir == temp_project_dir / ".auto-claude" / "gitlab"
        assert orchestrator.gitlab_dir.exists()


def test_GitLabOrchestrator_ReportProgress(
    temp_project_dir: Path, mock_gitlab_config: GitLabRunnerConfig
):
    """Test _report_progress method."""
    callbacks = []

    def collector(callback: ProgressCallback) -> None:
        callbacks.append(callback)

    with patch("runners.gitlab.orchestrator.GitLabClient"), patch(
        "runners.gitlab.orchestrator.MRReviewEngine"
    ):
        orchestrator = GitLabOrchestrator(
            project_dir=temp_project_dir,
            config=mock_gitlab_config,
            progress_callback=collector,
        )

        orchestrator._report_progress(
            "test_phase", 50, "Test message", mr_iid=123
        )

        assert len(callbacks) == 1
        assert callbacks[0].phase == "test_phase"
        assert callbacks[0].progress == 50
        assert callbacks[0].message == "Test message"
        assert callbacks[0].mr_iid == 123


@pytest.mark.asyncio
async def test_GitLabOrchestrator_GatherMRContext(orchestrator: GitLabOrchestrator):
    """Test _gather_mr_context method."""
    # Mock client responses
    orchestrator.client.get_mr = MagicMock(
        return_value={
            "title": "Test MR",
            "description": "Test description",
            "author": {"username": "testuser"},
            "source_branch": "feature-branch",
            "target_branch": "main",
            "state": "opened",
            "sha": "abc123",
        }
    )

    orchestrator.client.get_mr_changes = MagicMock(
        return_value={
            "changes": [
                {
                    "new_path": "file1.py",
                    "old_path": "file1.py",
                    "diff": "@@ -1,1 +1,2 @@\n-old line\n+new line\n+another new line",
                }
            ]
        }
    )

    orchestrator.client.get_mr_commits = MagicMock(
        return_value=[
            {"id": "abc123", "short_id": "abc123", "title": "Test commit"}
        ]
    )

    context = await orchestrator._gather_mr_context(123)

    assert context.mr_iid == 123
    assert context.title == "Test MR"
    assert context.author == "testuser"
    assert context.source_branch == "feature-branch"
    assert context.target_branch == "main"
    assert len(context.changed_files) == 1
    assert context.total_additions == 2
    assert context.total_deletions == 1
    assert context.head_sha == "abc123"


@pytest.mark.asyncio
async def test_GitLabOrchestrator_ReviewMR_Success(orchestrator: GitLabOrchestrator):
    """Test review_mr with successful review."""
    # Mock client
    orchestrator.client.get_mr = MagicMock(
        return_value={
            "title": "Test MR",
            "description": "Test description",
            "author": {"username": "testuser"},
            "source_branch": "feature",
            "target_branch": "main",
            "state": "opened",
            "sha": "abc123",
        }
    )
    orchestrator.client.get_mr_changes = MagicMock(return_value={"changes": []})
    orchestrator.client.get_mr_commits = MagicMock(return_value=[])

    # Mock review engine
    findings = [
        MRReviewFinding(
            id="1",
            severity=ReviewSeverity.LOW,
            category=ReviewCategory.STYLE,
            title="Style suggestion",
            description="Prefer double quotes",
            file="app.py",
            line=42,
        )
    ]
    orchestrator.review_engine.run_review = AsyncMock(
        return_value=(findings, MergeVerdict.READY_TO_MERGE, "No issues", [])
    )
    orchestrator.review_engine.generate_summary = MagicMock(return_value="Summary")

    result = await orchestrator.review_mr(123)

    assert result.success is True
    assert result.mr_iid == 123
    assert result.project == "group/project"
    assert len(result.findings) == 1
    assert result.verdict == MergeVerdict.READY_TO_MERGE


@pytest.mark.asyncio
async def test_GitLabOrchestrator_ReviewMR_HTTPError_401(orchestrator: GitLabOrchestrator):
    """Test review_mr with 401 authentication error."""
    import urllib.error

    orchestrator.client.get_mr = MagicMock(side_effect=urllib.error.HTTPError(
        url="https://gitlab.example.com",
        code=401,
        msg="Unauthorized",
        hdrs={},
        fp=None
    ))

    result = await orchestrator.review_mr(123)

    assert result.success is False
    assert result.mr_iid == 123
    assert "authentication failed" in result.error.lower()


@pytest.mark.asyncio
async def test_GitLabOrchestrator_ReviewMR_HTTPError_404(orchestrator: GitLabOrchestrator):
    """Test review_mr with 404 not found error."""
    import urllib.error

    orchestrator.client.get_mr = MagicMock(side_effect=urllib.error.HTTPError(
        url="https://gitlab.example.com",
        code=404,
        msg="Not Found",
        hdrs={},
        fp=None
    ))

    result = await orchestrator.review_mr(123)

    assert result.success is False
    assert "not found" in result.error.lower()


@pytest.mark.asyncio
async def test_GitLabOrchestrator_ReviewMR_HTTPError_429(orchestrator: GitLabOrchestrator):
    """Test review_mr with 429 rate limit error."""
    import urllib.error

    orchestrator.client.get_mr = MagicMock(side_effect=urllib.error.HTTPError(
        url="https://gitlab.example.com",
        code=429,
        msg="Too Many Requests",
        hdrs={},
        fp=None
    ))

    result = await orchestrator.review_mr(123)

    assert result.success is False
    assert "rate limit" in result.error.lower()


@pytest.mark.asyncio
async def test_GitLabOrchestrator_ReviewMR_JSONDecodeError(orchestrator: GitLabOrchestrator):
    """Test review_mr with invalid JSON response."""
    import json

    orchestrator.client.get_mr = MagicMock(side_effect=json.JSONDecodeError("Test", doc="{}", pos=0))

    result = await orchestrator.review_mr(123)

    assert result.success is False
    assert "json" in result.error.lower()


@pytest.mark.asyncio
async def test_GitLabOrchestrator_ReviewMR_OSError(orchestrator: GitLabOrchestrator):
    """Test review_mr with OS error."""
    orchestrator.client.get_mr = MagicMock(side_effect=OSError("File system error"))

    result = await orchestrator.review_mr(123)

    assert result.success is False
    assert "file system" in result.error.lower()


@pytest.mark.asyncio
async def test_GitLabOrchestrator_ReviewMR_GenericException(orchestrator: GitLabOrchestrator):
    """Test review_mr with generic exception."""
    orchestrator.client.get_mr = MagicMock(side_effect=RuntimeError("Unexpected error"))

    result = await orchestrator.review_mr(123)

    assert result.success is False
    assert "RuntimeError" in result.error


@pytest.mark.asyncio
async def test_GitLabOrchestrator_FollowupReviewMR_NoPreviousReview(
    orchestrator: GitLabOrchestrator,
):
    """Test followup_review_mr when no previous review exists."""
    # Mock that no previous review exists
    with patch.object(MRReviewResult, "load", return_value=None):
        with pytest.raises(ValueError, match="No previous review found"):
            await orchestrator.followup_review_mr(123)


@pytest.mark.asyncio
async def test_GitLabOrchestrator_FollowupReviewMR_NoCommitSHA(
    orchestrator: GitLabOrchestrator,
):
    """Test followup_review_mr when previous review has no commit SHA."""
    # Mock previous review without commit SHA
    previous_review = MRReviewResult(
        mr_iid=123,
        project="group/project",
        success=True,
        findings=[],
        summary="Previous review",
        reviewed_commit_sha=None,
    )

    with patch.object(MRReviewResult, "load", return_value=previous_review):
        with pytest.raises(ValueError, match="doesn't have commit SHA"):
            await orchestrator.followup_review_mr(123)


@pytest.mark.asyncio
async def test_GitLabOrchestrator_FollowupReviewMR_NoNewCommits(
    orchestrator: GitLabOrchestrator,
):
    """Test followup_review_mr when there are no new commits."""
    # Mock previous review
    previous_review = MRReviewResult(
        mr_iid=123,
        project="group/project",
        success=True,
        findings=[],
        summary="Previous review",
        reviewed_commit_sha="abc123",
        verdict=MergeVerdict.READY_TO_MERGE,
        overall_status="approve",
    )

    # Mock current MR state (same commit)
    orchestrator.client.get_mr = MagicMock(
        return_value={
            "title": "Test MR",
            "sha": "abc123",
            "diff_refs": {"head_sha": "abc123"},
        }
    )
    orchestrator.client.get_mr_changes = MagicMock(return_value={"changes": []})
    orchestrator.client.get_mr_commits = MagicMock(return_value=[])
    orchestrator.client.get_mr = MagicMock(
        return_value={
            "title": "Test MR",
            "sha": "abc123",
            "diff_refs": {"head_sha": "abc123"},
        }
    )

    with patch.object(MRReviewResult, "load", return_value=previous_review):
        result = await orchestrator.followup_review_mr(123)

        assert result.success is True
        assert "No new commits since last review" in result.summary


@pytest.mark.asyncio
async def test_GitLabOrchestrator_FollowupReviewMR_WithNewCommits(
    orchestrator: GitLabOrchestrator,
):
    """Test followup_review_mr with new commits."""
    # Mock previous review
    previous_review = MRReviewResult(
        mr_iid=123,
        project="group/project",
        success=True,
        findings=[],
        summary="Previous review",
        reviewed_commit_sha="abc123",
        verdict=MergeVerdict.NEEDS_REVISION,
        overall_status="request_changes",
    )

    # Mock current MR state (new commit)
    orchestrator.client.get_mr = MagicMock(
        return_value={
            "title": "Test MR",
            "sha": "def456",
            "diff_refs": {"head_sha": "def456"},
        }
    )
    orchestrator.client.get_mr_changes = MagicMock(return_value={"changes": []})
    orchestrator.client.get_mr_commits = MagicMock(return_value=[])

    # Mock review engine
    new_findings = [
        MRReviewFinding(
            id="2",
            severity=ReviewSeverity.LOW,
            category=ReviewCategory.STYLE,
            title="New issue",
            description="New finding",
            file="app.py",
            line=10,
        )
    ]
    orchestrator.review_engine.run_review = AsyncMock(
        return_value=(new_findings, MergeVerdict.READY_TO_MERGE, "Fixed", [])
    )
    orchestrator.review_engine.generate_summary = MagicMock(return_value="Updated summary")

    with patch.object(MRReviewResult, "load", return_value=previous_review):
        result = await orchestrator.followup_review_mr(123)

        assert result.success is True
        assert result.is_followup_review is True
        assert result.reviewed_commit_sha == "def456"


@pytest.mark.asyncio
async def test_GitLabOrchestrator_FollowupReviewMR_HTTPError(orchestrator: GitLabOrchestrator):
    """Test followup_review_mr with HTTP error."""
    import urllib.error

    # Mock previous review
    previous_review = MRReviewResult(
        mr_iid=123,
        project="group/project",
        success=True,
        findings=[],
        summary="Previous review",
        reviewed_commit_sha="abc123",
    )

    # Mock client to raise error
    orchestrator.client.get_mr = MagicMock(side_effect=urllib.error.HTTPError(
        url="https://gitlab.example.com",
        code=403,
        msg="Forbidden",
        hdrs={},
        fp=None
    ))

    with patch.object(MRReviewResult, "load", return_value=previous_review):
        result = await orchestrator.followup_review_mr(123)

        assert result.success is False
        assert "access forbidden" in result.error.lower()


@pytest.mark.asyncio
async def test_GitLabOrchestrator_FollowupReviewMR_JSONDecodeError(
    orchestrator: GitLabOrchestrator,
):
    """Test followup_review_mr with JSON decode error."""
    import json

    # Mock previous review
    previous_review = MRReviewResult(
        mr_iid=123,
        project="group/project",
        success=True,
        findings=[],
        summary="Previous review",
        reviewed_commit_sha="abc123",
    )

    # Mock client to raise error
    orchestrator.client.get_mr = MagicMock(side_effect=json.JSONDecodeError("Test", doc="{}", pos=0))

    with patch.object(MRReviewResult, "load", return_value=previous_review):
        result = await orchestrator.followup_review_mr(123)

        assert result.success is False
        assert "json" in result.error.lower()


@pytest.mark.asyncio
async def test_GitLabOrchestrator_FollowupReviewMR_GenericException(
    orchestrator: GitLabOrchestrator,
):
    """Test followup_review_mr with generic exception."""
    # Mock previous review
    previous_review = MRReviewResult(
        mr_iid=123,
        project="group/project",
        success=True,
        findings=[],
        summary="Previous review",
        reviewed_commit_sha="abc123",
    )

    # Mock client to raise error
    orchestrator.client.get_mr = MagicMock(side_effect=ValueError("Unexpected error"))

    with patch.object(MRReviewResult, "load", return_value=previous_review):
        result = await orchestrator.followup_review_mr(123)

        assert result.success is False
        assert "ValueError" in result.error


def test_GitLabOrchestrator_ForwardProgress(orchestrator: GitLabOrchestrator):
    """Test _forward_progress method."""
    callbacks = []

    def collector(callback: ProgressCallback) -> None:
        callbacks.append(callback)

    orchestrator = GitLabOrchestrator(
        project_dir=orchestrator.project_dir,
        config=orchestrator.config,
        progress_callback=collector,
    )

    # Simulate engine calling the forwarded callback
    engine_callback = ProgressCallback(phase="engine", progress=30, message="Engine progress")
    orchestrator._forward_progress(engine_callback)

    assert len(callbacks) == 1
    assert callbacks[0].phase == "engine"


def test_ProgressCallback():
    """Test ProgressCallback dataclass."""
    callback = ProgressCallback(
        phase="test",
        progress=50,
        message="Test message",
        mr_iid=123,
    )

    assert callback.phase == "test"
    assert callback.progress == 50
    assert callback.message == "Test message"
    assert callback.mr_iid == 123
