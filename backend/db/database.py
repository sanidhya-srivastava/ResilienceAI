from contextlib import contextmanager
import os
from pathlib import Path
import sqlite3
from typing import Iterator

DEFAULT_DB_PATH = "./incidents.db"
MIGRATION_FILE = Path(__file__).parent / "migrations" / "001_initial.sql"


def resolve_db_path(database_url: str | None = None) -> str:
    """Convert a sqlite:/// URL or raw path into a filesystem path for sqlite3."""
    raw = database_url or os.getenv("DATABASE_URL", DEFAULT_DB_PATH)
    if raw.startswith("sqlite:///"):
        return raw.removeprefix("sqlite:///")
    return raw


class Database:
    """SQLite connection manager with WAL mode and foreign key enforcement."""

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = resolve_db_path(db_path)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """Yield a SQLite connection configured with row factory and foreign keys."""
        conn = sqlite3.connect(self.db_path, timeout=10.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys=ON;")
            yield conn
        finally:
            conn.close()

    def init_db(self) -> None:
        """Enable WAL mode once and apply the initial SQL schema migration."""
        ddl = MIGRATION_FILE.read_text(encoding="utf-8")
        with self.connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.executescript(ddl)
            conn.commit()
