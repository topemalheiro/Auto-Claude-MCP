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

Note: Module-level placeholders are defined to satisfy CodeQL static analysis.
These trigger the actual import on first access through __getattr__.
"""

from __future__ import annotations

from typing import Any

from .base import AUTO_CONTINUE_DELAY_SECONDS, HUMAN_INTERVENTION_FILE
from .utils import sync_spec_to_source

# Module-level placeholders for CodeQL static analysis.
# These define the symbols as existing at module level (satisfying CodeQL),
# but __getattr__ is called to provide the actual values (Python 3.7+).
debug_memory_system_status: Any = None
get_graphiti_context: Any = None
save_session_memory: Any = None
save_session_to_graphiti: Any = None
run_autonomous_agent: Any = None
run_followup_planner: Any = None
post_session_processing: Any = None
run_agent_session: Any = None
get_latest_commit: Any = None
get_commit_count: Any = None
load_implementation_plan: Any = None
find_subtask_in_plan: Any = None
find_phase_for_subtask: Any = None

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


def __getattr__(name: str) -> Any:
    """Lazy imports to avoid circular dependencies.

    Python 3.7+ calls this for attributes that exist but are set to None
    when accessed via 'from module import name' syntax.
    """
    if name in ("AUTO_CONTINUE_DELAY_SECONDS", "HUMAN_INTERVENTION_FILE"):
        from .base import AUTO_CONTINUE_DELAY_SECONDS, HUMAN_INTERVENTION_FILE

        return (
            AUTO_CONTINUE_DELAY_SECONDS
            if name == "AUTO_CONTINUE_DELAY_SECONDS"
            else HUMAN_INTERVENTION_FILE
        )
    elif name == "run_autonomous_agent":
        from .coder import run_autonomous_agent

        return run_autonomous_agent
    elif name == "debug_memory_system_status":
        from .memory_manager import debug_memory_system_status

        return debug_memory_system_status
    elif name == "get_graphiti_context":
        from .memory_manager import get_graphiti_context

        return get_graphiti_context
    elif name == "save_session_memory":
        from .memory_manager import save_session_memory

        return save_session_memory
    elif name == "save_session_to_graphiti":
        from .memory_manager import save_session_to_graphiti

        return save_session_to_graphiti
    elif name == "run_followup_planner":
        from .planner import run_followup_planner

        return run_followup_planner
    elif name == "post_session_processing":
        from .session import post_session_processing

        return post_session_processing
    elif name == "run_agent_session":
        from .session import run_agent_session

        return run_agent_session
    elif name == "get_latest_commit":
        from .utils import get_latest_commit

        return get_latest_commit
    elif name == "get_commit_count":
        from .utils import get_commit_count

        return get_commit_count
    elif name == "load_implementation_plan":
        from .utils import load_implementation_plan

        return load_implementation_plan
    elif name == "find_subtask_in_plan":
        from .utils import find_subtask_in_plan

        return find_subtask_in_plan
    elif name == "find_phase_for_subtask":
        from .utils import find_phase_for_subtask

        return find_phase_for_subtask
    elif name == "sync_spec_to_source":
        from .utils import sync_spec_to_source

        return sync_spec_to_source
    raise AttributeError(f"module 'agents' has no attribute '{name}'")


def __dir__():
    """Return list of module attributes for autocomplete and dir()."""
    return __all__ + ["AUTO_CONTINUE_DELAY_SECONDS", "HUMAN_INTERVENTION_FILE"]
