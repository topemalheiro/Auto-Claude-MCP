"""Tests for models"""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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
    apply_branch_behind_downgrade,
    apply_ci_status_override,
    apply_merge_conflict_override,
    verdict_from_severity_counts,
    verdict_to_github_status,
)


def test_verdict_from_severity_counts():
    """Test verdict_from_severity_counts"""

    # Arrange
    critical_count = 1
    high_count = 0
    medium_count = 0
    low_count = 0

    # Act
    result = verdict_from_severity_counts(critical_count, high_count, medium_count, low_count)

    # Assert
    assert result == MergeVerdict.BLOCKED


def test_verdict_from_severity_counts_with_empty_inputs():
    """Test verdict_from_severity_counts with empty inputs"""

    # Arrange - no findings
    critical_count = 0
    high_count = 0
    medium_count = 0
    low_count = 0

    # Act
    result = verdict_from_severity_counts(critical_count, high_count, medium_count, low_count)

    # Assert
    assert result == MergeVerdict.READY_TO_MERGE


def test_verdict_from_severity_counts_with_high():
    """Test verdict_from_severity_counts with high findings"""

    # Arrange
    critical_count = 0
    high_count = 2
    medium_count = 0
    low_count = 0

    # Act
    result = verdict_from_severity_counts(critical_count, high_count, medium_count, low_count)

    # Assert
    assert result == MergeVerdict.NEEDS_REVISION


def test_verdict_from_severity_counts_with_medium():
    """Test verdict_from_severity_counts with medium findings"""

    # Arrange
    critical_count = 0
    high_count = 0
    medium_count = 1
    low_count = 0

    # Act
    result = verdict_from_severity_counts(critical_count, high_count, medium_count, low_count)

    # Assert
    assert result == MergeVerdict.NEEDS_REVISION


def test_verdict_from_severity_counts_with_low_only():
    """Test verdict_from_severity_counts with only low findings"""

    # Arrange
    critical_count = 0
    high_count = 0
    medium_count = 0
    low_count = 5

    # Act
    result = verdict_from_severity_counts(critical_count, high_count, medium_count, low_count)

    # Assert
    assert result == MergeVerdict.READY_TO_MERGE


def test_apply_merge_conflict_override():
    """Test apply_merge_conflict_override with conflicts"""

    # Arrange
    verdict = MergeVerdict.READY_TO_MERGE
    has_merge_conflicts = True

    # Act
    result = apply_merge_conflict_override(verdict, has_merge_conflicts)

    # Assert
    assert result == MergeVerdict.BLOCKED


def test_apply_merge_conflict_override_no_conflicts():
    """Test apply_merge_conflict_override without conflicts"""

    # Arrange
    verdict = MergeVerdict.READY_TO_MERGE
    has_merge_conflicts = False

    # Act
    result = apply_merge_conflict_override(verdict, has_merge_conflicts)

    # Assert
    assert result == MergeVerdict.READY_TO_MERGE


def test_apply_branch_behind_downgrade():
    """Test apply_branch_behind_downgrade with BEHIND status"""

    # Arrange
    verdict = MergeVerdict.READY_TO_MERGE
    merge_state_status = "BEHIND"

    # Act
    result = apply_branch_behind_downgrade(verdict, merge_state_status)

    # Assert
    assert result == MergeVerdict.NEEDS_REVISION


def test_apply_branch_behind_downgrade_preserves_blocked():
    """Test apply_branch_behind_downgrade preserves BLOCKED"""

    # Arrange
    verdict = MergeVerdict.BLOCKED
    merge_state_status = "BEHIND"

    # Act
    result = apply_branch_behind_downgrade(verdict, merge_state_status)

    # Assert
    assert result == MergeVerdict.BLOCKED


def test_apply_branch_behind_downgrade_clean_status():
    """Test apply_branch_behind_downgrade with CLEAN status"""

    # Arrange
    verdict = MergeVerdict.READY_TO_MERGE
    merge_state_status = "CLEAN"

    # Act
    result = apply_branch_behind_downgrade(verdict, merge_state_status)

    # Assert
    assert result == MergeVerdict.READY_TO_MERGE


def test_apply_ci_status_override_failing():
    """Test apply_ci_status_override with failing CI"""

    # Arrange
    verdict = MergeVerdict.READY_TO_MERGE
    failing_count = 2
    pending_count = 0

    # Act
    result = apply_ci_status_override(verdict, failing_count=failing_count, pending_count=pending_count)

    # Assert
    assert result == MergeVerdict.BLOCKED


def test_apply_ci_status_override_pending():
    """Test apply_ci_status_override with pending CI"""

    # Arrange
    verdict = MergeVerdict.READY_TO_MERGE
    failing_count = 0
    pending_count = 1

    # Act
    result = apply_ci_status_override(verdict, failing_count=failing_count, pending_count=pending_count)

    # Assert
    assert result == MergeVerdict.NEEDS_REVISION


def test_apply_ci_status_override_preserves_blocked():
    """Test apply_ci_status_override preserves BLOCKED"""

    # Arrange
    verdict = MergeVerdict.BLOCKED
    failing_count = 2
    pending_count = 0

    # Act
    result = apply_ci_status_override(verdict, failing_count=failing_count, pending_count=pending_count)

    # Assert
    assert result == MergeVerdict.BLOCKED


def test_verdict_to_github_status():
    """Test verdict_to_github_status"""

    # Arrange & Act & Assert
    assert verdict_to_github_status(MergeVerdict.BLOCKED) == "request_changes"
    assert verdict_to_github_status(MergeVerdict.NEEDS_REVISION) == "request_changes"
    assert verdict_to_github_status(MergeVerdict.MERGE_WITH_CHANGES) == "comment"
    assert verdict_to_github_status(MergeVerdict.READY_TO_MERGE) == "approve"


def test_AutoFixStatus_terminal_states():
    """Test AutoFixStatus.terminal_states"""

    # Act
    terminal = AutoFixStatus.terminal_states()

    # Assert
    assert AutoFixStatus.COMPLETED in terminal
    assert AutoFixStatus.FAILED in terminal
    assert AutoFixStatus.CANCELLED in terminal
    assert AutoFixStatus.PENDING not in terminal


def test_AutoFixStatus_recoverable_states():
    """Test AutoFixStatus.recoverable_states"""

    # Act
    recoverable = AutoFixStatus.recoverable_states()

    # Assert
    assert AutoFixStatus.FAILED in recoverable
    assert AutoFixStatus.STALE in recoverable
    assert AutoFixStatus.RATE_LIMITED in recoverable
    assert AutoFixStatus.MERGE_CONFLICT in recoverable


def test_AutoFixStatus_active_states():
    """Test AutoFixStatus.active_states"""

    # Act
    active = AutoFixStatus.active_states()

    # Assert
    assert AutoFixStatus.PENDING in active
    assert AutoFixStatus.ANALYZING in active
    assert AutoFixStatus.BUILDING in active


def test_AutoFixStatus_can_transition_to():
    """Test AutoFixStatus.can_transition_to"""

    # Assert valid transitions
    assert AutoFixStatus.PENDING.can_transition_to(AutoFixStatus.ANALYZING)
    assert AutoFixStatus.PENDING.can_transition_to(AutoFixStatus.CANCELLED)
    assert not AutoFixStatus.PENDING.can_transition_to(AutoFixStatus.COMPLETED)

    # Terminal states have no transitions
    assert not AutoFixStatus.COMPLETED.can_transition_to(AutoFixStatus.PENDING)
    assert not AutoFixStatus.CANCELLED.can_transition_to(AutoFixStatus.PENDING)


def test_PRReviewFinding_to_dict():
    """Test PRReviewFinding.to_dict"""

    # Arrange
    finding = PRReviewFinding(
        id="test-1",
        severity=ReviewSeverity.HIGH,
        category=ReviewCategory.QUALITY,
        title="Test Issue",
        description="This is a test issue",
        file="test.py",
        line=10,
        end_line=15,
        suggested_fix="Fix this",
        fixable=True,
        evidence="print('test')",
    )

    # Act
    result = finding.to_dict()

    # Assert
    assert result["id"] == "test-1"
    assert result["severity"] == "high"
    assert result["category"] == "quality"
    assert result["title"] == "Test Issue"
    assert result["file"] == "test.py"
    assert result["line"] == 10
    assert result["end_line"] == 15
    assert result["fixable"] is True


def test_PRReviewFinding_from_dict():
    """Test PRReviewFinding.from_dict"""

    # Arrange
    data = {
        "id": "test-2",
        "severity": "critical",
        "category": "security",
        "title": "Security Issue",
        "description": "Critical security flaw",
        "file": "auth.py",
        "line": 42,
        "end_line": 45,
        "suggested_fix": "Add validation",
        "fixable": True,
        "evidence": "unsafe code",
    }

    # Act
    result = PRReviewFinding.from_dict(data)

    # Assert
    assert result.id == "test-2"
    assert result.severity == ReviewSeverity.CRITICAL
    assert result.category == ReviewCategory.SECURITY
    assert result.title == "Security Issue"
    assert result.file == "auth.py"
    assert result.line == 42


def test_AICommentTriage_to_dict():
    """Test AICommentTriage.to_dict"""

    # Arrange
    triage = AICommentTriage(
        comment_id=123,
        tool_name="CodeRabbit",
        original_comment="This is wrong",
        verdict=AICommentVerdict.CRITICAL,
        reasoning="Security issue",
        response_comment="Please fix",
    )

    # Act
    result = triage.to_dict()

    # Assert
    assert result["comment_id"] == 123
    assert result["tool_name"] == "CodeRabbit"
    assert result["verdict"] == "critical"
    assert result["reasoning"] == "Security issue"


def test_AICommentTriage_from_dict():
    """Test AICommentTriage.from_dict"""

    # Arrange
    data = {
        "comment_id": 456,
        "tool_name": "Cursor",
        "original_comment": "Use async",
        "verdict": "nice_to_have",
        "reasoning": "Performance suggestion",
        "response_comment": None,
    }

    # Act
    result = AICommentTriage.from_dict(data)

    # Assert
    assert result.comment_id == 456
    assert result.tool_name == "Cursor"
    assert result.verdict == AICommentVerdict.NICE_TO_HAVE
    assert result.response_comment is None


def test_StructuralIssue_to_dict():
    """Test StructuralIssue.to_dict"""

    # Arrange
    issue = StructuralIssue(
        id="struct-1",
        issue_type="feature_creep",
        severity=ReviewSeverity.MEDIUM,
        title="Scope Creep",
        description="Adding too many features",
        impact="Delays delivery",
        suggestion="Focus on core requirements",
    )

    # Act
    result = issue.to_dict()

    # Assert
    assert result["id"] == "struct-1"
    assert result["issue_type"] == "feature_creep"
    assert result["severity"] == "medium"
    assert result["title"] == "Scope Creep"


def test_StructuralIssue_from_dict():
    """Test StructuralIssue.from_dict"""

    # Arrange
    data = {
        "id": "struct-2",
        "issue_type": "poor_structure",
        "severity": "high",
        "title": "Poor Structure",
        "description": "Code organization issues",
        "impact": "Maintainability",
        "suggestion": "Refactor modules",
    }

    # Act
    result = StructuralIssue.from_dict(data)

    # Assert
    assert result.id == "struct-2"
    assert result.issue_type == "poor_structure"
    assert result.severity == ReviewSeverity.HIGH
    assert result.title == "Poor Structure"


def test_TriageResult_to_dict():
    """Test TriageResult.to_dict"""

    # Arrange
    triage = TriageResult(
        issue_number=42,
        repo="owner/repo",
        category=TriageCategory.BUG,
        confidence=0.95,
        labels_to_add=["bug", "high-priority"],
        labels_to_remove=["needs-triage"],
        priority="high",
        comment="Confirmed bug",
    )

    # Act
    result = triage.to_dict()

    # Assert
    assert result["issue_number"] == 42
    assert result["category"] == "bug"
    assert result["confidence"] == 0.95
    assert result["priority"] == "high"


def test_TriageResult_from_dict():
    """Test TriageResult.from_dict"""

    # Arrange
    data = {
        "issue_number": 10,
        "repo": "owner/repo",
        "category": "feature",
        "confidence": 0.85,
        "labels_to_add": ["enhancement"],
        "priority": "medium",
        "triaged_at": "2024-01-01T00:00:00",
    }

    # Act
    result = TriageResult.from_dict(data)

    # Assert
    assert result.issue_number == 10
    assert result.category == TriageCategory.FEATURE
    assert result.confidence == 0.85
    assert result.priority == "medium"


@pytest.mark.asyncio
async def test_TriageResult_save(tmp_path):
    """Test TriageResult.save"""

    # Arrange
    github_dir = tmp_path / ".auto-claude" / "github"
    triage = TriageResult(
        issue_number=42,
        repo="owner/repo",
        category=TriageCategory.BUG,
        confidence=0.95,
    )

    # Act
    await triage.save(github_dir)

    # Assert
    triage_file = github_dir / "issues" / "triage_42.json"
    assert triage_file.exists()


def test_TriageResult_load(tmp_path):
    """Test TriageResult.load"""

    # Arrange
    github_dir = tmp_path / ".auto-claude" / "github"
    github_dir.mkdir(parents=True, exist_ok=True)
    issues_dir = github_dir / "issues"
    issues_dir.mkdir(parents=True, exist_ok=True)

    triage = TriageResult(
        issue_number=42,
        repo="owner/repo",
        category=TriageCategory.BUG,
        confidence=0.95,
    )
    asyncio.run(triage.save(github_dir))

    # Act
    result = TriageResult.load(github_dir, 42)

    # Assert
    assert result is not None
    assert result.issue_number == 42
    assert result.category == TriageCategory.BUG


def test_AutoFixState_to_dict():
    """Test AutoFixState.to_dict"""

    # Arrange
    state = AutoFixState(
        issue_number=10,
        issue_url="https://github.com/owner/repo/issues/10",
        repo="owner/repo",
        status=AutoFixStatus.ANALYZING,
        spec_id="spec-001",
        spec_dir="/path/to/spec",
    )

    # Act
    result = state.to_dict()

    # Assert
    assert result["issue_number"] == 10
    assert result["status"] == "analyzing"
    assert result["spec_id"] == "spec-001"


def test_AutoFixState_from_dict():
    """Test AutoFixState.from_dict"""

    # Arrange
    data = {
        "issue_number": 20,
        "issue_url": "https://github.com/owner/repo/issues/20",
        "repo": "owner/repo",
        "status": "building",
        "spec_id": "spec-002",
        "pr_number": 5,
        "pr_url": "https://github.com/owner/repo/pull/5",
    }

    # Act
    result = AutoFixState.from_dict(data)

    # Assert
    assert result.issue_number == 20
    assert result.status == AutoFixStatus.BUILDING
    assert result.pr_number == 5


def test_AutoFixState_update_status():
    """Test AutoFixState.update_status"""

    # Arrange
    state = AutoFixState(
        issue_number=10,
        issue_url="https://github.com/owner/repo/issues/10",
        repo="owner/repo",
        status=AutoFixStatus.PENDING,
    )

    # Act
    state.update_status(AutoFixStatus.ANALYZING)

    # Assert
    assert state.status == AutoFixStatus.ANALYZING


def test_AutoFixState_update_status_invalid_transition():
    """Test AutoFixState.update_status with invalid transition"""

    # Arrange
    state = AutoFixState(
        issue_number=10,
        issue_url="https://github.com/owner/repo/issues/10",
        repo="owner/repo",
        status=AutoFixStatus.COMPLETED,
    )

    # Act & Assert
    with pytest.raises(ValueError, match="Invalid state transition"):
        state.update_status(AutoFixStatus.PENDING)


@pytest.mark.asyncio
async def test_AutoFixState_save(tmp_path):
    """Test AutoFixState.save"""

    # Arrange
    github_dir = tmp_path / ".auto-claude" / "github"
    state = AutoFixState(
        issue_number=10,
        issue_url="https://github.com/owner/repo/issues/10",
        repo="owner/repo",
        status=AutoFixStatus.BUILDING,
    )

    # Act
    await state.save(github_dir)

    # Assert
    autofix_file = github_dir / "issues" / "autofix_10.json"
    assert autofix_file.exists()


def test_AutoFixState_load(tmp_path):
    """Test AutoFixState.load"""

    # Arrange
    github_dir = tmp_path / ".auto-claude" / "github"
    github_dir.mkdir(parents=True, exist_ok=True)
    issues_dir = github_dir / "issues"
    issues_dir.mkdir(parents=True, exist_ok=True)

    state = AutoFixState(
        issue_number=10,
        issue_url="https://github.com/owner/repo/issues/10",
        repo="owner/repo",
        status=AutoFixStatus.BUILDING,
    )
    asyncio.run(state.save(github_dir))

    # Act
    result = AutoFixState.load(github_dir, 10)

    # Assert
    assert result is not None
    assert result.issue_number == 10
    assert result.status == AutoFixStatus.BUILDING


def test_GitHubRunnerConfig_to_dict():
    """Test GitHubRunnerConfig.to_dict"""

    # Arrange
    config = GitHubRunnerConfig(
        token="test-token",
        repo="owner/repo",
        bot_token="bot-token",
        auto_fix_enabled=True,
        triage_enabled=True,
        pr_review_enabled=True,
        model="sonnet",
        thinking_level="high",
    )

    # Act
    result = config.to_dict()

    # Assert
    assert result["token"] == "***"  # Token should be masked
    assert result["bot_token"] == "***"
    assert result["repo"] == "owner/repo"
    assert result["auto_fix_enabled"] is True
    assert result["triage_enabled"] is True


def test_GitHubRunnerConfig_save_settings(tmp_path):
    """Test GitHubRunnerConfig.save_settings"""

    # Arrange
    github_dir = tmp_path / ".auto-claude" / "github"
    config = GitHubRunnerConfig(
        token="test-token",
        repo="owner/repo",
        auto_fix_enabled=True,
    )

    # Act
    config.save_settings(github_dir)

    # Assert
    config_file = github_dir / "config.json"
    assert config_file.exists()

    # Verify token not saved
    import json
    with open(config_file) as f:
        data = json.load(f)
    assert "token" not in data
    assert data["auto_fix_enabled"] is True


def test_GitHubRunnerConfig_load_settings(tmp_path):
    """Test GitHubRunnerConfig.load_settings"""

    # Arrange
    github_dir = tmp_path / ".auto-claude" / "github"
    github_dir.mkdir(parents=True, exist_ok=True)

    # Save a config file
    import json
    config_file = github_dir / "config.json"
    with open(config_file, "w") as f:
        json.dump({
            "auto_fix_enabled": True,
            "triage_enabled": True,
            "model": "opus",
            "thinking_level": "high",
        }, f)

    # Act
    result = GitHubRunnerConfig.load_settings(
        github_dir,
        token="test-token",
        repo="owner/repo",
    )

    # Assert
    assert result.token == "test-token"
    assert result.repo == "owner/repo"
    assert result.auto_fix_enabled is True
    assert result.triage_enabled is True
    assert result.model == "opus"


def test_PRReviewResult_to_dict():
    """Test PRReviewResult.to_dict"""

    # Arrange
    result = PRReviewResult(
        pr_number=42,
        repo="owner/repo",
        success=True,
        findings=[],
        summary="LGTM",
        overall_status="approve",
        verdict=MergeVerdict.READY_TO_MERGE,
    )

    # Act
    dict_result = result.to_dict()

    # Assert
    assert dict_result["pr_number"] == 42
    assert dict_result["success"] is True
    assert dict_result["overall_status"] == "approve"
    assert dict_result["verdict"] == "ready_to_merge"


def test_PRReviewResult_from_dict():
    """Test PRReviewResult.from_dict"""

    # Arrange
    data = {
        "pr_number": 123,
        "repo": "owner/repo",
        "success": True,
        "findings": [],
        "summary": "All good",
        "overall_status": "comment",
        "verdict": "merge_with_changes",
        "blockers": [],
    }

    # Act
    result = PRReviewResult.from_dict(data)

    # Assert
    assert result.pr_number == 123
    assert result.success is True
    assert result.verdict == MergeVerdict.MERGE_WITH_CHANGES
