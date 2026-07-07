"""Task service layer — business logic for task operations with state machine."""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Task
from app.schemas import ALLOWED_TRANSITIONS


async def list_tasks(db: AsyncSession, project_id: Optional[str] = None) -> list[Task]:
    query = select(Task).order_by(Task.created_at.desc())
    if project_id:
        query = query.where(Task.project_id == project_id)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_task(db: AsyncSession, task_id: str) -> Optional[Task]:
    result = await db.execute(select(Task).where(Task.id == task_id))
    return result.scalar_one_or_none()


async def create_task(
    db: AsyncSession,
    project_id: str,
    title: str,
    description: Optional[str] = None,
    assigned_agent_id: Optional[str] = None,
    parent_task_id: Optional[str] = None,
    priority: int = 0,
) -> Task:
    task = Task(
        project_id=project_id,
        title=title,
        description=description,
        status="backlog",
        assigned_agent_id=assigned_agent_id,
        parent_task_id=parent_task_id,
        priority=priority,
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)
    return task


async def update_task(
    db: AsyncSession,
    task_id: str,
    **kwargs,
) -> Optional[Task]:
    task = await get_task(db, task_id)
    if not task:
        return None

    # Handle state machine transition validation
    new_status = kwargs.get("status")
    if new_status and new_status != task.status:
        if not _validate_transition(task.status, new_status):
            raise ValueError(
                f"Invalid status transition: '{task.status}' → '{new_status}'. "
                f"Allowed transitions from '{task.status}': {ALLOWED_TRANSITIONS.get(task.status, set())}"
            )

    for key, value in kwargs.items():
        if value is not None and hasattr(task, key) and key != "id":
            setattr(task, key, value)

    await db.flush()
    await db.refresh(task)
    return task


def _validate_transition(current_status: str, new_status: str) -> bool:
    """Validate task status transitions per the Werk state machine."""
    if current_status not in ALLOWED_TRANSITIONS:
        return False
    return new_status in ALLOWED_TRANSITIONS[current_status]


def get_allowed_transitions(status: str) -> set[str]:
    """Get valid next states for a given status."""
    return ALLOWED_TRANSITIONS.get(status, set())