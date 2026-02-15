"""
Task Service
=============

Loads, creates, updates, and deletes tasks by scanning spec directories.
Ported from the TypeScript ProjectStore.loadTasksFromSpecsDir() logic.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# Valid task statuses used by the backend pipeline
VALID_STATUSES = frozenset(
    {
        "pending",
        "spec_creating",
        "planning",
        "in_progress",
        "qa_review",
        "qa_fixing",
        "human_review",
        "done",
        "failed",
        "cancelled",
    }
)

# Status priority for deduplication (higher = more "complete")
_STATUS_PRIORITY: dict[str, int] = {
    "done": 100,
    "human_review": 80,
    "qa_fixing": 70,
    "qa_review": 65,
    "in_progress": 50,
    "planning": 40,
    "spec_creating": 35,
    "pending": 20,
    "cancelled": 15,
    "failed": 10,
}


def _slugify(text: str) -> str:
    """Convert a title into a filesystem-safe slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")[:80]


def _safe_read_json(path: Path) -> dict | None:
    """Read a JSON file, returning None on any error."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, ValueError):
        return None


def _extract_spec_heading(spec_path: Path) -> str | None:
    """Extract the first markdown heading from a spec.md file."""
    try:
        content = spec_path.read_text(encoding="utf-8")
        match = re.search(
            r"^#\s+(?:Quick Spec:|Specification:)?\s*(.+)$", content, re.MULTILINE
        )
        if match:
            return match.group(1).strip()
    except OSError:
        pass
    return None


def _extract_spec_overview(spec_path: Path) -> str | None:
    """Extract the Overview section from a spec.md file."""
    try:
        content = spec_path.read_text(encoding="utf-8")
        match = re.search(r"## Overview\s*\n+([\s\S]*?)(?=\n#{1,6}\s|$)", content)
        if match:
            return match.group(1).strip()
    except OSError:
        pass
    return None


class TaskService:
    """Manages task lifecycle by reading/writing spec directories."""

    def __init__(self, project_dir: Path) -> None:
        self.project_dir = project_dir
        self.specs_dir = project_dir / ".auto-claude" / "specs"
        self.worktrees_dir = project_dir / ".auto-claude" / "worktrees" / "tasks"

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def list_tasks(self) -> list[dict]:
        """Scan spec directories and build a deduplicated task list.

        Scans both the main project specs dir and worktree specs dirs.
        Main project tasks take priority over worktree duplicates.
        """
        all_tasks: list[dict] = []
        main_spec_ids: set[str] = set()

        # 1. Scan main project specs
        if self.specs_dir.is_dir():
            main_tasks = self._load_tasks_from_specs_dir(self.specs_dir, "main")
            all_tasks.extend(main_tasks)
            main_spec_ids = {t["spec_id"] for t in main_tasks}

        # 2. Scan worktree specs (only include if spec exists in main)
        if self.worktrees_dir.is_dir():
            try:
                for worktree_dir in sorted(self.worktrees_dir.iterdir()):
                    if not worktree_dir.is_dir():
                        continue
                    wt_specs = worktree_dir / ".auto-claude" / "specs"
                    if wt_specs.is_dir():
                        wt_tasks = self._load_tasks_from_specs_dir(wt_specs, "worktree")
                        valid = [t for t in wt_tasks if t["spec_id"] in main_spec_ids]
                        all_tasks.extend(valid)
            except OSError as exc:
                logger.warning("Error scanning worktrees: %s", exc)

        # 3. Deduplicate — prefer main over worktree
        task_map: dict[str, dict] = {}
        for task in all_tasks:
            existing = task_map.get(task["spec_id"])
            if existing is None:
                task_map[task["spec_id"]] = task
            else:
                existing_is_main = existing.get("location") == "main"
                new_is_main = task.get("location") == "main"

                if existing_is_main and not new_is_main:
                    # Keep existing main
                    continue
                elif not existing_is_main and new_is_main:
                    # Replace worktree with main
                    task_map[task["spec_id"]] = task
                else:
                    # Same location — use status priority
                    ep = _STATUS_PRIORITY.get(existing.get("status", ""), 0)
                    np = _STATUS_PRIORITY.get(task.get("status", ""), 0)
                    if np > ep:
                        task_map[task["spec_id"]] = task

        return list(task_map.values())

    def get_task(self, spec_id: str) -> dict | None:
        """Get full details for a single task by spec_id."""
        spec_dir = self.specs_dir / spec_id
        if not spec_dir.is_dir():
            # Try worktrees
            spec_dir = self._find_spec_dir_in_worktrees(spec_id)
            if spec_dir is None:
                return None
        return self._load_single_task(spec_dir, "main")

    def create_task(self, title: str, description: str) -> dict:
        """Create a new spec directory with initial files.

        Returns the created task dict.
        """
        self.specs_dir.mkdir(parents=True, exist_ok=True)

        next_num = self._next_spec_number()
        slug = _slugify(title)
        dir_name = f"{next_num:03d}-{slug}" if slug else f"{next_num:03d}"
        spec_dir = self.specs_dir / dir_name

        spec_dir.mkdir(parents=True, exist_ok=True)

        now = datetime.now(timezone.utc).isoformat()

        # Write requirements.json
        requirements = {"task_description": description}
        (spec_dir / "requirements.json").write_text(
            json.dumps(requirements, indent=2), encoding="utf-8"
        )

        # Write implementation_plan.json
        plan = {
            "feature": title,
            "title": title,
            "description": description,
            "status": "pending",
            "phases": [],
            "created_at": now,
            "updated_at": now,
        }
        (spec_dir / "implementation_plan.json").write_text(
            json.dumps(plan, indent=2), encoding="utf-8"
        )

        # Write task_metadata.json
        metadata = {
            "created_at": now,
            "source": "mcp",
        }
        (spec_dir / "task_metadata.json").write_text(
            json.dumps(metadata, indent=2), encoding="utf-8"
        )

        return self._load_single_task(spec_dir, "main") or {
            "spec_id": dir_name,
            "title": title,
            "description": description,
            "status": "pending",
        }

    def update_task(
        self,
        spec_id: str,
        *,
        title: str | None = None,
        description: str | None = None,
        status: str | None = None,
    ) -> dict | None:
        """Update task metadata/plan fields."""
        spec_dir = self.specs_dir / spec_id
        if not spec_dir.is_dir():
            return None

        plan_path = spec_dir / "implementation_plan.json"
        plan = _safe_read_json(plan_path) or {}
        changed = False

        if title is not None:
            plan["feature"] = title
            plan["title"] = title
            changed = True

        if description is not None:
            plan["description"] = description
            # Also update requirements
            req_path = spec_dir / "requirements.json"
            reqs = _safe_read_json(req_path) or {}
            reqs["task_description"] = description
            req_path.write_text(json.dumps(reqs, indent=2), encoding="utf-8")
            changed = True

        if status is not None:
            if status not in VALID_STATUSES:
                return None
            plan["status"] = status
            changed = True

        if changed:
            plan["updated_at"] = datetime.now(timezone.utc).isoformat()
            plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")

        return self._load_single_task(spec_dir, "main")

    def delete_task(self, spec_id: str) -> bool:
        """Delete a spec directory. Returns True if deleted."""
        spec_dir = self.specs_dir / spec_id
        if not spec_dir.is_dir():
            return False

        # Safety: ensure it's actually within specs_dir (prevent traversal)
        try:
            spec_dir.resolve().relative_to(self.specs_dir.resolve())
        except ValueError:
            logger.error("Path traversal detected for spec_id: %s", spec_id)
            return False

        shutil.rmtree(spec_dir)
        return True

    def update_status(self, spec_id: str, status: str) -> dict | None:
        """Update just the status field in implementation_plan.json."""
        if status not in VALID_STATUSES:
            return None
        return self.update_task(spec_id, status=status)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _next_spec_number(self) -> int:
        """Find the highest existing spec number and return next."""
        max_num = 0
        if self.specs_dir.is_dir():
            for entry in self.specs_dir.iterdir():
                if entry.is_dir():
                    match = re.match(r"^(\d{3})-", entry.name)
                    if match:
                        max_num = max(max_num, int(match.group(1)))
        return max_num + 1

    def _find_spec_dir_in_worktrees(self, spec_id: str) -> Path | None:
        """Search worktree directories for a spec."""
        if not self.worktrees_dir.is_dir():
            return None
        for wt_dir in self.worktrees_dir.iterdir():
            if not wt_dir.is_dir():
                continue
            candidate = wt_dir / ".auto-claude" / "specs" / spec_id
            if candidate.is_dir():
                return candidate
        return None

    def _load_tasks_from_specs_dir(self, specs_dir: Path, location: str) -> list[dict]:
        """Load all tasks from a specs directory."""
        tasks: list[dict] = []

        try:
            entries = sorted(specs_dir.iterdir())
        except OSError as exc:
            logger.warning("Error reading specs directory %s: %s", specs_dir, exc)
            return []

        for entry in entries:
            if not entry.is_dir() or entry.name == ".gitkeep":
                continue
            try:
                task = self._load_single_task(entry, location)
                if task:
                    tasks.append(task)
            except Exception as exc:
                logger.warning("Error loading spec %s: %s", entry.name, exc)

        return tasks

    def _load_single_task(self, spec_dir: Path, location: str) -> dict | None:
        """Load a single task from its spec directory."""
        dir_name = spec_dir.name

        # Read implementation plan
        plan = _safe_read_json(spec_dir / "implementation_plan.json")

        # Read requirements
        requirements = _safe_read_json(spec_dir / "requirements.json")

        # Read metadata
        metadata = _safe_read_json(spec_dir / "task_metadata.json")

        # Determine title (priority: plan.feature > plan.title > dir name)
        title = (plan or {}).get("feature") or (plan or {}).get("title") or dir_name

        # If title looks like a spec ID (e.g. "054-some-slug"), try spec.md heading
        if re.match(r"^\d{3}-", title):
            spec_heading = _extract_spec_heading(spec_dir / "spec.md")
            if spec_heading:
                title = spec_heading

        # Determine description (priority: plan.description > requirements.task_description > spec.md overview)
        description = ""
        if plan and plan.get("description"):
            description = plan["description"]
        if not description and requirements and requirements.get("task_description"):
            description = requirements["task_description"]
        if not description:
            overview = _extract_spec_overview(spec_dir / "spec.md")
            if overview:
                description = overview

        # Determine status
        status = "pending"
        if plan and plan.get("status"):
            raw_status = plan["status"]
            # Map frontend-style statuses to valid backend statuses
            status_map: dict[str, str] = {
                "pending": "pending",
                "backlog": "pending",
                "queue": "pending",
                "queued": "pending",
                "spec_creating": "spec_creating",
                "planning": "planning",
                "coding": "in_progress",
                "in_progress": "in_progress",
                "review": "qa_review",
                "ai_review": "qa_review",
                "qa_review": "qa_review",
                "qa_fixing": "qa_fixing",
                "human_review": "human_review",
                "completed": "done",
                "done": "done",
                "pr_created": "done",
                "error": "failed",
                "failed": "failed",
                "cancelled": "cancelled",
            }
            status = status_map.get(raw_status, "pending")

        # Extract subtasks from plan phases
        subtasks: list[dict] = []
        if plan and plan.get("phases"):
            for phase in plan["phases"]:
                items = phase.get("subtasks") or phase.get("chunks") or []
                for st in items:
                    subtasks.append(
                        {
                            "id": st.get("id", ""),
                            "title": st.get("description", ""),
                            "status": st.get("status", "pending"),
                        }
                    )

        # Build result
        created_at = (plan or {}).get("created_at", "")
        updated_at = (plan or {}).get("updated_at", "")

        return {
            "spec_id": dir_name,
            "title": title,
            "description": description,
            "status": status,
            "subtasks": subtasks,
            "metadata": metadata,
            "location": location,
            "specs_path": str(spec_dir),
            "has_spec": (spec_dir / "spec.md").exists(),
            "has_plan": (spec_dir / "implementation_plan.json").exists(),
            "has_qa_report": (spec_dir / "qa_report.md").exists(),
            "created_at": created_at,
            "updated_at": updated_at,
        }
