"""
Tests for GitHub Orchestrator
==============================

Tests for runners.github.orchestrator - GitHub PR review orchestration
"""

from collections.abc import Callable
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

import pytest

from runners.github.context_gatherer import PRContext, ChangedFile
from runners.github.models import (
    AICommentTriage,
    AICommentVerdict,
    AutoFixState,
    AutoFixStatus,
    GitHubRunnerConfig,
    MergeVerdict,
    PRReviewFinding,
    PRReviewResult,
    ReviewCategory,
    ReviewSeverity,
    StructuralIssue,
    TriageCategory,
    TriageResult,
)
from runners.github.orchestrator import GitHubOrchestrator, ProgressCallback


@pytest.fixture
def temp_project_dir(tmp_path: Path) -> Path:
    """Create a temporary project directory."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir


@pytest.fixture
def mock_config() -> GitHubRunnerConfig:
    """Create a mock GitHubRunnerConfig."""
    return GitHubRunnerConfig(
        token="test_token",
        repo="owner/repo",
        bot_token="test_bot_token",
        model="claude-sonnet-4-5-20250929",
        thinking_level="medium",
        auto_fix_enabled=True,
        auto_fix_labels=["auto-fix"],
        auto_post_reviews=False,
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
    temp_project_dir: Path, mock_config: GitHubRunnerConfig
) -> GitHubOrchestrator:
    """Create a GitHubOrchestrator instance for testing."""
    with patch("runners.github.orchestrator.GHClient"), patch(
        "runners.github.orchestrator.BotDetector"
    ), patch("runners.github.orchestrator.GitHubPermissionChecker"), patch(
        "runners.github.orchestrator.RateLimiter"
    ), patch(
        "runners.github.orchestrator.PRReviewEngine"
    ), patch(
        "runners.github.orchestrator.TriageEngine"
    ), patch(
        "runners.github.orchestrator.AutoFixProcessor"
    ), patch(
        "runners.github.orchestrator.BatchProcessor"
    ):
        return GitHubOrchestrator(
            project_dir=temp_project_dir,
            config=mock_config,
            progress_callback=None,
        )


@pytest.mark.asyncio
async def test_GitHubOrchestrator___init__(
    temp_project_dir: Path, mock_config: GitHubRunnerConfig
):
    """Test GitHubOrchestrator initialization."""
    with patch("runners.github.orchestrator.GHClient"), patch(
        "runners.github.orchestrator.BotDetector"
    ), patch("runners.github.orchestrator.GitHubPermissionChecker"), patch(
        "runners.github.orchestrator.RateLimiter"
    ), patch(
        "runners.github.orchestrator.PRReviewEngine"
    ), patch(
        "runners.github.orchestrator.TriageEngine"
    ), patch(
        "runners.github.orchestrator.AutoFixProcessor"
    ), patch(
        "runners.github.orchestrator.BatchProcessor"
    ):
        orchestrator = GitHubOrchestrator(
            project_dir=temp_project_dir,
            config=mock_config,
            progress_callback=None,
        )

        assert orchestrator.project_dir == temp_project_dir
        assert orchestrator.config == mock_config
        assert orchestrator.github_dir == temp_project_dir / ".auto-claude" / "github"
        assert orchestrator.github_dir.exists()


def test_GitHubOrchestrator_ReportProgress(
    temp_project_dir: Path, mock_config: GitHubRunnerConfig
):
    """Test _report_progress method."""
    callbacks = []

    def collector(callback: ProgressCallback) -> None:
        callbacks.append(callback)

    with patch("runners.github.orchestrator.GHClient"), patch(
        "runners.github.orchestrator.BotDetector"
    ), patch("runners.github.orchestrator.GitHubPermissionChecker"), patch(
        "runners.github.orchestrator.RateLimiter"
    ), patch(
        "runners.github.orchestrator.PRReviewEngine"
    ), patch(
        "runners.github.orchestrator.TriageEngine"
    ), patch(
        "runners.github.orchestrator.AutoFixProcessor"
    ), patch(
        "runners.github.orchestrator.BatchProcessor"
    ):
        orchestrator = GitHubOrchestrator(
            project_dir=temp_project_dir,
            config=mock_config,
            progress_callback=collector,
        )

        orchestrator._report_progress(
            "test_phase", 50, "Test message", pr_number=123
        )

        assert len(callbacks) == 1
        assert callbacks[0].phase == "test_phase"
        assert callbacks[0].progress == 50
        assert callbacks[0].message == "Test message"
        assert callbacks[0].pr_number == 123


def test_GitHubOrchestrator_GenerateVerdict_no_findings(orchestrator: GitHubOrchestrator):
    """Test _generate_verdict with no findings."""
    findings: list[PRReviewFinding] = []
    structural_issues: list[StructuralIssue] = []
    ai_triages: list[AICommentTriage] = []
    ci_status = {"passing": 1, "failing": 0, "pending": 0, "awaiting_approval": 0}

    verdict, reasoning, blockers = orchestrator._generate_verdict(
        findings=findings,
        structural_issues=structural_issues,
        ai_triages=ai_triages,
        ci_status=ci_status,
        has_merge_conflicts=False,
        merge_state_status="CLEAN",
    )

    assert verdict == MergeVerdict.READY_TO_MERGE
    assert "No blocking issues found" in reasoning
    assert len(blockers) == 0


def test_GitHubOrchestrator_GenerateVerdict_critical_findings(orchestrator: GitHubOrchestrator):
    """Test _generate_verdict with critical findings."""
    findings = [
        PRReviewFinding(
            id="1",
            severity=ReviewSeverity.CRITICAL,
            category=ReviewCategory.SECURITY,
            title="Critical security issue",
            description="SQL injection vulnerability",
            file="app.py",
            line=42,
        )
    ]
    structural_issues: list[StructuralIssue] = []
    ai_triages: list[AICommentTriage] = []
    ci_status = {"passing": 1, "failing": 0, "pending": 0, "awaiting_approval": 0}

    verdict, reasoning, blockers = orchestrator._generate_verdict(
        findings=findings,
        structural_issues=structural_issues,
        ai_triages=ai_triages,
        ci_status=ci_status,
        has_merge_conflicts=False,
        merge_state_status="CLEAN",
    )

    assert verdict == MergeVerdict.BLOCKED
    assert "security" in reasoning.lower()
    assert len(blockers) > 0


def test_GitHubOrchestrator_GenerateVerdict_merge_conflicts(orchestrator: GitHubOrchestrator):
    """Test _generate_verdict with merge conflicts."""
    findings: list[PRReviewFinding] = []
    structural_issues: list[StructuralIssue] = []
    ai_triages: list[AICommentTriage] = []
    ci_status = {"passing": 1, "failing": 0, "pending": 0, "awaiting_approval": 0}

    verdict, reasoning, blockers = orchestrator._generate_verdict(
        findings=findings,
        structural_issues=structural_issues,
        ai_triages=ai_triages,
        ci_status=ci_status,
        has_merge_conflicts=True,
        merge_state_status="CLEAN",
    )

    assert verdict == MergeVerdict.BLOCKED
    assert "merge conflict" in reasoning.lower()
    assert any("merge conflict" in b.lower() for b in blockers)


def test_GitHubOrchestrator_GenerateVerdict_branch_behind(orchestrator: GitHubOrchestrator):
    """Test _generate_verdict with branch behind base."""
    findings = [
        PRReviewFinding(
            id="1",
            severity=ReviewSeverity.HIGH,
            category=ReviewCategory.QUALITY,
            title="Code quality issue",
            description="Missing error handling",
            file="app.py",
            line=42,
        )
    ]
    structural_issues: list[StructuralIssue] = []
    ai_triages: list[AICommentTriage] = []
    ci_status = {"passing": 1, "failing": 0, "pending": 0, "awaiting_approval": 0}

    verdict, reasoning, blockers = orchestrator._generate_verdict(
        findings=findings,
        structural_issues=structural_issues,
        ai_triages=ai_triages,
        ci_status=ci_status,
        has_merge_conflicts=False,
        merge_state_status="BEHIND",
    )

    assert verdict == MergeVerdict.NEEDS_REVISION
    assert "out of date" in reasoning.lower()
    assert any("behind" in b.lower() or "out of date" in b.lower() for b in blockers)


def test_GitHubOrchestrator_GenerateVerdict_ci_failing(orchestrator: GitHubOrchestrator):
    """Test _generate_verdict with failing CI."""
    findings: list[PRReviewFinding] = []
    structural_issues: list[StructuralIssue] = []
    ai_triages: list[AICommentTriage] = []
    ci_status = {
        "passing": 1,
        "failing": 2,
        "pending": 0,
        "awaiting_approval": 0,
        "failed_checks": ["test-suite", "lint"],
    }

    verdict, reasoning, blockers = orchestrator._generate_verdict(
        findings=findings,
        structural_issues=structural_issues,
        ai_triages=ai_triages,
        ci_status=ci_status,
        has_merge_conflicts=False,
        merge_state_status="CLEAN",
    )

    assert verdict == MergeVerdict.BLOCKED
    assert "ci" in reasoning.lower()
    assert any("ci failed" in b.lower() for b in blockers)


def test_GitHubOrchestrator_GenerateVerdict_workflows_awaiting_approval(
    orchestrator: GitHubOrchestrator,
):
    """Test _generate_verdict with workflows awaiting approval."""
    findings: list[PRReviewFinding] = []
    structural_issues: list[StructuralIssue] = []
    ai_triages: list[AICommentTriage] = []
    ci_status = {
        "passing": 1,
        "failing": 0,
        "pending": 0,
        "awaiting_approval": 2,
    }

    verdict, reasoning, blockers = orchestrator._generate_verdict(
        findings=findings,
        structural_issues=structural_issues,
        ai_triages=ai_triages,
        ci_status=ci_status,
        has_merge_conflicts=False,
        merge_state_status="CLEAN",
    )

    assert verdict == MergeVerdict.BLOCKED
    assert "awaiting" in reasoning.lower() or "approval" in reasoning.lower()
    assert any("awaiting" in b.lower() or "approval" in b.lower() for b in blockers)


def test_GitHubOrchestrator_GenerateVerdict_high_medium_findings(
    orchestrator: GitHubOrchestrator,
):
    """Test _generate_verdict with high and medium findings."""
    findings = [
        PRReviewFinding(
            id="1",
            severity=ReviewSeverity.HIGH,
            category=ReviewCategory.QUALITY,
            title="High severity issue",
            description="Missing error handling",
            file="app.py",
            line=42,
        ),
        PRReviewFinding(
            id="2",
            severity=ReviewSeverity.MEDIUM,
            category=ReviewCategory.STYLE,
            title="Medium severity issue",
            description="Code style inconsistency",
            file="app.py",
            line=50,
        ),
    ]
    structural_issues: list[StructuralIssue] = []
    ai_triages: list[AICommentTriage] = []
    ci_status = {"passing": 1, "failing": 0, "pending": 0, "awaiting_approval": 0}

    verdict, reasoning, blockers = orchestrator._generate_verdict(
        findings=findings,
        structural_issues=structural_issues,
        ai_triages=ai_triages,
        ci_status=ci_status,
        has_merge_conflicts=False,
        merge_state_status="CLEAN",
    )

    assert verdict == MergeVerdict.NEEDS_REVISION
    assert "must be addressed" in reasoning.lower()


def test_GitHubOrchestrator_GenerateVerdict_low_findings_only(
    orchestrator: GitHubOrchestrator,
):
    """Test _generate_verdict with only low severity findings."""
    findings = [
        PRReviewFinding(
            id="1",
            severity=ReviewSeverity.LOW,
            category=ReviewCategory.STYLE,
            title="Minor style issue",
            description="Prefer double quotes",
            file="app.py",
            line=42,
        )
    ]
    structural_issues: list[StructuralIssue] = []
    ai_triages: list[AICommentTriage] = []
    ci_status = {"passing": 1, "failing": 0, "pending": 0, "awaiting_approval": 0}

    verdict, reasoning, blockers = orchestrator._generate_verdict(
        findings=findings,
        structural_issues=structural_issues,
        ai_triages=ai_triages,
        ci_status=ci_status,
        has_merge_conflicts=False,
        merge_state_status="CLEAN",
    )

    assert verdict == MergeVerdict.READY_TO_MERGE
    assert "non-blocking" in reasoning.lower()


def test_GitHubOrchestrator_CalculateRiskAssessment(orchestrator: GitHubOrchestrator):
    """Test _calculate_risk_assessment."""
    context = PRContext(
        pr_number=123,
        title="Test PR",
        description="Test description",
        author="testuser",
        base_branch="main",
        head_branch="feature-branch",
        state="open",
        changed_files=[
            ChangedFile(
                path="file1.py",
                status="modified",
                additions=100,
                deletions=50,
                content="current content",
                base_content="base content",
                patch="diff content",
            )
        ],
        diff="+ 100 lines\n- 50 lines",
        repo_structure="Simple repo structure",
        related_files=[],
        commits=[],
        total_additions=300,
        total_deletions=100,
    )

    findings = [
        PRReviewFinding(
            id="1",
            severity=ReviewSeverity.MEDIUM,
            category=ReviewCategory.SECURITY,
            title="Security issue",
            description="Minor security concern",
            file="app.py",
            line=42,
        )
    ]
    structural_issues: list[StructuralIssue] = []

    risk = orchestrator._calculate_risk_assessment(context, findings, structural_issues)

    assert risk is not None
    assert "complexity" in risk
    assert "security_impact" in risk
    assert "scope_coherence" in risk
    assert risk["complexity"] == "medium"  # 400 total changes
    assert risk["security_impact"] == "low"  # medium severity security finding


def test_GitHubOrchestrator_GenerateBottomLine(orchestrator: GitHubOrchestrator):
    """Test _generate_bottom_line."""
    findings = [
        PRReviewFinding(
            id="1",
            severity=ReviewSeverity.HIGH,
            category=ReviewCategory.QUALITY,
            title="High severity issue",
            description="Missing error handling",
            file="app.py",
            line=42,
        )
    ]
    ci_status = {"passing": 1, "failing": 0, "pending": 0, "awaiting_approval": 0}
    blockers = []

    # Test READY_TO_MERGE
    bottom_line = orchestrator._generate_bottom_line(
        MergeVerdict.READY_TO_MERGE, ci_status, blockers, []
    )
    assert "ready to merge" in bottom_line.lower()

    # Test BLOCKED with merge conflicts
    blockers = ["Merge Conflicts: PR has conflicts"]
    bottom_line = orchestrator._generate_bottom_line(
        MergeVerdict.BLOCKED, ci_status, blockers, findings
    )
    assert "blocked" in bottom_line.lower()
    assert "merge conflict" in bottom_line.lower()

    # Test NEEDS_REVISION
    blockers = []
    bottom_line = orchestrator._generate_bottom_line(
        MergeVerdict.NEEDS_REVISION, ci_status, blockers, findings
    )
    assert "needs revision" in bottom_line.lower()


def test_GitHubOrchestrator_FormatReviewBody(orchestrator: GitHubOrchestrator):
    """Test _format_review_body."""
    result = PRReviewResult(
        pr_number=123,
        repo="owner/repo",
        success=True,
        findings=[],
        summary="Test summary",
        overall_status="approve",
    )

    body = orchestrator._format_review_body(result)

    assert body == "Test summary"


@pytest.mark.asyncio
async def test_GitHubOrchestrator_CreateSkipResult(orchestrator: GitHubOrchestrator):
    """Test _create_skip_result method."""
    result = await orchestrator._create_skip_result(123, "Bot-authored PR")

    assert result.pr_number == 123
    assert result.repo == "owner/repo"
    assert result.success is True
    assert result.findings == []
    assert "Skipped review" in result.summary
    assert "Bot-authored PR" in result.summary


@pytest.mark.asyncio
async def test_GitHubOrchestrator_FetchPRData(orchestrator: GitHubOrchestrator):
    """Test _fetch_pr_data method."""
    orchestrator.gh_client.pr_get = AsyncMock(
        return_value={"number": 123, "title": "Test PR", "state": "open"}
    )

    result = await orchestrator._fetch_pr_data(123)

    assert result["number"] == 123
    assert result["title"] == "Test PR"


@pytest.mark.asyncio
async def test_GitHubOrchestrator_FetchPRDiff(orchestrator: GitHubOrchestrator):
    """Test _fetch_pr_diff method."""
    orchestrator.gh_client.pr_diff = AsyncMock(return_value="diff --git a/file.py b/file.py")

    result = await orchestrator._fetch_pr_diff(123)

    assert result == "diff --git a/file.py b/file.py"


@pytest.mark.asyncio
async def test_GitHubOrchestrator_FetchIssueData(orchestrator: GitHubOrchestrator):
    """Test _fetch_issue_data method."""
    orchestrator.gh_client.issue_get = AsyncMock(
        return_value={"number": 42, "title": "Test Issue", "state": "open"}
    )

    result = await orchestrator._fetch_issue_data(42)

    assert result["number"] == 42
    assert result["title"] == "Test Issue"


@pytest.mark.asyncio
async def test_GitHubOrchestrator_FetchOpenIssues(orchestrator: GitHubOrchestrator):
    """Test _fetch_open_issues method."""
    orchestrator.gh_client.issue_list = AsyncMock(
        return_value=[{"number": 1, "title": "Issue 1"}, {"number": 2, "title": "Issue 2"}]
    )

    result = await orchestrator._fetch_open_issues(limit=100)

    assert len(result) == 2
    assert result[0]["number"] == 1


@pytest.mark.asyncio
async def test_GitHubOrchestrator_PostPRReview(orchestrator: GitHubOrchestrator):
    """Test _post_pr_review method."""
    orchestrator.gh_client.pr_review = AsyncMock(return_value=12345)

    result = await orchestrator._post_pr_review(
        123, body="LGTM!", event="APPROVE"
    )

    assert result == 12345


@pytest.mark.asyncio
async def test_GitHubOrchestrator_PostIssueComment(orchestrator: GitHubOrchestrator):
    """Test _post_issue_comment method."""
    orchestrator.gh_client.issue_comment = AsyncMock(return_value=None)

    result = await orchestrator._post_issue_comment(42, "Test comment")

    assert result is None


@pytest.mark.asyncio
async def test_GitHubOrchestrator_AddIssueLabels(orchestrator: GitHubOrchestrator):
    """Test _add_issue_labels method."""
    orchestrator.gh_client.issue_add_labels = AsyncMock(return_value=None)

    result = await orchestrator._add_issue_labels(42, ["bug", "enhancement"])

    assert result is None


@pytest.mark.asyncio
async def test_GitHubOrchestrator_RemoveIssueLabels(orchestrator: GitHubOrchestrator):
    """Test _remove_issue_labels method."""
    orchestrator.gh_client.issue_remove_labels = AsyncMock(return_value=None)

    result = await orchestrator._remove_issue_labels(42, ["wontfix"])

    assert result is None


@pytest.mark.asyncio
async def test_GitHubOrchestrator_TriageIssues(orchestrator: GitHubOrchestrator):
    """Test triage_issues method."""
    orchestrator._fetch_open_issues = AsyncMock(
        return_value=[
            {"number": 1, "title": "Bug issue", "state": "open"},
            {"number": 2, "title": "Feature issue", "state": "open"},
        ]
    )
    orchestrator.triage_engine.triage_single_issue = AsyncMock(
        side_effect=lambda issue, all_issues: TriageResult(
            issue_number=issue["number"],
            repo="owner/repo",
            category=TriageCategory.BUG,
            confidence=0.9,
            is_duplicate=False,
            is_spam=False,
            is_feature_creep=False,
        )
    )

    results = await orchestrator.triage_issues(issue_numbers=None, apply_labels=False)

    assert len(results) == 2
    assert results[0].issue_number == 1
    assert results[0].category == TriageCategory.BUG


@pytest.mark.asyncio
async def test_GitHubOrchestrator_AutoFixIssue(orchestrator: GitHubOrchestrator):
    """Test auto_fix_issue method."""
    orchestrator._fetch_issue_data = AsyncMock(
        return_value={"number": 42, "title": "Fix bug", "state": "open"}
    )
    expected_state = AutoFixState(
        issue_number=42,
        issue_url="https://github.com/owner/repo/issues/42",
        repo="owner/repo",
        status=AutoFixStatus.ANALYZING,
    )
    orchestrator.autofix_processor.process_issue = AsyncMock(return_value=expected_state)

    result = await orchestrator.auto_fix_issue(42)

    assert result.issue_number == 42
    assert result.status == AutoFixStatus.ANALYZING


@pytest.mark.asyncio
async def test_GitHubOrchestrator_GetAutoFixQueue(orchestrator: GitHubOrchestrator):
    """Test get_auto_fix_queue method."""
    expected_queue = [
        AutoFixState(
            issue_number=1,
            issue_url="https://github.com/owner/repo/issues/1",
            repo="owner/repo",
            status=AutoFixStatus.BUILDING,
        ),
        AutoFixState(
            issue_number=2,
            issue_url="https://github.com/owner/repo/issues/2",
            repo="owner/repo",
            status=AutoFixStatus.PENDING,
        ),
    ]
    orchestrator.autofix_processor.get_queue = AsyncMock(return_value=expected_queue)

    result = await orchestrator.get_auto_fix_queue()

    assert len(result) == 2
    assert result[0].issue_number == 1
    assert result[1].issue_number == 2


@pytest.mark.asyncio
async def test_GitHubOrchestrator_CheckAutoFixLabels(orchestrator: GitHubOrchestrator):
    """Test check_auto_fix_labels method."""
    orchestrator._fetch_open_issues = AsyncMock(
        return_value=[
            {"number": 1, "title": "Issue with label", "labels": [{"name": "auto-fix"}]},
        ]
    )
    orchestrator.autofix_processor.check_labeled_issues = AsyncMock(
        return_value=[{"number": 1, "trigger_label": "auto-fix", "authorized": True}]
    )

    result = await orchestrator.check_auto_fix_labels(verify_permissions=True)

    assert len(result) == 1
    assert result[0]["number"] == 1


@pytest.mark.asyncio
async def test_GitHubOrchestrator_CheckNewIssues(orchestrator: GitHubOrchestrator):
    """Test check_new_issues method."""
    orchestrator._fetch_open_issues = AsyncMock(
        return_value=[
            {"number": 1, "title": "Issue 1"},
            {"number": 2, "title": "Issue 2"},
        ]
    )
    orchestrator.autofix_processor.get_queue = AsyncMock(
        return_value=[
            AutoFixState(
                issue_number=1,
                issue_url="https://github.com/owner/repo/issues/1",
                repo="owner/repo",
                status=AutoFixStatus.BUILDING,
            )
        ]
    )

    result = await orchestrator.check_new_issues()

    assert len(result) == 1
    assert result[0]["number"] == 2


@pytest.mark.asyncio
async def test_GitHubOrchestrator_BatchAndFixIssues(orchestrator: GitHubOrchestrator):
    """Test batch_and_fix_issues method."""
    orchestrator._fetch_open_issues = AsyncMock(
        return_value=[
            {"number": 1, "title": "Bug in auth"},
            {"number": 2, "title": "Auth bug"},
        ]
    )
    orchestrator.batch_processor.batch_and_fix_issues = AsyncMock(return_value=[])

    result = await orchestrator.batch_and_fix_issues(issue_numbers=None)

    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_GitHubOrchestrator_AnalyzeIssuesPreview(orchestrator: GitHubOrchestrator):
    """Test analyze_issues_preview method."""
    orchestrator._fetch_open_issues = AsyncMock(
        return_value=[
            {"number": 1, "title": "Bug in auth"},
            {"number": 2, "title": "Auth bug"},
        ]
    )
    orchestrator.batch_processor.analyze_issues_preview = AsyncMock(
        return_value={
            "success": True,
            "total_issues": 2,
            "analyzed_issues": 2,
            "proposed_batches": [],
            "single_issues": [],
        }
    )

    result = await orchestrator.analyze_issues_preview(issue_numbers=None, max_issues=200)

    assert result["success"] is True
    assert result["total_issues"] == 2


@pytest.mark.asyncio
async def test_GitHubOrchestrator_ApproveAndExecuteBatches(orchestrator: GitHubOrchestrator):
    """Test approve_and_execute_batches method."""
    approved_batches = [
        {
            "batch_id": "batch-1",
            "theme": "Auth fixes",
            "issues": [{"issue_number": 1}, {"issue_number": 2}],
        }
    ]
    orchestrator.batch_processor.approve_and_execute_batches = AsyncMock(
        return_value=[]
    )

    result = await orchestrator.approve_and_execute_batches(approved_batches)

    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_GitHubOrchestrator_GetBatchStatus(orchestrator: GitHubOrchestrator):
    """Test get_batch_status method."""
    orchestrator.batch_processor.get_batch_status = AsyncMock(
        return_value={
            "total_batches": 5,
            "pending": 1,
            "processing": 2,
            "completed": 2,
            "failed": 0,
        }
    )

    result = await orchestrator.get_batch_status()

    assert result["total_batches"] == 5
    assert result["pending"] == 1


@pytest.mark.asyncio
async def test_GitHubOrchestrator_ProcessPendingBatches(orchestrator: GitHubOrchestrator):
    """Test process_pending_batches method."""
    orchestrator.batch_processor.process_pending_batches = AsyncMock(return_value=2)

    result = await orchestrator.process_pending_batches()

    assert result == 2
