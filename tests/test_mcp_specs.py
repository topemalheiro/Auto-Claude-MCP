"""
Tests for MCP Spec Service and Spec Tools
==========================================

Tests SpecService (spec status, content, listing) and the 4 spec_* MCP tools.
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

from mcp_server.services.spec_service import SpecService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_spec_dir(
    specs_dir: Path,
    name: str,
    *,
    plan: dict | None = None,
    requirements: dict | None = None,
    complexity: dict | None = None,
    spec_md: str | None = None,
    discovery_md: str | None = None,
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
    if complexity is not None:
        (d / "complexity_assessment.json").write_text(
            json.dumps(complexity), encoding="utf-8"
        )
    if spec_md is not None:
        (d / "spec.md").write_text(spec_md, encoding="utf-8")
    if discovery_md is not None:
        (d / "discovery.md").write_text(discovery_md, encoding="utf-8")
    if qa_report is not None:
        (d / "qa_report.md").write_text(qa_report, encoding="utf-8")
    return d


# ===========================================================================
# SpecService - get_spec_status
# ===========================================================================


class TestSpecServiceGetSpecStatus:
    def test_not_found(self, tmp_path):
        svc = SpecService(tmp_path)
        result = svc.get_spec_status("999-nope")
        assert "error" in result

    def test_pending_no_files(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(specs, "001-feat")
        svc = SpecService(tmp_path)
        result = svc.get_spec_status("001-feat")
        assert result["status"] == "pending"
        assert result["phases"]["discovery"] is False
        assert result["phases"]["requirements"] is False
        assert result["phases"]["spec"] is False
        assert result["phases"]["implementation_plan"] is False

    def test_discovery_complete(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(specs, "001-feat", discovery_md="# Discovery\nFindings here")
        svc = SpecService(tmp_path)
        result = svc.get_spec_status("001-feat")
        assert result["status"] == "discovery_complete"
        assert result["phases"]["discovery"] is True

    def test_requirements_gathered(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(
            specs,
            "001-feat",
            discovery_md="# D",
            requirements={"task_description": "Do thing"},
        )
        svc = SpecService(tmp_path)
        result = svc.get_spec_status("001-feat")
        assert result["status"] == "requirements_gathered"
        assert result["phases"]["requirements"] is True

    def test_spec_complete(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(
            specs,
            "001-feat",
            discovery_md="# D",
            requirements={"task_description": "X"},
            spec_md="# Spec\nContent here",
        )
        svc = SpecService(tmp_path)
        result = svc.get_spec_status("001-feat")
        assert result["status"] == "spec_complete"
        assert result["phases"]["spec"] is True

    def test_ready_to_build(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(
            specs,
            "001-feat",
            discovery_md="# D",
            requirements={"task_description": "X"},
            spec_md="# Spec",
            plan={"feature": "F", "phases": []},
        )
        svc = SpecService(tmp_path)
        result = svc.get_spec_status("001-feat")
        assert result["status"] == "ready_to_build"
        assert result["phases"]["implementation_plan"] is True

    def test_qa_reviewed(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(
            specs,
            "001-feat",
            plan={"feature": "F"},
            qa_report="# QA Report\nAll good",
        )
        svc = SpecService(tmp_path)
        result = svc.get_spec_status("001-feat")
        assert result["status"] == "qa_reviewed"

    def test_qa_approved(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(
            specs,
            "001-feat",
            plan={
                "feature": "F",
                "qa_signoff": {"status": "approved"},
            },
        )
        svc = SpecService(tmp_path)
        result = svc.get_spec_status("001-feat")
        assert result["status"] == "qa_approved"

    def test_qa_rejected(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(
            specs,
            "001-feat",
            plan={
                "feature": "F",
                "qa_signoff": {"status": "rejected"},
            },
        )
        svc = SpecService(tmp_path)
        result = svc.get_spec_status("001-feat")
        assert result["status"] == "qa_rejected"

    def test_complexity_assessment_phase(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(
            specs,
            "001-feat",
            requirements={"task_description": "X"},
            complexity={"complexity": "standard"},
        )
        svc = SpecService(tmp_path)
        result = svc.get_spec_status("001-feat")
        assert result["phases"]["complexity_assessment"] is True

    def test_prefix_matching(self, tmp_path):
        """get_spec_status supports prefix matching (e.g., '001' matches '001-feat')."""
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(specs, "001-my-feature", plan={"feature": "F"})
        svc = SpecService(tmp_path)
        result = svc.get_spec_status("001")
        assert result["spec_id"] == "001-my-feature"
        assert result["status"] == "ready_to_build"

    def test_returns_spec_dir_path(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(specs, "001-feat")
        svc = SpecService(tmp_path)
        result = svc.get_spec_status("001-feat")
        assert "spec_dir" in result
        assert result["spec_dir"].endswith("001-feat")


# ===========================================================================
# SpecService - get_spec_content
# ===========================================================================


class TestSpecServiceGetSpecContent:
    def test_not_found(self, tmp_path):
        svc = SpecService(tmp_path)
        result = svc.get_spec_content("999-nope")
        assert "error" in result

    def test_reads_spec_md(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(specs, "001-feat", spec_md="# My Spec\n\nContent here.")
        svc = SpecService(tmp_path)
        result = svc.get_spec_content("001-feat")
        assert "spec_md" in result
        assert "My Spec" in result["spec_md"]

    def test_reads_requirements(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(
            specs, "001-feat", requirements={"task_description": "Build auth"}
        )
        svc = SpecService(tmp_path)
        result = svc.get_spec_content("001-feat")
        assert "requirements" in result
        assert result["requirements"]["task_description"] == "Build auth"

    def test_reads_implementation_plan(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(
            specs,
            "001-feat",
            plan={"feature": "Auth", "phases": [{"name": "Phase 1"}]},
        )
        svc = SpecService(tmp_path)
        result = svc.get_spec_content("001-feat")
        assert "implementation_plan" in result
        assert result["implementation_plan"]["feature"] == "Auth"

    def test_reads_complexity_assessment(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(
            specs, "001-feat", complexity={"complexity": "standard", "confidence": 0.9}
        )
        svc = SpecService(tmp_path)
        result = svc.get_spec_content("001-feat")
        assert "complexity_assessment" in result
        assert result["complexity_assessment"]["complexity"] == "standard"

    def test_reads_qa_report(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(specs, "001-feat", qa_report="# QA Report\n\nAll tests pass.")
        svc = SpecService(tmp_path)
        result = svc.get_spec_content("001-feat")
        assert "qa_report" in result
        assert "All tests pass" in result["qa_report"]

    def test_empty_spec_dir(self, tmp_path):
        """A spec dir with no files returns only spec_id and spec_dir."""
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(specs, "001-empty")
        svc = SpecService(tmp_path)
        result = svc.get_spec_content("001-empty")
        assert result["spec_id"] == "001-empty"
        assert "spec_md" not in result
        assert "requirements" not in result
        assert "implementation_plan" not in result

    def test_prefix_matching(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(specs, "001-my-feature", spec_md="# Content")
        svc = SpecService(tmp_path)
        result = svc.get_spec_content("001")
        assert result["spec_id"] == "001-my-feature"
        assert "spec_md" in result

    def test_all_files_present(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(
            specs,
            "001-full",
            plan={"feature": "Full"},
            requirements={"task_description": "Build it"},
            complexity={"complexity": "complex"},
            spec_md="# Full Spec",
            qa_report="# QA\nAll good",
        )
        svc = SpecService(tmp_path)
        result = svc.get_spec_content("001-full")
        assert "spec_md" in result
        assert "requirements" in result
        assert "implementation_plan" in result
        assert "complexity_assessment" in result
        assert "qa_report" in result


# ===========================================================================
# SpecService - list_specs
# ===========================================================================


class TestSpecServiceListSpecs:
    def test_no_specs_dir(self, tmp_path):
        svc = SpecService(tmp_path)
        assert svc.list_specs() == []

    def test_empty_specs_dir(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        specs.mkdir(parents=True)
        svc = SpecService(tmp_path)
        assert svc.list_specs() == []

    def test_lists_multiple_specs(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(specs, "001-first", plan={"feature": "First"})
        _make_spec_dir(specs, "002-second", requirements={"task_description": "X"})
        _make_spec_dir(specs, "003-third")
        svc = SpecService(tmp_path)
        result = svc.list_specs()
        assert len(result) == 3
        ids = [s["spec_id"] for s in result]
        assert "001-first" in ids
        assert "002-second" in ids
        assert "003-third" in ids

    def test_skips_hidden_dirs(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(specs, "001-visible")
        (specs / ".hidden-dir").mkdir()
        svc = SpecService(tmp_path)
        result = svc.list_specs()
        assert len(result) == 1
        assert result[0]["spec_id"] == "001-visible"

    def test_skips_files(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(specs, "001-visible")
        (specs / "some-file.txt").write_text("not a dir")
        svc = SpecService(tmp_path)
        result = svc.list_specs()
        assert len(result) == 1

    def test_sorted_order(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(specs, "003-c")
        _make_spec_dir(specs, "001-a")
        _make_spec_dir(specs, "002-b")
        svc = SpecService(tmp_path)
        result = svc.list_specs()
        ids = [s["spec_id"] for s in result]
        assert ids == ["001-a", "002-b", "003-c"]

    def test_each_entry_has_status(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(specs, "001-feat", plan={"feature": "F"})
        svc = SpecService(tmp_path)
        result = svc.list_specs()
        assert "status" in result[0]
        assert "phases" in result[0]


# ===========================================================================
# SpecService - _resolve_spec_dir
# ===========================================================================


class TestSpecServiceResolveSpecDir:
    def test_exact_match(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(specs, "001-exact-name")
        svc = SpecService(tmp_path)
        result = svc._resolve_spec_dir(specs, "001-exact-name")
        assert result is not None
        assert result.name == "001-exact-name"

    def test_prefix_match(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(specs, "001-my-feature")
        svc = SpecService(tmp_path)
        result = svc._resolve_spec_dir(specs, "001")
        assert result is not None
        assert result.name == "001-my-feature"

    def test_no_match(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        specs.mkdir(parents=True)
        svc = SpecService(tmp_path)
        assert svc._resolve_spec_dir(specs, "999") is None

    def test_prefers_exact_over_prefix(self, tmp_path):
        specs = tmp_path / ".auto-claude" / "specs"
        _make_spec_dir(specs, "001")
        _make_spec_dir(specs, "001-with-slug")
        svc = SpecService(tmp_path)
        result = svc._resolve_spec_dir(specs, "001")
        assert result.name == "001"

    def test_no_specs_dir(self, tmp_path):
        svc = SpecService(tmp_path)
        assert svc._resolve_spec_dir(tmp_path / "nonexistent", "001") is None


# ===========================================================================
# SpecService - _load_json
# ===========================================================================


class TestSpecServiceLoadJson:
    def test_valid_json(self, tmp_path):
        p = tmp_path / "data.json"
        p.write_text('{"key": "value"}')
        svc = SpecService(tmp_path)
        assert svc._load_json(p) == {"key": "value"}

    def test_invalid_json(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("not json")
        svc = SpecService(tmp_path)
        assert svc._load_json(p) is None

    def test_missing_file(self, tmp_path):
        svc = SpecService(tmp_path)
        assert svc._load_json(tmp_path / "nope.json") is None


# ===========================================================================
# SpecService - create_spec (async, mocked)
# ===========================================================================


class TestSpecServiceCreateSpec:
    async def test_import_error(self, tmp_path, monkeypatch):
        """When SpecOrchestrator can't be imported, returns error."""
        svc = SpecService(tmp_path)
        # Ensure the import inside create_spec fails
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if "orchestrator" in name:
                raise ImportError("no module")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        result = await svc.create_spec("build a thing")
        assert result["success"] is False
        assert "not available" in result["error"]

    async def test_orchestrator_exception(self, tmp_path, monkeypatch):
        """When orchestrator raises, returns error."""
        svc = SpecService(tmp_path)

        mock_orch_cls = MagicMock()
        mock_orch_cls.side_effect = RuntimeError("boom")

        monkeypatch.setitem(
            sys.modules,
            "spec.pipeline.orchestrator",
            MagicMock(SpecOrchestrator=mock_orch_cls),
        )
        result = await svc.create_spec("task")
        assert result["success"] is False
        assert "boom" in result["error"]

    async def test_successful_spec_creation(self, tmp_path, monkeypatch):
        """When orchestrator succeeds, returns success with spec info."""
        svc = SpecService(tmp_path)

        spec_dir = tmp_path / ".auto-claude" / "specs" / "001-test"
        spec_dir.mkdir(parents=True)

        mock_instance = MagicMock()
        mock_instance.spec_dir = spec_dir
        mock_instance.run = MagicMock(return_value=True)
        # Make run a coroutine
        import asyncio

        async def mock_run(**kwargs):
            return True

        mock_instance.run = mock_run

        mock_orch_cls = MagicMock(return_value=mock_instance)

        monkeypatch.setitem(
            sys.modules,
            "spec.pipeline.orchestrator",
            MagicMock(SpecOrchestrator=mock_orch_cls),
        )
        result = await svc.create_spec("build a thing")
        assert result["success"] is True
        assert result["spec_id"] == "001-test"
        assert "spec_dir" in result


# ===========================================================================
# Spec Tools (mcp_server.tools.specs)
# ===========================================================================


class TestSpecTools:
    """Tests for the MCP spec_* tool functions.

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

    def test_spec_get_status_success(self):
        from mcp_server.tools.specs import spec_get_status

        _make_spec_dir(
            self.specs_dir,
            "001-feat",
            plan={"feature": "F"},
            spec_md="# Spec",
        )
        result = spec_get_status.fn("001-feat")
        assert result["status"] == "ready_to_build"
        assert result["spec_id"] == "001-feat"

    def test_spec_get_status_not_found(self):
        from mcp_server.tools.specs import spec_get_status

        self.specs_dir.mkdir(parents=True, exist_ok=True)
        result = spec_get_status.fn("999-nope")
        assert "error" in result

    def test_spec_get_status_prefix(self):
        from mcp_server.tools.specs import spec_get_status

        _make_spec_dir(self.specs_dir, "001-my-feature", plan={"feature": "F"})
        result = spec_get_status.fn("001")
        assert result["spec_id"] == "001-my-feature"

    def test_spec_get_content_success(self):
        from mcp_server.tools.specs import spec_get_content

        _make_spec_dir(
            self.specs_dir,
            "001-feat",
            spec_md="# The Spec",
            requirements={"task_description": "Build it"},
            plan={"feature": "Feature"},
        )
        result = spec_get_content.fn("001-feat")
        assert "spec_md" in result
        assert "requirements" in result
        assert "implementation_plan" in result

    def test_spec_get_content_not_found(self):
        from mcp_server.tools.specs import spec_get_content

        self.specs_dir.mkdir(parents=True, exist_ok=True)
        result = spec_get_content.fn("999-nope")
        assert "error" in result

    def test_spec_list_success(self):
        from mcp_server.tools.specs import spec_list

        _make_spec_dir(self.specs_dir, "001-first", plan={"feature": "First"})
        _make_spec_dir(self.specs_dir, "002-second")
        result = spec_list.fn()
        assert result["count"] == 2
        assert len(result["specs"]) == 2

    def test_spec_list_empty(self):
        from mcp_server.tools.specs import spec_list

        result = spec_list.fn()
        assert result["count"] == 0
        assert result["specs"] == []

    def test_spec_create_is_async(self):
        """spec_create wraps an async function for long-running operations."""
        from mcp_server.tools.specs import spec_create
        import inspect

        # The underlying fn is async (wrapped by FastMCP)
        assert inspect.iscoroutinefunction(spec_create.fn)
