"""
Project Management Tools
=========================

MCP tools for managing the active project: switching projects,
getting status, listing specs, and reading the project index.
"""

from __future__ import annotations

import logging

from mcp_server import config
from mcp_server.server import mcp

logger = logging.getLogger(__name__)


@mcp.tool()
def project_set_active(project_dir: str) -> dict:
    """Switch the MCP server to a different project directory.

    Re-initializes the server to point at a new project.
    All subsequent tool calls will operate on this project.

    Args:
        project_dir: Absolute path to the project directory
    """
    try:
        config.initialize(project_dir)
        project_path = config.get_project_dir()
        initialized = config.is_initialized()

        return {
            "success": True,
            "project_dir": str(project_path),
            "initialized": initialized,
            "message": f"Active project set to {project_path}",
        }
    except (ValueError, RuntimeError) as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
def project_get_status() -> dict:
    """Get the current project status.

    Returns the active project directory, initialization state,
    specs count, and project index summary.
    """
    try:
        project_dir = config.get_project_dir()
    except RuntimeError:
        return {
            "initialized": False,
            "error": "No project set. Use project_set_active() first.",
        }

    initialized = config.is_initialized()
    specs_count = 0

    if initialized:
        specs_dir = config.get_specs_dir()
        if specs_dir.is_dir():
            specs_count = sum(
                1
                for entry in specs_dir.iterdir()
                if entry.is_dir() and entry.name != ".gitkeep"
            )

    index = config.get_project_index()

    return {
        "project_dir": str(project_dir),
        "initialized": initialized,
        "specs_count": specs_count,
        "has_project_index": bool(index),
        "project_name": index.get("name", project_dir.name),
    }


@mcp.tool()
def project_list_specs() -> dict:
    """List all spec directories with their basic info.

    Returns each spec's name, whether it has a plan/spec file,
    and status from the implementation plan.
    """
    try:
        specs_dir = config.get_specs_dir()
    except RuntimeError:
        return {"error": "No project set. Use project_set_active() first.", "specs": []}

    if not specs_dir.is_dir():
        return {"specs": [], "message": "No specs directory found."}

    specs: list[dict] = []
    for entry in sorted(specs_dir.iterdir()):
        if not entry.is_dir() or entry.name == ".gitkeep":
            continue

        has_plan = (entry / "implementation_plan.json").exists()
        has_spec = (entry / "spec.md").exists()

        status = "pending"
        title = entry.name
        if has_plan:
            try:
                import json

                plan = json.loads(
                    (entry / "implementation_plan.json").read_text(encoding="utf-8")
                )
                status = plan.get("status", "pending")
                title = plan.get("feature") or plan.get("title") or entry.name
            except (json.JSONDecodeError, OSError):
                pass

        specs.append(
            {
                "name": entry.name,
                "title": title,
                "has_plan": has_plan,
                "has_spec": has_spec,
                "has_qa_report": (entry / "qa_report.md").exists(),
                "status": status,
            }
        )

    return {"specs": specs, "count": len(specs)}


@mcp.tool()
def project_get_index() -> dict:
    """Return the full project_index.json content.

    The project index contains metadata about the project
    such as file summaries, dependency info, and analysis results.
    """
    try:
        index = config.get_project_index()
    except RuntimeError:
        return {"error": "No project set. Use project_set_active() first."}

    if not index:
        return {"message": "No project index found. Run indexing first.", "index": {}}

    return {"index": index}
