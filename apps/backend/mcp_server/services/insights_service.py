"""
Insights Service
=================

Wraps the backend InsightsRunner for MCP tool access.
Captures stdout output since run_with_sdk prints to stdout.
"""

from __future__ import annotations

import contextlib
import io
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class InsightsService:
    """Service layer for codebase insights / AI chat."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir

    async def ask(
        self,
        question: str,
        history: list | None = None,
        model: str = "sonnet",
        thinking_level: str = "medium",
    ) -> dict:
        """Ask an AI question about the codebase.

        IMPORTANT: run_with_sdk prints to stdout, so we capture it.
        """
        try:
            from runners.insights_runner import run_with_sdk

            history = history or []
            captured = io.StringIO()
            with contextlib.redirect_stdout(captured):
                await run_with_sdk(
                    project_dir=str(self.project_dir),
                    message=question,
                    history=history,
                    model=model,
                    thinking_level=thinking_level,
                )

            output = captured.getvalue()

            # Parse out any task suggestions from the output
            task_suggestions = []
            response_lines = []
            for line in output.split("\n"):
                if line.startswith("__TASK_SUGGESTION__:"):
                    try:
                        suggestion_json = line.split("__TASK_SUGGESTION__:", 1)[1]
                        task_suggestions.append(json.loads(suggestion_json))
                    except (json.JSONDecodeError, IndexError):
                        pass
                elif line.startswith("__TOOL_START__:") or line.startswith(
                    "__TOOL_END__:"
                ):
                    # Skip tool markers - they're for the Electron UI
                    pass
                else:
                    response_lines.append(line)

            response_text = "\n".join(response_lines).strip()

            return {
                "success": True,
                "response": response_text,
                "task_suggestions": task_suggestions,
            }
        except ImportError:
            return {"error": "Insights runner module not available"}
        except Exception as e:
            return {"error": str(e)}

    def suggest_tasks(self) -> dict:
        """Get AI-suggested tasks based on project analysis.

        Reads the most recent ideation/insights data if available.
        """
        try:
            ideation_file = (
                self.project_dir / ".auto-claude" / "ideation" / "ideation.json"
            )
            if ideation_file.exists():
                with open(ideation_file, encoding="utf-8") as f:
                    ideation = json.load(f)
                ideas = ideation.get("ideas", [])
                # Convert top ideas to task suggestions
                suggestions = []
                for idea in ideas[:10]:
                    suggestions.append(
                        {
                            "title": idea.get("title", ""),
                            "description": idea.get("description", ""),
                            "category": idea.get("type", "feature"),
                            "impact": idea.get("impact", "medium"),
                            "effort": idea.get("effort", "medium"),
                        }
                    )
                return {"success": True, "suggestions": suggestions}

            return {
                "success": True,
                "suggestions": [],
                "message": "No ideation data available. Run ideation_generate first.",
            }
        except Exception as e:
            return {"error": str(e)}
