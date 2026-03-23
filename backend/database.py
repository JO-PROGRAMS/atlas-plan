"""
backend/database.py
SQLAlchemy engine + session factory for Atlas local SQLite database.
"""

from __future__ import annotations

import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# ── Path resolution ──────────────────────────────────────────────────────────
# DB lives next to the backend/ package, in the Atlas root directory.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get("ATLAS_DB_PATH", os.path.join(_ROOT, "atlas_tasks.db"))
DATABASE_URL = f"sqlite:///{DB_PATH}"

# ── Engine ───────────────────────────────────────────────────────────────────
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # required for SQLite + FastAPI
    echo=False,
)

# Enable WAL mode for SQLite — better concurrent read performance
@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_conn, _):
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA foreign_keys=ON")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.close()

# ── Session factory ──────────────────────────────────────────────────────────
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── Declarative base ─────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── FastAPI dependency ───────────────────────────────────────────────────────
def get_db():
    """Yield a database session and ensure it is closed after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables if they do not exist yet. Called on startup."""
    # Import models here to register them with Base before create_all
    from backend import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
