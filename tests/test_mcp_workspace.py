"""
Tests for mcp_server/services/workspace_service.py
====================================================

Tests worktree listing, diff retrieval (with truncation), merge strategies,
discard, and PR creation. WorktreeManager is fully mocked.
"""

import sys
from pathlib import Path

# Add backend to sys.path
_backend = Path(__file__).parent.parent / "apps" / "backend"
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

# Pre-mock SDK modules before any mcp_server imports
from unittest.mock import MagicMock, patch

if "claude_agent_sdk" not in sys.modules:
    sys.modules["claude_agent_sdk"] = MagicMock()
    sys.modules["claude_agent_sdk.types"] = MagicMock()

import pytest

from mcp_server.services.workspace_service import WorkspaceService


def _mock_worktree_info(
    spec_name="001-feat",
    branch="auto-claude/001-feat",
    path="/tmp/wt/001-feat",
    base_branch="main",
    is_active=True,
    commit_count=3,
    files_changed=5,
    additions=100,
    deletions=20,
    days_since_last_commit=1,
    last_commit_date=None,
):
    """Create a mock worktree info object."""
    info = MagicMock()
    info.spec_name = spec_name
    info.branch = branch
    info.path = Path(path)
    info.base_branch = base_branch
    info.is_active = is_active
    info.commit_count = commit_count
    info.files_changed = files_changed
    info.additions = additions
    info.deletions = deletions
    info.days_since_last_commit = days_since_last_commit
    info.last_commit_date = last_commit_date
    return info


class TestListWorktrees:
    """Tests for WorkspaceService.list_worktrees()."""

    def test_returns_worktree_list(self, tmp_path):
        """list_worktrees returns formatted worktree data."""
        svc = WorkspaceService(tmp_path)
        mock_manager = MagicMock()
        wt = _mock_worktree_info()
        mock_manager.list_all_worktrees.return_value = [wt]

        with patch.object(svc, "_get_manager", return_value=mock_manager):
            result = svc.list_worktrees()

        assert result["count"] == 1
        assert result["worktrees"][0]["spec_name"] == "001-feat"
        assert result["worktrees"][0]["branch"] == "auto-claude/001-feat"
        assert result["worktrees"][0]["is_active"] is True

    def test_returns_empty_list(self, tmp_path):
        """list_worktrees returns empty list when no worktrees exist."""
        svc = WorkspaceService(tmp_path)
        mock_manager = MagicMock()
        mock_manager.list_all_worktrees.return_value = []

        with patch.object(svc, "_get_manager", return_value=mock_manager):
            result = svc.list_worktrees()

        assert result["count"] == 0
        assert result["worktrees"] == []

    def test_handles_import_error(self, tmp_path):
        """list_worktrees returns error when backend unavailable."""
        svc = WorkspaceService(tmp_path)

        with patch.object(svc, "_get_manager", side_effect=ImportError("no module")):
            result = svc.list_worktrees()

        assert "error" in result

    def test_handles_manager_exception(self, tmp_path):
        """list_worktrees returns error on unexpected manager exception."""
        svc = WorkspaceService(tmp_path)
        mock_manager = MagicMock()
        mock_manager.list_all_worktrees.side_effect = RuntimeError("git error")

        with patch.object(svc, "_get_manager", return_value=mock_manager):
            result = svc.list_worktrees()

        assert "error" in result

    def test_includes_optional_fields(self, tmp_path):
        """list_worktrees includes days_since_last_commit when available."""
        from datetime import datetime, timezone

        svc = WorkspaceService(tmp_path)
        mock_manager = MagicMock()
        dt = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        wt = _mock_worktree_info(days_since_last_commit=5, last_commit_date=dt)
        mock_manager.list_all_worktrees.return_value = [wt]

        with patch.object(svc, "_get_manager", return_value=mock_manager):
            result = svc.list_worktrees()

        entry = result["worktrees"][0]
        assert entry["days_since_last_commit"] == 5
        assert "last_commit_date" in entry

    def test_omits_none_optional_fields(self, tmp_path):
        """list_worktrees omits optional fields when None."""
        svc = WorkspaceService(tmp_path)
        mock_manager = MagicMock()
        wt = _mock_worktree_info(days_since_last_commit=None, last_commit_date=None)
        mock_manager.list_all_worktrees.return_value = [wt]

        with patch.object(svc, "_get_manager", return_value=mock_manager):
            result = svc.list_worktrees()

        entry = result["worktrees"][0]
        assert "days_since_last_commit" not in entry
        assert "last_commit_date" not in entry


class TestGetDiff:
    """Tests for WorkspaceService.get_diff()."""

    def test_returns_diff_content(self, tmp_path):
        """get_diff returns diff data with changed files."""
        svc = WorkspaceService(tmp_path)
        mock_manager = MagicMock()
        info = _mock_worktree_info()
        mock_manager.get_worktree_info.return_value = info
        mock_manager.get_changed_files.return_value = [("M", "src/main.py")]
        mock_manager.get_change_summary.return_value = "1 file changed"

        mock_git_result = MagicMock()
        mock_git_result.returncode = 0
        mock_git_result.stdout = "diff --git a/src/main.py b/src/main.py\n+new line"

        # run_git is imported locally inside get_diff via `from core.git_executable import run_git`
        mock_git_module = MagicMock()
        mock_git_module.run_git = MagicMock(return_value=mock_git_result)
        with patch.object(svc, "_get_manager", return_value=mock_manager), \
             patch.dict(sys.modules, {"core.git_executable": mock_git_module}):
            result = svc.get_diff("001-feat")

        assert result["spec_id"] == "001-feat"
        assert len(result["changed_files"]) == 1
        assert result["changed_files"][0]["status"] == "M"

    def test_returns_error_for_missing_worktree(self, tmp_path):
        """get_diff returns error when worktree not found."""
        svc = WorkspaceService(tmp_path)
        mock_manager = MagicMock()
        mock_manager.get_worktree_info.return_value = None

        with patch.object(svc, "_get_manager", return_value=mock_manager):
            result = svc.get_diff("999-missing")

        assert "error" in result
        assert "No worktree" in result["error"]

    def test_handles_import_error(self, tmp_path):
        """get_diff returns error when backend unavailable."""
        svc = WorkspaceService(tmp_path)

        with patch.object(svc, "_get_manager", side_effect=ImportError("no module")):
            result = svc.get_diff("001-feat")

        assert "error" in result


class TestMerge:
    """Tests for WorkspaceService.merge()."""

    @pytest.mark.asyncio
    async def test_merge_auto_strategy(self, tmp_path):
        """merge with 'auto' strategy calls merge_worktree without no_commit."""
        svc = WorkspaceService(tmp_path)
        mock_manager = MagicMock()
        mock_manager.merge_worktree.return_value = True

        with patch.object(svc, "_get_manager", return_value=mock_manager):
            result = await svc.merge("001-feat", strategy="auto")

        assert result["success"] is True
        assert result["strategy"] == "auto"
        mock_manager.merge_worktree.assert_called_once_with(
            "001-feat", delete_after=False, no_commit=False
        )

    @pytest.mark.asyncio
    async def test_merge_no_commit_strategy(self, tmp_path):
        """merge with 'no-commit' strategy passes no_commit=True."""
        svc = WorkspaceService(tmp_path)
        mock_manager = MagicMock()
        mock_manager.merge_worktree.return_value = True

        with patch.object(svc, "_get_manager", return_value=mock_manager):
            result = await svc.merge("001-feat", strategy="no-commit")

        assert result["success"] is True
        mock_manager.merge_worktree.assert_called_once_with(
            "001-feat", delete_after=False, no_commit=True
        )

    @pytest.mark.asyncio
    async def test_merge_failure(self, tmp_path):
        """merge returns success=False when merge_worktree returns False."""
        svc = WorkspaceService(tmp_path)
        mock_manager = MagicMock()
        mock_manager.merge_worktree.return_value = False

        with patch.object(svc, "_get_manager", return_value=mock_manager):
            result = await svc.merge("001-feat")

        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_merge_handles_exception(self, tmp_path):
        """merge returns error on unexpected exception."""
        svc = WorkspaceService(tmp_path)
        mock_manager = MagicMock()
        mock_manager.merge_worktree.side_effect = RuntimeError("conflict")

        with patch.object(svc, "_get_manager", return_value=mock_manager):
            result = await svc.merge("001-feat")

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_merge_handles_import_error(self, tmp_path):
        """merge returns error when backend unavailable."""
        svc = WorkspaceService(tmp_path)

        with patch.object(svc, "_get_manager", side_effect=ImportError("no module")):
            result = await svc.merge("001-feat")

        assert "error" in result


class TestDiscard:
    """Tests for WorkspaceService.discard()."""

    def test_discard_success(self, tmp_path):
        """discard calls remove_worktree and returns success."""
        svc = WorkspaceService(tmp_path)
        mock_manager = MagicMock()

        with patch.object(svc, "_get_manager", return_value=mock_manager):
            result = svc.discard("001-feat")

        assert result["success"] is True
        mock_manager.remove_worktree.assert_called_once_with(
            "001-feat", delete_branch=True
        )

    def test_discard_handles_exception(self, tmp_path):
        """discard returns error on unexpected exception."""
        svc = WorkspaceService(tmp_path)
        mock_manager = MagicMock()
        mock_manager.remove_worktree.side_effect = RuntimeError("git error")

        with patch.object(svc, "_get_manager", return_value=mock_manager):
            result = svc.discard("001-feat")

        assert result["success"] is False
        assert "error" in result

    def test_discard_handles_import_error(self, tmp_path):
        """discard returns error when backend unavailable."""
        svc = WorkspaceService(tmp_path)

        with patch.object(svc, "_get_manager", side_effect=ImportError("no module")):
            result = svc.discard("001-feat")

        assert "error" in result


class TestCreatePR:
    """Tests for WorkspaceService.create_pr()."""

    @pytest.mark.asyncio
    async def test_create_pr_success(self, tmp_path):
        """create_pr returns success with PR URL."""
        svc = WorkspaceService(tmp_path)
        mock_manager = MagicMock()
        mock_manager.push_and_create_pr.return_value = {
            "success": True,
            "pr_url": "https://github.com/org/repo/pull/42",
            "branch": "auto-claude/001-feat",
            "provider": "github",
        }

        with patch.object(svc, "_get_manager", return_value=mock_manager):
            result = await svc.create_pr("001-feat", title="Add feature")

        assert result["success"] is True
        assert result["pr_url"] == "https://github.com/org/repo/pull/42"

    @pytest.mark.asyncio
    async def test_create_pr_failure(self, tmp_path):
        """create_pr returns error from manager."""
        svc = WorkspaceService(tmp_path)
        mock_manager = MagicMock()
        mock_manager.push_and_create_pr.return_value = {
            "success": False,
            "error": "Remote rejected push",
        }

        with patch.object(svc, "_get_manager", return_value=mock_manager):
            result = await svc.create_pr("001-feat")

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create_pr_handles_exception(self, tmp_path):
        """create_pr returns error on unexpected exception."""
        svc = WorkspaceService(tmp_path)
        mock_manager = MagicMock()
        mock_manager.push_and_create_pr.side_effect = RuntimeError("network error")

        with patch.object(svc, "_get_manager", return_value=mock_manager):
            result = await svc.create_pr("001-feat")

        assert result["success"] is False
        assert "error" in result
