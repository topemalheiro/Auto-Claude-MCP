"""
Spec Creation Module
====================

Modular spec creation pipeline with complexity-based phase selection.

Main Components:
- complexity: Task complexity assessment (AI and heuristic)
- requirements: Interactive and automated requirements gathering
- discovery: Project structure analysis
- context: Relevant file discovery
- writer: Spec document and plan creation
- validator: Validation helpers
- phases: Individual phase implementations
- pipeline: Main orchestration logic

Usage:
    from spec import SpecOrchestrator

    orchestrator = SpecOrchestrator(
        project_dir=Path.cwd(),
        task_description="Add user authentication",
    )

    success = await orchestrator.run()

Note:
    SpecOrchestrator and get_specs_dir are lazy-imported to avoid circular
    dependencies between spec.pipeline and core.client.

    Module-level placeholders (with _ prefix) are defined for CodeQL static
    analysis. The actual exported names (without _ prefix) trigger __getattr__
    for lazy loading.
"""

from typing import Any

from .complexity import (
    Complexity,
    ComplexityAnalyzer,
    ComplexityAssessment,
    run_ai_complexity_assessment,
    save_assessment,
)
from .phases import PhaseExecutor, PhaseResult

# Module-level placeholders for CodeQL static analysis.
_SpecOrchestrator = None  # type: Any
_get_specs_dir = None  # type: Any

# Public names that reference the placeholders above
SpecOrchestrator = _SpecOrchestrator
get_specs_dir = _get_specs_dir

__all__ = [
    # Main orchestrator
    "SpecOrchestrator",
    "get_specs_dir",
    # Complexity assessment
    "Complexity",
    "ComplexityAnalyzer",
    "ComplexityAssessment",
    "run_ai_complexity_assessment",
    "save_assessment",
    # Phase execution
    "PhaseExecutor",
    "PhaseResult",
]


def __getattr__(name: str) -> Any:
    """Lazy imports to avoid circular dependencies with core.client.

    The spec.pipeline module imports from core.client (via agent_runner.py),
    which imports from agents.tools_pkg, which imports from spec.validate_pkg.
    This creates a circular dependency when spec/__init__.py imports
    SpecOrchestrator at module level.

    By deferring these imports via __getattr__, the import chain only
    executes when these symbols are actually accessed, breaking the cycle.
    """
    private_map = {
        "SpecOrchestrator": "_SpecOrchestrator",
        "get_specs_dir": "_get_specs_dir",
    }

    if name in private_map:
        private_name = private_map[name]
        globals()[private_name] = _do_lazy_import(name)
        return globals()[private_name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _do_lazy_import(name: str) -> Any:
    """Perform the actual lazy import for a given name."""
    if name == "SpecOrchestrator":
        from .pipeline import SpecOrchestrator

        return SpecOrchestrator
    if name == "get_specs_dir":
        from .pipeline import get_specs_dir

        return get_specs_dir
    raise AssertionError(f"Unknown lazy import name: {name}")
