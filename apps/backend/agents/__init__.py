"""
Agents Module
=============

Modular agent system for autonomous coding.

This module provides:
- run_autonomous_agent: Main coder agent loop
- run_followup_planner: Follow-up planner for completed specs
- Memory management (Graphiti + file-based fallback)
- Session management and post-processing
- Utility functions for git and plan management

Uses lazy imports to avoid circular dependencies.
"""

from __future__ import annotations

# Lazy-loaded imports via __getattr__ below
from .base import AUTO_CONTINUE_DELAY_SECONDS, HUMAN_INTERVENTION_FILE
from .utils import sync_spec_to_source

# Cache for lazily imported modules
__all__ = [
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
]

# Module cache for lazy imports
_module_cache = {}


def __getattr__(name: str):
    """Lazy imports to avoid circular dependencies.

    This is called when an attribute is accessed but not found in the module.
    Python 3.7+ calls this for attributes that don't exist.
    """
    # Return cached value if available
    if name in _module_cache:
        return _module_cache[name]

    # Constants (not lazy-loaded, already imported)
    if name in ("AUTO_CONTINUE_DELAY_SECONDS", "HUMAN_INTERVENTION_FILE"):
        from .base import AUTO_CONTINUE_DELAY_SECONDS, HUMAN_INTERVENTION_FILE

        value = (
            AUTO_CONTINUE_DELAY_SECONDS
            if name == "AUTO_CONTINUE_DELAY_SECONDS"
            else HUMAN_INTERVENTION_FILE
        )
        _module_cache[name] = value
        return value

    # Utils (not lazy-loaded, already imported)
    if name == "sync_spec_to_source":
        from .utils import sync_spec_to_source

        _module_cache[name] = sync_spec_to_source
        return sync_spec_to_source

    # Lazy imports for submodules
    if name == "run_autonomous_agent":
        # Import the module first to ensure it's registered in sys.modules
        # This is required by tests that check for 'agents.coder' in sys.modules
        from . import coder

        _module_cache[name] = coder.run_autonomous_agent
        return coder.run_autonomous_agent

    if name in ("debug_memory_system_status", "get_graphiti_context"):
        from . import memory_manager

        if name == "debug_memory_system_status":
            _module_cache[name] = memory_manager.debug_memory_system_status
            return memory_manager.debug_memory_system_status
        else:  # get_graphiti_context
            _module_cache[name] = memory_manager.get_graphiti_context
            return memory_manager.get_graphiti_context

    if name in ("save_session_memory", "save_session_to_graphiti"):
        from . import memory_manager

        if name == "save_session_memory":
            _module_cache[name] = memory_manager.save_session_memory
            return memory_manager.save_session_memory
        else:  # save_session_to_graphiti
            _module_cache[name] = memory_manager.save_session_to_graphiti
            return memory_manager.save_session_to_graphiti

    if name == "run_followup_planner":
        # Import the module first to ensure it's registered in sys.modules
        from . import planner

        _module_cache[name] = planner.run_followup_planner
        return planner.run_followup_planner

    if name in ("post_session_processing", "run_agent_session"):
        from . import session

        if name == "post_session_processing":
            _module_cache[name] = session.post_session_processing
            return session.post_session_processing
        else:  # run_agent_session
            _module_cache[name] = session.run_agent_session
            return session.run_agent_session

    if name in ("get_latest_commit", "get_commit_count"):
        from . import utils

        if name == "get_latest_commit":
            _module_cache[name] = utils.get_latest_commit
            return utils.get_latest_commit
        else:  # get_commit_count
            _module_cache[name] = utils.get_commit_count
            return utils.get_commit_count

    if name == "load_implementation_plan":
        from . import utils

        _module_cache[name] = utils.load_implementation_plan
        return utils.load_implementation_plan

    if name in ("find_subtask_in_plan", "find_phase_for_subtask"):
        from . import utils

        if name == "find_subtask_in_plan":
            _module_cache[name] = utils.find_subtask_in_plan
            return utils.find_subtask_in_plan
        else:  # find_phase_for_subtask
            _module_cache[name] = utils.find_phase_for_subtask
            return utils.find_phase_for_subtask

    raise AttributeError(f"module 'agents' has no attribute '{name}'")


def __dir__():
    """Return list of module attributes for autocomplete and dir()."""
    return __all__ + ["AUTO_CONTINUE_DELAY_SECONDS", "HUMAN_INTERVENTION_FILE"]
