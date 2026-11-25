"""Shared dependencies for FastAPI routers."""
from __future__ import annotations

from functools import lru_cache

from backend.db.database import Database


@lru_cache(maxsize=1)
def get_database() -> Database:
    """Return the singleton Database instance."""
    return Database()


def get_db() -> Database:
    """FastAPI dependency returning the active Database manager."""
    return get_database()
