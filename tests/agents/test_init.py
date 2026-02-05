"""Tests for agents.__init__ module lazy import functionality."""

import sys
import importlib
from unittest.mock import patch, MagicMock
import pytest


class TestModuleInitLazyImports:
    """Test __getattr__ lazy import behavior in agents/__init__.py."""

    def setup_method(self):
        """Clear agents module from cache before each test."""
        # Remove agents module and all lazy-loaded submodules from cache
        modules_to_remove = [
            "agents",
            "agents.coder",
            "agents.planner",
            "agents.session",
            "agents.memory_manager",
            "agents.utils",
            "agents.base",
        ]
        for mod in modules_to_remove:
            if mod in sys.modules:
                del sys.modules[mod]

    def test_all_expected_symbols_in___all__(self):
        """Test that __all__ contains all expected symbols."""
        import agents

        expected_symbols = {
            # Main API
            "run_autonomous_agent",
            "run_followup_planner",
            # Memory
            "debug_memory_system_status",
            "get_graphiti_context",
            "save_session_memory",
            "save_session_to_graphiti",
            # Session
            "run_agent_session",
            "post_session_processing",
            # Utils
            "get_latest_commit",
            "get_commit_count",
            "load_implementation_plan",
            "find_subtask_in_plan",
            "find_phase_for_subtask",
            "sync_spec_to_source",
            # Constants
            "AUTO_CONTINUE_DELAY_SECONDS",
            "HUMAN_INTERVENTION_FILE",
        }

        assert set(agents.__all__) == expected_symbols

    def test_explicit_import_sync_spec_to_source(self):
        """Test that sync_spec_to_source is explicitly imported (CodeQL requirement)."""
        import agents

        # sync_spec_to_source should be available without triggering __getattr__
        assert hasattr(agents, "sync_spec_to_source")
        assert callable(agents.sync_spec_to_source)

    def test_lazy_import_constants_from_base(self):
        """Test lazy import of constants from agents.base."""
        import agents

        # Constants should not be imported until accessed
        assert "agents.base" not in sys.modules

        # Access first constant
        delay = agents.AUTO_CONTINUE_DELAY_SECONDS
        assert "agents.base" in sys.modules
        assert delay == 3

        # Access second constant - module already loaded
        pause_file = agents.HUMAN_INTERVENTION_FILE
        assert pause_file == "PAUSE"

    def test_lazy_import_run_autonomous_agent(self):
        """Test lazy import of run_autonomous_agent from agents.coder."""
        import agents

        # Module should not be imported until accessed
        assert "agents.coder" not in sys.modules

        # Access the function
        func = agents.run_autonomous_agent
        assert "agents.coder" in sys.modules
        assert callable(func)

    def test_lazy_import_run_followup_planner(self):
        """Test lazy import of run_followup_planner from agents.planner."""
        import agents

        assert "agents.planner" not in sys.modules

        func = agents.run_followup_planner
        assert "agents.planner" in sys.modules
        assert callable(func)

    def test_lazy_import_session_functions(self):
        """Test lazy import of session functions from agents.session."""
        import agents

        assert "agents.session" not in sys.modules

        # Access one function
        run_session = agents.run_agent_session
        assert "agents.session" in sys.modules
        assert callable(run_session)

        # Access another - module already loaded
        post_proc = agents.post_session_processing
        assert callable(post_proc)

    def test_lazy_import_memory_functions(self):
        """Test lazy import of memory functions from agents.memory_manager."""
        import agents

        assert "agents.memory_manager" not in sys.modules

        # Access each memory function
        debug_func = agents.debug_memory_system_status
        assert "agents.memory_manager" in sys.modules
        assert callable(debug_func)

        get_ctx = agents.get_graphiti_context
        assert callable(get_ctx)

        save_mem = agents.save_session_memory
        assert callable(save_mem)

        save_graph = agents.save_session_to_graphiti
        assert callable(save_graph)

    def test_lazy_import_utility_functions(self):
        """Test lazy import of utility functions from agents.utils."""
        import agents

        # Access each utility function (except sync_spec_to_source which is explicit)
        latest_commit = agents.get_latest_commit
        assert callable(latest_commit)

        commit_count = agents.get_commit_count
        assert callable(commit_count)

        load_plan = agents.load_implementation_plan
        assert callable(load_plan)

        find_subtask = agents.find_subtask_in_plan
        assert callable(find_subtask)

        find_phase = agents.find_phase_for_subtask
        assert callable(find_phase)

    def test_imports_deferred_until_accessed(self):
        """Test that submodules are not imported until symbols are accessed."""
        import agents

        # After importing agents, submodules should not be loaded
        # (except base because sync_spec_to_source is explicitly imported)
        assert "agents.coder" not in sys.modules
        assert "agents.planner" not in sys.modules
        assert "agents.session" not in sys.modules
        assert "agents.memory_manager" not in sys.modules

        # Only after accessing symbols
        _ = agents.run_autonomous_agent
        _ = agents.run_followup_planner
        _ = agents.run_agent_session
        _ = agents.get_graphiti_context

        # Now they should be loaded
        assert "agents.coder" in sys.modules
        assert "agents.planner" in sys.modules
        assert "agents.session" in sys.modules
        assert "agents.memory_manager" in sys.modules

    def test_attribute_error_for_invalid_symbol(self):
        """Test that AttributeError is raised for invalid symbols."""
        import agents

        with pytest.raises(AttributeError, match="module 'agents' has no attribute 'nonexistent'"):
            _ = agents.nonexistent

    def test_attribute_error_message_format(self):
        """Test that AttributeError message has correct format."""
        import agents

        with pytest.raises(AttributeError) as exc_info:
            _ = agents.invalid_name

        assert "module 'agents' has no attribute 'invalid_name'" in str(exc_info.value)

    def test_getattr_returns_correct_type_for_constants(self):
        """Test that __getattr__ returns correct types for constants."""
        import agents

        delay = agents.AUTO_CONTINUE_DELAY_SECONDS
        assert isinstance(delay, int)

        file = agents.HUMAN_INTERVENTION_FILE
        assert isinstance(file, str)

    def test_getattr_returns_callables_for_functions(self):
        """Test that __getattr__ returns callables for functions."""
        import agents

        assert callable(agents.run_autonomous_agent)
        assert callable(agents.run_followup_planner)
        assert callable(agents.run_agent_session)
        assert callable(agents.post_session_processing)
        assert callable(agents.debug_memory_system_status)
        assert callable(agents.get_graphiti_context)
        assert callable(agents.save_session_memory)
        assert callable(agents.save_session_to_graphiti)
        assert callable(agents.get_latest_commit)
        assert callable(agents.get_commit_count)
        assert callable(agents.load_implementation_plan)
        assert callable(agents.find_subtask_in_plan)
        assert callable(agents.find_phase_for_subtask)

    def test_module_dir_includes_all_symbols(self):
        """Test that dir() includes expected module attributes.

        Note: Lazy imports via __getattr__ don't appear in dir() by design.
        This is expected Python behavior - __getattr__ is a fallback mechanism
        that only runs when an attribute isn't found through normal lookup.
        """
        import agents

        # dir() will show standard module attributes
        dir_result = dir(agents)

        # Standard module attributes should be present
        assert "__all__" in dir_result
        assert "__doc__" in dir_result
        assert "__file__" in dir_result
        assert "__getattr__" in dir_result

        # But lazy-imported symbols should still be accessible via getattr
        for symbol in agents.__all__:
            value = getattr(agents, symbol)
            assert value is not None

    def test_module_has_docstring(self):
        """Test that module has proper documentation."""
        import agents

        assert agents.__doc__ is not None
        assert "lazy imports" in agents.__doc__.lower()

    def test_reloading_module_preserves_lazy_imports(self):
        """Test that reloading the module preserves lazy import behavior."""
        import agents

        # Access a symbol to load its module
        _ = agents.run_autonomous_agent
        assert "agents.coder" in sys.modules

        # Reload agents module
        importlib.reload(agents)

        # Clear coder module
        if "agents.coder" in sys.modules:
            del sys.modules["agents.coder"]

        # Access again - should trigger lazy import again
        assert "agents.coder" not in sys.modules
        _ = agents.run_autonomous_agent
        assert "agents.coder" in sys.modules

    def test_star_import_works(self):
        """Test that 'from agents import *' imports all symbols."""
        # Clear any cached imports
        if "agents" in sys.modules:
            del sys.modules["agents"]

        # Use exec to do star import in isolated namespace
        namespace = {}
        exec("from agents import *", namespace)

        # Check that all __all__ symbols are imported
        import agents as agents_module
        for symbol in agents_module.__all__:
            assert symbol in namespace

    def test_all_symbols_accessible_via_dot_notation(self):
        """Test that all symbols in __all__ are accessible via dot notation."""
        import agents

        for symbol in agents.__all__:
            # Should not raise AttributeError
            assert hasattr(agents, symbol)
            _ = getattr(agents, symbol)


class TestModuleInitIntegration:
    """Integration tests for agents.__init__ module."""

    def setup_method(self):
        """Clear agents module from cache before each test."""
        modules_to_remove = [
            "agents",
            "agents.coder",
            "agents.planner",
            "agents.session",
            "agents.memory_manager",
            "agents.utils",
            "agents.base",
        ]
        for mod in modules_to_remove:
            if mod in sys.modules:
                del sys.modules[mod]

    def test_import_order_independence(self):
        """Test that import order doesn't affect lazy loading."""
        # Import in different order than defined in __all__
        import agents

        # Access a memory function first
        _ = agents.get_graphiti_context
        assert "agents.memory_manager" in sys.modules

        # Then access coder
        _ = agents.run_autonomous_agent
        assert "agents.coder" in sys.modules

        # All should still work
        assert callable(agents.run_followup_planner)
        assert callable(agents.post_session_processing)

    def test_concurrent_access_thread_safety(self):
        """Test that lazy imports handle concurrent access gracefully."""
        import agents
        import threading

        results = {}
        errors = {}

        def access_symbol(symbol_name):
            try:
                import agents as ag
                value = getattr(ag, symbol_name)
                results[symbol_name] = value
            except Exception as e:
                errors[symbol_name] = e

        # Access multiple symbols from different threads
        threads = []
        symbols = [
            "run_autonomous_agent",
            "run_followup_planner",
            "run_agent_session",
            "get_graphiti_context",
        ]

        for symbol in symbols:
            t = threading.Thread(target=access_symbol, args=(symbol,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All should succeed
        assert len(errors) == 0
        assert len(results) == len(symbols)
        for symbol in symbols:
            assert symbol in results
            assert callable(results[symbol])
