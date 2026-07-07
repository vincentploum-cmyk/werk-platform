"""Per-project workspace API — list files, read a file, and run the tests."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import CurrentUser, get_optional_user
from app.services import workspace_service

router = APIRouter()


@router.get("/{project_id}/files")
async def list_workspace_files(
    project_id: str,
    user: Optional[CurrentUser] = Depends(get_optional_user),
):
    """List the files the agents have written into this project's workspace."""
    return {"files": workspace_service.list_files(project_id)}


@router.get("/{project_id}/file")
async def read_workspace_file(
    project_id: str,
    path: str,
    user: Optional[CurrentUser] = Depends(get_optional_user),
):
    """Read a single workspace file's content."""
    try:
        content = workspace_service.read_file(project_id, path)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid path.")
    if content is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
    return {"path": path, "content": content}


@router.post("/{project_id}/run-tests")
async def run_workspace_tests(
    project_id: str,
    user: Optional[CurrentUser] = Depends(get_optional_user),
):
    """Run the project's tests (sandboxed subprocess). Returns pass/fail + output."""
    return workspace_service.run_tests(project_id)


@router.post("/{project_id}/health-check")
async def health_check_workspace(
    project_id: str,
    user: Optional[CurrentUser] = Depends(get_optional_user),
):
    """Stand the workspace app up on a free port and probe its health endpoint."""
    import asyncio

    return await asyncio.to_thread(workspace_service.health_check, project_id)


@router.post("/{project_id}/install")
async def install_workspace_deps(
    project_id: str,
    user: Optional[CurrentUser] = Depends(get_optional_user),
):
    """Install the workspace's requirements.txt so agents can use real libraries."""
    return workspace_service.install_dependencies(project_id)


@router.get("/{project_id}/documents")
async def list_workspace_documents(
    project_id: str,
    user: Optional[CurrentUser] = Depends(get_optional_user),
):
    """List the shared documents agents have produced (name + size)."""
    docs = workspace_service.list_documents(project_id)
    return {"documents": [{"name": d["name"], "size": len(d["content"])} for d in docs]}
