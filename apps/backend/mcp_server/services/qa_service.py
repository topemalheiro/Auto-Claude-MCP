"""
QA Service
===========

Service layer wrapping the backend QA reviewer for MCP tool consumption.
Handles client creation, stdout isolation, and error management.
"""

from __future__ import annotations

import contextlib
import io
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class QAService:
    """Wraps QA review and approval operations for MCP server use."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir

    async def start_review(
        self,
        spec_id: str,
        model: str = "sonnet",
        thinking_level: str = "medium",
        max_iterations: int = 3,
    ) -> dict:
        """Run a QA review session for a completed build.

        Args:
            spec_id: The spec folder name
            model: Model shorthand
            thinking_level: Thinking level
            max_iterations: Maximum QA loop iterations

        Returns:
            Dict with review outcome (approved/rejected/error)
        """
        spec_dir = self._resolve_spec_dir(spec_id)
        if spec_dir is None:
            return {"error": f"Spec '{spec_id}' not found"}

        # Verify the build is complete before starting QA
        plan_file = spec_dir / "implementation_plan.json"
        if not plan_file.exists():
            return {
                "error": "No implementation plan found. Build the spec first.",
            }

        try:
            from core.client import create_client
            from qa.reviewer import run_qa_agent_session
        except ImportError as e:
            logger.error("Failed to import QA modules: %s", e)
            return {"error": f"Backend module not available: {e}"}

        try:
            # Determine QA session number from existing state
            qa_session = self._get_next_qa_session(spec_dir)

            # Create a Claude SDK client for the QA agent
            captured = io.StringIO()
            with contextlib.redirect_stdout(captured):
                client = create_client(
                    project_dir=self.project_dir,
                    spec_dir=spec_dir,
                    model=model,
                    phase="qa_reviewer",
                )

                status, response_text, error_info = await run_qa_agent_session(
                    client=client,
                    project_dir=self.project_dir,
                    spec_dir=spec_dir,
                    qa_session=qa_session,
                    max_iterations=max_iterations,
                )

            return {
                "spec_id": spec_id,
                "status": status,
                "qa_session": qa_session,
                "response_preview": response_text[:1000] if response_text else "",
                "error_info": error_info if error_info else None,
                "output": captured.getvalue()[-1000:] if captured.getvalue() else "",
            }
        except Exception as e:
            logger.exception("QA review failed for %s", spec_id)
            return {
                "spec_id": spec_id,
                "status": "error",
                "error": str(e),
            }

    def get_report(self, spec_id: str) -> dict:
        """Get the QA report for a spec.

        Args:
            spec_id: The spec folder name

        Returns:
            Dict with QA report content and status
        """
        spec_dir = self._resolve_spec_dir(spec_id)
        if spec_dir is None:
            return {"error": f"Spec '{spec_id}' not found"}

        result: dict = {"spec_id": spec_id}

        # Read qa_report.md
        qa_report = spec_dir / "qa_report.md"
        if qa_report.exists():
            try:
                result["report"] = qa_report.read_text(encoding="utf-8")
            except OSError as e:
                result["report_error"] = str(e)

        # Read QA fix request if present
        fix_request = spec_dir / "QA_FIX_REQUEST.md"
        if fix_request.exists():
            try:
                result["fix_request"] = fix_request.read_text(encoding="utf-8")
            except OSError as e:
                result["fix_request_error"] = str(e)

        # Read qa_signoff from implementation plan
        plan_file = spec_dir / "implementation_plan.json"
        if plan_file.exists():
            try:
                with open(plan_file, encoding="utf-8") as f:
                    plan = json.load(f)
                qa_signoff = plan.get("qa_signoff")
                if qa_signoff:
                    result["qa_signoff"] = qa_signoff
            except (json.JSONDecodeError, OSError):
                pass

        if "report" not in result and "qa_signoff" not in result:
            result["message"] = "No QA report found. Run QA review first."

        return result

    def approve(self, spec_id: str) -> dict:
        """Manually approve a spec's QA status.

        Args:
            spec_id: The spec folder name

        Returns:
            Dict with approval result
        """
        spec_dir = self._resolve_spec_dir(spec_id)
        if spec_dir is None:
            return {"error": f"Spec '{spec_id}' not found"}

        plan_file = spec_dir / "implementation_plan.json"
        if not plan_file.exists():
            return {"error": "No implementation plan found"}

        try:
            with open(plan_file, encoding="utf-8") as f:
                plan = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            return {"error": f"Could not read implementation plan: {e}"}

        from datetime import datetime, timezone

        plan["qa_signoff"] = {
            "status": "approved",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "qa_session": plan.get("qa_signoff", {}).get("qa_session", 0),
            "verified_by": "manual_approval",
            "note": "Manually approved via MCP tool",
        }

        try:
            with open(plan_file, "w", encoding="utf-8") as f:
                json.dump(plan, f, indent=2)
        except OSError as e:
            return {"error": f"Could not write implementation plan: {e}"}

        return {
            "success": True,
            "spec_id": spec_id,
            "message": "Spec manually approved",
        }

    def _get_next_qa_session(self, spec_dir: Path) -> int:
        """Get the next QA session number.

        Args:
            spec_dir: Path to the spec directory

        Returns:
            Next session number (1-based)
        """
        plan_file = spec_dir / "implementation_plan.json"
        if not plan_file.exists():
            return 1
        try:
            with open(plan_file, encoding="utf-8") as f:
                plan = json.load(f)
            qa_signoff = plan.get("qa_signoff", {})
            current = qa_signoff.get("qa_session", 0)
            return current + 1
        except (json.JSONDecodeError, OSError):
            return 1

    def _resolve_spec_dir(self, spec_id: str) -> Path | None:
        """Resolve spec_id to its directory path.

        Args:
            spec_id: Full or prefix spec identifier

        Returns:
            Path to spec directory or None
        """
        specs_dir = self.project_dir / ".auto-claude" / "specs"

        # Direct match
        exact = specs_dir / spec_id
        if exact.is_dir():
            return exact

        # Prefix match
        if specs_dir.is_dir():
            for item in specs_dir.iterdir():
                if item.is_dir() and item.name.startswith(spec_id):
                    return item

        return None
