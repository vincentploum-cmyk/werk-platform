"""Task API endpoints — CRUD with state machine validation + RBAC."""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.db_models import Agent, Artifact, Project
from app.schemas import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskListResponse,
    MessageResponse,
)
from app.services import task_service, llm, artifact_service, workspace_service, retrieval_service
from app.api.ws import broadcast_event
from app.api.agents import build_system
from app.core.auth import CurrentUser, RequirePermission, get_optional_user

router = APIRouter()

VALID_TASK_STATUSES = {"backlog", "in_progress", "review", "done", "blocked"}


@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    project_id: str | None = Query(None, description="Filter by project ID"),
    db: AsyncSession = Depends(get_db),
    user: Optional[CurrentUser] = Depends(get_optional_user),
):
    """List all tasks, optionally filtered by project."""
    tasks = await task_service.list_tasks(db, project_id=project_id)
    return TaskListResponse(tasks=tasks)


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    body: TaskCreate,
    db: AsyncSession = Depends(get_db),
    user: Optional[CurrentUser] = Depends(get_optional_user),
):
    """Create a new task in backlog status."""
    task = await task_service.create_task(
        db,
        project_id=body.project_id,
        title=body.title,
        description=body.description,
        assigned_agent_id=body.assigned_agent_id,
        parent_task_id=body.parent_task_id,
        priority=body.priority,
    )
    return task


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    user: Optional[CurrentUser] = Depends(get_optional_user),
):
    """Get task details by ID."""
    task = await task_service.get_task(db, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found",
        )
    return task


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    body: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    user: Optional[CurrentUser] = Depends(get_optional_user),
):
    """Update task fields and transition status through the state machine.

    Valid status transitions:
      backlog → in_progress
      in_progress → review
      review → in_progress | done | blocked
      done → (terminal state)
      blocked → in_progress
    """
    if body.status and body.status not in VALID_TASK_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid task status '{body.status}'. "
                   f"Valid: {', '.join(sorted(VALID_TASK_STATUSES))}",
        )

    update_data = body.model_dump(exclude_none=True)
    try:
        task = await task_service.update_task(db, task_id, **update_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found",
        )

    # Broadcast task update event for real-time frontend updates
    await broadcast_event("task.updated", {
        "task_id": task.id,
        "project_id": task.project_id,
        "title": task.title,
        "status": task.status,
        "result": task.result,
        "assigned_agent_id": task.assigned_agent_id,
    })

    return task


async def _run_execution_layer(db, task, agent, text: str) -> Optional[str]:
    """Developer writes code; Tester runs it; DevOps/Release stand the environment up and
    health-check it. Blocking subprocess work is offloaded so it doesn't stall the event loop."""
    import asyncio

    role = agent.role.lower()
    if role not in ("developer", "tester", "devops", "release"):
        return None

    notes = []
    files = workspace_service.extract_code_files(text)
    if files:
        written = workspace_service.write_files(task.project_id, files)
        notes.append("Wrote to workspace: " + ", ".join(written))
        for rel, content in files.items():
            ext = rel.rsplit(".", 1)[-1] if "." in rel else "txt"
            db.add(Artifact(
                project_id=task.project_id, task_id=task.id, agent_id=agent.id,
                file_path=rel, file_type=ext, content=content,
                metadata_json={"role": role, "source": "workspace"},
            ))
        await db.flush()
        if workspace_service.has_requirements(task.project_id):
            inst = await asyncio.to_thread(workspace_service.install_dependencies, task.project_id)
            notes.append(f"Dependency install: {'ok' if inst.get('installed') else 'see output'}\n{inst.get('output','')}")

    if role == "tester":
        result = await asyncio.to_thread(workspace_service.run_tests, task.project_id)
        if result.get("enabled") is False:
            notes.append(result["output"])
        else:
            passed = result.get("passed")
            verdict = "PASSED ✓" if passed else ("FAILED ✗" if passed is False else "no tests")
            notes.append(f"Test run: {verdict}\n{result.get('output', '')}")
            db.add(Artifact(
                project_id=task.project_id, task_id=task.id, agent_id=agent.id,
                file_path="test_results.txt", file_type="txt", content=result.get("output", ""),
                metadata_json={"role": role, "passed": passed, "source": "test-run"},
            ))
            await db.flush()

    if role in ("devops", "release"):
        env = "production" if role == "release" else "test"
        result = await asyncio.to_thread(workspace_service.health_check, task.project_id)
        if result.get("enabled") is False:
            notes.append(result["output"])
        else:
            healthy = result.get("healthy")
            verdict = "HEALTHY ✓" if healthy else ("UNHEALTHY ✗" if healthy is False else "no runnable app")
            notes.append(f"{env.title()} environment: {verdict}\n{result.get('output', '')}")
            db.add(Artifact(
                project_id=task.project_id, task_id=task.id, agent_id=agent.id,
                file_path=f"{env}_environment_health.txt", file_type="txt",
                content=result.get("output", ""),
                metadata_json={"role": role, "env": env, "healthy": healthy, "source": "health-check"},
            ))
            await db.flush()

    return "\n".join(notes) if notes else None


def _simulated_result(agent: Agent, task) -> str:
    """Offline fallback when no model is available — a structured placeholder deliverable."""
    caps = ", ".join(agent.capabilities or []) or "general consulting"
    return (
        f"[Simulated output — no model configured]\n\n"
        f"{agent.name} ({agent.role}) would deliver the following for “{task.title}”:\n"
        f"- Restate the goal and assumptions\n"
        f"- Apply skills: {caps}\n"
        f"- Produce the concrete artifact for this stage\n"
        f"- Flag open questions and hand off to the next agent\n\n"
        f"Enable the local model (USE_OLLAMA=true) to generate real output."
    )


@router.post("/{task_id}/run", response_model=TaskResponse)
async def run_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    user: Optional[CurrentUser] = Depends(get_optional_user),
):
    """Have the task's assigned agent actually do the work using the local model.

    Sets the task to in_progress, generates the deliverable, stores it as the task
    result + an artifact, then moves the task to review for human sign-off.
    """
    task = await task_service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if not task.assigned_agent_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assign this task to an agent before running it.",
        )

    agent = (
        await db.execute(select(Agent).where(Agent.id == task.assigned_agent_id))
    ).scalar_one_or_none()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Assigned agent no longer exists."
        )

    # Mark the agent as working and tell the canvas immediately.
    task.status = "in_progress"
    await db.flush()
    await broadcast_event("task.updated", {
        "task_id": task.id, "project_id": task.project_id,
        "title": task.title, "status": task.status,
        "assigned_agent_id": task.assigned_agent_id,
    })

    # Build the prompt from the agent's (possibly user-edited) instructions + the task.
    project = None
    if task.project_id:
        project = (
            await db.execute(select(Project).where(Project.id == task.project_id))
        ).scalar_one_or_none()
    context = f"Project: {project.name}\n" if project else ""
    if project and project.description:
        context += f"Project context: {project.description}\n"
    role = agent.role.lower()
    fmt_hint = ""
    if role == "developer":
        fmt_hint = (
            " Output the implementation as one or more fenced code blocks, each beginning with "
            "its file path on the fence line, e.g. ```python app/main.py. If you build a web "
            "service, name the entrypoint app.py, read the port from the PORT environment "
            "variable, and expose a GET /health endpoint that returns HTTP 200 — so the "
            "environment can be stood up and health-checked."
        )
    elif role == "tester":
        fmt_hint = (
            " Output the tests as a fenced Python block whose fence line is the filename "
            "test_main.py, using plain `assert` statements (no pytest), importing the code under test."
        )
    # Retrieve the MOST RELEVANT prior documents for this task (semantic search), so the
    # agent builds on the team's work without drowning in a full dump.
    query = f"{task.title} {task.description or ''}"
    prior_docs = await retrieval_service.retrieve_context(task.project_id, query)
    docs_context = (
        f"\n\nRelevant documents the team has produced — read and build on these:\n{prior_docs}\n"
        if prior_docs else ""
    )
    user_prompt = (
        f"{context}Task: {task.title}\n"
        f"{task.description or ''}{docs_context}\n\n"
        f"Produce the deliverable for this task as the {agent.role} agent. "
        f"Be concrete, complete, and ready to hand off to the next agent.{fmt_hint}"
    )

    text, provider = await llm.chat_complete(build_system(agent), user_prompt, max_tokens=1200)
    source = "llm" if text else "simulated"
    if not text:
        text = _simulated_result(agent, task)

    artifact = {
        "type": "deliverable",
        "summary": task.title,
        "created_by": agent.name,
        "role": agent.role,
        "source": source,
        "provider": provider,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "content": text,
    }
    # Reassign (not mutate) so SQLAlchemy persists the JSON change.
    task.result = text
    task.artifacts = list(task.artifacts or []) + [artifact]
    task.status = "review"
    await db.flush()

    # Persist the output as a first-class, downloadable artifact file.
    await artifact_service.create_output_artifact(
        db, project_id=task.project_id, task_id=task.id, agent_id=agent.id,
        role=agent.role, content=text, created_by=agent.name,
    )

    # Save the deliverable into the shared document folder so other agents can retrieve it.
    workspace_service.save_document(task.project_id, f"{agent.role.lower()}.md", text)

    # Execution layer: Developer writes real files; Tester runs them.
    exec_note = await _run_execution_layer(db, task, agent, text)
    if exec_note:
        task.result = (task.result or "") + "\n\n--- Execution ---\n" + exec_note
    await db.flush()
    await db.refresh(task)

    await broadcast_event("task.updated", {
        "task_id": task.id, "project_id": task.project_id,
        "title": task.title, "status": task.status, "result": task.result,
        "assigned_agent_id": task.assigned_agent_id,
    })
    await broadcast_event("artifact.created", {
        "task_id": task.id, "project_id": task.project_id,
        "agent": agent.name, "summary": task.title, "source": source,
    })
    return task


@router.delete("/{task_id}", response_model=MessageResponse)
async def delete_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("tasks:delete")),
):
    """Delete a task. Restricted to admin role."""
    task = await task_service.get_task(db, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found",
        )
    await db.delete(task)
    return MessageResponse(message=f"Task '{task_id}' deleted")


@router.get("/transitions/{status}", response_model=dict)
async def get_transitions(status: str):
    """Get allowed transitions for a given task status."""
    allowed = task_service.get_allowed_transitions(status)
    return {"status": status, "allowed_transitions": sorted(allowed)}