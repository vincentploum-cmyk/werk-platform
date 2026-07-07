"""Pydantic schemas for Werk Platform API."""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


# ─── Project Schemas ──────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    config: Optional[dict[str, Any]] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None  # draft, active, completed, archived
    config: Optional[dict[str, Any]] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    status: str
    config: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    projects: list[ProjectResponse]


# ─── Task Schemas ─────────────────────────────────────────────────────────────

VALID_TASK_STATUSES = {"backlog", "in_progress", "review", "done", "blocked"}

ALLOWED_TRANSITIONS = {
    "backlog": {"in_progress"},
    "in_progress": {"review"},
    "review": {"in_progress", "done", "blocked"},
    "done": set(),
    "blocked": {"in_progress"},
}


class TaskCreate(BaseModel):
    project_id: str
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    assigned_agent_id: Optional[str] = None
    parent_task_id: Optional[str] = None
    priority: int = 0


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None
    assigned_agent_id: Optional[str] = None
    priority: Optional[int] = None
    result: Optional[str] = None
    artifacts: Optional[list[dict[str, Any]]] = None


class TaskResponse(BaseModel):
    id: str
    project_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    status: str
    assigned_agent_id: Optional[str] = None
    parent_task_id: Optional[str] = None
    priority: int
    artifacts: list[dict[str, Any]]
    result: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]


# ─── Generic Schemas ──────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str