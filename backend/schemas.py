"""
backend/schemas.py
Pydantic v2 request / response schemas for the Atlas task API.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


# ── Enum definitions ─────────────────────────────────────────────────────────

class StatusEnum(str, Enum):
    not_started  = "Not started"
    in_progress  = "In progress"
    done         = "Done"
    planned      = "Planned"


class PriorityEnum(str, Enum):
    low    = "Low"
    medium = "Medium"
    high   = "High"


class EffortEnum(str, Enum):
    small  = "Small"
    medium = "Medium"
    large  = "Large"


# ── Task schemas ─────────────────────────────────────────────────────────────

class TaskBase(BaseModel):
    task_name:    str                  = Field(..., min_length=1, max_length=500,
                                               description="Task title")
    status:       StatusEnum           = StatusEnum.not_started
    priority:     PriorityEnum         = PriorityEnum.medium
    effort_level: Optional[EffortEnum] = None
    summary:      Optional[str]        = Field(None, max_length=2000)
    due_date:     Optional[datetime]   = None
    position:     int                  = Field(0, ge=0)
    archived:     bool                 = False


class TaskCreate(TaskBase):
    """Body for POST /tasks"""
    pass


class TaskUpdate(BaseModel):
    """
    Body for PATCH /tasks/{task_id}.
    All fields optional — only provided fields are updated.
    """
    task_name:    Optional[str]        = Field(None, min_length=1, max_length=500)
    status:       Optional[StatusEnum] = None
    priority:     Optional[PriorityEnum] = None
    effort_level: Optional[EffortEnum] = None
    summary:      Optional[str]        = Field(None, max_length=2000)
    due_date:     Optional[datetime]   = None
    position:     Optional[int]        = Field(None, ge=0)
    archived:     Optional[bool]       = None

    model_config = {"extra": "ignore"}


class TaskResponse(TaskBase):
    """Serialised task returned from the API."""
    id:         str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Bulk-reorder schema ──────────────────────────────────────────────────────

class ReorderItem(BaseModel):
    id:       str = Field(..., description="Task UUID")
    position: int = Field(..., ge=0)


class ReorderRequest(BaseModel):
    tasks: List[ReorderItem] = Field(..., min_length=1)


# ── Query / filter params ─────────────────────────────────────────────────────

class TaskFilter(BaseModel):
    """
    Query-parameter model for GET /tasks.
    All fields optional — omit to return everything.
    """
    status:       Optional[StatusEnum]   = None
    priority:     Optional[PriorityEnum] = None
    effort_level: Optional[EffortEnum]   = None
    archived:     bool                   = False          # default: exclude archived
    due_before:   Optional[datetime]     = None
    due_after:    Optional[datetime]     = None
    search:       Optional[str]          = Field(None, max_length=200)
    page:         int                    = Field(1,  ge=1)
    page_size:    int                    = Field(50, ge=1, le=200)

    @field_validator("page_size")
    @classmethod
    def cap_page_size(cls, v: int) -> int:
        return min(v, 200)


# ── Paginated list response ──────────────────────────────────────────────────

class TaskListResponse(BaseModel):
    items:       List[TaskResponse]
    total:       int
    page:        int
    page_size:   int
    total_pages: int


# ── Summary / daily-plan responses ──────────────────────────────────────────

class DailySummary(BaseModel):
    date:                str
    total_tasks:         int
    completed:           int
    in_progress:         int
    not_started:         int
    planned:             int
    completion_rate_pct: float
    overdue_count:       int
    high_priority_open:  int


class CarryoverTask(BaseModel):
    id:         str
    task_name:  str
    status:     str
    priority:   str
    due_date:   Optional[datetime]


class CarryoverResponse(BaseModel):
    date:         str
    carried_over: List[CarryoverTask]
    message:      str


# ── Status endpoint ──────────────────────────────────────────────────────────

class StatusResponse(BaseModel):
    agent:      bool
    db:         bool
    db_path:    str
    model:      str
    date:       str
    local_time: str
    task_count: int
