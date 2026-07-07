import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import projects, agents, tasks, artifacts
from app.api import ws as ws_api
from app.api import auth as auth_api
from app.api import orchestrator as orchestrator_api
from app.api import hello as hello_api
from app.api import sow as sow_api
from app.api import workspace as workspace_api
from app.core.config import settings
from app.database import init_db, ensure_schema, close_db

logger = logging.getLogger(__name__)

# Background task handles (for clean shutdown)
_background_tasks = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: initialize and tear down resources."""
    # Startup
    if settings.debug:
        await init_db()
    # Idempotent column migrations for already-provisioned databases.
    await ensure_schema()
    # Make sure the global roster has every catalog role (adds PMO, Release, etc.).
    try:
        from app.services.seed import ensure_default_agents
        await ensure_default_agents()
    except Exception as e:
        logger.warning(f"Could not ensure default agents: {e}")

    # Start the orchestrator event bus subscriber as a background task
    try:
        from app.services.orchestrator_service import subscribe_to_orchestrator_events
        task = asyncio.create_task(subscribe_to_orchestrator_events())
        _background_tasks.append(task)
        logger.info("Orchestrator event bus subscriber started")
    except Exception as e:
        logger.warning(f"Could not start event bus subscriber: {e}")

    yield

    # Shutdown: cancel background tasks
    for task in _background_tasks:
        task.cancel()
    await asyncio.gather(*_background_tasks, return_exceptions=True)
    await close_db()


app = FastAPI(
    title="Werk Platform API",
    version=settings.version,
    description="AI-orchestrated software development platform",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST Routers
app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(artifacts.router, prefix="/api/v1/artifacts", tags=["artifacts"])

# Orchestrator Router
app.include_router(orchestrator_api.router, prefix="/api/v1/orchestrator", tags=["orchestrator"])

# Auth Router
app.include_router(auth_api.router, prefix="/api/v1/auth", tags=["auth"])

# WebSocket Router
app.include_router(ws_api.router, prefix="/ws", tags=["websocket"])

# Hello World (public, no auth)
app.include_router(hello_api.router, prefix="/api", tags=["hello"])

# SOW intake — upload a Statement of Work, deploy a tailored team of agents
app.include_router(sow_api.router, prefix="/api/v1/sow", tags=["sow"])

# Execution layer — per-project code workspace + test running
app.include_router(workspace_api.router, prefix="/api/v1/workspace", tags=["workspace"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.version}