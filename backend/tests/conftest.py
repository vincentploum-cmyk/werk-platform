"""Pytest harness — boots the FastAPI app in-process against SQLite + fakeredis.

No Postgres, Redis, MinIO, or model server required: the whole platform is exercised
end-to-end offline. Mirrors the project's own start_perf_backend.py pattern.
"""

import asyncio
import os
import sys

# --- make app + orchestrator importable -----------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
ROOT = os.path.dirname(BACKEND)
# BACKEND must be searched BEFORE ROOT: the real `app` package lives at BACKEND/app.
# If ROOT (e.g. "/" in the container) is searched first and contains a directory named
# "app" (the WORKDIR /app), Python resolves `import app` to that namespace-package
# directory and `app.main` is not found. Inserting BACKEND last puts it at sys.path[0].
for p in (ROOT, BACKEND):
    if p in sys.path:
        sys.path.remove(p)
sys.path.insert(0, ROOT)
sys.path.insert(0, BACKEND)

# --- offline environment (must be set before importing the app) -----------
_DB_FILE = "/tmp/werk_test.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB_FILE}"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["DEBUG"] = "true"
os.environ["USE_OLLAMA"] = "false"
os.environ["OPENAI_API_KEY"] = ""
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["ENABLE_CODE_EXECUTION"] = "true"
os.environ["WORKSPACE_ROOT"] = "/tmp/werk_ws_test"

# --- patch the async engine for sqlite (drop PG-only kwargs, no pooling) ---
import sqlalchemy.ext.asyncio as _sa
from sqlalchemy.pool import NullPool

_orig_create = _sa.create_async_engine


def _patched_create(url, **kwargs):
    if str(url).startswith("sqlite"):
        kwargs.pop("pool_size", None)
        kwargs.pop("max_overflow", None)
        kwargs["poolclass"] = NullPool  # avoid cross-event-loop connection reuse
    return _orig_create(url, **kwargs)


_sa.create_async_engine = _patched_create

# --- patch redis with fakeredis -------------------------------------------
import redis.asyncio as _redis_async
import fakeredis.aioredis as _fakeredis

_redis_async.from_url = lambda *a, **k: _fakeredis.FakeRedis()

# --- now import the app ----------------------------------------------------
import httpx  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport  # noqa: E402

from app.main import app  # noqa: E402
from app.database import init_db, async_session_factory  # noqa: E402
from app.models.db_models import Agent  # noqa: E402

SEED_AGENTS = [
    ("PMO Agent", "leadership", "pmo", ["status-reporting", "coordination"]),
    ("Requirements Agent", "functional", "requirements", ["prd-generation", "user-story-writing"]),
    ("UX Agent", "functional", "ux", ["wireframing", "user-flow-design"]),
    ("Business Logic Agent", "functional", "business", ["data-modeling"]),
    ("Architect Agent", "technical", "architect", ["system-design", "schema-design"]),
    ("Developer Agent", "technical", "developer", ["code-generation"]),
    ("Tester Agent", "technical", "tester", ["unit-testing"]),
    ("DevOps Agent", "technical", "devops", ["test-env-deploy"]),
    ("Release Agent", "technical", "release", ["production-deploy"]),
]


async def _init_and_seed():
    if os.path.exists(_DB_FILE):
        os.remove(_DB_FILE)
    await init_db()
    async with async_session_factory() as db:
        for name, type_, role, caps in SEED_AGENTS:
            db.add(Agent(name=name, type=type_, role=role, capabilities=caps))
        await db.commit()


@pytest.fixture(scope="session", autouse=True)
def _setup_database():
    """Create tables and seed the 7 agents once for the whole test session."""
    asyncio.run(_init_and_seed())
    yield


@pytest_asyncio.fixture
async def client():
    """Anonymous in-process HTTP client against the ASGI app."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def admin_token(client):
    resp = await client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "admin123"}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def auth(client, admin_token):
    """Client authenticated as admin (all permissions)."""
    client.headers.update({"Authorization": f"Bearer {admin_token}"})
    return client


@pytest_asyncio.fixture
async def viewer_token(client):
    await client.post(
        "/api/v1/auth/register",
        json={"username": "v_user", "password": "viewpass", "role": "viewer"},
    )
    resp = await client.post(
        "/api/v1/auth/login", json={"username": "v_user", "password": "viewpass"}
    )
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def project_id(auth):
    """A freshly created project, returns its id."""
    resp = await auth.post("/api/v1/projects/", json={"name": "Test Project", "description": "for tests"})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]
