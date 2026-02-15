"""
Roadmap Service
================

Wraps the backend RoadmapOrchestrator for MCP tool access.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class RoadmapService:
    """Service layer for roadmap generation features."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.roadmap_dir = project_dir / ".auto-claude" / "roadmap"

    async def generate(
        self,
        refresh: bool = False,
        model: str = "sonnet",
        thinking_level: str = "medium",
    ) -> dict:
        """Generate a strategic roadmap for the project."""
        try:
            from runners.roadmap.orchestrator import RoadmapOrchestrator

            orchestrator = RoadmapOrchestrator(
                project_dir=self.project_dir,
                model=model,
                thinking_level=thinking_level,
                refresh=refresh,
            )
            success = await orchestrator.run()

            if success:
                # Load and return the generated roadmap
                return self.get_roadmap()
            return {"error": "Roadmap generation failed. Check logs for details."}
        except ImportError:
            return {"error": "Roadmap runner module not available"}
        except Exception as e:
            return {"error": str(e)}

    def get_roadmap(self) -> dict:
        """Get the current roadmap data from disk."""
        roadmap_file = self.roadmap_dir / "roadmap.json"
        if not roadmap_file.exists():
            return {
                "success": True,
                "data": None,
                "message": "No roadmap generated yet. Use roadmap_generate first.",
            }
        try:
            with open(roadmap_file, encoding="utf-8") as f:
                roadmap = json.load(f)
            return {"success": True, "data": roadmap}
        except (json.JSONDecodeError, OSError) as e:
            return {"error": f"Failed to load roadmap: {e}"}
