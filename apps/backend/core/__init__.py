"""
Core Framework Module
=====================

Core components for the Auto Claude autonomous coding framework.

Note: We use lazy imports here because the full agent module has many dependencies
that may not be needed for basic operations.
"""

from typing import Any

# Module-level placeholders for CodeQL static analysis.
# The actual exported names trigger __getattr__ for lazy loading.
_run_autonomous_agent: Any | None = None
_run_followup_planner: Any | None = None
_WorktreeManager: Any | None = None

# Public names that reference the placeholders above
run_autonomous_agent = _run_autonomous_agent
run_followup_planner = _run_followup_planner
WorktreeManager = _WorktreeManager

__all__ = [
    "run_autonomous_agent",
    "run_followup_planner",
    "WorktreeManager",
    "create_claude_client",
    "ClaudeClient",
]


def __getattr__(name: str) -> Any:
    """Lazy imports to avoid circular dependencies and heavy imports."""
    private_map = {
        "run_autonomous_agent": "_run_autonomous_agent",
        "run_followup_planner": "_run_followup_planner",
        "WorktreeManager": "_WorktreeManager",
    }

    if name in private_map:
        private_name = private_map[name]
        globals()[private_name] = _do_lazy_import(name)
        return globals()[private_name]

    if name in ("create_claude_client", "ClaudeClient"):
        from . import client as _client

        return getattr(_client, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _do_lazy_import(name: str) -> Any:
    """Perform the actual lazy import for a given name."""
    if name == "run_autonomous_agent":
        from .agent import run_autonomous_agent

        return run_autonomous_agent
    if name == "run_followup_planner":
        from .agent import run_followup_planner

        return run_followup_planner
    if name == "WorktreeManager":
        from .worktree import WorktreeManager

        return WorktreeManager
    raise AssertionError(f"Unknown lazy import name: {name}")
