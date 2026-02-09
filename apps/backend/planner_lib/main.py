#!/usr/bin/env python3
"""
Implementation Planner
======================

Generates implementation plans from specs by analyzing the task and codebase.
This replaces the initializer's test-generation with subtask-based planning.

The planner:
1. Reads the spec.md to understand what needs to be built
2. Reads project_index.json to understand the codebase structure
3. Reads context.json to know which files are relevant
4. Determines the workflow type (feature, refactor, investigation, etc.)
5. Generates phases and subtasks with proper dependencies
6. Outputs implementation_plan.json

Usage:
    python auto-claude/planner.py --spec-dir auto-claude/specs/001-feature/
"""

import io
import json
import sys
from pathlib import Path

# Configure safe encoding on Windows to handle Unicode characters in output
if sys.platform == "win32":
    for _stream_name in ("stdout", "stderr"):
        _stream = getattr(sys, _stream_name)
        # Method 1: Try reconfigure (works for TTY)
        if hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
                continue
            except (
                AttributeError,
                io.UnsupportedOperation,
                OSError,
            ):  # Stream doesn't support reconfigure
                pass  # no-op
        # Method 2: Wrap with TextIOWrapper for piped output
        try:
            if hasattr(_stream, "buffer"):
                _new_stream = io.TextIOWrapper(
                    _stream.buffer,
                    encoding="utf-8",
                    errors="replace",
                    line_buffering=True,
                )
                setattr(sys, _stream_name, _new_stream)
        except (
            AttributeError,
            io.UnsupportedOperation,
            OSError,
        ):  # Stream doesn't support wrapper
            pass  # no-op
    # Clean up temporary variables
    del _stream_name, _stream
    if "_new_stream" in dir():
        del _new_stream

from implementation_plan import ImplementationPlan
from planner_lib.context import ContextLoader
from planner_lib.generators import get_plan_generator


class ImplementationPlanner:
    """Generates implementation plans from specs."""

    def __init__(self, spec_dir: Path):
        self.spec_dir = spec_dir
        self.context_loader = ContextLoader(spec_dir)
        self.context = None

    def load_context(self):
        """Load all context files from spec directory."""
        self.context = self.context_loader.load_context()
        return self.context

    def generate_plan(self) -> ImplementationPlan:
        """Generate the appropriate plan based on workflow type."""
        if not self.context:
            self.load_context()

        generator = get_plan_generator(self.context, self.spec_dir)
        return generator.generate()

    def save_plan(self, plan: ImplementationPlan) -> Path:
        """Save plan to spec directory."""
        output_path = self.spec_dir / "implementation_plan.json"
        plan.save(output_path)
        print(f"Implementation plan saved to: {output_path}")
        return output_path


def generate_implementation_plan(spec_dir: Path) -> ImplementationPlan:
    """Main entry point for generating an implementation plan."""
    planner = ImplementationPlanner(spec_dir)
    planner.load_context()
    plan = planner.generate_plan()
    planner.save_plan(plan)
    return plan


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate implementation plan from spec"
    )
    parser.add_argument(
        "--spec-dir",
        type=Path,
        required=True,
        help="Directory containing spec.md, project_index.json, context.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path for implementation_plan.json (default: spec-dir/implementation_plan.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print plan without saving",
    )

    args = parser.parse_args()

    planner = ImplementationPlanner(args.spec_dir)
    planner.load_context()
    plan = planner.generate_plan()

    if args.dry_run:
        print(json.dumps(plan.to_dict(), indent=2))
        print("\n---\n")
        print(plan.get_status_summary())
    else:
        output_path = args.output or (args.spec_dir / "implementation_plan.json")
        plan.save(output_path)
        print(f"Plan saved to: {output_path}")
        print("\n" + plan.get_status_summary())


if __name__ == "__main__":
    main()
