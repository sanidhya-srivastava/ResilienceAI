"""FastAPI application entrypoint and router registration."""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.deps import get_database
from backend.api.routers import disaster, incidents, websocket


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Initialize SQLite schema on application startup."""
    get_database().init_db()
    yield


app = FastAPI(
    title="ResilienceAI API",
    description="Multi-agent AI disaster recovery simulator",
    version="0.1.0",
    lifespan=lifespan,
)

cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(disaster.router)
app.include_router(incidents.router)
app.include_router(websocket.router)


@app.get("/health")
async def health_check() -> dict:
    """Return service health and current mock mode status."""
    return {
        "status": "ok",
        "version": "0.1.0",
        "mock_mode": os.getenv("MOCK_MODE", "true").lower() == "true",
    }
