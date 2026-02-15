"""
GitHub Service
==============

Wraps the backend GitHubOrchestrator for MCP tool access.
Handles repo detection, config creation, and result serialization.
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class GitHubService:
    """Service layer for GitHub automation features."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.github_dir = project_dir / ".auto-claude" / "github"

    def _detect_repo(self) -> str | None:
        """Detect owner/repo from git remote origin."""
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                cwd=str(self.project_dir),
                timeout=10,
            )
            if result.returncode != 0:
                return None

            url = result.stdout.strip()
            # Handle SSH: git@github.com:owner/repo.git
            if url.startswith("git@"):
                parts = url.split(":")[-1]
                return parts.removesuffix(".git")
            # Handle HTTPS: https://github.com/owner/repo.git
            if "github.com" in url:
                parts = url.split("github.com/")[-1]
                return parts.removesuffix(".git")
            return None
        except Exception as e:
            logger.warning("Failed to detect repo from git remote: %s", e)
            return None

    def _get_repo(self, repo: str | None) -> str:
        """Get repo string, falling back to auto-detection."""
        if repo:
            return repo
        detected = self._detect_repo()
        if not detected:
            raise ValueError(
                "Could not detect repository. Provide 'repo' parameter "
                "in owner/repo format, or ensure a GitHub remote is configured."
            )
        return detected

    def _create_config(self, repo: str, model: str = "sonnet"):
        """Create a GitHubRunnerConfig with sensible defaults."""
        # Get GitHub token from environment
        import os

        from runners.github.models import GitHubRunnerConfig

        token = os.environ.get("GITHUB_TOKEN", "")
        if not token:
            # Try gh CLI auth token
            try:
                result = subprocess.run(
                    ["gh", "auth", "token"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    token = result.stdout.strip()
            except Exception:
                pass

        return GitHubRunnerConfig(
            token=token,
            repo=repo,
            model=model,
            thinking_level="medium",
            pr_review_enabled=True,
            triage_enabled=True,
        )

    async def review_pr(
        self, pr_number: int, repo: str | None = None, model: str = "sonnet"
    ) -> dict:
        """Review a pull request with AI."""
        try:
            from runners.github.orchestrator import GitHubOrchestrator

            resolved_repo = self._get_repo(repo)
            config = self._create_config(resolved_repo, model)
            orchestrator = GitHubOrchestrator(
                project_dir=self.project_dir, config=config
            )
            result = await orchestrator.review_pr(pr_number)
            return {"success": True, "data": result.to_dict()}
        except ImportError:
            return {"error": "GitHub runner module not available"}
        except Exception as e:
            return {"error": str(e)}

    async def list_issues(
        self, state: str = "open", limit: int = 30, repo: str | None = None
    ) -> dict:
        """List GitHub issues using gh CLI."""
        try:
            resolved_repo = self._get_repo(repo)
            cmd = [
                "gh",
                "issue",
                "list",
                "--repo",
                resolved_repo,
                "--state",
                state,
                "--limit",
                str(limit),
                "--json",
                "number,title,state,labels,author,createdAt,updatedAt",
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.project_dir),
                timeout=30,
            )
            if result.returncode != 0:
                return {"error": f"gh CLI failed: {result.stderr.strip()}"}
            issues = json.loads(result.stdout)
            return {"success": True, "issues": issues, "count": len(issues)}
        except Exception as e:
            return {"error": str(e)}

    async def auto_fix_issue(self, issue_number: int, repo: str | None = None) -> dict:
        """Auto-fix a GitHub issue."""
        try:
            from runners.github.orchestrator import GitHubOrchestrator

            resolved_repo = self._get_repo(repo)
            config = self._create_config(resolved_repo)
            config.auto_fix_enabled = True
            orchestrator = GitHubOrchestrator(
                project_dir=self.project_dir, config=config
            )
            state = await orchestrator.auto_fix_issue(issue_number)
            return {"success": True, "data": state.to_dict()}
        except ImportError:
            return {"error": "GitHub runner module not available"}
        except Exception as e:
            return {"error": str(e)}

    def get_review(self, pr_number: int) -> dict:
        """Get the most recent review result for a PR."""
        try:
            from runners.github.models import PRReviewResult

            result = PRReviewResult.load(self.github_dir, pr_number)
            if result is None:
                return {"error": f"No review found for PR #{pr_number}"}
            return {"success": True, "data": result.to_dict()}
        except ImportError:
            return {"error": "GitHub runner module not available"}
        except Exception as e:
            return {"error": str(e)}

    async def triage_issues(
        self, issue_numbers: list[int], repo: str | None = None
    ) -> dict:
        """Triage and classify GitHub issues."""
        try:
            from runners.github.orchestrator import GitHubOrchestrator

            resolved_repo = self._get_repo(repo)
            config = self._create_config(resolved_repo)
            config.triage_enabled = True
            orchestrator = GitHubOrchestrator(
                project_dir=self.project_dir, config=config
            )
            results = await orchestrator.triage_issues(issue_numbers=issue_numbers)
            return {
                "success": True,
                "data": [r.to_dict() for r in results],
                "count": len(results),
            }
        except ImportError:
            return {"error": "GitHub runner module not available"}
        except Exception as e:
            return {"error": str(e)}
