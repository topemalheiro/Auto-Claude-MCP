"""
Spec Service
=============

Service layer wrapping the backend SpecOrchestrator for MCP tool consumption.
Handles stdout isolation and error management.
"""

from __future__ import annotations

import contextlib
import io
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class SpecService:
    """Wraps backend spec creation pipeline for MCP server use."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir

    async def create_spec(
        self,
        task_description: str,
        model: str = "sonnet",
        thinking_level: str = "medium",
        complexity_override: str | None = None,
    ) -> dict:
        """Create a spec using the SpecOrchestrator.

        Redirects stdout to prevent protocol corruption when running
        under stdio transport.

        Args:
            task_description: Description of the task to spec out
            model: Model shorthand (sonnet, opus, etc.)
            thinking_level: Thinking level (low, medium, high)
            complexity_override: Force a specific complexity level

        Returns:
            Dict with success status, spec_dir, spec_id, and any captured output
        """
        try:
            from spec.pipeline.orchestrator import SpecOrchestrator
        except ImportError as e:
            logger.error("Failed to import SpecOrchestrator: %s", e)
            return {
                "success": False,
                "error": f"Backend module not available: {e}",
            }

        try:
            captured = io.StringIO()
            with contextlib.redirect_stdout(captured):
                orchestrator = SpecOrchestrator(
                    project_dir=self.project_dir,
                    task_description=task_description,
                    model=model,
                    thinking_level=thinking_level,
                    complexity_override=complexity_override,
                    use_ai_assessment=True,
                )
                # Run non-interactively with auto-approve for MCP
                success = await orchestrator.run(interactive=False, auto_approve=True)

            spec_dir = orchestrator.spec_dir
            return {
                "success": success,
                "spec_dir": str(spec_dir),
                "spec_id": spec_dir.name,
                "output": captured.getvalue()[-2000:] if captured.getvalue() else "",
            }
        except Exception as e:
            logger.exception("Spec creation failed")
            return {
                "success": False,
                "error": str(e),
            }

    def get_spec_status(self, spec_id: str) -> dict:
        """Get the status of a spec by checking which phase files exist.

        Args:
            spec_id: The spec folder name (e.g. '001-my-feature')

        Returns:
            Dict describing which phases are complete and current state
        """
        specs_dir = self.project_dir / ".auto-claude" / "specs"
        spec_dir = self._resolve_spec_dir(specs_dir, spec_id)
        if spec_dir is None:
            return {"error": f"Spec '{spec_id}' not found"}

        phases = {
            "discovery": (spec_dir / "discovery.md").exists(),
            "requirements": (spec_dir / "requirements.json").exists(),
            "complexity_assessment": (spec_dir / "complexity_assessment.json").exists(),
            "spec": (spec_dir / "spec.md").exists(),
            "implementation_plan": (spec_dir / "implementation_plan.json").exists(),
        }

        # Determine overall status
        if phases["implementation_plan"]:
            plan = self._load_json(spec_dir / "implementation_plan.json")
            qa_signoff = plan.get("qa_signoff") if plan else None
            if qa_signoff and qa_signoff.get("status") == "approved":
                status = "qa_approved"
            elif qa_signoff and qa_signoff.get("status") == "rejected":
                status = "qa_rejected"
            elif (spec_dir / "qa_report.md").exists():
                status = "qa_reviewed"
            else:
                status = "ready_to_build"
        elif phases["spec"]:
            status = "spec_complete"
        elif phases["requirements"]:
            status = "requirements_gathered"
        elif phases["discovery"]:
            status = "discovery_complete"
        else:
            status = "pending"

        return {
            "spec_id": spec_dir.name,
            "spec_dir": str(spec_dir),
            "status": status,
            "phases": phases,
        }

    def get_spec_content(self, spec_id: str) -> dict:
        """Get the full content of a spec.

        Args:
            spec_id: The spec folder name

        Returns:
            Dict with spec.md content, requirements, implementation plan, etc.
        """
        specs_dir = self.project_dir / ".auto-claude" / "specs"
        spec_dir = self._resolve_spec_dir(specs_dir, spec_id)
        if spec_dir is None:
            return {"error": f"Spec '{spec_id}' not found"}

        content: dict = {
            "spec_id": spec_dir.name,
            "spec_dir": str(spec_dir),
        }

        # Read spec.md
        spec_md = spec_dir / "spec.md"
        if spec_md.exists():
            try:
                content["spec_md"] = spec_md.read_text(encoding="utf-8")
            except OSError as e:
                content["spec_md_error"] = str(e)

        # Read requirements.json
        req = self._load_json(spec_dir / "requirements.json")
        if req is not None:
            content["requirements"] = req

        # Read implementation_plan.json
        plan = self._load_json(spec_dir / "implementation_plan.json")
        if plan is not None:
            content["implementation_plan"] = plan

        # Read complexity_assessment.json
        assessment = self._load_json(spec_dir / "complexity_assessment.json")
        if assessment is not None:
            content["complexity_assessment"] = assessment

        # Read QA report if present
        qa_report = spec_dir / "qa_report.md"
        if qa_report.exists():
            try:
                content["qa_report"] = qa_report.read_text(encoding="utf-8")
            except OSError:
                pass

        return content

    def list_specs(self) -> list[dict]:
        """List all specs in the project.

        Returns:
            List of spec summary dicts
        """
        specs_dir = self.project_dir / ".auto-claude" / "specs"
        if not specs_dir.is_dir():
            return []

        specs = []
        for item in sorted(specs_dir.iterdir()):
            if item.is_dir() and not item.name.startswith("."):
                status_info = self.get_spec_status(item.name)
                specs.append(status_info)
        return specs

    def _resolve_spec_dir(self, specs_dir: Path, spec_id: str) -> Path | None:
        """Resolve a spec_id to its directory, supporting prefix matching.

        Args:
            specs_dir: Parent specs directory
            spec_id: Full or prefix spec identifier

        Returns:
            Path to spec directory or None
        """
        # Direct match
        exact = specs_dir / spec_id
        if exact.is_dir():
            return exact

        # Prefix match (e.g. '001' matches '001-my-feature')
        if specs_dir.is_dir():
            for item in specs_dir.iterdir():
                if item.is_dir() and item.name.startswith(spec_id):
                    return item

        return None

    def _load_json(self, path: Path) -> dict | None:
        """Safely load a JSON file.

        Args:
            path: Path to the JSON file

        Returns:
            Parsed dict or None
        """
        if not path.exists():
            return None
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load %s: %s", path, e)
            return None
