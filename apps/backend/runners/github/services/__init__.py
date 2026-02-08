"""
GitHub Orchestrator Services
============================

Service layer for GitHub automation workflows.

NOTE: Uses lazy imports to avoid circular dependency with context_gatherer.py.
The circular import chain was: orchestrator -> context_gatherer -> services.io_utils
-> services/__init__ -> pr_review_engine -> context_gatherer (circular!)

Module-level placeholders (with _ prefix) are defined for CodeQL static
analysis. The actual exported names (without _ prefix) trigger __getattr__
for lazy loading.
"""

from __future__ import annotations

from typing import Any

# Module-level placeholders for CodeQL static analysis.
_AutoFixProcessor: Any | None = None
_BatchProcessor: Any | None = None
_PRReviewEngine: Any | None = None
_PromptManager: Any | None = None
_ResponseParser: Any | None = None
_TriageEngine: Any | None = None

# Public names that reference the placeholders above
AutoFixProcessor = _AutoFixProcessor
BatchProcessor = _BatchProcessor
PRReviewEngine = _PRReviewEngine
PromptManager = _PromptManager
ResponseParser = _ResponseParser
TriageEngine = _TriageEngine

__all__ = [
    "PromptManager",
    "ResponseParser",
    "PRReviewEngine",
    "TriageEngine",
    "AutoFixProcessor",
    "BatchProcessor",
]


def __getattr__(name: str) -> object:
    """Lazy import handler - loads classes on first access."""
    private_map = {
        "AutoFixProcessor": "_AutoFixProcessor",
        "BatchProcessor": "_BatchProcessor",
        "PRReviewEngine": "_PRReviewEngine",
        "PromptManager": "_PromptManager",
        "ResponseParser": "_ResponseParser",
        "TriageEngine": "_TriageEngine",
    }

    if name in private_map:
        private_name = private_map[name]
        globals()[private_name] = _do_lazy_import(name)
        return globals()[private_name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _do_lazy_import(name: str) -> Any:
    """Perform the actual lazy import for a given name."""
    if name == "AutoFixProcessor":
        from .autofix_processor import AutoFixProcessor

        return AutoFixProcessor
    if name == "BatchProcessor":
        from .batch_processor import BatchProcessor

        return BatchProcessor
    if name == "PRReviewEngine":
        from .pr_review_engine import PRReviewEngine

        return PRReviewEngine
    if name == "PromptManager":
        from .prompt_manager import PromptManager

        return PromptManager
    if name == "ResponseParser":
        from .response_parsers import ResponseParser

        return ResponseParser
    if name == "TriageEngine":
        from .triage_engine import TriageEngine

        return TriageEngine
    raise AssertionError(f"Unknown lazy import name: {name}")
