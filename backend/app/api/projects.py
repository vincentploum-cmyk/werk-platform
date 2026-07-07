"""Project API endpoints — CRUD for Werk projects with RBAC."""

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select

from app.database import get_db
from app.models.db_models import Agent, Task
from app.schemas import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
    MessageResponse,
)
from app.services import project_service, workspace_service, artifact_service, llm
from app.api.ws import broadcast_event
from app.core.auth import CurrentUser, RequirePermission, get_optional_user

logger = logging.getLogger(__name__)

router = APIRouter()

VALID_PROJECT_STATUSES = {"draft", "active", "completed", "archived"}


@router.get("/", response_model=ProjectListResponse)
async def list_projects(
    db: AsyncSession = Depends(get_db),
    user: Optional[CurrentUser] = Depends(get_optional_user),
):
    """List all projects, most recently created first."""
    projects = await project_service.list_projects(db)
    return ProjectListResponse(projects=projects)


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("projects:create")),
):
    """Create a new project."""
    project = await project_service.create_project(
        db,
        name=body.name,
        description=body.description,
        config=body.config,
    )

    # Broadcast project.created event
    await broadcast_event("project.created", {
        "project_id": project.id,
        "name": project.name,
        "status": project.status,
    })

    # Optionally auto-trigger orchestrator workflow if configured
    if body.config and body.config.get("auto_orchestrate", False):
        try:
            from app.services.orchestrator_service import run_project_workflow
            asyncio.create_task(run_project_workflow(project.id, project.name))
        except Exception as e:
            logger.warning(f"Failed to auto-start orchestrator for {project.id}: {e}")

    return project


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user: Optional[CurrentUser] = Depends(get_optional_user),
):
    """Get project details by ID."""
    project = await project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    body: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("projects:update")),
):
    """Update a project's name, description, status, or config."""
    if body.status and body.status not in VALID_PROJECT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid project status '{body.status}'. "
                   f"Valid: {', '.join(sorted(VALID_PROJECT_STATUSES))}",
        )

    update_data = body.model_dump(exclude_none=True)
    project = await project_service.update_project(db, project_id, **update_data)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    return project


@router.delete("/{project_id}", response_model=MessageResponse)
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("projects:delete")),
):
    """Delete a project. Restricted to admin role."""
    project = await project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    await db.delete(project)
    return MessageResponse(message=f"Project '{project_id}' deleted")


@router.post("/{project_id}/status-report")
async def generate_status_report(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user: Optional[CurrentUser] = Depends(get_optional_user),
):
    """The PMO agent synthesizes a status report from every agent's documents + task status."""
    from app.api.agents import build_system  # imported here to avoid an import cycle

    project = await project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # The project's PMO agent, else a global PMO, else a sensible default persona.
    pmo = (
        await db.execute(
            select(Agent).where(Agent.role == "pmo", Agent.project_id == project_id)
        )
    ).scalar_one_or_none()
    if pmo is None:
        pmo = (
            await db.execute(select(Agent).where(Agent.role == "pmo", Agent.project_id.is_(None)))
        ).scalar_one_or_none()

    # Inputs: the team's documents + a task-status summary.
    docs = workspace_service.documents_digest(project_id, max_chars=8000)
    tasks = (await db.execute(select(Task).where(Task.project_id == project_id))).scalars().all()
    by_status: dict[str, int] = {}
    for t in tasks:
        by_status[t.status] = by_status.get(t.status, 0) + 1
    task_summary = ", ".join(f"{k}: {v}" for k, v in sorted(by_status.items())) or "no tasks yet"

    system = build_system(pmo) if pmo else _PMO_DEFAULT_SYSTEM
    user_prompt = (
        f"Project: {project.name}\n"
        f"Task status — {task_summary}.\n\n"
        f"Documents the team has produced:\n{docs or '(none yet)'}\n\n"
        "Produce a concise PROJECT STATUS REPORT for leadership with these sections: "
        "Summary, Progress by workstream, Risks & issues, and Recommended next steps / direction."
    )
    text, provider = await llm.chat_complete(system, user_prompt, max_tokens=1200)
    source = "llm" if text else "simulated"
    if not text:
        text = (
            f"# Status Report — {project.name}\n\n"
            f"## Summary\nTask status: {task_summary}.\n\n"
            f"## Progress by workstream\n{docs[:1500] or 'No documents yet.'}\n\n"
            "## Risks & issues\n- (enable a model for an analyzed report)\n\n"
            "## Recommended next steps\n- Continue execution; PMO to direct priorities."
        )

    # Save as a shared document + downloadable artifact.
    workspace_service.save_document(project_id, "status_report.md", text)
    await artifact_service.create_output_artifact(
        db, project_id=project_id, task_id=None,
        agent_id=str(pmo.id) if pmo else None,
        role="pmo", content=text, created_by=pmo.name if pmo else "PMO Agent",
    )
    await broadcast_event("artifact.created", {"project_id": project_id, "stage": "status_report"})
    return {"project_id": project_id, "source": source, "report": text}


_PMO_DEFAULT_SYSTEM = (
    "You are the PMO Agent leading this engagement. Synthesize a clear, concise project status "
    "report for leadership from the team's documents and task status, and recommend direction."
)