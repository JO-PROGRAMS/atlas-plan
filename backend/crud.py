"""
backend/crud.py
All database operations for the Atlas task system.
Stateless functions — receive a Session, return ORM objects or primitives.
"""

from __future__ import annotations

import uuid
from datetime import datetime, date, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from backend.models import Task
from backend.schemas import (
    TaskCreate, TaskFilter, TaskUpdate,
    ReorderItem,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _next_position(db: Session) -> int:
    """Return the next available position value (max + 1)."""
    result = db.query(func.max(Task.position)).filter(Task.archived == False).scalar()
    return (result or 0) + 1


# ── Create ───────────────────────────────────────────────────────────────────

def create_task(db: Session, data: TaskCreate) -> Task:
    """Insert a new task row, auto-assigning position if not provided."""
    now = datetime.utcnow()
    position = data.position if data.position > 0 else _next_position(db)

    task = Task(
        id           = str(uuid.uuid4()),
        task_name    = data.task_name.strip(),
        status       = data.status.value,
        priority     = data.priority.value,
        effort_level = data.effort_level.value if data.effort_level else None,
        summary      = (data.summary or "").strip() or None,
        due_date     = data.due_date,
        position     = position,
        archived     = False,
        created_at   = now,
        updated_at   = now,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


# ── Read ─────────────────────────────────────────────────────────────────────

def get_task(db: Session, task_id: str) -> Optional[Task]:
    """Fetch a single task by UUID string."""
    return db.query(Task).filter(Task.id == task_id).first()


def get_tasks(
    db: Session,
    filters: TaskFilter,
) -> Tuple[List[Task], int]:
    """
    Return (items, total_count) respecting all filters + pagination.
    The query always excludes archived tasks unless archived=True is passed.
    """
    q = db.query(Task)

    # ── Archived filter ────────────────────────────────────────────────────
    q = q.filter(Task.archived == filters.archived)

    # ── Enum filters ──────────────────────────────────────────────────────
    if filters.status:
        q = q.filter(Task.status == filters.status.value)
    if filters.priority:
        q = q.filter(Task.priority == filters.priority.value)
    if filters.effort_level:
        q = q.filter(Task.effort_level == filters.effort_level.value)

    # ── Date range ────────────────────────────────────────────────────────
    if filters.due_after:
        q = q.filter(Task.due_date >= filters.due_after)
    if filters.due_before:
        q = q.filter(Task.due_date <= filters.due_before)

    # ── Full-text search ──────────────────────────────────────────────────
    if filters.search:
        term = f"%{filters.search.strip()}%"
        q = q.filter(
            or_(
                Task.task_name.ilike(term),
                Task.summary.ilike(term),
            )
        )

    # ── Total count before pagination ─────────────────────────────────────
    total = q.count()

    # ── Ordering: by position asc, then created_at desc ───────────────────
    q = q.order_by(Task.position.asc(), Task.created_at.desc())

    # ── Pagination ────────────────────────────────────────────────────────
    offset = (filters.page - 1) * filters.page_size
    items  = q.offset(offset).limit(filters.page_size).all()

    return items, total


def get_today_tasks(db: Session) -> List[Task]:
    """
    Return all non-archived tasks whose due_date falls on today (local UTC date),
    plus any unfinished tasks from previous days (carry-over).
    """
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end   = today_start + timedelta(days=1)

    # Today's tasks (due today)
    today_q = (
        db.query(Task)
        .filter(
            Task.archived == False,
            Task.due_date >= today_start,
            Task.due_date <  today_end,
        )
        .order_by(Task.position.asc())
        .all()
    )

    # Overdue unfinished tasks (due before today, not done)
    overdue_q = (
        db.query(Task)
        .filter(
            Task.archived == False,
            Task.due_date < today_start,
            Task.status.notin_(["Done"]),
        )
        .order_by(Task.due_date.asc())
        .all()
    )

    # Deduplicate preserving order
    seen = set()
    result = []
    for t in overdue_q + today_q:
        if t.id not in seen:
            seen.add(t.id)
            result.append(t)
    return result


def get_summary(db: Session) -> dict:
    """Return aggregate statistics for today and all tasks."""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end   = today_start + timedelta(days=1)

    # All active (non-archived) tasks
    base = db.query(Task).filter(Task.archived == False)
    total = base.count()

    by_status = {
        "Not started": base.filter(Task.status == "Not started").count(),
        "In progress":  base.filter(Task.status == "In progress").count(),
        "Done":         base.filter(Task.status == "Done").count(),
        "Planned":      base.filter(Task.status == "Planned").count(),
    }

    # Overdue (due before today AND not done)
    overdue = base.filter(
        Task.due_date < today_start,
        Task.status.notin_(["Done"])
    ).count()

    # High-priority open
    high_open = base.filter(
        Task.priority == "High",
        Task.status.notin_(["Done"])
    ).count()

    # Completion rate
    done  = by_status["Done"]
    rate  = round((done / total * 100), 1) if total else 0.0

    return {
        "date":                date.today().isoformat(),
        "total_tasks":         total,
        "completed":           done,
        "in_progress":         by_status["In progress"],
        "not_started":         by_status["Not started"],
        "planned":             by_status["Planned"],
        "completion_rate_pct": rate,
        "overdue_count":       overdue,
        "high_priority_open":  high_open,
    }


def get_carryover(db: Session) -> dict:
    """Return tasks from previous days that are still unfinished (not Done/Planned)."""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    stale = (
        db.query(Task)
        .filter(
            Task.archived == False,
            Task.due_date < today_start,
            Task.due_date.isnot(None),
            Task.status.notin_(["Done", "Planned"]),
        )
        .order_by(Task.due_date.asc())
        .all()
    )

    items = [
        {
            "id":        t.id,
            "task_name": t.task_name,
            "status":    t.status,
            "priority":  t.priority,
            "due_date":  t.due_date,
        }
        for t in stale
    ]

    return {
        "date":         date.today().isoformat(),
        "carried_over": items,
        "message": (
            f"{len(items)} unfinished task(s) from previous sessions carried over."
            if items else
            "No overdue tasks — you're up to date! 🎉"
        ),
    }


# ── Update ───────────────────────────────────────────────────────────────────

def update_task(db: Session, task_id: str, data: TaskUpdate) -> Optional[Task]:
    """
    Apply partial updates to a task.
    Only fields explicitly provided in the request body are changed.
    updated_at is always refreshed.
    """
    task = get_task(db, task_id)
    if task is None:
        return None

    payload = data.model_dump(exclude_unset=True)

    for field, value in payload.items():
        # Pydantic enums → unwrap to string value
        if hasattr(value, "value"):
            value = value.value
        setattr(task, field, value)

    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    return task


def archive_task(db: Session, task_id: str) -> Optional[Task]:
    """Soft-delete a task by setting archived=True."""
    task = get_task(db, task_id)
    if task is None:
        return None
    task.archived   = True
    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    return task


def restore_task(db: Session, task_id: str) -> Optional[Task]:
    """Un-archive a previously archived task."""
    task = get_task(db, task_id)
    if task is None:
        return None
    task.archived   = False
    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    return task


# ── Delete ───────────────────────────────────────────────────────────────────

def delete_task(db: Session, task_id: str) -> bool:
    """Permanently delete a task row. Returns True if deleted, False if not found."""
    task = get_task(db, task_id)
    if task is None:
        return False
    db.delete(task)
    db.commit()
    return True


# ── Reorder ──────────────────────────────────────────────────────────────────

def reorder_tasks(db: Session, items: List[ReorderItem]) -> int:
    """
    Bulk-update the position column for a list of tasks.
    Returns the number of tasks successfully updated.
    """
    updated = 0
    now     = datetime.utcnow()
    for item in items:
        task = get_task(db, item.id)
        if task:
            task.position   = item.position
            task.updated_at = now
            updated += 1
    db.commit()
    return updated
