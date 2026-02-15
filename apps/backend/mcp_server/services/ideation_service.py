"""
Ideation Service
=================

Wraps the backend IdeationOrchestrator for MCP tool access.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Valid ideation types
VALID_IDEATION_TYPES = [
    "low_hanging_fruit",
    "ui_ux_improvements",
    "high_value_features",
]


class IdeationService:
    """Service layer for AI-powered ideation generation."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.ideation_dir = project_dir / ".auto-claude" / "ideation"

    async def generate(
        self,
        types: list[str] | None = None,
        refresh: bool = False,
        model: str = "sonnet",
        thinking_level: str = "medium",
    ) -> dict:
        """Generate ideas for project improvements."""
        try:
            from ideation import IdeationOrchestrator

            # Validate types
            enabled_types = types or VALID_IDEATION_TYPES
            invalid = [t for t in enabled_types if t not in VALID_IDEATION_TYPES]
            if invalid:
                return {
                    "error": f"Invalid ideation types: {invalid}. "
                    f"Valid types: {VALID_IDEATION_TYPES}"
                }

            orchestrator = IdeationOrchestrator(
                project_dir=self.project_dir,
                enabled_types=enabled_types,
                model=model,
                thinking_level=thinking_level,
                refresh=refresh,
            )
            success = await orchestrator.run()

            if success:
                return self.get_ideation()
            return {"error": "Ideation generation failed. Check logs for details."}
        except ImportError:
            return {"error": "Ideation module not available"}
        except Exception as e:
            return {"error": str(e)}

    def get_ideation(self) -> dict:
        """Get previously generated ideation results from disk."""
        ideation_file = self.ideation_dir / "ideation.json"
        if not ideation_file.exists():
            return {
                "success": True,
                "data": None,
                "message": "No ideation data yet. Use ideation_generate first.",
            }
        try:
            with open(ideation_file, encoding="utf-8") as f:
                ideation = json.load(f)
            return {"success": True, "data": ideation}
        except (json.JSONDecodeError, OSError) as e:
            return {"error": f"Failed to load ideation data: {e}"}
