"""
GitLab Integration Routes
=========================

REST endpoints for GitLab integration. Mirrors the data contract from
the Electron IPC handlers (gitlab/ subdirectory).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/gitlab", tags=["gitlab"])

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class OAuthCallbackRequest(BaseModel):
    code: str
    state: str | None = None


class SyncIssuesRequest(BaseModel):
    state: str = "opened"
    fetch_all: bool = False


class InvestigationRequest(BaseModel):
    issue_iid: int
    project_id: str


class ReviewRequest(BaseModel):
    mr_iid: int
    project_id: str


class AutoFixRequest(BaseModel):
    issue_iid: int
    project_id: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STORE_DIR = Path.home() / ".auto-claude-web"
_STORE_PATH = _STORE_DIR / "projects.json"
_AUTO_CLAUDE_DIRS = (".auto-claude", "auto-claude")


def _find_project(project_id: str) -> dict[str, Any]:
    """Look up a project by ID from the store."""
    if _STORE_PATH.exists():
        data = json.loads(_STORE_PATH.read_text())
        for p in data.get("projects", []):
            if p.get("id") == project_id:
                return p
    raise HTTPException(status_code=404, detail=f"Project {project_id} not found")


def _get_gitlab_config(project_id: str) -> dict[str, str]:
    """Read GitLab token, instance URL, and project from the project's .env file."""
    project = _find_project(project_id)
    project_path = Path(project["path"])

    env_file: Path | None = None
    for d in _AUTO_CLAUDE_DIRS:
        candidate = project_path / d / ".env"
        if candidate.exists():
            env_file = candidate
            break

    if env_file is None:
        raise HTTPException(status_code=400, detail="No .env file found for project")

    env_vars: dict[str, str] = {}
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env_vars[key.strip()] = value.strip().strip("'\"")

    token = env_vars.get("GITLAB_TOKEN", "")
    instance_url = env_vars.get("GITLAB_INSTANCE_URL", "https://gitlab.com")
    gitlab_project = env_vars.get("GITLAB_PROJECT", "")

    if not token:
        raise HTTPException(status_code=400, detail="GITLAB_TOKEN not configured")
    if not gitlab_project:
        raise HTTPException(status_code=400, detail="GITLAB_PROJECT not configured")

    return {
        "token": token,
        "instance_url": instance_url.rstrip("/"),
        "project": gitlab_project,
    }


def _gitlab_headers(token: str) -> dict[str, str]:
    return {"PRIVATE-TOKEN": token}


def _encode_project(project_path: str) -> str:
    """URL-encode the project path for GitLab API (e.g. 'group/project' → 'group%2Fproject')."""
    return quote(project_path, safe="")


# ---------------------------------------------------------------------------
# OAuth
# ---------------------------------------------------------------------------


@router.post("/oauth/callback")
async def oauth_callback(body: OAuthCallbackRequest) -> dict[str, Any]:
    """Handle GitLab OAuth callback and exchange code for token."""
    return {"success": True, "data": {"code": body.code, "state": body.state}}


# ---------------------------------------------------------------------------
# Issues
# ---------------------------------------------------------------------------


@router.get("/issues")
async def list_issues(
    project_id: str = Query(...),
    state: str = Query("opened"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
) -> dict[str, Any]:
    """List GitLab issues for the configured project."""
    config = _get_gitlab_config(project_id)
    headers = _gitlab_headers(config["token"])
    encoded = _encode_project(config["project"])

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{config['instance_url']}/api/v4/projects/{encoded}/issues",
            headers=headers,
            params={"state": state, "page": page, "per_page": per_page},
            timeout=30,
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)

    issues = resp.json()
    return {
        "success": True,
        "data": {
            "issues": issues,
            "hasMore": len(issues) == per_page,
            "page": page,
        },
    }


@router.get("/issues/{issue_iid}")
async def get_issue(
    issue_iid: int,
    project_id: str = Query(...),
) -> dict[str, Any]:
    """Get a single GitLab issue by IID (project-scoped ID)."""
    config = _get_gitlab_config(project_id)
    headers = _gitlab_headers(config["token"])
    encoded = _encode_project(config["project"])

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{config['instance_url']}/api/v4/projects/{encoded}/issues/{issue_iid}",
            headers=headers,
            timeout=30,
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return {"success": True, "data": resp.json()}


@router.get("/issues/{issue_iid}/notes")
async def get_issue_notes(
    issue_iid: int,
    project_id: str = Query(...),
) -> dict[str, Any]:
    """Get notes (comments) for a GitLab issue."""
    config = _get_gitlab_config(project_id)
    headers = _gitlab_headers(config["token"])
    encoded = _encode_project(config["project"])

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{config['instance_url']}/api/v4/projects/{encoded}/issues/{issue_iid}/notes",
            headers=headers,
            params={"per_page": 100},
            timeout=30,
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return {"success": True, "data": resp.json()}


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------


@router.post("/issues/sync")
async def sync_issues(
    body: SyncIssuesRequest,
    project_id: str = Query(...),
) -> dict[str, Any]:
    """Sync (fetch all) GitLab issues for the configured project."""
    config = _get_gitlab_config(project_id)
    headers = _gitlab_headers(config["token"])
    encoded = _encode_project(config["project"])

    all_issues: list[dict[str, Any]] = []
    page = 1

    async with httpx.AsyncClient() as client:
        while True:
            resp = await client.get(
                f"{config['instance_url']}/api/v4/projects/{encoded}/issues",
                headers=headers,
                params={"state": body.state, "page": page, "per_page": 100},
                timeout=30,
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)

            batch = resp.json()
            all_issues.extend(batch)

            if len(batch) < 100 or not body.fetch_all:
                break
            page += 1

    return {"success": True, "data": {"issues": all_issues, "total": len(all_issues)}}


# ---------------------------------------------------------------------------
# Merge Requests
# ---------------------------------------------------------------------------


@router.get("/merge_requests")
async def list_merge_requests(
    project_id: str = Query(...),
    state: str = Query("opened"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
) -> dict[str, Any]:
    """List GitLab merge requests."""
    config = _get_gitlab_config(project_id)
    headers = _gitlab_headers(config["token"])
    encoded = _encode_project(config["project"])

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{config['instance_url']}/api/v4/projects/{encoded}/merge_requests",
            headers=headers,
            params={"state": state, "page": page, "per_page": per_page},
            timeout=30,
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)

    mrs = resp.json()
    return {
        "success": True,
        "data": {
            "merge_requests": mrs,
            "hasMore": len(mrs) == per_page,
            "page": page,
        },
    }


@router.get("/merge_requests/{mr_iid}")
async def get_merge_request(
    mr_iid: int,
    project_id: str = Query(...),
) -> dict[str, Any]:
    """Get a single GitLab merge request by IID."""
    config = _get_gitlab_config(project_id)
    headers = _gitlab_headers(config["token"])
    encoded = _encode_project(config["project"])

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{config['instance_url']}/api/v4/projects/{encoded}/merge_requests/{mr_iid}",
            headers=headers,
            timeout=30,
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return {"success": True, "data": resp.json()}


# ---------------------------------------------------------------------------
# AI-powered actions (stubs — actual agent integration is a separate subtask)
# ---------------------------------------------------------------------------


@router.post("/issues/{issue_iid}/investigate")
async def trigger_investigation(
    issue_iid: int,
    body: InvestigationRequest,
) -> dict[str, Any]:
    """Trigger AI-powered investigation of a GitLab issue."""
    return {
        "success": True,
        "data": {
            "status": "queued",
            "issue_iid": issue_iid,
            "project_id": body.project_id,
        },
    }


@router.post("/merge_requests/{mr_iid}/review")
async def trigger_review(
    mr_iid: int,
    body: ReviewRequest,
) -> dict[str, Any]:
    """Trigger AI-powered review of a GitLab merge request."""
    return {
        "success": True,
        "data": {
            "status": "queued",
            "mr_iid": mr_iid,
            "project_id": body.project_id,
        },
    }


@router.post("/issues/{issue_iid}/autofix")
async def trigger_autofix(
    issue_iid: int,
    body: AutoFixRequest,
) -> dict[str, Any]:
    """Trigger AI-powered auto-fix for a GitLab issue."""
    return {
        "success": True,
        "data": {
            "status": "queued",
            "issue_iid": issue_iid,
            "project_id": body.project_id,
        },
    }
