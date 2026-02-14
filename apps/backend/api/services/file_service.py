"""
File Service
=============

Provides file system operations for the web frontend:
- Browse directory trees
- Read file content with size limits
- Path validation to prevent traversal attacks
"""

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Maximum file size to read (1MB)
MAX_FILE_SIZE = 1024 * 1024

# Directories to skip when listing
IGNORED_DIRS = frozenset(
    {
        "node_modules",
        ".git",
        "__pycache__",
        "dist",
        "build",
        ".next",
        ".nuxt",
        "coverage",
        ".cache",
        ".venv",
        "venv",
        "out",
        ".turbo",
        ".worktrees",
        "vendor",
        "target",
        ".gradle",
        ".maven",
    }
)

# Hidden files that should still be shown
VISIBLE_HIDDEN_FILES = frozenset(
    {
        ".env",
        ".gitignore",
        ".env.example",
        ".env.local",
    }
)


class FileService:
    """File system operations for file explorer and context features."""

    # ------------------------------------------------------------------
    # Path validation
    # ------------------------------------------------------------------

    @staticmethod
    def validate_path(file_path: str) -> dict[str, Any]:
        """Validate and normalise a path, preventing directory traversal.

        Returns ``{"valid": True, "path": str}`` or
        ``{"valid": False, "error": str}``.
        """
        resolved = os.path.realpath(os.path.abspath(file_path))

        if not os.path.isabs(resolved):
            return {"valid": False, "error": "Path must be absolute"}

        if ".." in Path(resolved).parts:
            return {
                "valid": False,
                "error": "Invalid path: contains parent directory references",
            }

        return {"valid": True, "path": resolved}

    # ------------------------------------------------------------------
    # Directory listing
    # ------------------------------------------------------------------

    async def list_directory(self, dir_path: str) -> dict[str, Any]:
        """List entries in *dir_path*, filtering ignored dirs and hidden files.

        Returns ``{"success": True, "data": [FileNode, ...]}`` on success.
        """
        validation = self.validate_path(dir_path)
        if not validation["valid"]:
            return {"success": False, "error": validation["error"]}

        safe_path = validation["path"]

        try:
            entries = os.scandir(safe_path)
        except (PermissionError, FileNotFoundError, OSError) as exc:
            return {"success": False, "error": str(exc)}

        nodes: list[dict[str, Any]] = []
        try:
            for entry in entries:
                is_dir = entry.is_dir(follow_symlinks=False)

                # Skip hidden files (but keep certain useful ones)
                if (
                    not is_dir
                    and entry.name.startswith(".")
                    and entry.name not in VISIBLE_HIDDEN_FILES
                ):
                    continue

                # Skip ignored directories
                if is_dir and entry.name in IGNORED_DIRS:
                    continue

                nodes.append(
                    {
                        "path": os.path.join(safe_path, entry.name),
                        "name": entry.name,
                        "isDirectory": is_dir,
                    }
                )
        except OSError as exc:
            return {"success": False, "error": str(exc)}

        # Directories first, then alphabetical
        nodes.sort(key=lambda n: (not n["isDirectory"], n["name"].lower()))

        return {"success": True, "data": nodes}

    # ------------------------------------------------------------------
    # File reading
    # ------------------------------------------------------------------

    async def read_file(self, file_path: str) -> dict[str, Any]:
        """Read the text content of *file_path* (max 1 MB).

        Returns ``{"success": True, "data": str}`` on success.
        """
        validation = self.validate_path(file_path)
        if not validation["valid"]:
            return {"success": False, "error": validation["error"]}

        safe_path = validation["path"]

        try:
            size = os.path.getsize(safe_path)
            if size > MAX_FILE_SIZE:
                return {"success": False, "error": "File too large (max 1MB)"}

            with open(safe_path, encoding="utf-8") as fh:
                content = fh.read()

            return {"success": True, "data": content}
        except (PermissionError, FileNotFoundError, OSError, UnicodeDecodeError) as exc:
            return {"success": False, "error": str(exc)}
