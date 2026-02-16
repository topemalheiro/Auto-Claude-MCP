"""
Tests for mcp_server/config.py
==============================

Tests project configuration initialization, directory resolution,
project index loading, and initialization state checks.
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

import mcp_server.config as config


class TestInitialize:
    """Tests for config.initialize()."""

    def setup_method(self):
        """Reset global state before each test."""
        config._project_dir = None
        config._auto_claude_dir = None

    def test_initialize_valid_project_dir(self, tmp_path):
        """Initialize with a valid directory sets the project dir."""
        ac_dir = tmp_path / ".auto-claude"
        ac_dir.mkdir()
        config.initialize(tmp_path)
        assert config.get_project_dir() == tmp_path.resolve()

    def test_initialize_missing_dir_raises_value_error(self, tmp_path):
        """Initialize with nonexistent directory raises ValueError."""
        import pytest

        bad_path = tmp_path / "nonexistent"
        with pytest.raises(ValueError, match="does not exist"):
            config.initialize(bad_path)

    def test_initialize_with_string_path(self, tmp_path):
        """Initialize accepts a string path and resolves it."""
        ac_dir = tmp_path / ".auto-claude"
        ac_dir.mkdir()
        config.initialize(str(tmp_path))
        assert config.get_project_dir() == tmp_path.resolve()

    def test_initialize_finds_auto_claude_dir(self, tmp_path):
        """Initialize locates the .auto-claude directory."""
        ac_dir = tmp_path / ".auto-claude"
        ac_dir.mkdir()
        config.initialize(tmp_path)
        assert config.get_auto_claude_dir() == ac_dir

    def test_initialize_finds_legacy_auto_claude_dir(self, tmp_path):
        """Initialize falls back to legacy auto-claude (no dot prefix)."""
        legacy_dir = tmp_path / "auto-claude"
        legacy_dir.mkdir()
        config.initialize(tmp_path)
        assert config.get_auto_claude_dir() == legacy_dir

    def test_initialize_warns_when_no_auto_claude_dir(self, tmp_path):
        """Initialize still works but warns when no .auto-claude dir exists."""
        config.initialize(tmp_path)
        # Should point to the expected (but missing) .auto-claude path
        assert config._auto_claude_dir == tmp_path / ".auto-claude"


class TestGetProjectDir:
    """Tests for config.get_project_dir()."""

    def setup_method(self):
        config._project_dir = None
        config._auto_claude_dir = None

    def test_get_project_dir_before_initialize_raises(self):
        """get_project_dir raises RuntimeError when not initialized."""
        import pytest

        with pytest.raises(RuntimeError, match="not initialized"):
            config.get_project_dir()

    def test_get_project_dir_after_initialize(self, tmp_path):
        """get_project_dir returns the resolved project path."""
        (tmp_path / ".auto-claude").mkdir()
        config.initialize(tmp_path)
        assert config.get_project_dir() == tmp_path.resolve()


class TestGetAutoClaudeDir:
    """Tests for config.get_auto_claude_dir()."""

    def setup_method(self):
        config._project_dir = None
        config._auto_claude_dir = None

    def test_get_auto_claude_dir_before_initialize_raises(self):
        """get_auto_claude_dir raises RuntimeError when not initialized."""
        import pytest

        with pytest.raises(RuntimeError, match="not initialized"):
            config.get_auto_claude_dir()

    def test_get_auto_claude_dir_after_initialize(self, tmp_path):
        """get_auto_claude_dir returns the .auto-claude path."""
        ac_dir = tmp_path / ".auto-claude"
        ac_dir.mkdir()
        config.initialize(tmp_path)
        assert config.get_auto_claude_dir() == ac_dir


class TestGetSpecsDir:
    """Tests for config.get_specs_dir()."""

    def setup_method(self):
        config._project_dir = None
        config._auto_claude_dir = None

    def test_get_specs_dir_returns_specs_subdir(self, tmp_path):
        """get_specs_dir returns .auto-claude/specs path."""
        ac_dir = tmp_path / ".auto-claude"
        ac_dir.mkdir()
        config.initialize(tmp_path)
        assert config.get_specs_dir() == ac_dir / "specs"


class TestGetProjectIndex:
    """Tests for config.get_project_index()."""

    def setup_method(self):
        config._project_dir = None
        config._auto_claude_dir = None

    def test_get_project_index_loads_valid_json(self, tmp_path):
        """get_project_index loads and returns valid JSON data."""
        ac_dir = tmp_path / ".auto-claude"
        ac_dir.mkdir()
        index_data = {"files": ["main.py"], "language": "python"}
        (ac_dir / "project_index.json").write_text(json.dumps(index_data))
        config.initialize(tmp_path)
        result = config.get_project_index()
        assert result == index_data

    def test_get_project_index_returns_empty_on_missing_file(self, tmp_path):
        """get_project_index returns empty dict when file doesn't exist."""
        ac_dir = tmp_path / ".auto-claude"
        ac_dir.mkdir()
        config.initialize(tmp_path)
        result = config.get_project_index()
        assert result == {}

    def test_get_project_index_returns_empty_on_invalid_json(self, tmp_path):
        """get_project_index returns empty dict on malformed JSON."""
        ac_dir = tmp_path / ".auto-claude"
        ac_dir.mkdir()
        (ac_dir / "project_index.json").write_text("{invalid json!!")
        config.initialize(tmp_path)
        result = config.get_project_index()
        assert result == {}


class TestIsInitialized:
    """Tests for config.is_initialized()."""

    def setup_method(self):
        config._project_dir = None
        config._auto_claude_dir = None

    def test_is_initialized_returns_false_before_init(self):
        """is_initialized returns False when config hasn't been initialized."""
        assert config.is_initialized() is False

    def test_is_initialized_returns_true_with_existing_dir(self, tmp_path):
        """is_initialized returns True when .auto-claude directory exists."""
        ac_dir = tmp_path / ".auto-claude"
        ac_dir.mkdir()
        config.initialize(tmp_path)
        assert config.is_initialized() is True

    def test_is_initialized_returns_false_when_dir_missing(self, tmp_path):
        """is_initialized returns False when .auto-claude dir doesn't exist on disk."""
        config.initialize(tmp_path)
        # _auto_claude_dir is set but directory doesn't exist on disk
        assert config.is_initialized() is False
