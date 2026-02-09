#!/usr/bin/env python3
"""
AI-Enhanced Project Analyzer - CLI Entry Point

Runs AI analysis to extract deep insights after programmatic analysis.
Uses Claude Agent SDK for intelligent codebase understanding.

Example:
    # Run full analysis
    python ai_analyzer_runner.py --project-dir /path/to/project

    # Run specific analyzers only
    python ai_analyzer_runner.py --analyzers security performance

    # Skip cache
    python ai_analyzer_runner.py --skip-cache
"""

import asyncio
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


def main() -> int:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="AI-Enhanced Project Analyzer")
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=Path.cwd(),
        help="Project directory to analyze",
    )
    parser.add_argument(
        "--index",
        type=str,
        default="comprehensive_analysis.json",
        help="Path to programmatic analysis JSON",
    )
    parser.add_argument(
        "--skip-cache", action="store_true", help="Skip cached results and re-analyze"
    )
    parser.add_argument(
        "--analyzers",
        nargs="+",
        help="Run only specific analyzers (code_relationships, business_logic, etc.)",
    )

    args = parser.parse_args()

    # Load programmatic analysis
    index_path = args.project_dir / args.index
    if not index_path.exists():
        print(f"✗ Error: Programmatic analysis not found: {index_path}")
        print(f"Run: python analyzer.py --project-dir {args.project_dir} --index")
        return 1

    project_index = json.loads(index_path.read_text(encoding="utf-8"))

    # Import here to avoid import errors if dependencies are missing
    try:
        from ai_analyzer import AIAnalyzerRunner
    except ImportError as e:
        print(f"✗ Error: Failed to import AI analyzer: {e}")
        print("Make sure all dependencies are installed.")
        return 1

    # Create and run analyzer
    analyzer = AIAnalyzerRunner(args.project_dir, project_index)

    # Run async analysis
    insights = asyncio.run(
        analyzer.run_full_analysis(
            skip_cache=args.skip_cache, selected_analyzers=args.analyzers
        )
    )

    # Print summary
    analyzer.print_summary(insights)

    return 0


if __name__ == "__main__":
    exit(main())
