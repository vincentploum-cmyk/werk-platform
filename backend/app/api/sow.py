"""SOW intake API — configurable parameters + rules-driven team deployment."""

from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.db_models import Agent, AppSetting, Project, Task
from app.core.auth import CurrentUser, RequirePermission, get_optional_user
from app.services import doc_extract, sow_service
from app.api.ws import broadcast_event

router = APIRouter()

_DEF_KEY = "sow_parameter_definitions"


async def _get_definitions(db: AsyncSession) -> list[dict]:
    row = await db.get(AppSetting, _DEF_KEY)
    if row and isinstance(row.value, list) and row.value:
        return row.value
    return sow_service.DEFAULT_DEFINITIONS


# ─── Configurable parameter definitions ─────────────────────────────────────
class DefinitionsBody(BaseModel):
    definitions: list[dict[str, Any]]


@router.get("/parameters/definitions")
async def get_definitions(
    db: AsyncSession = Depends(get_db),
    user: Optional[CurrentUser] = Depends(get_optional_user),
):
    """The configurable parameter schema that drives extraction + staffing."""
    return {"definitions": await _get_definitions(db)}


@router.put("/parameters/definitions")
async def put_definitions(
    body: DefinitionsBody,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("projects:create")),
):
    """Replace the parameter definitions. Each needs at least key/label/type."""
    for d in body.definitions:
        if not d.get("key") or not d.get("type"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Every parameter needs a 'key' and a 'type'.",
            )
    row = await db.get(AppSetting, _DEF_KEY)
    if row:
        row.value = body.definitions
    else:
        db.add(AppSetting(key=_DEF_KEY, value=body.definitions))
    await db.flush()
    return {"definitions": body.definitions}


# ─── Analyze ────────────────────────────────────────────────────────────────
class SowPlan(BaseModel):
    project_name: str
    summary: str
    parameters: dict[str, Any]
    definitions: list[dict[str, Any]]
    agents: list[dict[str, Any]]
    source: str = "heuristic"
    filename: str = ""
    char_count: int = 0


@router.post("/analyze", response_model=SowPlan)
async def analyze_sow(
    file: UploadFile = File(...),
    instruction: str = Form(""),
    db: AsyncSession = Depends(get_db),
    user: Optional[CurrentUser] = Depends(get_optional_user),
):
    """Read a signed SOW and extract the configured parameters + the resulting team."""
    filename = file.filename or "sow"
    if not doc_extract.supported(filename):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type. Use .pptx, .pdf, .docx, or .txt.",
        )
    content = await file.read()
    try:
        text = doc_extract.extract_text(filename, content)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Could not read '{filename}': {exc}"
        )
    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No readable text in the document."
        )

    definitions = await _get_definitions(db)
    plan = await sow_service.analyze_sow(text, definitions)
    return SowPlan(
        project_name=plan["project_name"],
        summary=plan["summary"],
        parameters=plan["parameters"],
        definitions=definitions,
        agents=plan["agents"],
        source=plan.get("source", "heuristic"),
        filename=filename,
        char_count=len(text),
    )


# ─── Re-derive team from edited parameters ──────────────────────────────────
class TeamRequest(BaseModel):
    parameters: dict[str, Any]
    summary: str = ""


@router.post("/team")
async def derive_team(
    body: TeamRequest,
    db: AsyncSession = Depends(get_db),
    user: Optional[CurrentUser] = Depends(get_optional_user),
):
    """Re-derive the recommended team from (possibly user-edited) parameters."""
    definitions = await _get_definitions(db)
    agents = sow_service.derive_team(body.parameters, definitions, body.summary)
    return {"agents": agents}


# ─── Deploy ─────────────────────────────────────────────────────────────────
class PlannedAgent(BaseModel):
    role: str
    name: str
    rationale: str = ""
    instructions: str = ""


class DeployRequest(BaseModel):
    project_name: str
    summary: str = ""
    parameters: dict[str, Any] = {}
    agents: list[PlannedAgent]
    create_kickoff_tasks: bool = True


class DeployedAgent(BaseModel):
    id: str
    name: str
    role: str
    type: str


class DeployResponse(BaseModel):
    project_id: str
    project_name: str
    agents: list[DeployedAgent]
    tasks_created: int


@router.post("/deploy", response_model=DeployResponse)
async def deploy_sow(
    body: DeployRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("projects:create")),
):
    """Create the project (storing parameters) and deploy the chosen project-scoped agents."""
    if not body.agents:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Select at least one agent to deploy."
        )

    project = Project(
        name=body.project_name or "New Engagement",
        description=body.summary or None,
        status="active",
        config={"origin": "sow", "parameters": body.parameters},
    )
    db.add(project)
    await db.flush()

    deployed: list[DeployedAgent] = []
    tasks_created = 0
    for planned in body.agents:
        cat = sow_service.ROLE_CATALOG.get(planned.role.lower())
        if not cat:
            continue
        agent = Agent(
            name=planned.name or cat["name"],
            type=cat["type"],
            role=planned.role.lower(),
            project_id=project.id,
            capabilities=cat["capabilities"],
            llm_config={"instructions": planned.instructions or ""},
            status="idle",
        )
        db.add(agent)
        await db.flush()
        deployed.append(DeployedAgent(id=str(agent.id), name=agent.name, role=agent.role, type=agent.type))
        if body.create_kickoff_tasks:
            db.add(Task(
                project_id=project.id,
                title=f"{agent.name}: kick off — {cat['brief']}",
                description=f"Initial task for the {planned.role} agent on this engagement.",
                status="backlog",
                assigned_agent_id=agent.id,
            ))
            tasks_created += 1

    await db.commit()
    await broadcast_event("project.created", {"project_id": str(project.id), "name": project.name})
    await broadcast_event("agents.deployed", {"project_id": str(project.id), "count": len(deployed)})

    return DeployResponse(
        project_id=str(project.id),
        project_name=project.name,
        agents=deployed,
        tasks_created=tasks_created,
    )
