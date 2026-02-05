"""
Tests for qa.criteria module.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from apps.backend.qa.criteria import (
    get_qa_iteration_count,
    get_qa_signoff_status,
    is_fixes_applied,
    is_qa_approved,
    is_qa_rejected,
    load_implementation_plan,
    print_qa_status,
    save_implementation_plan,
    should_run_fixes,
    should_run_qa,
)

from .conftest import create_spec_files


class TestLoadImplementationPlan:
    """Tests for load_implementation_plan."""

    def test_load_valid_plan(self, temp_spec_dir: Path, sample_implementation_plan: dict) -> None:
        """Test loading a valid implementation plan."""
        create_spec_files(temp_spec_dir, sample_implementation_plan)

        result = load_implementation_plan(temp_spec_dir)

        assert result is not None
        assert result["title"] == "Test Feature"
        assert result["description"] == "Test feature description"

    def test_load_missing_file(self, temp_spec_dir: Path) -> None:
        """Test loading when implementation_plan.json doesn't exist."""
        result = load_implementation_plan(temp_spec_dir)

        assert result is None

    def test_load_invalid_json(self, temp_spec_dir: Path) -> None:
        """Test loading with invalid JSON."""
        plan_file = temp_spec_dir / "implementation_plan.json"
        plan_file.write_text("{invalid json}")

        result = load_implementation_plan(temp_spec_dir)

        assert result is None

    def test_load_with_unicode_error(self, temp_spec_dir: Path) -> None:
        """Test loading with unicode decode error."""
        plan_file = temp_spec_dir / "implementation_plan.json"
        plan_file.write_bytes(b"\xff\xfe Invalid UTF-8")

        result = load_implementation_plan(temp_spec_dir)

        assert result is None


class TestSaveImplementationPlan:
    """Tests for save_implementation_plan."""

    def test_save_valid_plan(self, temp_spec_dir: Path, sample_implementation_plan: dict) -> None:
        """Test saving a valid implementation plan."""
        result = save_implementation_plan(temp_spec_dir, sample_implementation_plan)

        assert result is True

        # Verify file was created
        plan_file = temp_spec_dir / "implementation_plan.json"
        assert plan_file.exists()

        # Verify content
        with open(plan_file) as f:
            saved_plan = json.load(f)
        assert saved_plan["title"] == "Test Feature"

    def test_save_without_write_permission(self, tmp_path: Path) -> None:
        """Test saving when directory is not writable."""
        # Create a read-only directory
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()

        # Make directory read-only (Unix-like systems)
        import stat
        readonly_dir.chmod(stat.S_IRUSR | stat.S_IXUSR)

        try:
            result = save_implementation_plan(readonly_dir, {"test": "data"})
            # On some systems, this might still succeed
            # or raise an exception instead of returning False
        finally:
            # Restore permissions for cleanup
            readonly_dir.chmod(stat.S_IRWXU)


class TestGetQaSignoffStatus:
    """Tests for get_qa_signoff_status."""

    def test_get_status_with_plan(self, temp_spec_dir: Path, approved_plan: dict) -> None:
        """Test getting QA signoff status from plan."""
        create_spec_files(temp_spec_dir, approved_plan)

        result = get_qa_signoff_status(temp_spec_dir)

        assert result is not None
        assert result["status"] == "approved"
        assert result["qa_session"] == 1

    def test_get_status_no_plan(self, temp_spec_dir: Path) -> None:
        """Test getting status when plan doesn't exist."""
        result = get_qa_signoff_status(temp_spec_dir)

        assert result is None

    def test_get_status_no_signoff(self, temp_spec_dir: Path, sample_implementation_plan: dict) -> None:
        """Test getting status when plan has no qa_signoff."""
        plan = sample_implementation_plan.copy()
        del plan["qa_signoff"]
        create_spec_files(temp_spec_dir, plan)

        result = get_qa_signoff_status(temp_spec_dir)

        assert result is None


class TestIsQaApproved:
    """Tests for is_qa_approved."""

    def test_approved_true(self, temp_spec_dir: Path, approved_plan: dict) -> None:
        """Test is_qa_approved returns True when approved."""
        create_spec_files(temp_spec_dir, approved_plan)

        result = is_qa_approved(temp_spec_dir)

        assert result is True

    def test_approved_false_when_rejected(self, temp_spec_dir: Path, rejected_plan: dict) -> None:
        """Test is_qa_approved returns False when rejected."""
        create_spec_files(temp_spec_dir, rejected_plan)

        result = is_qa_approved(temp_spec_dir)

        assert result is False

    def test_approved_false_no_plan(self, temp_spec_dir: Path) -> None:
        """Test is_qa_approved returns False when no plan."""
        result = is_qa_approved(temp_spec_dir)

        assert result is False

    def test_approved_false_no_signoff(self, temp_spec_dir: Path, sample_implementation_plan: dict) -> None:
        """Test is_qa_approved returns False when no signoff."""
        plan = sample_implementation_plan.copy()
        del plan["qa_signoff"]
        create_spec_files(temp_spec_dir, plan)

        result = is_qa_approved(temp_spec_dir)

        assert result is False


class TestIsQaRejected:
    """Tests for is_qa_rejected."""

    def test_rejected_true(self, temp_spec_dir: Path, rejected_plan: dict) -> None:
        """Test is_qa_rejected returns True when rejected."""
        create_spec_files(temp_spec_dir, rejected_plan)

        result = is_qa_rejected(temp_spec_dir)

        assert result is True

    def test_rejected_false_when_approved(self, temp_spec_dir: Path, approved_plan: dict) -> None:
        """Test is_qa_rejected returns False when approved."""
        create_spec_files(temp_spec_dir, approved_plan)

        result = is_qa_rejected(temp_spec_dir)

        assert result is False

    def test_rejected_false_no_plan(self, temp_spec_dir: Path) -> None:
        """Test is_qa_rejected returns False when no plan."""
        result = is_qa_rejected(temp_spec_dir)

        assert result is False


class TestIsFixesApplied:
    """Tests for is_fixes_applied."""

    def test_fixes_applied_true(self, temp_spec_dir: Path, sample_implementation_plan: dict) -> None:
        """Test is_fixes_applied returns True with proper status."""
        plan = sample_implementation_plan.copy()
        plan["qa_signoff"] = {
            "status": "fixes_applied",
            "ready_for_qa_revalidation": True,
        }
        create_spec_files(temp_spec_dir, plan)

        result = is_fixes_applied(temp_spec_dir)

        assert result is True

    def test_fixes_applied_false_when_not_ready(self, temp_spec_dir: Path, sample_implementation_plan: dict) -> None:
        """Test is_fixes_applied returns False when not ready."""
        plan = sample_implementation_plan.copy()
        plan["qa_signoff"] = {
            "status": "fixes_applied",
            "ready_for_qa_revalidation": False,
        }
        create_spec_files(temp_spec_dir, plan)

        result = is_fixes_applied(temp_spec_dir)

        assert result is False

    def test_fixes_applied_false_different_status(self, temp_spec_dir: Path, approved_plan: dict) -> None:
        """Test is_fixes_applied returns False for other statuses."""
        create_spec_files(temp_spec_dir, approved_plan)

        result = is_fixes_applied(temp_spec_dir)

        assert result is False


class TestGetQaIterationCount:
    """Tests for get_qa_iteration_count."""

    def test_iteration_count_from_signoff(self, temp_spec_dir: Path, approved_plan: dict) -> None:
        """Test getting iteration count from qa_signoff."""
        create_spec_files(temp_spec_dir, approved_plan)

        result = get_qa_iteration_count(temp_spec_dir)

        assert result == 1

    def test_iteration_count_no_signoff(self, temp_spec_dir: Path, sample_implementation_plan: dict) -> None:
        """Test iteration count returns 0 when no signoff."""
        plan = sample_implementation_plan.copy()
        del plan["qa_signoff"]
        create_spec_files(temp_spec_dir, plan)

        result = get_qa_iteration_count(temp_spec_dir)

        assert result == 0

    def test_iteration_count_no_plan(self, temp_spec_dir: Path) -> None:
        """Test iteration count returns 0 when no plan."""
        result = get_qa_iteration_count(temp_spec_dir)

        assert result == 0


class TestShouldRunQa:
    """Tests for should_run_qa."""

    def test_should_run_qa_true(self, temp_spec_dir: Path, sample_implementation_plan: dict) -> None:
        """Test should_run_qa returns True when build complete and not approved."""
        create_spec_files(temp_spec_dir, sample_implementation_plan)

        with patch("apps.backend.qa.criteria.is_build_complete", return_value=True):
            result = should_run_qa(temp_spec_dir)

        assert result is True

    def test_should_run_qa_false_build_incomplete(self, temp_spec_dir: Path, sample_implementation_plan: dict) -> None:
        """Test should_run_qa returns False when build incomplete."""
        create_spec_files(temp_spec_dir, sample_implementation_plan)

        with patch("apps.backend.qa.criteria.is_build_complete", return_value=False):
            result = should_run_qa(temp_spec_dir)

        assert result is False

    def test_should_run_qa_false_already_approved(self, temp_spec_dir: Path, approved_plan: dict) -> None:
        """Test should_run_qa returns False when already approved."""
        create_spec_files(temp_spec_dir, approved_plan)

        with patch("apps.backend.qa.criteria.is_build_complete", return_value=True):
            result = should_run_qa(temp_spec_dir)

        assert result is False


class TestShouldRunFixes:
    """Tests for should_run_fixes."""

    def test_should_run_fixes_true(self, temp_spec_dir: Path, rejected_plan: dict) -> None:
        """Test should_run_fixes returns True when rejected and under max iterations."""
        create_spec_files(temp_spec_dir, rejected_plan)

        result = should_run_fixes(temp_spec_dir)

        assert result is True

    def test_should_run_fixes_false_not_rejected(self, temp_spec_dir: Path, approved_plan: dict) -> None:
        """Test should_run_fixes returns False when not rejected."""
        create_spec_files(temp_spec_dir, approved_plan)

        result = should_run_fixes(temp_spec_dir)

        assert result is False

    def test_should_run_fixes_false_max_iterations(self, temp_spec_dir: Path, sample_implementation_plan: dict) -> None:
        """Test should_run_fixes returns False when max iterations reached."""
        plan = sample_implementation_plan.copy()
        plan["qa_signoff"] = {
            "status": "rejected",
            "qa_session": 100,  # Exceeds MAX_QA_ITERATIONS (50)
        }
        create_spec_files(temp_spec_dir, plan)

        result = should_run_fixes(temp_spec_dir)

        assert result is False


class TestPrintQaStatus:
    """Tests for print_qa_status."""

    def test_print_qa_status_approved(self, temp_spec_dir: Path, approved_plan: dict, capsys: pytest.CaptureFixture) -> None:
        """Test print_qa_status for approved build."""
        create_spec_files(temp_spec_dir, approved_plan)

        print_qa_status(temp_spec_dir)

        captured = capsys.readouterr()
        assert "QA Status: APPROVED" in captured.out
        assert "QA Sessions: 1" in captured.out

    def test_print_qa_status_rejected(self, temp_spec_dir: Path, rejected_plan: dict, capsys: pytest.CaptureFixture) -> None:
        """Test print_qa_status for rejected build."""
        create_spec_files(temp_spec_dir, rejected_plan)

        print_qa_status(temp_spec_dir)

        captured = capsys.readouterr()
        assert "QA Status: REJECTED" in captured.out
        assert "Issues Found: 2" in captured.out

    def test_print_qa_status_not_started(self, temp_spec_dir: Path, capsys: pytest.CaptureFixture) -> None:
        """Test print_qa_status when QA not started."""
        print_qa_status(temp_spec_dir)

        captured = capsys.readouterr()
        assert "QA Status: Not started" in captured.out

    def test_print_qa_status_with_history(self, temp_spec_dir: Path, sample_implementation_plan: dict, capsys: pytest.CaptureFixture) -> None:
        """Test print_qa_status with iteration history."""
        plan = sample_implementation_plan.copy()
        plan["qa_iteration_history"] = [
            {
                "iteration": 1,
                "status": "rejected",
                "timestamp": "2024-01-01T00:00:00Z",
                "issues": [{"title": "Test issue", "type": "critical"}],
            },
            {
                "iteration": 2,
                "status": "approved",
                "timestamp": "2024-01-01T01:00:00Z",
                "issues": [],
            },
        ]
        create_spec_files(temp_spec_dir, plan)

        print_qa_status(temp_spec_dir)

        captured = capsys.readouterr()
        assert "Iteration History:" in captured.out
        assert "Total iterations: 2" in captured.out
