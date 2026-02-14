"""
Project Routes
==============

REST endpoints for project management. Mirrors the data contract from
the Electron IPC handlers (project-handlers.ts / project-store.ts).
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/projects", tags=["projects"])

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class NotificationSettings(BaseModel):
    onTaskComplete: bool = True
    onTaskFailed: bool = True
    onReviewNeeded: bool = True
    sound: bool = True


class ProjectSettings(BaseModel):
    model: str = "claude-sonnet-4-20250514"
    memoryBackend: str = "file"
    linearSync: bool = False
    linearTeamId: str | None = None
    notifications: NotificationSettings = Field(default_factory=NotificationSettings)
    graphitiMcpEnabled: bool = False
    graphitiMcpUrl: str | None = None
    mainBranch: str | None = None
    useClaudeMd: bool | None = None
    maxParallelTasks: int | None = None


class Project(BaseModel):
    id: str
    name: str
    path: str
    autoBuildPath: str
    settings: ProjectSettings
    createdAt: str
    updatedAt: str


class AddProjectRequest(BaseModel):
    path: str
    name: str | None = None


# ---------------------------------------------------------------------------
# Store — JSON-file-backed project list
# ---------------------------------------------------------------------------

_AUTO_CLAUDE_DIRS = (".auto-claude", "auto-claude")
_STORE_DIR = Path.home() / ".auto-claude-web"
_STORE_PATH = _STORE_DIR / "projects.json"


def _load_store() -> dict[str, Any]:
    """Load the projects store from disk."""
    if _STORE_PATH.exists():
        try:
            return json.loads(_STORE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"projects": [], "settings": {}}


def _save_store(data: dict[str, Any]) -> None:
    """Persist the projects store to disk."""
    _STORE_DIR.mkdir(parents=True, exist_ok=True)
    _STORE_PATH.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def _get_auto_build_path(project_path: str) -> str:
    """Detect the .auto-claude directory inside a project, if any."""
    for dirname in _AUTO_CLAUDE_DIRS:
        candidate = os.path.join(project_path, dirname)
        if os.path.isdir(candidate):
            return dirname
    return ""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("")
async def list_projects() -> dict[str, Any]:
    """List all registered projects.

    Validates that .auto-claude folders still exist; resets autoBuildPath
    for any project whose folder was removed so the UI can prompt for
    re-initialisation.
    """
    store = _load_store()
    projects: list[dict[str, Any]] = store.get("projects", [])

    changed = False
    for project in projects:
        if project.get("autoBuildPath"):
            full = os.path.join(project["path"], project["autoBuildPath"])
            if not os.path.isdir(full):
                project["autoBuildPath"] = ""
                project["updatedAt"] = _now_iso()
                changed = True

    if changed:
        _save_store(store)

    return {"success": True, "data": projects}


@router.post("")
async def add_project(body: AddProjectRequest) -> dict[str, Any]:
    """Register a new project by filesystem path.

    If the project path is already registered the existing record is returned.
    """
    project_path = os.path.abspath(body.path)

    if not os.path.isdir(project_path):
        raise HTTPException(status_code=400, detail="Directory does not exist")

    store = _load_store()
    projects: list[dict[str, Any]] = store.get("projects", [])

    # Return existing project if path already registered
    for project in projects:
        if project["path"] == project_path:
            return {"success": True, "data": project}

    name = body.name or os.path.basename(project_path)
    auto_build_path = _get_auto_build_path(project_path)
    now = _now_iso()

    new_project: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "name": name,
        "path": project_path,
        "autoBuildPath": auto_build_path,
        "settings": ProjectSettings().model_dump(),
        "createdAt": now,
        "updatedAt": now,
    }

    projects.append(new_project)
    store["projects"] = projects
    _save_store(store)

    return {"success": True, "data": new_project}


@router.get("/{project_id}")
async def get_project(project_id: str) -> dict[str, Any]:
    """Get a single project by ID, including its settings."""
    store = _load_store()
    projects: list[dict[str, Any]] = store.get("projects", [])

    for project in projects:
        if project["id"] == project_id:
            # Validate autoBuildPath still exists
            if project.get("autoBuildPath"):
                full = os.path.join(project["path"], project["autoBuildPath"])
                if not os.path.isdir(full):
                    project["autoBuildPath"] = ""
                    project["updatedAt"] = _now_iso()
                    _save_store(store)
            return {"success": True, "data": project}

    raise HTTPException(status_code=404, detail="Project not found")
