"""
Human Review Checkpoint System - Facade
========================================

This is a backward-compatible facade for the refactored review module.
The actual implementation has been split into focused submodules:

- review/state.py - ReviewState class and hash functions
- review/diff_analyzer.py - Markdown extraction utilities
- review/formatters.py - Display/summary functions
- review/reviewer.py - Main orchestration logic
- review/__init__.py - Public API exports

For new code, prefer importing directly from the review package:
    from review import ReviewState, run_review_checkpoint

This facade maintains compatibility with existing imports:
    from review import ReviewState, run_review_checkpoint

Design Principles:
- Block automatic build start until human approval is given
- Persist approval state in review_state.json
- Detect spec changes after approval (requires re-approval)
- Support both interactive and auto-approve modes
- Graceful Ctrl+C handling

Usage:
    # Programmatic use
    from review import ReviewState, run_review_checkpoint

    state = ReviewState.load(spec_dir)
    if not state.is_approved():
        state = run_review_checkpoint(spec_dir)

    # CLI use (for manual review)
    python auto-claude/review.py --spec-dir auto-claude/specs/001-feature
"""

import io
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

# Re-export all public APIs from the review package
from review import (
    ReviewState,
    display_review_status,
    # Display functions
    run_review_checkpoint,
)
from ui import print_status


def main():
    """CLI entry point for manual review."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Human review checkpoint for auto-claude specs"
    )
    parser.add_argument(
        "--spec-dir",
        type=str,
        required=True,
        help="Path to the spec directory",
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Skip interactive review and auto-approve",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show review status without interactive prompt",
    )

    args = parser.parse_args()

    spec_dir = Path(args.spec_dir)
    if not spec_dir.exists():
        print_status(f"Spec directory not found: {spec_dir}", "error")
        sys.exit(1)

    if args.status:
        # Just show status
        display_review_status(spec_dir)
        state = ReviewState.load(spec_dir)
        if state.is_approval_valid(spec_dir):
            print()
            print_status("Ready to build.", "success")
            sys.exit(0)
        else:
            print()
            print_status("Review required before building.", "warning")
            sys.exit(1)

    # Run interactive review
    try:
        state = run_review_checkpoint(spec_dir, auto_approve=args.auto_approve)
        if state.is_approved():
            sys.exit(0)
        else:
            sys.exit(1)
    except KeyboardInterrupt:
        print()
        print_status("Review interrupted. Your feedback has been saved.", "info")
        sys.exit(0)


if __name__ == "__main__":
    main()
