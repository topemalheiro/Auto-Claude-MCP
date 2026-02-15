"""
MCP Server Configuration
========================

Manages project context and backend initialization for the MCP server.
The project directory is set once at startup and used by all tools.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Global project context - set once at server startup
_project_dir: Path | None = None
_auto_claude_dir: Path | None = None


def initialize(project_dir: str | Path) -> None:
    """Initialize the MCP server with a project directory.

    This sets up the Python path so backend modules can be imported,
    loads the .env file, and validates the project structure.

    Args:
        project_dir: Path to the user's project directory
    """
    global _project_dir, _auto_claude_dir

    _project_dir = Path(project_dir).resolve()
    if not _project_dir.is_dir():
        raise ValueError(f"Project directory does not exist: {_project_dir}")

    # Add backend to sys.path so existing modules can be imported
    backend_dir = Path(__file__).parent.parent
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    # Load .env if present
    try:
        from cli.utils import import_dotenv

        load_dotenv = import_dotenv()
        env_file = backend_dir / ".env"
        if env_file.exists():
            load_dotenv(env_file)
    except Exception:
        logger.debug("Could not load .env file (non-critical)")

    # Determine .auto-claude directory
    auto_claude = _project_dir / ".auto-claude"
    if not auto_claude.is_dir():
        # Also check legacy 'auto-claude' (no dot prefix)
        alt = _project_dir / "auto-claude"
        if alt.is_dir():
            auto_claude = alt
        else:
            logger.warning(
                "No .auto-claude directory found in %s. "
                "Some tools may not work until the project is initialized.",
                _project_dir,
            )
    _auto_claude_dir = auto_claude

    logger.info("MCP server initialized for project: %s", _project_dir)


def get_project_dir() -> Path:
    """Get the active project directory. Raises if not initialized."""
    if _project_dir is None:
        raise RuntimeError(
            "MCP server not initialized. Call config.initialize() first."
        )
    return _project_dir


def get_auto_claude_dir() -> Path:
    """Get the .auto-claude directory for the active project."""
    if _auto_claude_dir is None:
        raise RuntimeError(
            "MCP server not initialized. Call config.initialize() first."
        )
    return _auto_claude_dir


def get_specs_dir() -> Path:
    """Get the specs directory for the active project."""
    return get_auto_claude_dir() / "specs"


def get_project_index() -> dict:
    """Load and return the project index if available."""
    index_path = get_auto_claude_dir() / "project_index.json"
    if not index_path.exists():
        return {}
    try:
        with open(index_path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load project index: %s", e)
        return {}


def is_initialized() -> bool:
    """Check if the project has been initialized with .auto-claude."""
    try:
        ac_dir = get_auto_claude_dir()
        return ac_dir.is_dir()
    except RuntimeError:
        return False
