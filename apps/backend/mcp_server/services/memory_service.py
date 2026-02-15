"""
Memory Service
===============

Wraps the Graphiti memory system for MCP tool access.
Gracefully handles the case where Graphiti is not enabled/configured.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def _is_graphiti_enabled() -> bool:
    """Check if Graphiti memory is enabled via environment variable."""
    return os.environ.get("GRAPHITI_ENABLED", "").lower() in ("true", "1")


class MemoryService:
    """Service layer for Graphiti-based semantic memory."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self._memory = None

    def _get_disabled_message(self) -> dict:
        """Return a helpful error when Graphiti is not enabled."""
        return {
            "error": "Graphiti memory is not enabled. "
            "Set GRAPHITI_ENABLED=true in your .env file and configure "
            "the required provider settings (LLM and embedder). "
            "See the project documentation for setup instructions."
        }

    async def _get_memory(self):
        """Lazily initialize and return a GraphitiMemory instance."""
        if self._memory is not None:
            return self._memory

        if not _is_graphiti_enabled():
            return None

        try:
            from integrations.graphiti.memory import (
                GraphitiMemory,
                GroupIdMode,
            )

            # Use a dummy spec_dir since we're in project-wide mode
            spec_dir = self.project_dir / ".auto-claude" / "mcp_memory"
            spec_dir.mkdir(parents=True, exist_ok=True)

            memory = GraphitiMemory(
                spec_dir=spec_dir,
                project_dir=self.project_dir,
                group_id_mode=GroupIdMode.PROJECT,
            )

            if not await memory.initialize():
                logger.warning("Failed to initialize Graphiti memory")
                return None

            self._memory = memory
            return memory
        except ImportError:
            logger.warning("Graphiti modules not available")
            return None
        except Exception as e:
            logger.warning("Failed to create Graphiti memory: %s", e)
            return None

    async def search(self, query: str, limit: int = 10) -> dict:
        """Search the project's semantic memory."""
        if not _is_graphiti_enabled():
            return self._get_disabled_message()

        try:
            memory = await self._get_memory()
            if memory is None:
                return {"error": "Could not initialize Graphiti memory"}

            results = await memory._search.get_relevant_context(
                query=query,
                num_results=limit,
            )

            return {
                "success": True,
                "results": results,
                "count": len(results),
            }
        except Exception as e:
            return {"error": f"Memory search failed: {e}"}

    async def add_episode(self, content: str, source: str = "mcp") -> dict:
        """Add a new episode/fact to the project's memory."""
        if not _is_graphiti_enabled():
            return self._get_disabled_message()

        try:
            memory = await self._get_memory()
            if memory is None:
                return {"error": "Could not initialize Graphiti memory"}

            success = await memory.save_session_insights(
                session_num=0,
                insights={
                    "content": content,
                    "source": source,
                    "type": "mcp_episode",
                },
            )

            if success:
                return {"success": True, "message": "Episode added to memory"}
            return {"error": "Failed to save episode to memory"}
        except Exception as e:
            return {"error": f"Failed to add episode: {e}"}

    async def get_recent(self, limit: int = 10) -> dict:
        """Get recent memory entries."""
        if not _is_graphiti_enabled():
            return self._get_disabled_message()

        try:
            memory = await self._get_memory()
            if memory is None:
                return {"error": "Could not initialize Graphiti memory"}

            # Use a broad search to get recent entries
            results = await memory._search.get_relevant_context(
                query="recent project activity and insights",
                num_results=limit,
            )

            return {
                "success": True,
                "results": results,
                "count": len(results),
            }
        except Exception as e:
            return {"error": f"Failed to get recent memory: {e}"}
