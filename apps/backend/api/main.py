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

from .routes.health import router as health_router
from .routes.projects import router as projects_router

# Socket.IO async server for real-time communication
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=["http://localhost:3000", "http://localhost:3001"],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    # Startup
    yield
    # Shutdown


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

# Mount Socket.IO as ASGI sub-application
sio_asgi_app = socketio.ASGIApp(sio, other_asgi_app=app)
