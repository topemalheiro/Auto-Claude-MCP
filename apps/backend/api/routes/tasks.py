"""
Task Routes
===========

REST endpoints for task/spec management. Mirrors the data contract from
the Electron IPC handlers (task/crud-handlers.ts).
"""

from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .projects import _load_store

router = APIRouter(prefix="/api", tags=["tasks"])

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_AUTO_CLAUDE_DIRS = (".auto-claude", "auto-claude")
_IMPLEMENTATION_PLAN = "implementation_plan.json"
_REQUIREMENTS = "requirements.json"
_TASK_METADATA = "task_metadata.json"
_SPEC_FILE = "spec.md"


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class TaskMetadata(BaseModel):
    sourceType: str = "manual"
    category: str | None = None
    attachedImages: list[dict[str, Any]] | None = None
    baseBranch: str | None = None
    thinkingLevel: str = "medium"
    fastMode: bool = False


class CreateTaskRequest(BaseModel):
    title: str = ""
    description: str
    metadata: TaskMetadata | None = None


class UpdateStatusRequest(BaseModel):
    status: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _find_project(project_id: str) -> dict[str, Any]:
    """Look up a project by ID from the store."""
    store = _load_store()
    for project in store.get("projects", []):
        if project["id"] == project_id:
            return project
    raise HTTPException(status_code=404, detail="Project not found")


def _specs_dir(project: dict[str, Any]) -> Path:
    """Return the specs directory for a project."""
    project_path = project["path"]
    auto_build = project.get("autoBuildPath", "")
    if not auto_build:
        for dirname in _AUTO_CLAUDE_DIRS:
            candidate = os.path.join(project_path, dirname)
            if os.path.isdir(candidate):
                auto_build = dirname
                break
    if not auto_build:
        raise HTTPException(
            status_code=400,
            detail="Project has no .auto-claude directory",
        )
    return Path(project_path) / auto_build / "specs"


def _slugify(text: str) -> str:
    """Convert text into a URL-friendly slug."""
    slug = text.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug[:50]


def _read_json(filepath: Path) -> dict[str, Any] | None:
    """Read a JSON file, returning None if it doesn't exist or is invalid."""
    if not filepath.exists():
        return None
    try:
        return json.loads(filepath.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _build_task(
    spec_folder: Path,
    project_id: str,
    include_subtasks: bool = False,
) -> dict[str, Any]:
    """Build a task dict from a spec folder on disk."""
    folder_name = spec_folder.name
    parts = folder_name.split("-", 1)
    spec_number = parts[0] if parts[0].isdigit() else "0"
    spec_name = parts[1] if len(parts) > 1 else folder_name

    plan = _read_json(spec_folder / _IMPLEMENTATION_PLAN)
    metadata = _read_json(spec_folder / _TASK_METADATA)
    requirements = _read_json(spec_folder / _REQUIREMENTS)

    # Determine title and description
    title = (plan or {}).get("feature", spec_name)
    description = (plan or {}).get(
        "description",
        (requirements or {}).get("task_description", ""),
    )

    # Determine status
    status = "backlog"
    progress = "0/0"
    subtasks: list[dict[str, Any]] = []

    if plan:
        plan_status = plan.get("status", "pending")
        status_map = {
            "pending": "backlog",
            "in_progress": "in_progress",
            "review": "human_review",
            "completed": "done",
        }
        status = status_map.get(plan_status, plan_status)

        # Count subtasks
        completed = 0
        total = 0
        for phase in plan.get("phases", []):
            for st in phase.get("subtasks", []):
                total += 1
                if st.get("status") == "completed":
                    completed += 1
                if include_subtasks:
                    subtasks.append(st)
        progress = f"{completed}/{total}"

    created_at = (plan or {}).get("created_at", "")
    updated_at = (plan or {}).get("updated_at", "")

    task: dict[str, Any] = {
        "id": folder_name,
        "specId": folder_name,
        "projectId": project_id,
        "title": title,
        "description": description,
        "status": status,
        "progress": progress,
        "metadata": metadata or TaskMetadata().model_dump(),
        "createdAt": created_at,
        "updatedAt": updated_at,
    }

    if include_subtasks:
        task["subtasks"] = subtasks

    return task


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/projects/{project_id}/tasks")
async def list_tasks(project_id: str) -> dict[str, Any]:
    """List all tasks/specs for a project."""
    project = _find_project(project_id)
    specs_path = _specs_dir(project)

    tasks: list[dict[str, Any]] = []
    if not specs_path.exists():
        return {"success": True, "data": tasks}

    for spec_folder in sorted(specs_path.iterdir()):
        if not spec_folder.is_dir():
            continue
        # Must have a valid spec structure (implementation_plan or spec.md)
        if (
            not (spec_folder / _IMPLEMENTATION_PLAN).exists()
            and not (spec_folder / _SPEC_FILE).exists()
        ):
            continue
        tasks.append(_build_task(spec_folder, project_id))

    return {"success": True, "data": tasks}


@router.post("/projects/{project_id}/tasks")
async def create_task(project_id: str, body: CreateTaskRequest) -> dict[str, Any]:
    """Create a new task/spec for a project."""
    project = _find_project(project_id)
    specs_path = _specs_dir(project)

    # Determine title
    title = body.title.strip() if body.title else ""
    if not title:
        # Fallback: first line of description, max 60 chars
        title = body.description.split("\n")[0][:60]
        if len(title) == 60:
            title += "..."

    # Find next spec number
    spec_number = 1
    if specs_path.exists():
        existing_numbers = []
        for d in specs_path.iterdir():
            if d.is_dir():
                match = re.match(r"^(\d+)", d.name)
                if match:
                    existing_numbers.append(int(match.group(1)))
        if existing_numbers:
            spec_number = max(existing_numbers) + 1

    spec_id = f"{spec_number:03d}-{_slugify(title)}"
    spec_dir = specs_path / spec_id
    spec_dir.mkdir(parents=True, exist_ok=True)

    now = _now_iso()

    # Create implementation_plan.json
    plan = {
        "feature": title,
        "description": body.description,
        "created_at": now,
        "updated_at": now,
        "status": "pending",
        "phases": [],
    }
    (spec_dir / _IMPLEMENTATION_PLAN).write_text(
        json.dumps(plan, indent=2), encoding="utf-8"
    )

    # Create requirements.json
    meta = body.metadata or TaskMetadata()
    requirements = {
        "task_description": body.description,
        "workflow_type": meta.category or "feature",
    }
    (spec_dir / _REQUIREMENTS).write_text(
        json.dumps(requirements, indent=2), encoding="utf-8"
    )

    # Save task metadata
    (spec_dir / _TASK_METADATA).write_text(
        json.dumps(meta.model_dump(), indent=2), encoding="utf-8"
    )

    task = {
        "id": spec_id,
        "specId": spec_id,
        "projectId": project_id,
        "title": title,
        "description": body.description,
        "status": "backlog",
        "progress": "0/0",
        "subtasks": [],
        "metadata": meta.model_dump(),
        "createdAt": now,
        "updatedAt": now,
    }

    return {"success": True, "data": task}


@router.get("/tasks/{task_id}")
async def get_task(task_id: str, project_id: str) -> dict[str, Any]:
    """Get task detail with subtasks.

    Requires project_id as a query parameter to locate the spec on disk.
    """
    project = _find_project(project_id)
    specs_path = _specs_dir(project)
    spec_folder = specs_path / task_id

    if not spec_folder.exists() or not spec_folder.is_dir():
        raise HTTPException(status_code=404, detail="Task not found")

    task = _build_task(spec_folder, project_id, include_subtasks=True)
    return {"success": True, "data": task}


@router.put("/tasks/{task_id}/status")
async def update_task_status(
    task_id: str, body: UpdateStatusRequest, project_id: str
) -> dict[str, Any]:
    """Update a task's status.

    Requires project_id as a query parameter.
    """
    project = _find_project(project_id)
    specs_path = _specs_dir(project)
    spec_folder = specs_path / task_id

    if not spec_folder.exists() or not spec_folder.is_dir():
        raise HTTPException(status_code=404, detail="Task not found")

    plan_path = spec_folder / _IMPLEMENTATION_PLAN
    plan = _read_json(plan_path)
    if plan is None:
        plan = {"feature": task_id, "status": "pending", "phases": []}

    # Map REST status back to plan status
    reverse_status_map = {
        "backlog": "pending",
        "in_progress": "in_progress",
        "human_review": "review",
        "done": "completed",
    }
    plan["status"] = reverse_status_map.get(body.status, body.status)
    plan["updated_at"] = _now_iso()

    plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")

    task = _build_task(spec_folder, project_id)
    return {"success": True, "data": task}


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, project_id: str) -> dict[str, Any]:
    """Delete a task/spec.

    Requires project_id as a query parameter.
    """
    project = _find_project(project_id)
    specs_path = _specs_dir(project)
    spec_folder = specs_path / task_id

    if not spec_folder.exists() or not spec_folder.is_dir():
        raise HTTPException(status_code=404, detail="Task not found")

    shutil.rmtree(spec_folder)

    return {"success": True, "data": {"id": task_id, "deleted": True}}
