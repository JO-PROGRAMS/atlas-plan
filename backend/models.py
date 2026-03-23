"""
backend/models.py
SQLAlchemy ORM model for the tasks table.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Index, Integer,
    String, Text, func,
)
from sqlalchemy.orm import Mapped

from backend.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


class Task(Base):
    """
    Represents one task row in atlas_tasks.db.

    Enums are stored as plain strings — validation happens in the Pydantic
    schemas so the DB layer stays simple and migratable.
    """

    __tablename__ = "tasks"

    # ── Primary key ───────────────────────────────────────────────────────
    id: Mapped[str] = Column(
        String(36), primary_key=True, default=_new_uuid, index=True
    )

    # ── Core fields ───────────────────────────────────────────────────────
    task_name: Mapped[str] = Column(
        Text, nullable=False, default="Untitled"
    )

    # status: "Not started" | "In progress" | "Done" | "Planned"
    status: Mapped[str] = Column(
        String(20), nullable=False, default="Not started", index=True
    )

    # priority: "Low" | "Medium" | "High"
    priority: Mapped[str] = Column(
        String(10), nullable=False, default="Medium", index=True
    )

    # effort_level: "Small" | "Medium" | "Large"
    effort_level: Mapped[str] = Column(
        String(10), nullable=True
    )

    # Optional rich text summary
    summary: Mapped[str] = Column(Text, nullable=True)

    # Due date — nullable, stored as UTC datetime
    due_date: Mapped[datetime] = Column(DateTime, nullable=True, index=True)

    # ── Timestamps ────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = Column(
        DateTime, nullable=False, default=datetime.utcnow,
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = Column(
        DateTime, nullable=False, default=datetime.utcnow,
        onupdate=datetime.utcnow, server_default=func.now()
    )

    # ── Ordering & lifecycle ──────────────────────────────────────────────
    position: Mapped[int] = Column(
        Integer, nullable=False, default=0, index=True
    )
    archived: Mapped[bool] = Column(
        Boolean, nullable=False, default=False, index=True
    )

    # ── Composite indexes for common query patterns ───────────────────────
    __table_args__ = (
        Index("ix_tasks_status_archived",  "status",   "archived"),
        Index("ix_tasks_priority_archived", "priority", "archived"),
        Index("ix_tasks_due_archived",      "due_date", "archived"),
        Index("ix_tasks_position",          "position", "archived"),
    )

    def __repr__(self) -> str:
        return f"<Task id={self.id[:8]} name={self.task_name!r} status={self.status!r}>"
