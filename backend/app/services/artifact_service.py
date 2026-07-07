"""Turn an agent's generated output into a first-class, downloadable artifact file."""

from __future__ import annotations

from app.models.db_models import Artifact

# Per-role default deliverable filename + type.
_ROLE_ARTIFACT: dict[str, tuple[str, str]] = {
    "pmo": ("status_report.md", "md"),
    "requirements": ("functional_requirements.md", "md"),
    "ux": ("ux_design.md", "md"),
    "business": ("data_model.md", "md"),
    "architect": ("architecture.md", "md"),
    "developer": ("implementation.md", "md"),
    "tester": ("test_plan.md", "md"),
    "devops": ("deployment_test.md", "md"),
    "release": ("deployment_production.md", "md"),
}

# Stage → role (mirror of the orchestrator mapping) for naming workflow artifacts.
_STAGE_ROLE = {
    "init": "requirements", "ux_design": "ux", "architecture": "architect",
    "development": "developer", "testing": "tester", "review": "requirements",
    "deploy": "devops", "deploy_prod": "release",
}

MEDIA_TYPES = {
    "md": "text/markdown", "py": "text/x-python", "ts": "text/x-typescript",
    "js": "text/javascript", "json": "application/json", "yml": "text/yaml",
    "yaml": "text/yaml", "sql": "application/sql", "sh": "text/x-shellscript",
}


def filename_for(role: str, stage: str | None = None) -> tuple[str, str]:
    if stage and stage in _STAGE_ROLE:
        role = _STAGE_ROLE[stage]
    return _ROLE_ARTIFACT.get(role, ("deliverable.md", "md"))


def media_type_for(file_type: str | None) -> str:
    return MEDIA_TYPES.get((file_type or "").lower(), "text/plain")


async def create_output_artifact(
    db,
    *,
    project_id,
    task_id,
    agent_id,
    role: str,
    content: str,
    stage: str | None = None,
    created_by: str | None = None,
) -> Artifact:
    """Persist an agent's output as an Artifact row with a sensible filename + type."""
    fname, ftype = filename_for(role, stage)
    artifact = Artifact(
        project_id=project_id,
        task_id=task_id,
        agent_id=agent_id,
        file_path=f"{role}/{fname}",
        file_type=ftype,
        content=content or "",
        metadata_json={"role": role, "stage": stage, "created_by": created_by},
    )
    db.add(artifact)
    await db.flush()
    return artifact


def artifact_dict(a: Artifact, include_content: bool = False) -> dict:
    data = {
        "id": str(a.id),
        "project_id": str(a.project_id) if a.project_id else None,
        "task_id": str(a.task_id) if a.task_id else None,
        "agent_id": str(a.agent_id) if a.agent_id else None,
        "file_path": a.file_path,
        "filename": (a.file_path or "").split("/")[-1],
        "file_type": a.file_type,
        "size": len(a.content or ""),
        "metadata": a.metadata_json or {},
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }
    if include_content:
        data["content"] = a.content or ""
    return data
