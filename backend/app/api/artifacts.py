"""Artifact API — list, read, and download the deliverables agents produce."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.db_models import Artifact
from app.core.auth import CurrentUser, RequirePermission, get_optional_user
from app.services import artifact_service

router = APIRouter()


@router.get("/")
async def list_artifacts(
    project_id: str | None = None,
    task_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: Optional[CurrentUser] = Depends(get_optional_user),
):
    """List artifacts (metadata only), optionally filtered by project or task."""
    query = select(Artifact).order_by(Artifact.created_at.desc())
    if project_id:
        query = query.where(Artifact.project_id == project_id)
    if task_id:
        query = query.where(Artifact.task_id == task_id)
    result = await db.execute(query)
    artifacts = result.scalars().all()
    return {"artifacts": [artifact_service.artifact_dict(a) for a in artifacts]}


@router.get("/{artifact_id}")
async def get_artifact(
    artifact_id: str,
    db: AsyncSession = Depends(get_db),
    user: Optional[CurrentUser] = Depends(get_optional_user),
):
    """Get a single artifact including its content."""
    a = (await db.execute(select(Artifact).where(Artifact.id == artifact_id))).scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    return artifact_service.artifact_dict(a, include_content=True)


@router.get("/{artifact_id}/download")
async def download_artifact(
    artifact_id: str,
    db: AsyncSession = Depends(get_db),
    user: Optional[CurrentUser] = Depends(get_optional_user),
):
    """Download the artifact as a file."""
    a = (await db.execute(select(Artifact).where(Artifact.id == artifact_id))).scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    filename = (a.file_path or "deliverable.md").split("/")[-1]
    return Response(
        content=a.content or "",
        media_type=artifact_service.media_type_for(a.file_type),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_artifact(
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("artifacts:create")),
):
    """Create an artifact directly (used by tooling/tests)."""
    artifact = Artifact(
        project_id=body.get("project_id"),
        task_id=body.get("task_id"),
        agent_id=body.get("agent_id"),
        file_path=body["file_path"],
        file_type=body.get("file_type"),
        content=body.get("content", ""),
        metadata_json=body.get("metadata", {}),
    )
    db.add(artifact)
    await db.flush()
    await db.refresh(artifact)
    return artifact_service.artifact_dict(artifact, include_content=True)
