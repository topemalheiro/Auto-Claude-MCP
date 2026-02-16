"""
Tests for mcp_server/services/qa_service.py
=============================================

Tests QA report retrieval, manual approval, session number resolution,
spec directory resolution, and start_review error paths.
"""

import sys
from pathlib import Path

# Add backend to sys.path
_backend = Path(__file__).parent.parent / "apps" / "backend"
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

# Pre-mock SDK modules before any mcp_server imports
from unittest.mock import MagicMock

if "claude_agent_sdk" not in sys.modules:
    sys.modules["claude_agent_sdk"] = MagicMock()
    sys.modules["claude_agent_sdk.types"] = MagicMock()

import json

import pytest

from mcp_server.services.qa_service import QAService


def _make_spec_dir(tmp_path: Path, spec_name: str = "001-feat") -> Path:
    """Create a spec directory structure for testing."""
    specs_dir = tmp_path / ".auto-claude" / "specs" / spec_name
    specs_dir.mkdir(parents=True)
    return specs_dir


class TestResolveSpecDir:
    """Tests for QAService._resolve_spec_dir()."""

    def test_exact_match(self, tmp_path):
        """Resolves exact spec directory name."""
        spec_dir = _make_spec_dir(tmp_path, "001-feature")
        svc = QAService(tmp_path)
        assert svc._resolve_spec_dir("001-feature") == spec_dir

    def test_prefix_match(self, tmp_path):
        """Resolves spec directory by prefix."""
        spec_dir = _make_spec_dir(tmp_path, "001-my-feature")
        svc = QAService(tmp_path)
        assert svc._resolve_spec_dir("001") == spec_dir

    def test_no_match_returns_none(self, tmp_path):
        """Returns None when no spec matches."""
        _make_spec_dir(tmp_path, "001-feat")
        svc = QAService(tmp_path)
        assert svc._resolve_spec_dir("999") is None

    def test_no_specs_dir_returns_none(self, tmp_path):
        """Returns None when specs directory doesn't exist."""
        svc = QAService(tmp_path)
        assert svc._resolve_spec_dir("001") is None


class TestGetNextQaSession:
    """Tests for QAService._get_next_qa_session()."""

    def test_first_session_when_no_plan(self, tmp_path):
        """Returns 1 when no implementation plan exists."""
        spec_dir = _make_spec_dir(tmp_path)
        svc = QAService(tmp_path)
        assert svc._get_next_qa_session(spec_dir) == 1

    def test_increments_from_existing_session(self, tmp_path):
        """Increments the qa_session number from existing signoff."""
        spec_dir = _make_spec_dir(tmp_path)
        plan = {"qa_signoff": {"qa_session": 2, "status": "rejected"}}
        (spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

        svc = QAService(tmp_path)
        assert svc._get_next_qa_session(spec_dir) == 3

    def test_first_session_when_no_signoff(self, tmp_path):
        """Returns 1 when plan exists but has no qa_signoff."""
        spec_dir = _make_spec_dir(tmp_path)
        plan = {"subtasks": []}
        (spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

        svc = QAService(tmp_path)
        assert svc._get_next_qa_session(spec_dir) == 1

    def test_handles_corrupt_plan(self, tmp_path):
        """Returns 1 when plan file has invalid JSON."""
        spec_dir = _make_spec_dir(tmp_path)
        (spec_dir / "implementation_plan.json").write_text("not json!!")

        svc = QAService(tmp_path)
        assert svc._get_next_qa_session(spec_dir) == 1


class TestStartReview:
    """Tests for QAService.start_review()."""

    @pytest.mark.asyncio
    async def test_returns_error_for_missing_spec(self, tmp_path):
        """start_review returns error when spec not found."""
        (tmp_path / ".auto-claude" / "specs").mkdir(parents=True)
        svc = QAService(tmp_path)
        result = await svc.start_review("999-missing")
        assert "error" in result
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_returns_error_for_missing_plan(self, tmp_path):
        """start_review returns error when no implementation plan exists."""
        _make_spec_dir(tmp_path, "001-feat")
        svc = QAService(tmp_path)
        result = await svc.start_review("001-feat")
        assert "error" in result
        assert "implementation plan" in result["error"].lower() or "Build" in result["error"]

    @pytest.mark.asyncio
    async def test_returns_error_on_import_failure(self, tmp_path, monkeypatch):
        """start_review returns error when backend QA modules unavailable."""
        spec_dir = _make_spec_dir(tmp_path, "001-feat")
        plan = {"subtasks": [{"status": "completed"}]}
        (spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

        svc = QAService(tmp_path)
        # The import of core.client / qa.reviewer will fail naturally
        # since we haven't set up the backend path properly for these modules
        result = await svc.start_review("001-feat")
        assert "error" in result


class TestGetReport:
    """Tests for QAService.get_report()."""

    def test_returns_error_for_missing_spec(self, tmp_path):
        """get_report returns error when spec not found."""
        (tmp_path / ".auto-claude" / "specs").mkdir(parents=True)
        svc = QAService(tmp_path)
        result = svc.get_report("999-missing")
        assert "error" in result

    def test_reads_qa_report(self, tmp_path):
        """get_report returns qa_report.md content."""
        spec_dir = _make_spec_dir(tmp_path, "001-feat")
        report_text = "# QA Report\n\nAll tests passed."
        (spec_dir / "qa_report.md").write_text(report_text)

        svc = QAService(tmp_path)
        result = svc.get_report("001-feat")
        assert result["report"] == report_text
        assert result["spec_id"] == "001-feat"

    def test_reads_fix_request(self, tmp_path):
        """get_report includes QA_FIX_REQUEST.md content when present."""
        spec_dir = _make_spec_dir(tmp_path, "001-feat")
        fix_text = "## Fix Required\n\nFix the error handling."
        (spec_dir / "QA_FIX_REQUEST.md").write_text(fix_text)

        svc = QAService(tmp_path)
        result = svc.get_report("001-feat")
        assert result["fix_request"] == fix_text

    def test_reads_qa_signoff(self, tmp_path):
        """get_report includes qa_signoff from implementation plan."""
        spec_dir = _make_spec_dir(tmp_path, "001-feat")
        signoff = {"status": "approved", "qa_session": 2}
        plan = {"qa_signoff": signoff}
        (spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

        svc = QAService(tmp_path)
        result = svc.get_report("001-feat")
        assert result["qa_signoff"] == signoff

    def test_no_report_message(self, tmp_path):
        """get_report returns 'no report' message when nothing exists."""
        _make_spec_dir(tmp_path, "001-feat")
        svc = QAService(tmp_path)
        result = svc.get_report("001-feat")
        assert "No QA report" in result.get("message", "")

    def test_reads_all_artifacts(self, tmp_path):
        """get_report combines report, fix request, and signoff."""
        spec_dir = _make_spec_dir(tmp_path, "001-feat")
        (spec_dir / "qa_report.md").write_text("Report content")
        (spec_dir / "QA_FIX_REQUEST.md").write_text("Fix content")
        plan = {"qa_signoff": {"status": "rejected", "qa_session": 1}}
        (spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

        svc = QAService(tmp_path)
        result = svc.get_report("001-feat")
        assert "report" in result
        assert "fix_request" in result
        assert "qa_signoff" in result

    def test_handles_corrupt_plan_gracefully(self, tmp_path):
        """get_report skips qa_signoff on corrupt plan file."""
        spec_dir = _make_spec_dir(tmp_path, "001-feat")
        (spec_dir / "qa_report.md").write_text("Report content")
        (spec_dir / "implementation_plan.json").write_text("bad json!")

        svc = QAService(tmp_path)
        result = svc.get_report("001-feat")
        assert "report" in result
        assert "qa_signoff" not in result


class TestApprove:
    """Tests for QAService.approve()."""

    def test_returns_error_for_missing_spec(self, tmp_path):
        """approve returns error when spec not found."""
        (tmp_path / ".auto-claude" / "specs").mkdir(parents=True)
        svc = QAService(tmp_path)
        result = svc.approve("999-missing")
        assert "error" in result

    def test_returns_error_for_missing_plan(self, tmp_path):
        """approve returns error when no implementation plan exists."""
        _make_spec_dir(tmp_path, "001-feat")
        svc = QAService(tmp_path)
        result = svc.approve("001-feat")
        assert "error" in result
        assert "implementation plan" in result["error"].lower()

    def test_writes_qa_signoff(self, tmp_path):
        """approve writes qa_signoff to the implementation plan."""
        spec_dir = _make_spec_dir(tmp_path, "001-feat")
        plan = {"subtasks": [{"status": "completed"}]}
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan))

        svc = QAService(tmp_path)
        result = svc.approve("001-feat")

        assert result["success"] is True
        assert result["spec_id"] == "001-feat"

        # Verify file was updated
        updated_plan = json.loads(plan_file.read_text())
        assert updated_plan["qa_signoff"]["status"] == "approved"
        assert updated_plan["qa_signoff"]["verified_by"] == "manual_approval"

    def test_preserves_existing_session_number(self, tmp_path):
        """approve preserves the existing qa_session number."""
        spec_dir = _make_spec_dir(tmp_path, "001-feat")
        plan = {"qa_signoff": {"qa_session": 3, "status": "rejected"}}
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan))

        svc = QAService(tmp_path)
        svc.approve("001-feat")

        updated_plan = json.loads(plan_file.read_text())
        assert updated_plan["qa_signoff"]["qa_session"] == 3

    def test_returns_error_on_corrupt_plan(self, tmp_path):
        """approve returns error when plan file contains invalid JSON."""
        spec_dir = _make_spec_dir(tmp_path, "001-feat")
        (spec_dir / "implementation_plan.json").write_text("not json!")

        svc = QAService(tmp_path)
        result = svc.approve("001-feat")
        assert "error" in result
