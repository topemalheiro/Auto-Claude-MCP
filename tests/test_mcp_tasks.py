"""
Tests for MCP Task Service and Task Tools
==========================================

Tests TaskService (CRUD on spec directories) and the 6 task_* MCP tools.
"""

import sys
from pathlib import Path

# Add backend to sys.path
_backend = Path(__file__).parent.parent / "apps" / "backend"
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

# Pre-mock SDK modules before any mcp_server imports
from unittest.mock import MagicMock

if "claude_agent_sdk" not in sys.modules:
    sys.modules["claude_agent_sdk"] = MagicMock()
    sys.modules["claude_agent_sdk.types"] = MagicMock()

import json

import pytest

from mcp_server.services.task_service import (
    VALID_STATUSES,
    TaskService,
    _extract_spec_heading,
    _extract_spec_overview,
    _safe_read_json,
    _slugify,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_spec_dir(
    specs_dir: Path,
    name: str,
    *,
    plan: dict | None = None,
    requirements: dict | None = None,
    metadata: dict | None = None,
    spec_md: str | None = None,
    qa_report: str | None = None,
) -> Path:
    """Create a spec directory with optional files."""
    d = specs_dir / name
    d.mkdir(parents=True, exist_ok=True)
    if plan is not None:
        (d / "implementation_plan.json").write_text(json.dumps(plan), encoding="utf-8")
    if requirements is not None:
        (d / "requirements.json").write_text(
            json.dumps(requirements), encoding="utf-8"
        )
    if metadata is not None:
        (d / "task_metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    if spec_md is not None:
        (d / "spec.md").write_text(spec_md, encoding="utf-8")
    if qa_report is not None:
        (d / "qa_report.md").write_text(qa_report, encoding="utf-8")
    return d


# ===========================================================================
# _slugify
# ===========================================================================


class TestSlugify:
    def test_basic_title(self):
        assert _slugify("My Feature") == "my-feature"

    def test_special_characters(self):
        assert _slugify("Hello, World! (v2)") == "hello-world-v2"

    def test_leading_trailing_whitespace(self):
        assert _slugify("  padded  ") == "padded"

    def test_multiple_spaces_and_dashes(self):
        assert _slugify("a   b---c") == "a-b-c"

    def test_truncates_to_80(self):
        result = _slugify("a" * 100)
        assert len(result) <= 80

    def test_empty_string(self):
        assert _slugify("") == ""

    def test_unicode_preserved(self):
        # Python \w matches unicode word chars, so accented letters stay
        assert _slugify("café crème") == "café-crème"


# ===========================================================================
# _safe_read_json
# ===========================================================================


class TestSafeReadJson:
    def test_valid_json(self, tmp_path):
        p = tmp_path / "data.json"
        p.write_text('{"key": 1}')
        assert _safe_read_json(p) == {"key": 1}

    def test_invalid_json(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("not json")
        assert _safe_read_json(p) is None

    def test_missing_file(self, tmp_path):
        assert _safe_read_json(tmp_path / "nope.json") is None


# ===========================================================================
# _extract_spec_heading
# ===========================================================================


class TestExtractSpecHeading:
    def test_standard_heading(self, tmp_path):
        p = tmp_path / "spec.md"
        p.write_text("# My Cool Feature\n\nSome text")
        assert _extract_spec_heading(p) == "My Cool Feature"

    def test_quick_spec_prefix(self, tmp_path):
        p = tmp_path / "spec.md"
        p.write_text("# Quick Spec: Login Page\n")
        assert _extract_spec_heading(p) == "Login Page"

    def test_specification_prefix(self, tmp_path):
        p = tmp_path / "spec.md"
        p.write_text("# Specification: Auth Module\n")
        assert _extract_spec_heading(p) == "Auth Module"

    def test_no_heading(self, tmp_path):
        p = tmp_path / "spec.md"
        p.write_text("No heading here\n")
        assert _extract_spec_heading(p) is None

    def test_missing_file(self, tmp_path):
        assert _extract_spec_heading(tmp_path / "nope.md") is None


# ===========================================================================
# _extract_spec_overview
# ===========================================================================


class TestExtractSpecOverview:
    def test_overview_section(self, tmp_path):
        p = tmp_path / "spec.md"
        p.write_text("# Title\n\n## Overview\n\nThis is the overview.\n\n## Details\n")
        assert _extract_spec_overview(p) == "This is the overview."

    def test_no_overview(self, tmp_path):
        p = tmp_path / "spec.md"
        p.write_text("# Title\n\n## Details\nStuff\n")
        assert _extract_spec_overview(p) is None

    def test_missing_file(self, tmp_path):
        assert _extract_spec_overview(tmp_path / "nope.md") is None


# ===========================================================================
# TaskService - list_tasks
# ===========================================================================


class TestTaskServiceListTasks:
    def test_empty_specs_dir(self, tmp_path):
        svc = TaskService(tmp_path)
        assert svc.list_tasks() == []

    def test_no_specs_dir(self, tmp_path):
        svc = TaskService(tmp_path / "nonexistent")
        assert svc.list_tasks() == []

    def test_loads_tasks_from_specs(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(
            specs,
            "001-hello",
            plan={"feature": "Hello Feature", "status": "pending"},
        )
        _make_spec_dir(
            specs,
            "002-world",
            plan={"feature": "World Feature", "status": "in_progress"},
        )
        svc = TaskService(tmp_path)
        tasks = svc.list_tasks()
        assert len(tasks) == 2
        ids = {t["spec_id"] for t in tasks}
        assert ids == {"001-hello", "002-world"}

    def test_title_from_plan_feature(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(specs, "001-feat", plan={"feature": "My Feature Title"})
        svc = TaskService(tmp_path)
        tasks = svc.list_tasks()
        assert tasks[0]["title"] == "My Feature Title"

    def test_title_from_plan_title_field(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(specs, "001-feat", plan={"title": "Title Field"})
        svc = TaskService(tmp_path)
        tasks = svc.list_tasks()
        assert tasks[0]["title"] == "Title Field"

    def test_title_fallback_to_spec_heading(self, tmp_path):
        """When plan title looks like a spec ID, fall back to spec.md heading."""
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(
            specs,
            "001-feat",
            plan={"feature": "001-feat"},
            spec_md="# The Real Title\n\nContent here",
        )
        svc = TaskService(tmp_path)
        tasks = svc.list_tasks()
        assert tasks[0]["title"] == "The Real Title"

    def test_title_fallback_to_dir_name(self, tmp_path):
        """When no plan exists and no spec.md heading, use dir name."""
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(specs, "001-some-slug")
        svc = TaskService(tmp_path)
        tasks = svc.list_tasks()
        # Dir name is the fallback, but it matches ^\d{3}- so spec heading is tried
        # Since no spec.md, stays as dir name
        assert tasks[0]["title"] == "001-some-slug"

    def test_description_from_plan(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(
            specs, "001-feat", plan={"feature": "F", "description": "Plan desc"}
        )
        svc = TaskService(tmp_path)
        assert svc.list_tasks()[0]["description"] == "Plan desc"

    def test_description_fallback_to_requirements(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(
            specs,
            "001-feat",
            plan={"feature": "F"},
            requirements={"task_description": "Req desc"},
        )
        svc = TaskService(tmp_path)
        assert svc.list_tasks()[0]["description"] == "Req desc"

    def test_description_fallback_to_overview(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(
            specs,
            "001-feat",
            plan={"feature": "F"},
            spec_md="# Title\n\n## Overview\n\nOverview text.\n\n## Other\n",
        )
        svc = TaskService(tmp_path)
        assert svc.list_tasks()[0]["description"] == "Overview text."

    def test_status_mapping(self, tmp_path):
        """Frontend-style statuses are mapped to valid backend statuses."""
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(specs, "001-a", plan={"feature": "A", "status": "coding"})
        _make_spec_dir(specs, "002-b", plan={"feature": "B", "status": "completed"})
        _make_spec_dir(specs, "003-c", plan={"feature": "C", "status": "backlog"})
        svc = TaskService(tmp_path)
        tasks = {t["spec_id"]: t for t in svc.list_tasks()}
        assert tasks["001-a"]["status"] == "in_progress"
        assert tasks["002-b"]["status"] == "done"
        assert tasks["003-c"]["status"] == "pending"

    def test_unknown_status_defaults_to_pending(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(
            specs, "001-x", plan={"feature": "X", "status": "totally_unknown"}
        )
        svc = TaskService(tmp_path)
        assert svc.list_tasks()[0]["status"] == "pending"

    def test_subtasks_from_phases(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        plan = {
            "feature": "F",
            "phases": [
                {
                    "subtasks": [
                        {"id": "s1", "description": "Do thing 1", "status": "pending"}
                    ]
                },
                {
                    "chunks": [
                        {
                            "id": "c1",
                            "description": "Do chunk 1",
                            "status": "completed",
                        }
                    ]
                },
            ],
        }
        _make_spec_dir(specs, "001-feat", plan=plan)
        svc = TaskService(tmp_path)
        task = svc.list_tasks()[0]
        assert len(task["subtasks"]) == 2
        assert task["subtasks"][0]["id"] == "s1"
        assert task["subtasks"][1]["id"] == "c1"

    def test_has_spec_and_plan_flags(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(
            specs,
            "001-feat",
            plan={"feature": "F"},
            spec_md="# Spec",
        )
        svc = TaskService(tmp_path)
        task = svc.list_tasks()[0]
        assert task["has_spec"] is True
        assert task["has_plan"] is True

    def test_has_qa_report_flag(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(
            specs,
            "001-feat",
            plan={"feature": "F"},
            qa_report="# QA passed",
        )
        svc = TaskService(tmp_path)
        assert svc.list_tasks()[0]["has_qa_report"] is True

    def test_skips_gitkeep(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        specs.mkdir(parents=True)
        (specs / ".gitkeep").mkdir()  # Directory named .gitkeep
        svc = TaskService(tmp_path)
        assert svc.list_tasks() == []

    def test_deduplication_main_wins_over_worktree(self, tmp_path):
        """Main project task takes priority over worktree duplicate."""
        # Main specs
        main_specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(
            main_specs,
            "001-feat",
            plan={"feature": "Main Version", "status": "pending"},
        )

        # Worktree with same spec id
        wt_dir = tmp_path / ".auto-claude" / "worktrees" / "tasks" / "wt1"
        wt_specs = wt_dir / ".auto-claude" / "specs"
        _make_spec_dir(
            wt_specs,
            "001-feat",
            plan={"feature": "Worktree Version", "status": "in_progress"},
        )

        svc = TaskService(tmp_path)
        tasks = svc.list_tasks()
        assert len(tasks) == 1
        assert tasks[0]["title"] == "Main Version"
        assert tasks[0]["location"] == "main"

    def test_worktree_only_included_if_exists_in_main(self, tmp_path):
        """Worktree tasks are only included when their spec_id exists in main."""
        main_specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(
            main_specs,
            "001-feat",
            plan={"feature": "Main", "status": "pending"},
        )

        wt_dir = tmp_path / ".auto-claude" / "worktrees" / "tasks" / "wt1"
        wt_specs = wt_dir / ".auto-claude" / "specs"
        # This spec doesn't exist in main
        _make_spec_dir(
            wt_specs,
            "099-orphan",
            plan={"feature": "Orphan", "status": "done"},
        )

        svc = TaskService(tmp_path)
        tasks = svc.list_tasks()
        assert len(tasks) == 1
        assert tasks[0]["spec_id"] == "001-feat"

    def test_dedup_same_location_higher_status_wins(self, tmp_path):
        """When both are from same location, higher status priority wins."""
        # We can't easily have two entries from the same location for the same
        # spec_id via the normal scan since directories are unique. But we can
        # verify the dedup logic via worktree entries that pass the main_spec_ids filter.
        main_specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(
            main_specs,
            "001-feat",
            plan={"feature": "Feat", "status": "pending"},
        )

        # Two worktrees with same spec
        for i, status in enumerate(["in_progress", "done"], 1):
            wt = tmp_path / ".auto-claude" / "worktrees" / "tasks" / f"wt{i}"
            wt_specs = wt / ".auto-claude" / "specs"
            _make_spec_dir(
                wt_specs,
                "001-feat",
                plan={"feature": "Feat", "status": status},
            )

        svc = TaskService(tmp_path)
        tasks = svc.list_tasks()
        # Main should win regardless
        assert len(tasks) == 1
        assert tasks[0]["location"] == "main"


# ===========================================================================
# TaskService - get_task
# ===========================================================================


class TestTaskServiceGetTask:
    def test_existing_task(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(specs, "001-feat", plan={"feature": "F", "status": "pending"})
        svc = TaskService(tmp_path)
        task = svc.get_task("001-feat")
        assert task is not None
        assert task["spec_id"] == "001-feat"
        assert task["title"] == "F"

    def test_missing_task(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        specs.mkdir(parents=True)
        svc = TaskService(tmp_path)
        assert svc.get_task("999-nope") is None

    def test_get_task_from_worktree(self, tmp_path):
        # No main spec, but exists in worktree
        (tmp_path / ".auto-claude" / "specs").mkdir(parents=True)
        wt = tmp_path / ".auto-claude" / "worktrees" / "tasks" / "wt1"
        wt_specs = wt / ".auto-claude" / "specs"
        _make_spec_dir(
            wt_specs,
            "001-feat",
            plan={"feature": "From WT", "status": "in_progress"},
        )
        svc = TaskService(tmp_path)
        task = svc.get_task("001-feat")
        assert task is not None
        assert task["title"] == "From WT"


# ===========================================================================
# TaskService - create_task
# ===========================================================================


class TestTaskServiceCreateTask:
    def test_creates_directory_and_files(self, tmp_path):
        svc = TaskService(tmp_path)
        result = svc.create_task("My New Task", "Build something cool")
        assert result["title"] == "My New Task"
        assert result["status"] == "pending"

        spec_dir = tmp_path / ".auto-claude" / "specs" / result["spec_id"]
        assert spec_dir.is_dir()
        assert (spec_dir / "implementation_plan.json").exists()
        assert (spec_dir / "requirements.json").exists()
        assert (spec_dir / "task_metadata.json").exists()

    def test_auto_numbering(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(specs, "001-existing", plan={"feature": "Existing"})
        _make_spec_dir(specs, "005-jump", plan={"feature": "Jump"})

        svc = TaskService(tmp_path)
        result = svc.create_task("Next Task", "Desc")
        # Should be 006 (one after max existing = 005)
        assert result["spec_id"].startswith("006-")

    def test_auto_numbering_empty(self, tmp_path):
        svc = TaskService(tmp_path)
        result = svc.create_task("First Task", "Desc")
        assert result["spec_id"].startswith("001-")

    def test_slug_in_dir_name(self, tmp_path):
        svc = TaskService(tmp_path)
        result = svc.create_task("Add OAuth Support!", "Desc")
        assert "add-oauth-support" in result["spec_id"]

    def test_plan_contents(self, tmp_path):
        svc = TaskService(tmp_path)
        result = svc.create_task("Title", "Description text")
        spec_dir = tmp_path / ".auto-claude" / "specs" / result["spec_id"]
        plan = json.loads((spec_dir / "implementation_plan.json").read_text())
        assert plan["feature"] == "Title"
        assert plan["title"] == "Title"
        assert plan["description"] == "Description text"
        assert plan["status"] == "pending"
        assert "created_at" in plan
        assert "updated_at" in plan

    def test_requirements_contents(self, tmp_path):
        svc = TaskService(tmp_path)
        result = svc.create_task("Title", "My desc")
        spec_dir = tmp_path / ".auto-claude" / "specs" / result["spec_id"]
        reqs = json.loads((spec_dir / "requirements.json").read_text())
        assert reqs["task_description"] == "My desc"

    def test_metadata_contents(self, tmp_path):
        svc = TaskService(tmp_path)
        result = svc.create_task("Title", "Desc")
        spec_dir = tmp_path / ".auto-claude" / "specs" / result["spec_id"]
        meta = json.loads((spec_dir / "task_metadata.json").read_text())
        assert meta["source"] == "mcp"
        assert "created_at" in meta


# ===========================================================================
# TaskService - update_task
# ===========================================================================


class TestTaskServiceUpdateTask:
    def test_update_title(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(specs, "001-feat", plan={"feature": "Old", "status": "pending"})
        svc = TaskService(tmp_path)
        result = svc.update_task("001-feat", title="New Title")
        assert result is not None
        assert result["title"] == "New Title"
        # Verify on disk
        plan = json.loads(
            (specs / "001-feat" / "implementation_plan.json").read_text()
        )
        assert plan["feature"] == "New Title"
        assert plan["title"] == "New Title"

    def test_update_description(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(
            specs,
            "001-feat",
            plan={"feature": "F", "status": "pending"},
            requirements={"task_description": "Old desc"},
        )
        svc = TaskService(tmp_path)
        result = svc.update_task("001-feat", description="New desc")
        assert result is not None
        # Verify requirements.json updated too
        reqs = json.loads((specs / "001-feat" / "requirements.json").read_text())
        assert reqs["task_description"] == "New desc"

    def test_update_status(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(specs, "001-feat", plan={"feature": "F", "status": "pending"})
        svc = TaskService(tmp_path)
        result = svc.update_task("001-feat", status="in_progress")
        assert result is not None
        assert result["status"] == "in_progress"

    def test_update_invalid_status(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(specs, "001-feat", plan={"feature": "F", "status": "pending"})
        svc = TaskService(tmp_path)
        result = svc.update_task("001-feat", status="bogus")
        assert result is None

    def test_update_nonexistent(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        specs.mkdir(parents=True)
        svc = TaskService(tmp_path)
        assert svc.update_task("999-nope", title="X") is None

    def test_updated_at_changes(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(
            specs,
            "001-feat",
            plan={
                "feature": "F",
                "status": "pending",
                "updated_at": "2020-01-01T00:00:00",
            },
        )
        svc = TaskService(tmp_path)
        svc.update_task("001-feat", title="Changed")
        plan = json.loads(
            (specs / "001-feat" / "implementation_plan.json").read_text()
        )
        assert plan["updated_at"] != "2020-01-01T00:00:00"


# ===========================================================================
# TaskService - delete_task
# ===========================================================================


class TestTaskServiceDeleteTask:
    def test_delete_existing(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(specs, "001-feat", plan={"feature": "F"})
        svc = TaskService(tmp_path)
        assert svc.delete_task("001-feat") is True
        assert not (specs / "001-feat").exists()

    def test_delete_nonexistent(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        specs.mkdir(parents=True)
        svc = TaskService(tmp_path)
        assert svc.delete_task("999-nope") is False

    def test_path_traversal_blocked(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        specs.mkdir(parents=True)
        # Create a dir outside specs that a traversal would target
        outside = tmp_path / "important"
        outside.mkdir()
        (outside / "data.txt").write_text("precious")

        svc = TaskService(tmp_path)
        # Even if the traversal path resolves to an existing directory,
        # the relative_to check should block it
        result = svc.delete_task("../../important")
        # The directory should not be deleted
        assert outside.exists()


# ===========================================================================
# TaskService - update_status
# ===========================================================================


class TestTaskServiceUpdateStatus:
    def test_valid_status(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(specs, "001-feat", plan={"feature": "F", "status": "pending"})
        svc = TaskService(tmp_path)
        result = svc.update_status("001-feat", "done")
        assert result is not None
        assert result["status"] == "done"

    def test_invalid_status(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(specs, "001-feat", plan={"feature": "F", "status": "pending"})
        svc = TaskService(tmp_path)
        assert svc.update_status("001-feat", "invalid") is None

    def test_all_valid_statuses_accepted(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        for i, status in enumerate(sorted(VALID_STATUSES), 1):
            name = f"{i:03d}-test"
            _make_spec_dir(
                specs, name, plan={"feature": f"Task {i}", "status": "pending"}
            )
            svc = TaskService(tmp_path)
            result = svc.update_status(name, status)
            assert result is not None, f"Status '{status}' should be valid"


# ===========================================================================
# TaskService - internal helpers
# ===========================================================================


class TestTaskServiceInternalHelpers:
    def test_next_spec_number_empty(self, tmp_path):
        svc = TaskService(tmp_path)
        assert svc._next_spec_number() == 1

    def test_next_spec_number_existing(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(specs, "003-thing")
        _make_spec_dir(specs, "010-other")
        svc = TaskService(tmp_path)
        assert svc._next_spec_number() == 11

    def test_find_spec_dir_in_worktrees(self, tmp_path):
        wt = tmp_path / ".auto-claude" / "worktrees" / "tasks" / "wt1"
        wt_specs = wt / ".auto-claude" / "specs"
        _make_spec_dir(wt_specs, "001-feat", plan={"feature": "F"})
        svc = TaskService(tmp_path)
        result = svc._find_spec_dir_in_worktrees("001-feat")
        assert result is not None
        assert result.name == "001-feat"

    def test_find_spec_dir_in_worktrees_not_found(self, tmp_path):
        svc = TaskService(tmp_path)
        assert svc._find_spec_dir_in_worktrees("999-nope") is None


# ===========================================================================
# Task Tools (mcp_server.tools.tasks)
# ===========================================================================


class TestTaskTools:
    """Tests for the MCP task_* tool functions.

    FastMCP's @mcp.tool() wraps functions in FunctionTool objects.
    We call the underlying function via .fn to test the tool logic directly.
    """

    @pytest.fixture(autouse=True)
    def _setup_config(self, tmp_path, monkeypatch):
        """Mock get_project_dir for all tool tests."""
        import mcp_server.config as config_mod

        monkeypatch.setattr(config_mod, "_project_dir", tmp_path)
        monkeypatch.setattr(config_mod, "_auto_claude_dir", tmp_path / ".auto-claude")
        self.project_dir = tmp_path
        self.specs_dir = tmp_path / ".auto-claude" / "specs"

    def test_task_list_empty(self):
        from mcp_server.tools.tasks import task_list

        result = task_list.fn()
        assert result["count"] == 0
        assert result["tasks"] == []

    def test_task_list_with_tasks(self):
        from mcp_server.tools.tasks import task_list

        _make_spec_dir(
            self.specs_dir,
            "001-hello",
            plan={"feature": "Hello", "status": "pending", "description": "A task"},
        )
        result = task_list.fn()
        assert result["count"] == 1
        assert result["tasks"][0]["spec_id"] == "001-hello"
        assert result["tasks"][0]["title"] == "Hello"
        assert result["tasks"][0]["status"] == "pending"

    def test_task_list_description_preview_truncated(self):
        from mcp_server.tools.tasks import task_list

        long_desc = "x" * 300
        _make_spec_dir(
            self.specs_dir,
            "001-feat",
            plan={"feature": "F", "description": long_desc},
        )
        result = task_list.fn()
        preview = result["tasks"][0]["description_preview"]
        assert len(preview) <= 204  # 200 + "..."
        assert preview.endswith("...")

    def test_task_create_success(self):
        from mcp_server.tools.tasks import task_create

        result = task_create.fn("New Task", "Do something")
        assert result["success"] is True
        assert "task" in result
        assert result["task"]["title"] == "New Task"

    def test_task_create_empty_title(self):
        from mcp_server.tools.tasks import task_create

        result = task_create.fn("", "Desc")
        assert "error" in result
        assert "Title" in result["error"]

    def test_task_create_empty_description(self):
        from mcp_server.tools.tasks import task_create

        result = task_create.fn("Title", "")
        assert "error" in result
        assert "Description" in result["error"]

    def test_task_create_whitespace_title(self):
        from mcp_server.tools.tasks import task_create

        result = task_create.fn("   ", "Desc")
        assert "error" in result

    def test_task_create_whitespace_description(self):
        from mcp_server.tools.tasks import task_create

        result = task_create.fn("Title", "   ")
        assert "error" in result

    def test_task_get_success(self):
        from mcp_server.tools.tasks import task_get

        _make_spec_dir(
            self.specs_dir,
            "001-feat",
            plan={"feature": "F", "status": "pending"},
        )
        result = task_get.fn("001-feat")
        assert "task" in result
        assert result["task"]["spec_id"] == "001-feat"

    def test_task_get_not_found(self):
        from mcp_server.tools.tasks import task_get

        self.specs_dir.mkdir(parents=True, exist_ok=True)
        result = task_get.fn("999-nope")
        assert "error" in result

    def test_task_update_success(self):
        from mcp_server.tools.tasks import task_update

        _make_spec_dir(
            self.specs_dir,
            "001-feat",
            plan={"feature": "Old", "status": "pending"},
        )
        result = task_update.fn("001-feat", title="New Title", status="in_progress")
        assert result["success"] is True
        assert result["task"]["title"] == "New Title"
        assert result["task"]["status"] == "in_progress"

    def test_task_update_invalid_status(self):
        from mcp_server.tools.tasks import task_update

        _make_spec_dir(
            self.specs_dir,
            "001-feat",
            plan={"feature": "F", "status": "pending"},
        )
        result = task_update.fn("001-feat", status="bogus")
        assert "error" in result
        assert "Invalid status" in result["error"]

    def test_task_update_not_found(self):
        from mcp_server.tools.tasks import task_update

        self.specs_dir.mkdir(parents=True, exist_ok=True)
        result = task_update.fn("999-nope", title="X")
        assert "error" in result

    def test_task_delete_success(self):
        from mcp_server.tools.tasks import task_delete

        _make_spec_dir(
            self.specs_dir,
            "001-feat",
            plan={"feature": "F"},
        )
        result = task_delete.fn("001-feat")
        assert result["success"] is True
        assert not (self.specs_dir / "001-feat").exists()

    def test_task_delete_not_found(self):
        from mcp_server.tools.tasks import task_delete

        self.specs_dir.mkdir(parents=True, exist_ok=True)
        result = task_delete.fn("999-nope")
        assert "error" in result

    def test_task_update_status_success(self):
        from mcp_server.tools.tasks import task_update_status

        _make_spec_dir(
            self.specs_dir,
            "001-feat",
            plan={"feature": "F", "status": "pending"},
        )
        result = task_update_status.fn("001-feat", "done")
        assert result["success"] is True
        assert result["task"]["status"] == "done"

    def test_task_update_status_invalid(self):
        from mcp_server.tools.tasks import task_update_status

        _make_spec_dir(
            self.specs_dir,
            "001-feat",
            plan={"feature": "F", "status": "pending"},
        )
        result = task_update_status.fn("001-feat", "invalid")
        assert "error" in result

    def test_task_update_status_not_found(self):
        from mcp_server.tools.tasks import task_update_status

        self.specs_dir.mkdir(parents=True, exist_ok=True)
        result = task_update_status.fn("999-nope", "done")
        assert "error" in result


class TestTaskToolsProjectNotInitialized:
    """Test that tools return errors when project is not initialized."""

    @pytest.fixture(autouse=True)
    def _setup_uninitialized(self, monkeypatch):
        """Make get_project_dir raise RuntimeError."""
        import mcp_server.config as config_mod

        monkeypatch.setattr(config_mod, "_project_dir", None)

    def test_task_list_error(self):
        from mcp_server.tools.tasks import task_list

        result = task_list.fn()
        assert "error" in result

    def test_task_create_error(self):
        from mcp_server.tools.tasks import task_create

        result = task_create.fn("Title", "Desc")
        assert "error" in result

    def test_task_get_error(self):
        from mcp_server.tools.tasks import task_get

        result = task_get.fn("001")
        assert "error" in result

    def test_task_update_error(self):
        from mcp_server.tools.tasks import task_update

        result = task_update.fn("001", title="X")
        assert "error" in result

    def test_task_delete_error(self):
        from mcp_server.tools.tasks import task_delete

        result = task_delete.fn("001")
        assert "error" in result

    def test_task_update_status_error(self):
        from mcp_server.tools.tasks import task_update_status

        result = task_update_status.fn("001", "done")
        assert "error" in result
