"""
Workspace Service
==================

Service layer wrapping the backend WorktreeManager for MCP tool consumption.
Handles git worktree operations: list, diff, merge, discard, and PR creation.
"""

from __future__ import annotations

import contextlib
import io
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class WorkspaceService:
    """Wraps WorktreeManager operations for MCP server use."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir

    def _get_manager(self):
        """Lazily create a WorktreeManager instance.

        Returns:
            WorktreeManager instance

        Raises:
            ImportError: If backend module is not available
        """
        from core.worktree import WorktreeManager

        return WorktreeManager(self.project_dir)

    def list_worktrees(self) -> dict:
        """List all active git worktrees for the project.

        Returns:
            Dict with list of worktree info dicts
        """
        try:
            manager = self._get_manager()
        except ImportError as e:
            return {"error": f"Backend module not available: {e}"}

        try:
            captured = io.StringIO()
            with contextlib.redirect_stdout(captured):
                worktrees = manager.list_all_worktrees()

            result = []
            for wt in worktrees:
                entry = {
                    "spec_name": wt.spec_name,
                    "branch": wt.branch,
                    "path": str(wt.path),
                    "base_branch": wt.base_branch,
                    "is_active": wt.is_active,
                    "commit_count": wt.commit_count,
                    "files_changed": wt.files_changed,
                    "additions": wt.additions,
                    "deletions": wt.deletions,
                }
                if wt.days_since_last_commit is not None:
                    entry["days_since_last_commit"] = wt.days_since_last_commit
                if wt.last_commit_date is not None:
                    entry["last_commit_date"] = wt.last_commit_date.isoformat()
                result.append(entry)

            return {"worktrees": result, "count": len(result)}
        except Exception as e:
            logger.exception("Failed to list worktrees")
            return {"error": str(e)}

    def get_diff(self, spec_id: str) -> dict:
        """Get the git diff for a spec's worktree.

        Args:
            spec_id: The spec folder name

        Returns:
            Dict with diff content and change summary
        """
        try:
            manager = self._get_manager()
        except ImportError as e:
            return {"error": f"Backend module not available: {e}"}

        try:
            captured = io.StringIO()
            with contextlib.redirect_stdout(captured):
                info = manager.get_worktree_info(spec_id)

            if info is None:
                return {"error": f"No worktree found for spec '{spec_id}'"}

            # Get changed files
            files = manager.get_changed_files(spec_id)
            summary = manager.get_change_summary(spec_id)

            # Get actual diff content
            from core.git_executable import run_git

            diff_result = run_git(
                ["diff", f"{info.base_branch}...HEAD"],
                cwd=info.path,
            )
            diff_content = ""
            if diff_result.returncode == 0:
                diff_content = diff_result.stdout
                # Truncate very large diffs
                if len(diff_content) > 50000:
                    diff_content = (
                        diff_content[:50000]
                        + "\n\n... (diff truncated, total length: "
                        + str(len(diff_result.stdout))
                        + " chars)"
                    )

            return {
                "spec_id": spec_id,
                "branch": info.branch,
                "base_branch": info.base_branch,
                "changed_files": [
                    {"status": status, "path": path} for status, path in files
                ],
                "summary": summary,
                "diff": diff_content,
            }
        except Exception as e:
            logger.exception("Failed to get diff for %s", spec_id)
            return {"error": str(e)}

    async def merge(self, spec_id: str, strategy: str = "auto") -> dict:
        """Merge a spec's worktree changes back to the main branch.

        Args:
            spec_id: The spec folder name
            strategy: Merge strategy - 'auto' (git merge), 'no-commit' (stage only)

        Returns:
            Dict with merge result
        """
        try:
            manager = self._get_manager()
        except ImportError as e:
            return {"error": f"Backend module not available: {e}"}

        try:
            no_commit = strategy == "no-commit"

            captured = io.StringIO()
            with contextlib.redirect_stdout(captured):
                success = manager.merge_worktree(
                    spec_id,
                    delete_after=False,
                    no_commit=no_commit,
                )

            return {
                "success": success,
                "spec_id": spec_id,
                "strategy": strategy,
                "output": captured.getvalue()[-2000:] if captured.getvalue() else "",
            }
        except Exception as e:
            logger.exception("Failed to merge worktree for %s", spec_id)
            return {"success": False, "error": str(e)}

    def discard(self, spec_id: str) -> dict:
        """Discard a spec's worktree and optionally its branch.

        Args:
            spec_id: The spec folder name

        Returns:
            Dict with discard result
        """
        try:
            manager = self._get_manager()
        except ImportError as e:
            return {"error": f"Backend module not available: {e}"}

        try:
            captured = io.StringIO()
            with contextlib.redirect_stdout(captured):
                manager.remove_worktree(spec_id, delete_branch=True)

            return {
                "success": True,
                "spec_id": spec_id,
                "message": f"Worktree and branch for '{spec_id}' removed",
                "output": captured.getvalue() if captured.getvalue() else "",
            }
        except Exception as e:
            logger.exception("Failed to discard worktree for %s", spec_id)
            return {"success": False, "error": str(e)}

    async def create_pr(
        self,
        spec_id: str,
        title: str | None = None,
        body: str | None = None,
    ) -> dict:
        """Push branch and create a pull request from a spec's worktree.

        Automatically detects the git provider (GitHub/GitLab).

        Args:
            spec_id: The spec folder name
            title: PR title (defaults to spec name)
            body: PR body (defaults to spec summary)

        Returns:
            Dict with PR URL and status
        """
        try:
            manager = self._get_manager()
        except ImportError as e:
            return {"error": f"Backend module not available: {e}"}

        try:
            captured = io.StringIO()
            with contextlib.redirect_stdout(captured):
                result = manager.push_and_create_pr(
                    spec_name=spec_id,
                    title=title,
                )

            return {
                "success": result.get("success", False),
                "spec_id": spec_id,
                "pr_url": result.get("pr_url"),
                "branch": result.get("branch"),
                "provider": result.get("provider"),
                "already_exists": result.get("already_exists", False),
                "error": result.get("error"),
                "output": captured.getvalue()[-1000:] if captured.getvalue() else "",
            }
        except Exception as e:
            logger.exception("Failed to create PR for %s", spec_id)
            return {"success": False, "error": str(e)}
