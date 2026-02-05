"""Tests for memory/__init__.py - Session memory system exports."""

import pytest
from pathlib import Path

from memory import (
    # Graphiti helpers
    is_graphiti_memory_enabled,
    # Directory management
    get_memory_dir,
    get_session_insights_dir,
    clear_memory,
    # Session insights
    save_session_insights,
    load_all_insights,
    # Codebase map
    update_codebase_map,
    load_codebase_map,
    # Patterns and gotchas
    append_pattern,
    load_patterns,
    append_gotcha,
    load_gotchas,
    # Summary
    get_memory_summary,
)


class TestMemoryModuleExports:
    """Tests for memory module public API exports."""

    def test_is_graphiti_memory_enabled_export(self):
        """Test that is_graphiti_memory_enabled is exported."""
        assert is_graphiti_memory_enabled is not None

    def test_get_memory_dir_export(self):
        """Test that get_memory_dir is exported."""
        assert get_memory_dir is not None

    def test_get_session_insights_dir_export(self):
        """Test that get_session_insights_dir is exported."""
        assert get_session_insights_dir is not None

    def test_clear_memory_export(self):
        """Test that clear_memory is exported."""
        assert clear_memory is not None

    def test_save_session_insights_export(self):
        """Test that save_session_insights is exported."""
        assert save_session_insights is not None

    def test_load_all_insights_export(self):
        """Test that load_all_insights is exported."""
        assert load_all_insights is not None

    def test_update_codebase_map_export(self):
        """Test that update_codebase_map is exported."""
        assert update_codebase_map is not None

    def test_load_codebase_map_export(self):
        """Test that load_codebase_map is exported."""
        assert load_codebase_map is not None

    def test_append_pattern_export(self):
        """Test that append_pattern is exported."""
        assert append_pattern is not None

    def test_load_patterns_export(self):
        """Test that load_patterns is exported."""
        assert load_patterns is not None

    def test_append_gotcha_export(self):
        """Test that append_gotcha is exported."""
        assert append_gotcha is not None

    def test_load_gotchas_export(self):
        """Test that load_gotchas is exported."""
        assert load_gotchas is not None

    def test_get_memory_summary_export(self):
        """Test that get_memory_summary is exported."""
        assert get_memory_summary is not None

    def test_module_has_all_attribute(self):
        """Test that module has __all__ attribute."""
        import memory

        assert hasattr(memory, "__all__")
        assert isinstance(memory.__all__, list)

    def test_all_exports_exist(self):
        """Test that all exports in __all__ actually exist."""
        import memory

        for name in memory.__all__:
            assert hasattr(memory, name), f"{name} in __all__ but not exported"

    def test_expected_exports_in_all(self):
        """Test that expected exports are in __all__."""
        import memory

        expected = {
            "is_graphiti_memory_enabled",
            "get_memory_dir",
            "get_session_insights_dir",
            "clear_memory",
            "save_session_insights",
            "load_all_insights",
            "update_codebase_map",
            "load_codebase_map",
            "append_pattern",
            "load_patterns",
            "append_gotcha",
            "load_gotchas",
            "get_memory_summary",
        }

        assert set(memory.__all__) >= expected


class TestMemoryModuleImports:
    """Tests for memory module import structure."""

    def test_import_from_submodules_works(self):
        """Test that direct imports from submodules work."""
        # Verify functions are callable and have the same signature
        from memory.codebase_map import load_codebase_map as DirectLoadCodebaseMap
        from memory.graphiti_helpers import is_graphiti_memory_enabled as DirectIsGraphitiEnabled
        from memory.paths import get_memory_dir as DirectGetMemoryDir
        from memory.patterns import append_pattern as DirectAppendPattern
        from memory.sessions import save_session_insights as DirectSaveSessionInsights
        from memory.summary import get_memory_summary as DirectGetMemorySummary

        # Check that all are callable
        assert callable(DirectLoadCodebaseMap)
        assert callable(DirectIsGraphitiEnabled)
        assert callable(DirectGetMemoryDir)
        assert callable(DirectAppendPattern)
        assert callable(DirectSaveSessionInsights)
        assert callable(DirectGetMemorySummary)

        # Check they match the package-level imports
        assert callable(load_codebase_map)
        assert callable(is_graphiti_memory_enabled)
        assert callable(get_memory_dir)
        assert callable(append_pattern)
        assert callable(save_session_insights)
        assert callable(get_memory_summary)

    def test_no_circular_imports(self):
        """Test that importing memory doesn't cause circular imports."""
        import importlib
        import sys

        # Remove from cache if present
        if "memory" in sys.modules:
            del sys.modules["memory"]

        # Should import without issues
        import memory

        assert memory is not None


class TestMemoryModuleFacade:
    """Tests for memory module as a facade."""

    def test_facade_reexports_from_codebase_map(self):
        """Test that memory re-exports codebase_map functions."""
        from memory import load_codebase_map, update_codebase_map
        from memory.codebase_map import (
            load_codebase_map as CodebaseLoad,
            update_codebase_map as CodebaseUpdate,
        )

        assert load_codebase_map is CodebaseLoad
        assert update_codebase_map is CodebaseUpdate

    def test_facade_reexports_from_graphiti_helpers(self):
        """Test that memory re-exports graphiti_helpers functions."""
        from memory import is_graphiti_memory_enabled
        from memory.graphiti_helpers import (
            is_graphiti_memory_enabled as GraphitiHelpersEnabled,
        )

        assert is_graphiti_memory_enabled is GraphitiHelpersEnabled

    def test_facade_reexports_from_paths(self):
        """Test that memory re-exports path functions."""
        from memory import clear_memory, get_memory_dir, get_session_insights_dir
        from memory.paths import (
            clear_memory as PathsClear,
            get_memory_dir as PathsGetDir,
            get_session_insights_dir as PathsGetSessionDir,
        )

        assert clear_memory is PathsClear
        assert get_memory_dir is PathsGetDir
        assert get_session_insights_dir is PathsGetSessionDir

    def test_facade_reexports_from_patterns(self):
        """Test that memory re-exports pattern functions."""
        from memory import append_gotcha, append_pattern, load_gotchas, load_patterns
        from memory.patterns import (
            append_gotcha as PatternsAppendGotcha,
            append_pattern as PatternsAppendPattern,
            load_gotchas as PatternsLoadGotchas,
            load_patterns as PatternsLoadPatterns,
        )

        assert append_gotcha is PatternsAppendGotcha
        assert append_pattern is PatternsAppendPattern
        assert load_gotchas is PatternsLoadGotchas
        assert load_patterns is PatternsLoadPatterns

    def test_facade_reexports_from_sessions(self):
        """Test that memory re-exports session functions."""
        from memory import load_all_insights, save_session_insights
        from memory.sessions import (
            load_all_insights as SessionsLoadAll,
            save_session_insights as SessionsSave,
        )

        assert load_all_insights is SessionsLoadAll
        assert save_session_insights is SessionsSave

    def test_facade_reexports_from_summary(self):
        """Test that memory re-exports summary functions."""
        from memory import get_memory_summary
        from memory.summary import get_memory_summary as SummaryGet

        assert get_memory_summary is SummaryGet


class TestMemoryModuleTypes:
    """Tests for memory module exported function signatures."""

    def test_is_graphiti_memory_enabled_is_callable(self):
        """Test that is_graphiti_memory_enabled is callable."""
        assert callable(is_graphiti_memory_enabled)

    def test_get_memory_dir_is_callable(self):
        """Test that get_memory_dir is callable."""
        assert callable(get_memory_dir)

    def test_clear_memory_is_callable(self):
        """Test that clear_memory is callable."""
        assert callable(clear_memory)

    def test_save_session_insights_is_callable(self):
        """Test that save_session_insights is callable."""
        assert callable(save_session_insights)

    def test_load_all_insights_is_callable(self):
        """Test that load_all_insights is callable."""
        assert callable(load_all_insights)

    def test_update_codebase_map_is_callable(self):
        """Test that update_codebase_map is callable."""
        assert callable(update_codebase_map)

    def test_load_codebase_map_is_callable(self):
        """Test that load_codebase_map is callable."""
        assert callable(load_codebase_map)

    def test_append_pattern_is_callable(self):
        """Test that append_pattern is callable."""
        assert callable(append_pattern)

    def test_append_gotcha_is_callable(self):
        """Test that append_gotcha is callable."""
        assert callable(append_gotcha)

    def test_load_patterns_is_callable(self):
        """Test that load_patterns is callable."""
        assert callable(load_patterns)

    def test_load_gotchas_is_callable(self):
        """Test that load_gotchas is callable."""
        assert callable(load_gotchas)

    def test_get_memory_summary_is_callable(self):
        """Test that get_memory_summary is callable."""
        assert callable(get_memory_summary)


class TestMemoryModuleIntegration:
    """Tests for memory module integration points."""

    def test_is_graphiti_memory_enabled_returns_bool(self, tmp_path: Path):
        """Test that is_graphiti_memory_enabled returns a boolean."""
        result = is_graphiti_memory_enabled()
        assert isinstance(result, bool)

    def test_get_memory_dir_returns_path(self, tmp_path: Path):
        """Test that get_memory_dir returns a Path."""
        result = get_memory_dir(tmp_path)
        assert isinstance(result, Path)

    def test_get_session_insights_dir_returns_path(self, tmp_path: Path):
        """Test that get_session_insights_dir returns a Path."""
        result = get_session_insights_dir(tmp_path)
        assert isinstance(result, Path)

    def test_get_memory_summary_returns_dict(self, tmp_path: Path):
        """Test that get_memory_summary returns a dictionary."""
        # Create a memory directory
        memory_dir = tmp_path / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)

        result = get_memory_summary(tmp_path)
        assert isinstance(result, dict)

    def test_load_patterns_returns_list(self, tmp_path: Path):
        """Test that load_patterns returns a list."""
        result = load_patterns(tmp_path)
        assert isinstance(result, list)

    def test_load_gotchas_returns_list(self, tmp_path: Path):
        """Test that load_gotchas returns a list."""
        result = load_gotchas(tmp_path)
        assert isinstance(result, list)

    def test_load_all_insights_returns_list(self, tmp_path: Path):
        """Test that load_all_insights returns a list."""
        result = load_all_insights(tmp_path)
        assert isinstance(result, list)

    def test_load_codebase_map_returns_dict(self, tmp_path: Path):
        """Test that load_codebase_map returns a dict."""
        result = load_codebase_map(tmp_path)
        assert isinstance(result, dict)
