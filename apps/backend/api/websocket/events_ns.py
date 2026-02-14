"""
Events WebSocket Namespace  (/events)
======================================

General-purpose event namespace for broadcasting application-wide events.

Client → Server
----------------
(none — this namespace is primarily server-push)

Server → Client
----------------
- project:updated        — project metadata changed
- task:statusChanged     — task status transition
- settings:changed       — user settings updated
- rateLimit:detected     — API rate limit hit
- auth:failure           — authentication failure detected
"""

import logging
from typing import Any

import socketio

logger = logging.getLogger(__name__)


class EventsNamespace(socketio.AsyncNamespace):
    """Socket.IO namespace for general application events."""

    def __init__(self) -> None:
        super().__init__("/events")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def on_connect(self, sid: str, environ: dict) -> None:
        logger.info("Events client connected: %s", sid)

    async def on_disconnect(self, sid: str) -> None:
        logger.info("Events client disconnected: %s", sid)

    # ------------------------------------------------------------------
    # Broadcast helpers
    # ------------------------------------------------------------------

    async def broadcast_project_updated(self, data: dict[str, Any]) -> None:
        """Emit project:updated to all connected clients."""
        await self.emit("project:updated", data)

    async def broadcast_task_status_changed(self, data: dict[str, Any]) -> None:
        """Emit task:statusChanged to all connected clients."""
        await self.emit("task:statusChanged", data)

    async def broadcast_settings_changed(self, data: dict[str, Any]) -> None:
        """Emit settings:changed to all connected clients."""
        await self.emit("settings:changed", data)

    async def broadcast_rate_limit(self, data: dict[str, Any]) -> None:
        """Emit rateLimit:detected to all connected clients."""
        await self.emit("rateLimit:detected", data)

    async def broadcast_auth_failure(self, data: dict[str, Any]) -> None:
        """Emit auth:failure to all connected clients."""
        await self.emit("auth:failure", data)


# ------------------------------------------------------------------
# Singleton & registration
# ------------------------------------------------------------------

_events_ns: EventsNamespace | None = None


def get_events_namespace() -> EventsNamespace:
    """Return the singleton EventsNamespace instance."""
    global _events_ns  # noqa: PLW0603
    if _events_ns is None:
        _events_ns = EventsNamespace()
    return _events_ns


def register_events_namespace(sio: socketio.AsyncServer) -> None:
    """Register the /events namespace on the given Socket.IO server."""
    ns = get_events_namespace()
    sio.register_namespace(ns)
    logger.info("Registered /events namespace")
