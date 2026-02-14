"""
Settings Routes
================

REST endpoints for application settings. Mirrors the data contract from
the Electron IPC handlers (settings-handlers.ts).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/settings", tags=["settings"])

# ---------------------------------------------------------------------------
# Store — JSON-file-backed app settings
# ---------------------------------------------------------------------------

_STORE_DIR = Path.home() / ".auto-claude-web"
_SETTINGS_PATH = _STORE_DIR / "settings.json"

# Default application settings (mirrors DEFAULT_APP_SETTINGS from the Electron app)
_DEFAULT_SETTINGS: dict[str, Any] = {
    "defaultModel": "claude-sonnet-4-20250514",
    "selectedAgentProfile": "auto",
    "theme": "default",
    "colorMode": "dark",
    "language": "en",
    "spellCheckEnabled": True,
    "spellCheckLanguage": "en-US",
    "showTerminalTimestamps": False,
    "maxParallelAgents": 1,
    "autoStartQA": True,
    "autoStartFix": True,
    "maxQACycles": 3,
    "enableSounds": True,
    "enableNotifications": True,
}


def _load_settings() -> dict[str, Any]:
    """Load app settings from disk, merged with defaults."""
    settings = dict(_DEFAULT_SETTINGS)
    if _SETTINGS_PATH.exists():
        try:
            saved = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
            settings.update(saved)
        except (json.JSONDecodeError, OSError):
            pass
    return settings


def _save_settings(settings: dict[str, Any]) -> None:
    """Persist app settings to disk."""
    _STORE_DIR.mkdir(parents=True, exist_ok=True)
    _SETTINGS_PATH.write_text(
        json.dumps(settings, indent=2, default=str), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class SettingsUpdate(BaseModel):
    """Partial settings update — all fields optional."""

    model_config = {"extra": "allow"}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("")
async def get_settings() -> dict[str, Any]:
    """Read application settings, merged with defaults."""
    settings = _load_settings()
    return {"success": True, "data": settings}


@router.put("")
async def update_settings(body: SettingsUpdate) -> dict[str, Any]:
    """Save application settings (partial update)."""
    settings = _load_settings()
    settings.update(body.model_dump(exclude_unset=True))
    _save_settings(settings)
    return {"success": True, "data": settings}
