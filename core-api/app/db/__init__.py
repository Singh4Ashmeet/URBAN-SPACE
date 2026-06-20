"""SQLAlchemy engine and session management for UrbanShield Core API."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = Path(os.environ.get("URBANSHIELD_DATA_DIR", ROOT / ".data"))
DB_PATH = Path(os.environ.get("URBANSHIELD_CORE_DB", DATA_DIR / "urbanshield-core.sqlite3"))


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


def get_database_url() -> str:
    """Return the SQLAlchemy database URL."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{DB_PATH}"


def _set_sqlite_pragmas(dbapi_connection, connection_record):
    """Configure SQLite pragmas on every new raw connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode = PERSIST")
    cursor.execute("PRAGMA synchronous = NORMAL")
    cursor.execute("PRAGMA temp_store = MEMORY")
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()


engine = create_engine(
    get_database_url(),
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
)
event.listen(engine, "connect", _set_sqlite_pragmas)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
