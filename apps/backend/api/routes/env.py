"""
Environment Routes
===================

REST endpoints for per-project environment configuration (.env files).
Mirrors the data contract from the Electron IPC handlers (env-handlers.ts).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/projects", tags=["environment"])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STORE_DIR = Path.home() / ".auto-claude-web"
_STORE_PATH = _STORE_DIR / "projects.json"
_AUTO_CLAUDE_DIRS = (".auto-claude", "auto-claude")


def _find_project(project_id: str) -> dict[str, Any]:
    """Look up a project by ID from the store."""
    if _STORE_PATH.exists():
        try:
            store = json.loads(_STORE_PATH.read_text(encoding="utf-8"))
            for project in store.get("projects", []):
                if project["id"] == project_id:
                    return project
        except (json.JSONDecodeError, OSError):
            pass
    raise HTTPException(status_code=404, detail="Project not found")


def _env_path(project: dict[str, Any]) -> Path:
    """Resolve the .env file path for a project."""
    project_path = project["path"]
    auto_build = project.get("autoBuildPath", "")
    if auto_build:
        return Path(project_path) / auto_build / ".env"
    # Fallback: check known auto-claude directories
    for dirname in _AUTO_CLAUDE_DIRS:
        candidate = Path(project_path) / dirname
        if candidate.is_dir():
            return candidate / ".env"
    # Default to .auto-claude
    return Path(project_path) / ".auto-claude" / ".env"


def _parse_env_file(content: str) -> dict[str, str]:
    """Parse a .env file into a key-value dict (ignores comments/blanks)."""
    result: dict[str, str] = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            result[key.strip()] = value.strip()
    return result


def _env_to_config(env_vars: dict[str, str]) -> dict[str, Any]:
    """Map .env variables to a ProjectEnvConfig-style dict."""
    config: dict[str, Any] = {}
    _map = {
        "CLAUDE_CODE_OAUTH_TOKEN": "claudeOAuthToken",
        "AUTO_BUILD_MODEL": "autoBuildModel",
        "LINEAR_API_KEY": "linearApiKey",
        "LINEAR_TEAM_ID": "linearTeamId",
        "LINEAR_PROJECT_ID": "linearProjectId",
        "GITHUB_TOKEN": "githubToken",
        "GITHUB_REPO": "githubRepo",
        "DEFAULT_BRANCH": "defaultBranch",
        "OPENAI_API_KEY": "openaiApiKey",
        "GITLAB_TOKEN": "gitlabToken",
        "GITLAB_INSTANCE_URL": "gitlabInstanceUrl",
        "GITLAB_PROJECT": "gitlabProject",
    }
    for env_key, config_key in _map.items():
        if env_key in env_vars:
            config[config_key] = env_vars[env_key]

    # Boolean fields
    _bool_map = {
        "LINEAR_REALTIME_SYNC": "linearRealtimeSync",
        "GITHUB_AUTO_SYNC": "githubAutoSync",
        "GRAPHITI_ENABLED": "graphitiEnabled",
        "GITLAB_ENABLED": "gitlabEnabled",
        "GITLAB_AUTO_SYNC": "gitlabAutoSync",
        "ENABLE_FANCY_UI": "enableFancyUi",
    }
    for env_key, config_key in _bool_map.items():
        if env_key in env_vars:
            config[config_key] = env_vars[env_key].lower() == "true"

    return config


def _config_to_env_lines(config: dict[str, Any]) -> dict[str, str]:
    """Map a ProjectEnvConfig-style dict back to env key-value pairs."""
    env_vars: dict[str, str] = {}
    _map = {
        "claudeOAuthToken": "CLAUDE_CODE_OAUTH_TOKEN",
        "autoBuildModel": "AUTO_BUILD_MODEL",
        "linearApiKey": "LINEAR_API_KEY",
        "linearTeamId": "LINEAR_TEAM_ID",
        "linearProjectId": "LINEAR_PROJECT_ID",
        "githubToken": "GITHUB_TOKEN",
        "githubRepo": "GITHUB_REPO",
        "defaultBranch": "DEFAULT_BRANCH",
        "openaiApiKey": "OPENAI_API_KEY",
        "gitlabToken": "GITLAB_TOKEN",
        "gitlabInstanceUrl": "GITLAB_INSTANCE_URL",
        "gitlabProject": "GITLAB_PROJECT",
    }
    _bool_map = {
        "linearRealtimeSync": "LINEAR_REALTIME_SYNC",
        "githubAutoSync": "GITHUB_AUTO_SYNC",
        "graphitiEnabled": "GRAPHITI_ENABLED",
        "gitlabEnabled": "GITLAB_ENABLED",
        "gitlabAutoSync": "GITLAB_AUTO_SYNC",
        "enableFancyUi": "ENABLE_FANCY_UI",
    }
    for config_key, env_key in _map.items():
        if config_key in config and config[config_key] is not None:
            env_vars[env_key] = str(config[config_key])
    for config_key, env_key in _bool_map.items():
        if config_key in config and config[config_key] is not None:
            env_vars[env_key] = "true" if config[config_key] else "false"
    return env_vars


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class EnvConfigUpdate(BaseModel):
    """Partial env config update — all fields optional."""

    model_config = {"extra": "allow"}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/{project_id}/env")
async def get_env(project_id: str) -> dict[str, Any]:
    """Read a project's environment configuration from its .env file."""
    project = _find_project(project_id)
    env_file = _env_path(project)

    if not env_file.exists():
        return {"success": True, "data": {}}

    try:
        content = env_file.read_text(encoding="utf-8")
        env_vars = _parse_env_file(content)
        config = _env_to_config(env_vars)
        return {"success": True, "data": config}
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read .env: {exc}")


@router.put("/{project_id}/env")
async def update_env(project_id: str, body: EnvConfigUpdate) -> dict[str, Any]:
    """Save a project's environment configuration to its .env file."""
    project = _find_project(project_id)
    env_file = _env_path(project)

    # Load existing env vars
    existing_vars: dict[str, str] = {}
    if env_file.exists():
        try:
            existing_vars = _parse_env_file(env_file.read_text(encoding="utf-8"))
        except OSError:
            pass

    # Merge new values
    new_vars = _config_to_env_lines(body.model_dump(exclude_unset=True))
    existing_vars.update(new_vars)

    # Write back
    try:
        env_file.parent.mkdir(parents=True, exist_ok=True)
        lines = [f"{k}={v}" for k, v in sorted(existing_vars.items())]
        env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to write .env: {exc}")

    config = _env_to_config(existing_vars)
    return {"success": True, "data": config}
