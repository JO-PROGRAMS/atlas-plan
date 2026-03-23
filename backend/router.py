"""
backend/router.py
FastAPI router: all /tasks endpoints.
Mounted at /tasks by the main FastAPI app in app.py.
"""

from __future__ import annotations

import math
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend import crud
from backend.database import get_db
from backend.schemas import (
    CarryoverResponse,
    DailySummary,
    ReorderRequest,
    TaskCreate,
    TaskFilter,
    TaskListResponse,
    TaskResponse,
    TaskUpdate,
    StatusEnum,
    PriorityEnum,
    EffortEnum,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


# ─── helpers ─────────────────────────────────────────────────────────────────

def _404(task_id: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Task '{task_id}' not found.",
    )


# ─── GET /tasks ──────────────────────────────────────────────────────────────

@router.get("", response_model=TaskListResponse, summary="List tasks")
def list_tasks(
    # ── Filter params ─────────────────────────────────────────────────────
    task_status: Optional[StatusEnum]   = Query(None,  alias="status",
                                                description="Filter by status"),
    priority:    Optional[PriorityEnum] = Query(None,  description="Filter by priority"),
    effort:      Optional[EffortEnum]   = Query(None,  alias="effort_level",
                                                description="Filter by effort level"),
    archived:    bool                   = Query(False, description="Include archived tasks"),
    due_before:  Optional[datetime]     = Query(None,  description="Due date upper bound (ISO 8601)"),
    due_after:   Optional[datetime]     = Query(None,  description="Due date lower bound (ISO 8601)"),
    search:      Optional[str]          = Query(None,  description="Free-text search on name/summary"),
    page:        int                    = Query(1,   ge=1,   description="Page number"),
    page_size:   int                    = Query(50,  ge=1, le=200, description="Items per page"),
    db: Session = Depends(get_db),
):
    """
    Return a paginated, optionally-filtered list of tasks.

    - **status** – `Not started` | `In progress` | `Done` | `Planned`
    - **priority** – `Low` | `Medium` | `High`
    - **effort_level** – `Small` | `Medium` | `Large`
    - **search** – case-insensitive substring match on name and summary
    - Default: only non-archived tasks, ordered by position then created_at desc
    """
    filters = TaskFilter(
        status       = task_status,
        priority     = priority,
        effort_level = effort,
        archived     = archived,
        due_before   = due_before,
        due_after    = due_after,
        search       = search,
        page         = page,
        page_size    = page_size,
    )
    items, total = crud.get_tasks(db, filters)
    total_pages  = math.ceil(total / page_size) if page_size else 1

    return TaskListResponse(
        items       = [TaskResponse.model_validate(t) for t in items],
        total       = total,
        page        = page,
        page_size   = page_size,
        total_pages = total_pages,
    )


# ─── GET /tasks/today ────────────────────────────────────────────────────────

@router.get("/today", response_model=List[TaskResponse], summary="Today's tasks")
def today_tasks(db: Session = Depends(get_db)):
    """
    Return tasks due today **plus** any overdue unfinished tasks from previous days.
    Sorted by position; overdue tasks appear first.
    """
    tasks = crud.get_today_tasks(db)
    return [TaskResponse.model_validate(t) for t in tasks]


# ─── GET /tasks/summary ──────────────────────────────────────────────────────

@router.get("/summary", response_model=DailySummary, summary="Completion summary")
def summary(db: Session = Depends(get_db)):
    """
    Return aggregate statistics: total tasks, counts by status,
    overdue count, completion rate, and high-priority open items.
    """
    return crud.get_summary(db)


# ─── GET /tasks/carryover ────────────────────────────────────────────────────

@router.get("/carryover", response_model=CarryoverResponse,
            summary="Unfinished tasks from previous days")
def carryover(db: Session = Depends(get_db)):
    """
    Return tasks from previous days that are still **Not started** or
    **In progress** — i.e. tasks that were not completed and should be
    reviewed or rescheduled today.
    """
    return crud.get_carryover(db)


# ─── GET /tasks/{task_id} ────────────────────────────────────────────────────

@router.get("/{task_id}", response_model=TaskResponse, summary="Get single task")
def get_task(task_id: str, db: Session = Depends(get_db)):
    """Retrieve a single task by its UUID."""
    task = crud.get_task(db, task_id)
    if not task:
        raise _404(task_id)
    return TaskResponse.model_validate(task)


# ─── POST /tasks ─────────────────────────────────────────────────────────────

@router.post("", response_model=TaskResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Create task")
def create_task(data: TaskCreate, db: Session = Depends(get_db)):
    """
    Create a new task.

    - `task_name` is required; all other fields are optional.
    - `created_at` and `updated_at` are set automatically.
    - `position` defaults to the next available slot (appended to the end).
    """
    task = crud.create_task(db, data)
    return TaskResponse.model_validate(task)


# ─── PATCH /tasks/{task_id} ──────────────────────────────────────────────────

@router.patch("/{task_id}", response_model=TaskResponse, summary="Update task")
def update_task(task_id: str, data: TaskUpdate, db: Session = Depends(get_db)):
    """
    Partially update a task. Only fields included in the request body are changed.
    `updated_at` is refreshed automatically.
    """
    task = crud.update_task(db, task_id, data)
    if not task:
        raise _404(task_id)
    return TaskResponse.model_validate(task)


# ─── DELETE /tasks/{task_id} ─────────────────────────────────────────────────

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete task")
def delete_task(task_id: str, db: Session = Depends(get_db)):
    """
    Permanently delete a task. This action cannot be undone.
    To soft-delete (archive), use `PATCH /tasks/{task_id}` with `archived: true`.
    """
    deleted = crud.delete_task(db, task_id)
    if not deleted:
        raise _404(task_id)
    return None   # 204 No Content


# ─── POST /tasks/{task_id}/archive ───────────────────────────────────────────

@router.post("/{task_id}/archive", response_model=TaskResponse,
             summary="Archive task")
def archive_task(task_id: str, db: Session = Depends(get_db)):
    """Soft-delete a task by setting `archived = true`."""
    task = crud.archive_task(db, task_id)
    if not task:
        raise _404(task_id)
    return TaskResponse.model_validate(task)


# ─── POST /tasks/{task_id}/restore ───────────────────────────────────────────

@router.post("/{task_id}/restore", response_model=TaskResponse,
             summary="Restore archived task")
def restore_task(task_id: str, db: Session = Depends(get_db)):
    """Un-archive a previously archived task."""
    task = crud.restore_task(db, task_id)
    if not task:
        raise _404(task_id)
    return TaskResponse.model_validate(task)


# ─── POST /tasks/reorder ─────────────────────────────────────────────────────

@router.post("/reorder", status_code=status.HTTP_200_OK,
             summary="Bulk reorder tasks")
def reorder(data: ReorderRequest, db: Session = Depends(get_db)):
    """
    Bulk-update `position` values for drag-and-drop reordering.
    Send the full new order as an array of `{id, position}` objects.
    """
    updated = crud.reorder_tasks(db, data.tasks)
    return {"ok": True, "updated": updated}
