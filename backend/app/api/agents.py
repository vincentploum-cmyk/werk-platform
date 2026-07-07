"""Agent API endpoints — register, query, and chat with Werk agents (RBAC enforced)."""

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.db_models import Agent
from app.core.auth import CurrentUser, RequirePermission, get_optional_user
from app.services import doc_extract, requirements_gen, llm

router = APIRouter()


def _default_instructions(agent: Agent) -> str:
    """A complete, editable starting system prompt for an agent."""
    role = (agent.role or "").lower()
    brief = _ROLE_BRIEF.get(role, "support the delivery of this project")
    caps = ", ".join(agent.capabilities or []) or "general consulting"
    return (
        f"You are {agent.name}, a {agent.type} consulting agent on the Werk platform.\n"
        f"Your job is to {brief}.\n"
        f"Your skills: {caps}.\n"
        "Answer concisely and practically, in character, as this specialist. "
        "Be specific, avoid fluff, and propose concrete next steps or artifacts."
    )


def _effective_instructions(agent: Agent) -> str:
    """The agent's saved instructions, or the default if none have been set."""
    saved = (agent.llm_config or {}).get("instructions")
    return saved if saved and saved.strip() else _default_instructions(agent)


# Public alias so other modules (e.g. tasks.py task-run) can reuse it.
effective_instructions = _effective_instructions


def _examples_of(agent: Agent) -> list:
    """Stored few-shot examples: list of {input?: str, output: str}."""
    ex = (agent.llm_config or {}).get("examples")
    return ex if isinstance(ex, list) else []


def build_system(agent: Agent) -> str:
    """Full system prompt = instructions + any few-shot examples. Used for all generation."""
    system = _effective_instructions(agent)
    examples = _examples_of(agent)
    if examples:
        blocks = []
        for i, ex in enumerate(examples, start=1):
            out = (ex.get("output") or "").strip()
            if not out:
                continue
            inp = (ex.get("input") or "").strip()
            if inp:
                blocks.append(f"Example {i} — given: {inp}\nGood output:\n{out}")
            else:
                blocks.append(f"Example {i} — good output:\n{out}")
        if blocks:
            system += (
                "\n\nHere are examples of strong output. Match this style, structure, and level "
                "of detail:\n\n" + "\n\n".join(blocks)
            )
    return system


def _agent_dict(agent: Agent) -> dict:
    """Serialize an Agent ORM row into clean JSON (UUID/datetime → str)."""
    cfg = agent.llm_config or {}
    return {
        "id": str(agent.id),
        "name": agent.name,
        "type": agent.type,
        "role": agent.role,
        "project_id": str(agent.project_id) if agent.project_id else None,
        "capabilities": agent.capabilities or [],
        "status": agent.status,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
        "instructions": _effective_instructions(agent),
        "instructions_custom": bool(cfg.get("instructions", "").strip()),
        "examples": cfg.get("examples") if isinstance(cfg.get("examples"), list) else [],
    }


@router.get("/")
async def list_agents(
    project_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("agents:read")),
):
    """List agents. With ?project_id, returns that project's deployed team;
    without it, returns the global template roster (project_id IS NULL)."""
    query = select(Agent)
    if project_id:
        query = query.where(Agent.project_id == project_id)
    else:
        query = query.where(Agent.project_id.is_(None))
    result = await db.execute(query.order_by(Agent.name))
    agents = result.scalars().all()
    return {"agents": [_agent_dict(a) for a in agents]}


@router.post("/", status_code=status.HTTP_201_CREATED)
async def register_agent(
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("agents:create")),
):
    """Register a new agent type. Restricted to admin and lead roles."""
    agent = Agent(
        name=body["name"],
        type=body["type"],
        role=body["role"],
        capabilities=body.get("capabilities", []),
    )
    db.add(agent)
    await db.flush()
    await db.refresh(agent)
    return _agent_dict(agent)


@router.get("/{agent_id}")
async def get_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("agents:read")),
):
    """Get agent details by ID."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return _agent_dict(agent)


# ---------------------------------------------------------------------------
# Chat with an agent
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    message: str
    project_id: Optional[str] = None


class ChatResponse(BaseModel):
    agent_id: str
    agent_name: str
    role: str
    reply: str
    source: str  # "llm" or "persona" — tells the UI whether a real model answered


# What each consulting role does, used to ground replies (LLM and offline both).
_ROLE_BRIEF: dict[str, str] = {
    "pmo": "lead the engagement: synthesize status reports from every agent's work, track risks "
           "and progress, and set direction for the team",
    "requirements": "translate business goals into PRDs, user stories, and acceptance criteria",
    "ux": "turn requirements into wireframes, user flows, and design-system decisions",
    "business": "define data models, business rules, and validation logic",
    "architect": "choose the tech stack and design the system and database schema",
    "developer": "implement features, write clean code, and refactor",
    "tester": "write unit, integration, and end-to-end tests and find defects",
    "devops": "deploy to the test/staging environment and keep it healthy and running",
    "release": "deploy to production with rollout/rollback and keep production healthy and running",
}

_ROLE_NEXT: dict[str, str] = {
    "pmo": "share the status report with leadership and direct the team's next steps",
    "requirements": "hand the PRD to the UX and Architect agents",
    "ux": "pass the wireframes to the Architect and Developer agents",
    "business": "share the data model with the Architect agent",
    "architect": "hand the architecture to the Developer agent to implement",
    "developer": "send the build to the Tester agent for validation",
    "tester": "route results to the Review gate for sign-off",
    "devops": "hand off to the Release Agent for production once the test environment is healthy",
    "release": "confirm production is live and report status to the PMO",
}


def _persona_reply(agent: Agent, message: str) -> str:
    """Deterministic, offline-safe reply grounded in the agent's role + capabilities.

    Replaced transparently by an LLM call when an API key is configured.
    """
    role = (agent.role or "").lower()
    brief = _ROLE_BRIEF.get(role, "support the delivery of this project")
    nxt = _ROLE_NEXT.get(role, "coordinate with the rest of the team")
    caps = ", ".join(agent.capabilities or []) or "general consulting"
    return (
        f"I'm the {agent.name}. My job on this engagement is to {brief}. "
        f"On “{message.strip()}” — here's how I'd approach it: I'd start from what we know, "
        f"apply my skills ({caps}), and produce a concrete artifact you can review. "
        f"When that's signed off, I'd {nxt}. Want me to take this on as a task?"
    )


async def _llm_reply(agent: Agent, message: str) -> Optional[str]:
    """Try a real model reply (local Ollama or a configured API). None if none available."""
    system = build_system(agent)
    text, _provider = await llm.chat_complete(system, message, max_tokens=500)
    return text


@router.post("/{agent_id}/chat", response_model=ChatResponse)
async def chat_with_agent(
    agent_id: str,
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user: Optional[CurrentUser] = Depends(get_optional_user),
):
    """Chat with a specific agent. Uses a configured LLM if available, else a persona reply."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    reply = await _llm_reply(agent, body.message)
    source = "llm" if reply else "persona"
    if not reply:
        reply = _persona_reply(agent, body.message)

    return ChatResponse(
        agent_id=str(agent.id),
        agent_name=agent.name,
        role=agent.role,
        reply=reply,
        source=source,
    )


# ---------------------------------------------------------------------------
# Edit an agent's instructions (system prompt) — "tuning" the agent
# ---------------------------------------------------------------------------


class InstructionsRequest(BaseModel):
    instructions: str  # empty string resets to the role default


@router.get("/{agent_id}/instructions")
async def get_instructions(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("agents:read")),
):
    """Return an agent's effective and default instructions."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return {
        "agent_id": str(agent.id),
        "instructions": _effective_instructions(agent),
        "default_instructions": _default_instructions(agent),
        "is_custom": bool((agent.llm_config or {}).get("instructions", "").strip()),
    }


@router.put("/{agent_id}/instructions")
async def update_instructions(
    agent_id: str,
    body: InstructionsRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("agents:update")),
):
    """Save custom instructions for an agent. Takes effect immediately for chat + analysis.

    Sending an empty string resets the agent to its role default.
    """
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    # JSON columns need reassignment for SQLAlchemy to detect the change.
    cfg = dict(agent.llm_config or {})
    cfg["instructions"] = (body.instructions or "").strip()
    agent.llm_config = cfg
    await db.flush()
    await db.refresh(agent)
    return _agent_dict(agent)


class ExampleItem(BaseModel):
    input: str = ""
    output: str


class ExamplesRequest(BaseModel):
    examples: list[ExampleItem]


@router.put("/{agent_id}/examples")
async def update_examples(
    agent_id: str,
    body: ExamplesRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("agents:update")),
):
    """Save few-shot examples for an agent. Included in its prompt for all generation."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    cleaned = [
        {"input": (e.input or "").strip(), "output": e.output.strip()}
        for e in body.examples
        if e.output and e.output.strip()
    ]
    cfg = dict(agent.llm_config or {})
    cfg["examples"] = cleaned
    agent.llm_config = cfg
    await db.flush()
    await db.refresh(agent)
    return _agent_dict(agent)


# ---------------------------------------------------------------------------
# Analyze an uploaded document → functional requirements
# ---------------------------------------------------------------------------


class RequirementItem(BaseModel):
    id: str
    text: str


class AnalyzeResponse(BaseModel):
    agent_id: str
    agent_name: str
    source: str  # "llm" or "heuristic"
    filename: str
    char_count: int
    preview: str
    requirements: list[RequirementItem]


@router.post("/{agent_id}/analyze", response_model=AnalyzeResponse)
async def analyze_document(
    agent_id: str,
    file: UploadFile = File(...),
    instruction: str = Form(""),
    db: AsyncSession = Depends(get_db),
    user: Optional[CurrentUser] = Depends(get_optional_user),
):
    """Read an uploaded requirements doc (pptx/pdf/docx/txt) and draft functional requirements."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    filename = file.filename or "upload"
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
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not read '{filename}': {exc}",
        )

    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No readable text found in the document.",
        )

    reqs, source = await requirements_gen.generate_requirements(
        text, instruction, system=build_system(agent)
    )

    return AnalyzeResponse(
        agent_id=str(agent.id),
        agent_name=agent.name,
        source=source,
        filename=filename,
        char_count=len(text),
        preview=text[:600],
        requirements=[RequirementItem(id=f"FR-{i}", text=r) for i, r in enumerate(reqs, start=1)],
    )


class RequirementsDocRequest(BaseModel):
    title: str = "Functional Requirements"
    requirements: list[str]
    source_name: str = ""


@router.post("/{agent_id}/requirements-doc")
async def requirements_doc(
    agent_id: str,
    body: RequirementsDocRequest,
    db: AsyncSession = Depends(get_db),
    user: Optional[CurrentUser] = Depends(get_optional_user),
):
    """Render a (possibly edited) requirements list as a downloadable .docx."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    cleaned = [r.strip() for r in body.requirements if r and r.strip()]
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No requirements to write.",
        )

    data = requirements_gen.build_requirements_docx(body.title, cleaned, body.source_name)
    safe = (body.title or "requirements").lower().replace(" ", "_")[:40]
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{safe}.docx"'},
    )