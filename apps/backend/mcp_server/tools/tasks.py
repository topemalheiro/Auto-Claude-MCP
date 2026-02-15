"""
Task Management Tools
======================

MCP tools for CRUD operations on tasks (specs).
Tasks are stored as spec directories under .auto-claude/specs/.
"""

from __future__ import annotations

import logging

from mcp_server import config
from mcp_server.server import mcp
from mcp_server.services.task_service import VALID_STATUSES, TaskService

logger = logging.getLogger(__name__)


def _get_task_service() -> TaskService:
    """Get a TaskService instance for the active project."""
    return TaskService(config.get_project_dir())


@mcp.tool()
def task_list() -> dict:
    """List all tasks with id, title, status, and description preview.

    Scans both the main project and worktree spec directories,
    deduplicating with main project taking priority.
    """
    try:
        service = _get_task_service()
    except RuntimeError as exc:
        return {"error": str(exc), "tasks": []}

    tasks = service.list_tasks()

    # Return a concise view for listing
    summary = []
    for t in tasks:
        desc = t.get("description", "")
        preview = (desc[:200] + "...") if len(desc) > 200 else desc
        summary.append(
            {
                "spec_id": t["spec_id"],
                "title": t["title"],
                "status": t["status"],
                "description_preview": preview,
                "has_spec": t.get("has_spec", False),
                "has_plan": t.get("has_plan", False),
                "subtask_count": len(t.get("subtasks", [])),
            }
        )

    return {"tasks": summary, "count": len(summary)}


@mcp.tool()
def task_create(title: str, description: str) -> dict:
    """Create a new task (spec directory) with initial files.

    Generates the next spec number automatically and creates
    the directory with requirements.json, implementation_plan.json,
    and task_metadata.json.

    Args:
        title: The task title (used for the directory name slug)
        description: Full description of what needs to be done
    """
    try:
        service = _get_task_service()
    except RuntimeError as exc:
        return {"error": str(exc)}

    if not title or not title.strip():
        return {"error": "Title is required"}
    if not description or not description.strip():
        return {"error": "Description is required"}

    task = service.create_task(title.strip(), description.strip())
    return {"success": True, "task": task}


@mcp.tool()
def task_get(spec_id: str) -> dict:
    """Get full task details including subtasks, metadata, and file info.

    Args:
        spec_id: The spec directory name (e.g., "001-my-feature")
    """
    try:
        service = _get_task_service()
    except RuntimeError as exc:
        return {"error": str(exc)}

    task = service.get_task(spec_id)
    if task is None:
        return {"error": f"Task '{spec_id}' not found"}

    return {"task": task}


@mcp.tool()
def task_update(
    spec_id: str,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
) -> dict:
    """Update task metadata (title, description, and/or status).

    Args:
        spec_id: The spec directory name (e.g., "001-my-feature")
        title: New title (optional)
        description: New description (optional)
        status: New status (optional) - must be a valid status
    """
    try:
        service = _get_task_service()
    except RuntimeError as exc:
        return {"error": str(exc)}

    if status is not None and status not in VALID_STATUSES:
        return {"error": f"Invalid status '{status}'. Valid: {sorted(VALID_STATUSES)}"}

    task = service.update_task(
        spec_id, title=title, description=description, status=status
    )
    if task is None:
        return {"error": f"Task '{spec_id}' not found or invalid update"}

    return {"success": True, "task": task}


@mcp.tool()
def task_delete(spec_id: str) -> dict:
    """Delete a task by removing its spec directory.

    WARNING: This permanently deletes the spec directory and all its contents.

    Args:
        spec_id: The spec directory name (e.g., "001-my-feature")
    """
    try:
        service = _get_task_service()
    except RuntimeError as exc:
        return {"error": str(exc)}

    deleted = service.delete_task(spec_id)
    if not deleted:
        return {"error": f"Task '{spec_id}' not found"}

    return {"success": True, "message": f"Task '{spec_id}' deleted"}


@mcp.tool()
def task_update_status(spec_id: str, status: str) -> dict:
    """Update just the status field of a task.

    Args:
        spec_id: The spec directory name (e.g., "001-my-feature")
        status: New status value. Valid statuses: pending, spec_creating,
                planning, in_progress, qa_review, qa_fixing, human_review,
                done, failed, cancelled
    """
    try:
        service = _get_task_service()
    except RuntimeError as exc:
        return {"error": str(exc)}

    if status not in VALID_STATUSES:
        return {"error": f"Invalid status '{status}'. Valid: {sorted(VALID_STATUSES)}"}

    task = service.update_status(spec_id, status)
    if task is None:
        return {"error": f"Task '{spec_id}' not found"}

    return {"success": True, "task": task}
