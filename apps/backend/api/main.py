"""
Auto Claude API — FastAPI Application
======================================

Main FastAPI application with CORS middleware, Socket.IO integration,
and lifespan events. Serves as the backend for the Next.js web frontend.
"""

from contextlib import asynccontextmanager

import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.agents import router as agents_router
from .routes.changelog import router as changelog_router
from .routes.context import router as context_router
from .routes.env import router as env_router
from .routes.github import router as github_router
from .routes.gitlab import router as gitlab_router
from .routes.health import router as health_router
from .routes.ideation import router as ideation_router
from .routes.insights import router as insights_router
from .routes.projects import router as projects_router
from .routes.roadmap import router as roadmap_router
from .routes.settings import router as settings_router
from .routes.tasks import router as tasks_router
from .routes.terminal import router as terminal_router
from .websocket.agent_ns import register_agent_namespace
from .websocket.events_ns import register_events_namespace
from .websocket.terminal_ns import get_terminal_service, register_terminal_namespace

# Socket.IO async server for real-time communication
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=["http://localhost:3000", "http://localhost:3001"],
)

# Register Socket.IO namespaces
register_terminal_namespace(sio)
register_agent_namespace(sio)
register_events_namespace(sio)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    # Startup
    yield
    # Shutdown — kill all PTY sessions
    await get_terminal_service().kill_all()


app = FastAPI(
    title="Auto Claude API",
    description="Backend API for the Auto Claude web frontend",
    lifespan=lifespan,
)

# CORS middleware for Next.js dev servers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(health_router)
app.include_router(projects_router)
app.include_router(tasks_router)
app.include_router(settings_router)
app.include_router(env_router)
app.include_router(agents_router)
app.include_router(terminal_router)
app.include_router(github_router)
app.include_router(gitlab_router)
app.include_router(roadmap_router)
app.include_router(ideation_router)
app.include_router(insights_router)
app.include_router(changelog_router)
app.include_router(context_router)

# Mount Socket.IO as ASGI sub-application
sio_asgi_app = socketio.ASGIApp(sio, other_asgi_app=app)
