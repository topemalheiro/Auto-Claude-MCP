"""
Tests for mcp_server/tools/project.py
=======================================

Tests project management tools: set active, get status, list specs,
and get project index. Uses monkeypatch to mock config module.
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

import mcp_server.config as config

# @mcp.tool() wraps functions as FunctionTool objects; access .fn for the raw callable
from mcp_server.tools.project import (
    project_get_index as _project_get_index_tool,
    project_get_status as _project_get_status_tool,
    project_list_specs as _project_list_specs_tool,
    project_set_active as _project_set_active_tool,
)

project_set_active = _project_set_active_tool.fn
project_get_status = _project_get_status_tool.fn
project_list_specs = _project_list_specs_tool.fn
project_get_index = _project_get_index_tool.fn


@pytest.fixture(autouse=True)
def reset_config():
    """Reset config state between tests."""
    config._project_dir = None
    config._auto_claude_dir = None
    yield
    config._project_dir = None
    config._auto_claude_dir = None


class TestProjectSetActive:
    """Tests for project_set_active()."""

    def test_set_active_valid_project(self, tmp_path):
        """Sets the active project directory."""
        ac_dir = tmp_path / ".auto-claude"
        ac_dir.mkdir()
        result = project_set_active(str(tmp_path))
        assert result["success"] is True
        assert result["initialized"] is True
        assert str(tmp_path.resolve()) in result["project_dir"]

    def test_set_active_nonexistent_dir(self):
        """Returns error for a nonexistent directory."""
        result = project_set_active("/nonexistent/path/to/project")
        assert result["success"] is False
        assert "error" in result

    def test_set_active_without_auto_claude(self, tmp_path):
        """Sets project even without .auto-claude dir (warns but works)."""
        result = project_set_active(str(tmp_path))
        assert result["success"] is True
        # initialized should be False since .auto-claude doesn't exist on disk
        assert result["initialized"] is False


class TestProjectGetStatus:
    """Tests for project_get_status()."""

    def test_returns_error_when_not_initialized(self):
        """Returns error when no project has been set."""
        result = project_get_status()
        assert result["initialized"] is False
        assert "error" in result

    def test_returns_status_with_specs(self, tmp_path):
        """Returns project status including specs count."""
        ac_dir = tmp_path / ".auto-claude"
        specs_dir = ac_dir / "specs"
        specs_dir.mkdir(parents=True)
        (specs_dir / "001-feature-a").mkdir()
        (specs_dir / "002-feature-b").mkdir()

        config.initialize(tmp_path)
        result = project_get_status()

        assert result["initialized"] is True
        assert result["specs_count"] == 2
        assert str(tmp_path.resolve()) in result["project_dir"]

    def test_excludes_gitkeep_from_count(self, tmp_path):
        """Specs count excludes .gitkeep entries."""
        ac_dir = tmp_path / ".auto-claude"
        specs_dir = ac_dir / "specs"
        specs_dir.mkdir(parents=True)
        (specs_dir / "001-feat").mkdir()
        (specs_dir / ".gitkeep").mkdir()

        config.initialize(tmp_path)
        result = project_get_status()

        assert result["specs_count"] == 1

    def test_returns_project_name_from_index(self, tmp_path):
        """Uses project name from project_index.json when available."""
        ac_dir = tmp_path / ".auto-claude"
        ac_dir.mkdir()
        index = {"name": "My Awesome Project"}
        (ac_dir / "project_index.json").write_text(json.dumps(index))

        config.initialize(tmp_path)
        result = project_get_status()

        assert result["project_name"] == "My Awesome Project"

    def test_uses_dir_name_as_fallback_project_name(self, tmp_path):
        """Falls back to directory name when no project_index exists."""
        ac_dir = tmp_path / ".auto-claude"
        ac_dir.mkdir()

        config.initialize(tmp_path)
        result = project_get_status()

        assert result["project_name"] == tmp_path.resolve().name

    def test_handles_no_specs_dir(self, tmp_path):
        """Returns zero specs when specs directory doesn't exist."""
        ac_dir = tmp_path / ".auto-claude"
        ac_dir.mkdir()

        config.initialize(tmp_path)
        result = project_get_status()

        assert result["specs_count"] == 0


class TestProjectListSpecs:
    """Tests for project_list_specs()."""

    def test_returns_error_when_not_initialized(self):
        """Returns error when no project set."""
        result = project_list_specs()
        assert "error" in result

    def test_lists_specs_with_plan(self, tmp_path):
        """Returns spec list with plan details."""
        ac_dir = tmp_path / ".auto-claude"
        specs_dir = ac_dir / "specs"
        spec_dir = specs_dir / "001-auth"
        spec_dir.mkdir(parents=True)

        plan = {"feature": "User Authentication", "status": "building"}
        (spec_dir / "implementation_plan.json").write_text(json.dumps(plan))
        (spec_dir / "spec.md").write_text("# Auth Spec")

        config.initialize(tmp_path)
        result = project_list_specs()

        assert result["count"] == 1
        spec = result["specs"][0]
        assert spec["name"] == "001-auth"
        assert spec["title"] == "User Authentication"
        assert spec["has_plan"] is True
        assert spec["has_spec"] is True
        assert spec["status"] == "building"

    def test_lists_specs_without_plan(self, tmp_path):
        """Returns spec with default status when no plan exists."""
        ac_dir = tmp_path / ".auto-claude"
        specs_dir = ac_dir / "specs"
        spec_dir = specs_dir / "001-feat"
        spec_dir.mkdir(parents=True)

        config.initialize(tmp_path)
        result = project_list_specs()

        spec = result["specs"][0]
        assert spec["has_plan"] is False
        assert spec["status"] == "pending"
        assert spec["title"] == "001-feat"

    def test_detects_qa_report(self, tmp_path):
        """Returns has_qa_report=True when qa_report.md exists."""
        ac_dir = tmp_path / ".auto-claude"
        specs_dir = ac_dir / "specs"
        spec_dir = specs_dir / "001-feat"
        spec_dir.mkdir(parents=True)
        (spec_dir / "qa_report.md").write_text("# QA Report")

        config.initialize(tmp_path)
        result = project_list_specs()

        assert result["specs"][0]["has_qa_report"] is True

    def test_empty_specs_dir(self, tmp_path):
        """Returns empty list when specs directory is empty."""
        ac_dir = tmp_path / ".auto-claude"
        (ac_dir / "specs").mkdir(parents=True)

        config.initialize(tmp_path)
        result = project_list_specs()

        assert result["count"] == 0
        assert result["specs"] == []

    def test_no_specs_dir(self, tmp_path):
        """Returns message when specs directory doesn't exist."""
        ac_dir = tmp_path / ".auto-claude"
        ac_dir.mkdir()

        config.initialize(tmp_path)
        result = project_list_specs()

        assert result["specs"] == []
        assert "message" in result

    def test_excludes_gitkeep(self, tmp_path):
        """Excludes .gitkeep from specs list."""
        ac_dir = tmp_path / ".auto-claude"
        specs_dir = ac_dir / "specs"
        specs_dir.mkdir(parents=True)
        (specs_dir / ".gitkeep").mkdir()
        (specs_dir / "001-feat").mkdir()

        config.initialize(tmp_path)
        result = project_list_specs()

        assert result["count"] == 1
        assert result["specs"][0]["name"] == "001-feat"

    def test_handles_corrupt_plan(self, tmp_path):
        """Handles corrupt implementation_plan.json gracefully."""
        ac_dir = tmp_path / ".auto-claude"
        specs_dir = ac_dir / "specs"
        spec_dir = specs_dir / "001-feat"
        spec_dir.mkdir(parents=True)
        (spec_dir / "implementation_plan.json").write_text("bad json!")

        config.initialize(tmp_path)
        result = project_list_specs()

        spec = result["specs"][0]
        assert spec["has_plan"] is True
        assert spec["status"] == "pending"  # fallback

    def test_specs_sorted_by_name(self, tmp_path):
        """Specs are returned sorted by directory name."""
        ac_dir = tmp_path / ".auto-claude"
        specs_dir = ac_dir / "specs"
        specs_dir.mkdir(parents=True)
        (specs_dir / "003-third").mkdir()
        (specs_dir / "001-first").mkdir()
        (specs_dir / "002-second").mkdir()

        config.initialize(tmp_path)
        result = project_list_specs()

        names = [s["name"] for s in result["specs"]]
        assert names == ["001-first", "002-second", "003-third"]


class TestProjectGetIndex:
    """Tests for project_get_index()."""

    def test_returns_error_when_not_initialized(self):
        """Returns error when no project set."""
        result = project_get_index()
        assert "error" in result

    def test_returns_index_data(self, tmp_path):
        """Returns project index content."""
        ac_dir = tmp_path / ".auto-claude"
        ac_dir.mkdir()
        index_data = {"files": ["main.py"], "language": "python"}
        (ac_dir / "project_index.json").write_text(json.dumps(index_data))

        config.initialize(tmp_path)
        result = project_get_index()

        assert result["index"] == index_data

    def test_returns_empty_when_no_index(self, tmp_path):
        """Returns empty index when file doesn't exist."""
        ac_dir = tmp_path / ".auto-claude"
        ac_dir.mkdir()

        config.initialize(tmp_path)
        result = project_get_index()

        assert result["index"] == {}
        assert "message" in result
