"""
Tests for GitLab Models
=======================

Tests for runners.gitlab.models - GitLab automation data models
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from runners.gitlab.models import (
    FollowupMRContext,
    GitLabRunnerConfig,
    MergeVerdict,
    MRContext,
    MRReviewFinding,
    MRReviewResult,
    ReviewCategory,
    ReviewPass,
    ReviewSeverity,
)


class TestReviewSeverity:
    """Tests for ReviewSeverity enum."""

    def test_severity_values(self):
        """Test ReviewSeverity enum values."""
        assert ReviewSeverity.CRITICAL.value == "critical"
        assert ReviewSeverity.HIGH.value == "high"
        assert ReviewSeverity.MEDIUM.value == "medium"
        assert ReviewSeverity.LOW.value == "low"

    def test_severity_from_string(self):
        """Test creating ReviewSeverity from string."""
        assert ReviewSeverity("critical") == ReviewSeverity.CRITICAL
        assert ReviewSeverity("high") == ReviewSeverity.HIGH
        assert ReviewSeverity("medium") == ReviewSeverity.MEDIUM
        assert ReviewSeverity("low") == ReviewSeverity.LOW

    def test_severity_invalid_string(self):
        """Test ReviewSeverity with invalid string raises ValueError."""
        with pytest.raises(ValueError):
            ReviewSeverity("invalid")


class TestReviewCategory:
    """Tests for ReviewCategory enum."""

    def test_category_values(self):
        """Test ReviewCategory enum values."""
        assert ReviewCategory.SECURITY.value == "security"
        assert ReviewCategory.QUALITY.value == "quality"
        assert ReviewCategory.STYLE.value == "style"
        assert ReviewCategory.TEST.value == "test"
        assert ReviewCategory.DOCS.value == "docs"
        assert ReviewCategory.PATTERN.value == "pattern"
        assert ReviewCategory.PERFORMANCE.value == "performance"

    def test_category_from_string(self):
        """Test creating ReviewCategory from string."""
        assert ReviewCategory("security") == ReviewCategory.SECURITY
        assert ReviewCategory("quality") == ReviewCategory.QUALITY
        assert ReviewCategory("performance") == ReviewCategory.PERFORMANCE


class TestReviewPass:
    """Tests for ReviewPass enum."""

    def test_pass_values(self):
        """Test ReviewPass enum values."""
        assert ReviewPass.QUICK_SCAN.value == "quick_scan"
        assert ReviewPass.SECURITY.value == "security"
        assert ReviewPass.QUALITY.value == "quality"
        assert ReviewPass.DEEP_ANALYSIS.value == "deep_analysis"


class TestMergeVerdict:
    """Tests for MergeVerdict enum."""

    def test_verdict_values(self):
        """Test MergeVerdict enum values."""
        assert MergeVerdict.READY_TO_MERGE.value == "ready_to_merge"
        assert MergeVerdict.MERGE_WITH_CHANGES.value == "merge_with_changes"
        assert MergeVerdict.NEEDS_REVISION.value == "needs_revision"
        assert MergeVerdict.BLOCKED.value == "blocked"


class TestMRReviewFinding:
    """Tests for MRReviewFinding dataclass."""

    @pytest.fixture
    def sample_finding(self):
        """Create a sample MRReviewFinding."""
        return MRReviewFinding(
            id="finding-123",
            severity=ReviewSeverity.HIGH,
            category=ReviewCategory.SECURITY,
            title="SQL Injection vulnerability",
            description="Potential SQL injection in user input handling",
            file="src/auth.py",
            line=42,
            end_line=45,
            suggested_fix="Use parameterized queries",
            fixable=True,
        )

    def test_finding_creation(self, sample_finding):
        """Test creating an MRReviewFinding."""
        assert sample_finding.id == "finding-123"
        assert sample_finding.severity == ReviewSeverity.HIGH
        assert sample_finding.category == ReviewCategory.SECURITY
        assert sample_finding.title == "SQL Injection vulnerability"
        assert sample_finding.file == "src/auth.py"
        assert sample_finding.line == 42
        assert sample_finding.end_line == 45
        assert sample_finding.suggested_fix == "Use parameterized queries"
        assert sample_finding.fixable is True

    def test_finding_with_optional_fields(self):
        """Test creating a finding with optional fields as None."""
        finding = MRReviewFinding(
            id="finding-456",
            severity=ReviewSeverity.LOW,
            category=ReviewCategory.STYLE,
            title="Style issue",
            description="Minor style concern",
            file="src/utils.py",
            line=10,
        )
        assert finding.end_line is None
        assert finding.suggested_fix is None
        assert finding.fixable is False

    def test_finding_to_dict(self, sample_finding):
        """Test converting finding to dictionary."""
        result = sample_finding.to_dict()
        assert result["id"] == "finding-123"
        assert result["severity"] == "high"
        assert result["category"] == "security"
        assert result["title"] == "SQL Injection vulnerability"
        assert result["file"] == "src/auth.py"
        assert result["line"] == 42
        assert result["end_line"] == 45
        assert result["suggested_fix"] == "Use parameterized queries"
        assert result["fixable"] is True

    def test_finding_from_dict(self, sample_finding):
        """Test creating finding from dictionary."""
        data = sample_finding.to_dict()
        restored = MRReviewFinding.from_dict(data)
        assert restored.id == sample_finding.id
        assert restored.severity == sample_finding.severity
        assert restored.category == sample_finding.category
        assert restored.title == sample_finding.title
        assert restored.file == sample_finding.file
        assert restored.line == sample_finding.line
        assert restored.end_line == sample_finding.end_line
        assert restored.suggested_fix == sample_finding.suggested_fix
        assert restored.fixable == sample_finding.fixable

    def test_finding_from_dict_with_optional_fields(self):
        """Test creating finding from dict with missing optional fields."""
        data = {
            "id": "finding-789",
            "severity": "medium",
            "category": "quality",
            "title": "Code quality issue",
            "description": "Refactor needed",
            "file": "src/service.py",
            "line": 100,
        }
        finding = MRReviewFinding.from_dict(data)
        assert finding.end_line is None
        assert finding.suggested_fix is None
        assert finding.fixable is False


class TestMRReviewResult:
    """Tests for MRReviewResult dataclass."""

    @pytest.fixture
    def sample_result(self, tmp_path):
        """Create a sample MRReviewResult."""
        return MRReviewResult(
            mr_iid=123,
            project="group/project",
            success=True,
            findings=[],
            summary="MR looks good",
            overall_status="approve",
            verdict=MergeVerdict.READY_TO_MERGE,
            verdict_reasoning="No issues found",
        )

    @pytest.fixture
    def sample_findings(self):
        """Create sample findings for testing."""
        return [
            MRReviewFinding(
                id="finding-1",
                severity=ReviewSeverity.CRITICAL,
                category=ReviewCategory.SECURITY,
                title="Security issue",
                description="Critical security vulnerability",
                file="src/auth.py",
                line=10,
            ),
            MRReviewFinding(
                id="finding-2",
                severity=ReviewSeverity.MEDIUM,
                category=ReviewCategory.QUALITY,
                title="Code quality",
                description="Improve error handling",
                file="src/utils.py",
                line=25,
            ),
        ]

    def test_result_creation(self, sample_result):
        """Test creating an MRReviewResult."""
        assert sample_result.mr_iid == 123
        assert sample_result.project == "group/project"
        assert sample_result.success is True
        assert sample_result.findings == []
        assert sample_result.summary == "MR looks good"
        assert sample_result.overall_status == "approve"
        assert sample_result.verdict == MergeVerdict.READY_TO_MERGE
        assert sample_result.verdict_reasoning == "No issues found"

    def test_result_with_findings(self, sample_findings):
        """Test creating result with findings."""
        result = MRReviewResult(
            mr_iid=456,
            project="group/repo",
            success=True,
            findings=sample_findings,
            summary="Issues found",
            overall_status="request_changes",
            verdict=MergeVerdict.NEEDS_REVISION,
            verdict_reasoning="Critical security issues",
            blockers=["Security issue (src/auth.py:10)"],
        )
        assert len(result.findings) == 2
        assert result.findings[0].severity == ReviewSeverity.CRITICAL
        assert result.blockers == ["Security issue (src/auth.py:10)"]

    def test_result_followup_fields(self):
        """Test result with follow-up review fields."""
        result = MRReviewResult(
            mr_iid=789,
            project="group/project",
            success=True,
            is_followup_review=True,
            previous_review_id=1,
            reviewed_commit_sha="abc123",
            resolved_findings=["finding-1"],
            unresolved_findings=["finding-2"],
            new_findings_since_last_review=["finding-3"],
        )
        assert result.is_followup_review is True
        assert result.previous_review_id == 1
        assert result.reviewed_commit_sha == "abc123"
        assert len(result.resolved_findings) == 1
        assert len(result.unresolved_findings) == 1
        assert len(result.new_findings_since_last_review) == 1

    def test_result_posting_tracking(self):
        """Test result with posting tracking fields."""
        result = MRReviewResult(
            mr_iid=100,
            project="group/project",
            success=True,
            has_posted_findings=True,
            posted_finding_ids=["finding-1", "finding-2"],
        )
        assert result.has_posted_findings is True
        assert len(result.posted_finding_ids) == 2

    def test_result_to_dict(self, sample_result):
        """Test converting result to dictionary."""
        result_dict = sample_result.to_dict()
        assert result_dict["mr_iid"] == 123
        assert result_dict["project"] == "group/project"
        assert result_dict["success"] is True
        assert result_dict["summary"] == "MR looks good"
        assert result_dict["verdict"] == "ready_to_merge"
        assert result_dict["verdict_reasoning"] == "No issues found"

    def test_result_from_dict(self, sample_result):
        """Test creating result from dictionary."""
        result_dict = sample_result.to_dict()
        restored = MRReviewResult.from_dict(result_dict)
        assert restored.mr_iid == sample_result.mr_iid
        assert restored.project == sample_result.project
        assert restored.success == sample_result.success
        assert restored.summary == sample_result.summary
        assert restored.verdict == sample_result.verdict

    def test_result_save_and_load(self, sample_result, tmp_path):
        """Test saving and loading a review result."""
        # Save the result
        gitlab_dir = tmp_path / ".auto-claude" / "gitlab"
        sample_result.save(gitlab_dir)

        # Check file was created
        review_file = gitlab_dir / "mr" / "review_123.json"
        assert review_file.exists()

        # Load the result
        loaded = MRReviewResult.load(gitlab_dir, 123)
        assert loaded is not None
        assert loaded.mr_iid == sample_result.mr_iid
        assert loaded.project == sample_result.project
        assert loaded.success == sample_result.success
        assert loaded.summary == sample_result.summary

    def test_result_load_nonexistent(self, tmp_path):
        """Test loading a non-existent result returns None."""
        gitlab_dir = tmp_path / ".auto-claude" / "gitlab"
        result = MRReviewResult.load(gitlab_dir, 999)
        assert result is None

    def test_result_with_findings_to_dict(self, sample_findings):
        """Test converting result with findings to dict."""
        result = MRReviewResult(
            mr_iid=1,
            project="group/project",
            success=True,
            findings=sample_findings,
        )
        result_dict = result.to_dict()
        assert len(result_dict["findings"]) == 2
        assert result_dict["findings"][0]["id"] == "finding-1"
        assert result_dict["findings"][1]["id"] == "finding-2"

    def test_result_with_findings_from_dict(self, sample_findings):
        """Test creating result with findings from dict."""
        result = MRReviewResult(
            mr_iid=1,
            project="group/project",
            success=True,
            findings=sample_findings,
        )
        result_dict = result.to_dict()
        restored = MRReviewResult.from_dict(result_dict)
        assert len(restored.findings) == 2
        assert restored.findings[0].id == "finding-1"
        assert restored.findings[1].id == "finding-2"
        assert restored.findings[0].severity == ReviewSeverity.CRITICAL

    def test_result_default_reviewed_at(self):
        """Test that reviewed_at defaults to current time."""
        result = MRReviewResult(mr_iid=1, project="group/project", success=True)
        # Just check that reviewed_at is set and is a valid ISO format string
        assert result.reviewed_at
        # Should be able to parse it
        reviewed_at = datetime.fromisoformat(result.reviewed_at)
        # Check it's a valid datetime (within reasonable range)
        now = datetime.now()
        # Allow some timezone flexibility - just check it's recent
        assert (now - reviewed_at.replace(tzinfo=None)).total_seconds() < 60


class TestGitLabRunnerConfig:
    """Tests for GitLabRunnerConfig dataclass."""

    def test_config_creation(self):
        """Test creating a GitLabRunnerConfig."""
        config = GitLabRunnerConfig(
            token="test_token",
            project="group/project",
            instance_url="https://gitlab.example.com",
            model="claude-sonnet-4-5-20250929",
            thinking_level="high",
        )
        assert config.token == "test_token"
        assert config.project == "group/project"
        assert config.instance_url == "https://gitlab.example.com"
        assert config.model == "claude-sonnet-4-5-20250929"
        assert config.thinking_level == "high"

    def test_config_defaults(self):
        """Test GitLabRunnerConfig default values."""
        config = GitLabRunnerConfig(
            token="token",
            project="group/repo",
        )
        assert config.instance_url == "https://gitlab.com"
        assert config.model == "claude-sonnet-4-5-20250929"
        assert config.thinking_level == "medium"

    def test_config_to_dict(self):
        """Test converting config to dictionary."""
        config = GitLabRunnerConfig(
            token="secret_token",
            project="group/project",
            instance_url="https://custom.gitlab.com",
        )
        config_dict = config.to_dict()
        assert config_dict["token"] == "***"  # Token should be masked
        assert config_dict["project"] == "group/project"
        assert config_dict["instance_url"] == "https://custom.gitlab.com"


class TestMRContext:
    """Tests for MRContext dataclass."""

    def test_context_creation(self):
        """Test creating an MRContext."""
        context = MRContext(
            mr_iid=123,
            title="Feature: Add authentication",
            description="Adds OAuth2 authentication",
            author="john_doe",
            source_branch="feature/auth",
            target_branch="main",
            state="opened",
            changed_files=[{"new_path": "src/auth.py", "old_path": "src/auth.py"}],
            diff="+def authenticate():\n+    pass",
            total_additions=10,
            total_deletions=5,
            commits=[{"id": "abc123"}],
            head_sha="abc123",
        )
        assert context.mr_iid == 123
        assert context.title == "Feature: Add authentication"
        assert context.author == "john_doe"
        assert context.source_branch == "feature/auth"
        assert context.target_branch == "main"
        assert context.state == "opened"
        assert len(context.changed_files) == 1
        assert context.total_additions == 10
        assert context.total_deletions == 5
        assert context.head_sha == "abc123"

    def test_context_defaults(self):
        """Test MRContext default values."""
        context = MRContext(
            mr_iid=1,
            title="Test",
            description="Test MR",
            author="user",
            source_branch="feature",
            target_branch="main",
            state="opened",
        )
        assert context.changed_files == []
        assert context.diff == ""
        assert context.total_additions == 0
        assert context.total_deletions == 0
        assert context.commits == []
        assert context.head_sha is None


class TestFollowupMRContext:
    """Tests for FollowupMRContext dataclass."""

    @pytest.fixture
    def base_review(self):
        """Create a base review for followup context."""
        return MRReviewResult(
            mr_iid=123,
            project="group/project",
            success=True,
            findings=[],
            reviewed_commit_sha="old_sha",
        )

    def test_followup_context_creation(self, base_review):
        """Test creating a FollowupMRContext."""
        context = FollowupMRContext(
            mr_iid=123,
            previous_review=base_review,
            previous_commit_sha="old_sha",
            current_commit_sha="new_sha",
            commits_since_review=[{"id": "commit1"}],
            files_changed_since_review=["src/file1.py", "src/file2.py"],
            diff_since_review="+new code",
        )
        assert context.mr_iid == 123
        assert context.previous_review == base_review
        assert context.previous_commit_sha == "old_sha"
        assert context.current_commit_sha == "new_sha"
        assert len(context.commits_since_review) == 1
        assert len(context.files_changed_since_review) == 2
        assert context.diff_since_review == "+new code"

    def test_followup_context_defaults(self, base_review):
        """Test FollowupMRContext default values."""
        context = FollowupMRContext(
            mr_iid=1,
            previous_review=base_review,
            previous_commit_sha="old",
            current_commit_sha="new",
        )
        assert context.commits_since_review == []
        assert context.files_changed_since_review == []
        assert context.diff_since_review == ""
