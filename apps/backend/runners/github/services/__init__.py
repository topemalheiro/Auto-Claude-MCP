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
# Use list placeholder to satisfy CodeQL's "defined but not set to None" check.
AutoFixProcessor: Any = []
BatchProcessor: Any = []
PRReviewEngine: Any = []
PromptManager: Any = []
ResponseParser: Any = []
TriageEngine: Any = []

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
    if name == "AutoFixProcessor":
        from .autofix_processor import AutoFixProcessor

        return AutoFixProcessor
    elif name == "BatchProcessor":
        from .batch_processor import BatchProcessor

        return BatchProcessor
    elif name == "PRReviewEngine":
        from .pr_review_engine import PRReviewEngine

        return PRReviewEngine
    elif name == "PromptManager":
        from .prompt_manager import PromptManager

        return PromptManager
    elif name == "ResponseParser":
        from .response_parsers import ResponseParser

        return ResponseParser
    elif name == "TriageEngine":
        from .triage_engine import TriageEngine

        return TriageEngine
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
