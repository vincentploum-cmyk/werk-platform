"""Project service layer — business logic for project operations."""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Project


async def list_projects(db: AsyncSession) -> list[Project]:
    result = await db.execute(select(Project).order_by(Project.created_at.desc()))
    return list(result.scalars().all())


async def get_project(db: AsyncSession, project_id: str) -> Optional[Project]:
    result = await db.execute(select(Project).where(Project.id == project_id))
    return result.scalar_one_or_none()


async def create_project(db: AsyncSession, name: str, description: Optional[str] = None,
                         config: Optional[dict] = None) -> Project:
    project = Project(
        name=name,
        description=description,
        config=config or {},
    )
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return project


async def update_project(db: AsyncSession, project_id: str, **kwargs) -> Optional[Project]:
    project = await get_project(db, project_id)
    if not project:
        return None
    for key, value in kwargs.items():
        if value is not None and hasattr(project, key):
            setattr(project, key, value)
    await db.flush()
    await db.refresh(project)
    return project