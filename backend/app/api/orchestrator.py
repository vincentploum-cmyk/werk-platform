"""Orchestrator API endpoints — manage LangGraph project workflows (RBAC enforced)."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.services.orchestrator_service import (
    run_project_workflow,
    approve_review,
    reject_review,
    approve_prod,
    reject_prod,
    get_workflow_status,
)
from app.core.auth import CurrentUser, RequirePermission, RequireRole

router = APIRouter()


@router.post("/projects/{project_id}/run")
async def run_workflow(
    project_id: str,
    project_name: str = "",
    user: CurrentUser = Depends(RequireRole("lead")),
):
    """Start the LangGraph workflow for a project.

    Requires 'lead' role or higher.
    Triggers the 7-stage orchestration lifecycle:
    Init → UX → Architecture → Development → Testing → Review → Deploy
    """
    if not project_name:
        project_name = f"Project {project_id[:8]}"

    # The pipeline makes several model calls and can take minutes on a local model,
    # so run it in the background and stream progress to the UI via WebSocket events.
    import asyncio

    asyncio.create_task(run_project_workflow(project_id, project_name))
    return {
        "project_id": project_id,
        "status": "started",
        "message": "Workflow running — watch the canvas for stage updates.",
    }


@router.post("/projects/{project_id}/review/approve")
async def approve_review_gate(
    project_id: str,
    feedback: str = "",
    user: CurrentUser = Depends(RequireRole("lead")),
):
    """Approve the review gate, allowing the workflow to proceed to deploy.
    Requires 'lead' role or higher."""
    success = await approve_review(project_id, feedback=feedback)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to approve review (orchestrator not available)",
        )
    return {"project_id": project_id, "status": "approved", "feedback": feedback}


@router.post("/projects/{project_id}/review/reject")
async def reject_review_gate(
    project_id: str,
    feedback: str = "Rework requested",
    user: CurrentUser = Depends(RequireRole("lead")),
):
    """Reject the review gate, returning the workflow to development.
    Requires 'lead' role or higher."""
    if not feedback:
        feedback = "Rework requested"
    success = await reject_review(project_id, feedback=feedback)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to reject review (orchestrator not available)",
        )
    return {"project_id": project_id, "status": "rejected", "feedback": feedback}


@router.post("/projects/{project_id}/prod/approve")
async def approve_prod_gate(
    project_id: str,
    feedback: str = "",
    user: CurrentUser = Depends(RequireRole("lead")),
):
    """Approve the PRODUCTION gate, deploying the release to production.
    Requires 'lead' role or higher."""
    success = await approve_prod(project_id, feedback=feedback)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No workflow is awaiting production sign-off for this project.",
        )
    return {"project_id": project_id, "status": "prod_approved", "feedback": feedback}


@router.post("/projects/{project_id}/prod/reject")
async def reject_prod_gate(
    project_id: str,
    feedback: str = "Production deploy held",
    user: CurrentUser = Depends(RequireRole("lead")),
):
    """Reject the PRODUCTION gate, holding the production deploy.
    Requires 'lead' role or higher."""
    success = await reject_prod(project_id, feedback=feedback or "Production deploy held")
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No workflow is awaiting production sign-off for this project.",
        )
    return {"project_id": project_id, "status": "prod_rejected", "feedback": feedback}


@router.get("/projects/{project_id}/status")
async def workflow_status(
    project_id: str,
    user: CurrentUser = Depends(RequirePermission("projects:read")),
):
    """Get the current workflow status for a project."""
    status_data = await get_workflow_status(project_id)
    return status_data