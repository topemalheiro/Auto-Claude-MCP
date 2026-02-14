"""
GitHub Integration Routes
=========================

REST endpoints for GitHub integration. Mirrors the data contract from
the Electron IPC handlers (github/ subdirectory).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/github", tags=["github"])

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class OAuthCallbackRequest(BaseModel):
    code: str
    state: str | None = None


class SyncIssuesRequest(BaseModel):
    state: str = "open"
    fetch_all: bool = False


class InvestigationRequest(BaseModel):
    issue_number: int
    project_id: str


class ReviewRequest(BaseModel):
    pr_number: int
    project_id: str


class AutoFixRequest(BaseModel):
    issue_number: int
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


def _get_github_config(project_id: str) -> dict[str, str]:
    """Read GitHub token and repo from the project's .env file."""
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

    token = env_vars.get("GITHUB_TOKEN", "")
    repo = env_vars.get("GITHUB_REPO", "")
    if not token:
        raise HTTPException(status_code=400, detail="GITHUB_TOKEN not configured")
    if not repo:
        raise HTTPException(status_code=400, detail="GITHUB_REPO not configured")

    return {"token": token, "repo": repo}


def _github_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


_GITHUB_API = "https://api.github.com"


# ---------------------------------------------------------------------------
# OAuth
# ---------------------------------------------------------------------------


@router.post("/oauth/callback")
async def oauth_callback(body: OAuthCallbackRequest) -> dict[str, Any]:
    """Handle GitHub OAuth callback and exchange code for token."""
    return {"success": True, "data": {"code": body.code, "state": body.state}}


# ---------------------------------------------------------------------------
# Issues
# ---------------------------------------------------------------------------


@router.get("/issues")
async def list_issues(
    project_id: str = Query(...),
    state: str = Query("open"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
) -> dict[str, Any]:
    """List GitHub issues for the configured repository."""
    config = _get_github_config(project_id)
    headers = _github_headers(config["token"])

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{_GITHUB_API}/repos/{config['repo']}/issues",
            headers=headers,
            params={"state": state, "page": page, "per_page": per_page},
            timeout=30,
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)

        issues = resp.json()
        # Filter out pull requests (GitHub returns PRs in issues endpoint)
        issues = [i for i in issues if "pull_request" not in i]

    return {
        "success": True,
        "data": {
            "issues": issues,
            "hasMore": len(issues) == per_page,
            "page": page,
        },
    }


@router.get("/issues/{issue_number}")
async def get_issue(
    issue_number: int,
    project_id: str = Query(...),
) -> dict[str, Any]:
    """Get a single GitHub issue by number."""
    config = _get_github_config(project_id)
    headers = _github_headers(config["token"])

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{_GITHUB_API}/repos/{config['repo']}/issues/{issue_number}",
            headers=headers,
            timeout=30,
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return {"success": True, "data": resp.json()}


@router.get("/issues/{issue_number}/comments")
async def get_issue_comments(
    issue_number: int,
    project_id: str = Query(...),
) -> dict[str, Any]:
    """Get comments for a GitHub issue."""
    config = _get_github_config(project_id)
    headers = _github_headers(config["token"])

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{_GITHUB_API}/repos/{config['repo']}/issues/{issue_number}/comments",
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
    """Sync (fetch all) GitHub issues for the configured repository."""
    config = _get_github_config(project_id)
    headers = _github_headers(config["token"])

    all_issues: list[dict[str, Any]] = []
    page = 1

    async with httpx.AsyncClient() as client:
        while True:
            resp = await client.get(
                f"{_GITHUB_API}/repos/{config['repo']}/issues",
                headers=headers,
                params={"state": body.state, "page": page, "per_page": 100},
                timeout=30,
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)

            batch = resp.json()
            # Filter out pull requests
            batch = [i for i in batch if "pull_request" not in i]
            all_issues.extend(batch)

            if len(batch) < 100 or not body.fetch_all:
                break
            page += 1

    return {"success": True, "data": {"issues": all_issues, "total": len(all_issues)}}


# ---------------------------------------------------------------------------
# Pull Requests
# ---------------------------------------------------------------------------


@router.get("/pulls")
async def list_pulls(
    project_id: str = Query(...),
    state: str = Query("open"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
) -> dict[str, Any]:
    """List GitHub pull requests."""
    config = _get_github_config(project_id)
    headers = _github_headers(config["token"])

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{_GITHUB_API}/repos/{config['repo']}/pulls",
            headers=headers,
            params={"state": state, "page": page, "per_page": per_page},
            timeout=30,
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)

    pulls = resp.json()
    return {
        "success": True,
        "data": {
            "pulls": pulls,
            "hasMore": len(pulls) == per_page,
            "page": page,
        },
    }


@router.get("/pulls/{pr_number}")
async def get_pull(
    pr_number: int,
    project_id: str = Query(...),
) -> dict[str, Any]:
    """Get a single GitHub pull request by number."""
    config = _get_github_config(project_id)
    headers = _github_headers(config["token"])

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{_GITHUB_API}/repos/{config['repo']}/pulls/{pr_number}",
            headers=headers,
            timeout=30,
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return {"success": True, "data": resp.json()}


# ---------------------------------------------------------------------------
# AI-powered actions (stubs — actual agent integration is a separate subtask)
# ---------------------------------------------------------------------------


@router.post("/issues/{issue_number}/investigate")
async def trigger_investigation(
    issue_number: int,
    body: InvestigationRequest,
) -> dict[str, Any]:
    """Trigger AI-powered investigation of a GitHub issue."""
    # Agent integration will be wired in a later subtask
    return {
        "success": True,
        "data": {
            "status": "queued",
            "issue_number": issue_number,
            "project_id": body.project_id,
        },
    }


@router.post("/pulls/{pr_number}/review")
async def trigger_review(
    pr_number: int,
    body: ReviewRequest,
) -> dict[str, Any]:
    """Trigger AI-powered review of a GitHub pull request."""
    return {
        "success": True,
        "data": {
            "status": "queued",
            "pr_number": pr_number,
            "project_id": body.project_id,
        },
    }


@router.post("/issues/{issue_number}/autofix")
async def trigger_autofix(
    issue_number: int,
    body: AutoFixRequest,
) -> dict[str, Any]:
    """Trigger AI-powered auto-fix for a GitHub issue."""
    return {
        "success": True,
        "data": {
            "status": "queued",
            "issue_number": issue_number,
            "project_id": body.project_id,
        },
    }
