"""
Tests for qa.report module.
"""

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.backend.qa.report import (
    RECURRING_ISSUE_THRESHOLD,
    ISSUE_SIMILARITY_THRESHOLD,
    check_test_discovery,
    create_manual_test_plan,
    escalate_to_human,
    get_iteration_history,
    get_recurring_issue_summary,
    has_recurring_issues,
    is_no_test_project,
    record_iteration,
    _normalize_issue_key,
    _issue_similarity,
)

from .conftest import create_spec_files


class TestIterationTracking:
    """Tests for iteration tracking functions."""

    def test_get_iteration_history_empty(self, temp_spec_dir: Path) -> None:
        """Test getting history when no plan exists."""
        result = get_iteration_history(temp_spec_dir)

        assert result == []

    def test_get_iteration_history_with_data(self, temp_spec_dir: Path, sample_implementation_plan: dict) -> None:
        """Test getting history with existing iterations."""
        plan = sample_implementation_plan.copy()
        plan["qa_iteration_history"] = [
            {"iteration": 1, "status": "rejected", "timestamp": "2024-01-01T00:00:00Z", "issues": []},
            {"iteration": 2, "status": "approved", "timestamp": "2024-01-01T01:00:00Z", "issues": []},
        ]
        create_spec_files(temp_spec_dir, plan)

        result = get_iteration_history(temp_spec_dir)

        assert len(result) == 2
        assert result[0]["iteration"] == 1
        assert result[1]["status"] == "approved"

    def test_record_iteration_success(self, temp_spec_dir: Path, sample_implementation_plan: dict, sample_issues: list) -> None:
        """Test recording a QA iteration."""
        create_spec_files(temp_spec_dir, sample_implementation_plan)

        result = record_iteration(
            temp_spec_dir,
            iteration=1,
            status="rejected",
            issues=sample_issues,
            duration_seconds=45.5,
        )

        assert result is True

        # Verify it was saved
        history = get_iteration_history(temp_spec_dir)
        assert len(history) == 1
        assert history[0]["iteration"] == 1
        assert history[0]["status"] == "rejected"
        assert history[0]["duration_seconds"] == 45.5
        assert len(history[0]["issues"]) == 2

    def test_record_iteration_without_duration(self, temp_spec_dir: Path, sample_implementation_plan: dict) -> None:
        """Test recording iteration without duration."""
        create_spec_files(temp_spec_dir, sample_implementation_plan)

        result = record_iteration(
            temp_spec_dir,
            iteration=1,
            status="approved",
            issues=[],
            duration_seconds=None,
        )

        assert result is True

        history = get_iteration_history(temp_spec_dir)
        assert "duration_seconds" not in history[0]

    def test_record_iteration_creates_new_plan(self, temp_spec_dir: Path, sample_issues: list) -> None:
        """Test recording iteration when no plan exists."""
        result = record_iteration(
            temp_spec_dir,
            iteration=1,
            status="rejected",
            issues=sample_issues,
        )

        assert result is True

        # Verify plan was created
        plan_file = temp_spec_dir / "implementation_plan.json"
        assert plan_file.exists()

    def test_record_iteration_updates_stats(self, temp_spec_dir: Path, sample_implementation_plan: dict, sample_issues: list) -> None:
        """Test that recording updates QA stats."""
        create_spec_files(temp_spec_dir, sample_implementation_plan)

        record_iteration(temp_spec_dir, 1, "rejected", sample_issues)

        # Load plan and check stats
        from apps.backend.qa.criteria import load_implementation_plan
        plan = load_implementation_plan(temp_spec_dir)
        assert plan["qa_stats"]["total_iterations"] == 1
        assert plan["qa_stats"]["last_iteration"] == 1
        assert plan["qa_stats"]["last_status"] == "rejected"
        assert "issues_by_type" in plan["qa_stats"]


class TestIssueSimilarity:
    """Tests for issue similarity functions."""

    def test_normalize_issue_key_full(self) -> None:
        """Test normalizing issue key with all fields."""
        issue = {
            "title": "ERROR: Test failure in auth module",
            "file": "src/auth.py",
            "line": 42,
        }

        result = _normalize_issue_key(issue)

        assert result == "test failure in auth module|src/auth.py|42"

    def test_normalize_issue_key_missing_fields(self) -> None:
        """Test normalizing issue key with missing fields."""
        issue = {
            "title": "BUG: Memory leak",
        }

        result = _normalize_issue_key(issue)

        assert result == "memory leak||"

    def test_normalize_issue_key_prefix_removal(self) -> None:
        """Test that common prefixes are removed."""
        cases = [
            ("ERROR: Something went wrong", "something went wrong"),
            ("Issue: Test fails", "test fails"),
            ("bug: Invalid input", "invalid input"),
            ("Fix: Missing import", "missing import"),
        ]

        for title, expected in cases:
            issue = {"title": title}
            result = _normalize_issue_key(issue)
            assert result.startswith(expected.lower())

    def test_issue_similarity_identical(self) -> None:
        """Test similarity score for identical issues."""
        issue1 = {"title": "Test failure", "file": "test.py", "line": 10}
        issue2 = {"title": "Test failure", "file": "test.py", "line": 10}

        result = _issue_similarity(issue1, issue2)

        assert result == 1.0

    def test_issue_similarity_different(self) -> None:
        """Test similarity score for different issues."""
        issue1 = {"title": "Test failure in auth", "file": "auth.py", "line": 10}
        issue2 = {"title": "Database connection error", "file": "db.py", "line": 50}

        result = _issue_similarity(issue1, issue2)

        assert result < ISSUE_SIMILARITY_THRESHOLD

    def test_issue_similarity_similar(self) -> None:
        """Test similarity score for similar issues."""
        issue1 = {"title": "Test failure in auth module", "file": "auth.py", "line": 42}
        issue2 = {"title": "ERROR: Test failure in auth module", "file": "auth.py", "line": 42}

        result = _issue_similarity(issue1, issue2)

        assert result >= ISSUE_SIMILARITY_THRESHOLD

    def test_issue_similarity_case_insensitive(self) -> None:
        """Test that similarity is case-insensitive."""
        issue1 = {"title": "Test Failure", "file": "test.py"}
        issue2 = {"title": "test failure", "file": "test.py"}

        result = _issue_similarity(issue1, issue2)

        assert result == 1.0


class TestRecurringIssues:
    """Tests for recurring issue detection."""

    def test_has_recurring_issues_none(self, temp_spec_dir: Path, sample_issues: list) -> None:
        """Test when no recurring issues."""
        history = []  # Empty history
        current_issues = sample_issues

        has_recurring, recurring = has_recurring_issues(current_issues, history)

        assert has_recurring is False
        assert recurring == []

    def test_has_recurring_issues_below_threshold(self, temp_spec_dir: Path, sample_issues: list) -> None:
        """Test when issue appears but below threshold."""
        history = [
            {
                "iteration": 1,
                "status": "rejected",
                "issues": [sample_issues[0]],  # Same issue once
            }
        ]
        current_issues = [sample_issues[0]]

        has_recurring, recurring = has_recurring_issues(current_issues, history, threshold=3)

        assert has_recurring is False
        assert recurring == []

    def test_has_recurring_issues_at_threshold(self, temp_spec_dir: Path, sample_issues: list) -> None:
        """Test when issue reaches threshold."""
        history = [
            {
                "iteration": 1,
                "status": "rejected",
                "issues": [sample_issues[0]],
            },
            {
                "iteration": 2,
                "status": "rejected",
                "issues": [sample_issues[0]],
            },
        ]
        current_issues = [sample_issues[0]]  # 3rd occurrence

        has_recurring, recurring = has_recurring_issues(current_issues, history, threshold=3)

        assert has_recurring is True
        assert len(recurring) == 1
        assert recurring[0]["occurrence_count"] == 3

    def test_has_recurring_issues_multiple(self, temp_spec_dir: Path, sample_issues: list) -> None:
        """Test multiple recurring issues."""
        history = [
            {
                "iteration": 1,
                "status": "rejected",
                "issues": sample_issues,
            },
            {
                "iteration": 2,
                "status": "rejected",
                "issues": sample_issues,
            },
        ]
        current_issues = sample_issues  # 3rd occurrence of both

        has_recurring, recurring = has_recurring_issues(current_issues, history, threshold=3)

        assert has_recurring is True
        assert len(recurring) == 2
        assert all(r["occurrence_count"] == 3 for r in recurring)

    def test_has_recurring_issues_similar_not_identical(self, temp_spec_dir: Path) -> None:
        """Test that similar (not identical) issues are detected."""
        issue1 = {"title": "Test failure in auth", "file": "auth.py", "line": 42}
        issue2 = {"title": "ERROR: Test failure in auth", "file": "auth.py", "line": 42}
        issue3 = {"title": "Bug: Test failure in auth", "file": "auth.py", "line": 42}

        history = [
            {"iteration": 1, "status": "rejected", "issues": [issue1]},
            {"iteration": 2, "status": "rejected", "issues": [issue2]},
        ]
        current_issues = [issue3]

        has_recurring, recurring = has_recurring_issues(current_issues, history, threshold=3)

        assert has_recurring is True
        assert len(recurring) == 1


class TestRecurringIssueSummary:
    """Tests for recurring issue summary."""

    def test_summary_empty_history(self) -> None:
        """Test summary with empty history."""
        result = get_recurring_issue_summary([])

        assert result["total_issues"] == 0
        assert result["unique_issues"] == 0
        assert result["most_common"] == []

    def test_summary_with_issues(self, temp_spec_dir: Path, sample_issues: list) -> None:
        """Test summary with various issues."""
        history = [
            {"iteration": 1, "status": "rejected", "issues": [sample_issues[0]]},
            {"iteration": 2, "status": "rejected", "issues": sample_issues},
            {"iteration": 3, "status": "approved", "issues": []},
        ]

        result = get_recurring_issue_summary(history)

        assert result["total_issues"] == 3
        assert result["unique_issues"] == 2
        assert result["iterations_approved"] == 1
        assert result["iterations_rejected"] == 2
        assert len(result["most_common"]) == 2

    def test_summary_groups_similar_issues(self) -> None:
        """Test that similar issues are grouped."""
        history = [
            {
                "iteration": 1,
                "status": "rejected",
                "issues": [{"title": "Test failure", "file": "test.py", "line": 10}],
            },
            {
                "iteration": 2,
                "status": "rejected",
                "issues": [{"title": "ERROR: Test failure", "file": "test.py", "line": 10}],
            },
        ]

        result = get_recurring_issue_summary(history)

        # Should group similar issues
        assert result["unique_issues"] == 1
        assert result["most_common"][0]["occurrences"] == 2

    def test_summary_fix_success_rate(self) -> None:
        """Test fix success rate calculation."""
        history = [
            {"iteration": 1, "status": "rejected", "issues": []},
            {"iteration": 2, "status": "rejected", "issues": []},
            {"iteration": 3, "status": "approved", "issues": []},
            {"iteration": 4, "status": "approved", "issues": []},
        ]

        result = get_recurring_issue_summary(history)

        assert result["iterations_approved"] == 2
        assert result["iterations_rejected"] == 2
        assert result["fix_success_rate"] == 0.5


class TestEscalation:
    """Tests for escalation functions."""

    @pytest.mark.asyncio
    async def test_escalate_to_human(self, temp_spec_dir: Path, sample_issues: list) -> None:
        """Test creating escalation file."""
        # Setup: create history
        plan = {
            "title": "Test",
            "qa_iteration_history": [
                {"iteration": i, "status": "rejected", "issues": [sample_issues[0]]}
                for i in range(1, 4)
            ],
        }
        create_spec_files(temp_spec_dir, plan)

        recurring_issues = [
            {**sample_issues[0], "occurrence_count": 3},
        ]

        await escalate_to_human(temp_spec_dir, recurring_issues, iteration=3)

        # Verify escalation file was created
        escalation_file = temp_spec_dir / "QA_ESCALATION.md"
        assert escalation_file.exists()

        content = escalation_file.read_text()
        assert "QA Escalation" in content
        assert "Recurring issues detected" in content
        assert "Test failure in auth module" in content

    @pytest.mark.asyncio
    async def test_escalate_includes_summary(self, temp_spec_dir: Path, sample_issues: list) -> None:
        """Test that escalation includes issue summary."""
        plan = {
            "title": "Test",
            "qa_iteration_history": [
                {"iteration": i, "status": "rejected", "issues": sample_issues}
                for i in range(1, 4)
            ],
        }
        create_spec_files(temp_spec_dir, plan)

        await escalate_to_human(temp_spec_dir, sample_issues, iteration=3)

        escalation_file = temp_spec_dir / "QA_ESCALATION.md"
        content = escalation_file.read_text()

        assert "Most Common Issues" in content
        assert "**Total QA Iterations**: 3" in content

    @pytest.mark.asyncio
    async def test_escalate_with_empty_history(self, temp_spec_dir: Path, sample_issues: list) -> None:
        """Test escalation with minimal history."""
        plan = {"title": "Test", "qa_iteration_history": []}
        create_spec_files(temp_spec_dir, plan)

        await escalate_to_human(temp_spec_dir, sample_issues, iteration=1)

        escalation_file = temp_spec_dir / "QA_ESCALATION.md"
        assert escalation_file.exists()


class TestManualTestPlan:
    """Tests for manual test plan creation."""

    def test_create_manual_test_plan(self, temp_spec_dir: Path) -> None:
        """Test creating a manual test plan."""
        result = create_manual_test_plan(temp_spec_dir, "test-feature")

        assert result == temp_spec_dir / "MANUAL_TEST_PLAN.md"
        assert result.exists()

        content = result.read_text()
        assert "Manual Test Plan - test-feature" in content
        assert "No automated test framework detected" in content

    def test_create_manual_test_plan_from_spec(self, temp_spec_dir: Path) -> None:
        """Test creating test plan with acceptance criteria from spec."""
        spec_content = """
# Feature Spec

## Acceptance Criteria
- User can log in with valid credentials
- System shows error for invalid credentials
- Password reset functionality works
        """
        spec_file = temp_spec_dir / "spec.md"
        spec_file.write_text(spec_content)

        result = create_manual_test_plan(temp_spec_dir, "auth-feature")

        content = result.read_text()
        assert "User can log in with valid credentials" in content
        assert "System shows error for invalid credentials" in content
        assert "Password reset functionality works" in content

    def test_create_manual_test_plan_default_criteria(self, temp_spec_dir: Path) -> None:
        """Test creating test plan with default criteria when no spec."""
        result = create_manual_test_plan(temp_spec_dir, "test-feature")

        content = result.read_text()
        assert "Core functionality works as expected" in content
        assert "Edge cases are handled" in content
        assert "Error states are handled gracefully" in content


class TestTestDiscovery:
    """Tests for test discovery functions."""

    def test_check_test_discovery_none(self, temp_spec_dir: Path) -> None:
        """Test check_test_discovery when file doesn't exist."""
        result = check_test_discovery(temp_spec_dir)

        assert result is None

    def test_check_test_discovery_valid(self, temp_spec_dir: Path) -> None:
        """Test check_test_discovery with valid data."""
        discovery_data = {
            "frameworks": ["pytest", "vitest"],
            "test_files": 25,
        }
        discovery_file = temp_spec_dir / "test_discovery.json"
        discovery_file.write_text(json.dumps(discovery_data))

        result = check_test_discovery(temp_spec_dir)

        assert result is not None
        assert result["frameworks"] == ["pytest", "vitest"]
        assert result["test_files"] == 25

    def test_check_test_discovery_invalid_json(self, temp_spec_dir: Path) -> None:
        """Test check_test_discovery with invalid JSON."""
        discovery_file = temp_spec_dir / "test_discovery.json"
        discovery_file.write_text("{invalid}")

        result = check_test_discovery(temp_spec_dir)

        assert result is None

    def test_is_no_test_project_with_discovery(self, temp_spec_dir: Path) -> None:
        """Test is_no_test_project using cached discovery."""
        discovery_data = {"frameworks": []}  # No frameworks found
        discovery_file = temp_spec_dir / "test_discovery.json"
        discovery_file.write_text(json.dumps(discovery_data))

        result = is_no_test_project(temp_spec_dir, temp_spec_dir)

        assert result is True

    def test_is_no_test_project_with_frameworks(self, temp_spec_dir: Path) -> None:
        """Test is_no_test_project when frameworks are detected."""
        discovery_data = {"frameworks": ["pytest"]}
        discovery_file = temp_spec_dir / "test_discovery.json"
        discovery_file.write_text(json.dumps(discovery_data))

        result = is_no_test_project(temp_spec_dir, temp_spec_dir)

        assert result is False

    def test_is_no_test_project_scans_pytest(self, temp_project_dir: Path, temp_spec_dir: Path) -> None:
        """Test detecting pytest by pyproject.toml."""
        pyproject = temp_project_dir / "pyproject.toml"
        pyproject.write_text("[tool.pytest]")

        result = is_no_test_project(temp_spec_dir, temp_project_dir)

        assert result is False

    def test_is_no_test_project_scans_jest(self, temp_project_dir: Path, temp_spec_dir: Path) -> None:
        """Test detecting jest by config file."""
        jest_config = temp_project_dir / "jest.config.js"
        jest_config.write_text("module.exports = {};")

        result = is_no_test_project(temp_spec_dir, temp_project_dir)

        assert result is False

    def test_is_no_test_project_scans_test_dir(self, temp_project_dir: Path, temp_spec_dir: Path) -> None:
        """Test detecting tests by directory."""
        test_dir = temp_project_dir / "tests"
        test_dir.mkdir()
        (test_dir / "test_example.py").write_text("def test_pass(): pass")

        result = is_no_test_project(temp_spec_dir, temp_project_dir)

        assert result is False

    def test_is_no_test_project_true_no_indicators(self, temp_project_dir: Path, temp_spec_dir: Path) -> None:
        """Test is_no_test_project returns True when no indicators."""
        # Create a project with no test indicators
        src_dir = temp_project_dir / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("print('hello')")

        result = is_no_test_project(temp_spec_dir, temp_project_dir)

        assert result is True
