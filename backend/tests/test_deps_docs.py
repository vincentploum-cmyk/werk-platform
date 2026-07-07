"""Dependency-installed workspaces + the shared document folder agents retrieve from."""

import shutil

import pytest

from app.services import workspace_service
from app.api import tasks as tasks_api


@pytest.fixture(autouse=True)
def _clean_ws():
    shutil.rmtree("/tmp/werk_ws_test", ignore_errors=True)
    yield
    shutil.rmtree("/tmp/werk_ws_test", ignore_errors=True)


# ── dependencies ────────────────────────────────────────────────────────────
def test_install_without_requirements():
    res = workspace_service.install_dependencies("p-nodep")
    assert res["enabled"] is True
    assert res["installed"] is False
    assert "No requirements.txt" in res["output"]


def test_tests_can_import_from_deps_dir():
    pid = "p-deps"
    # simulate an installed package by placing it in the .deps target dir
    workspace_service.write_files(pid, {".deps/mylib.py": "def greet():\n    return 'hi'\n"})
    workspace_service.write_files(pid, {"test_uses_dep.py": "import mylib\nassert mylib.greet() == 'hi'\n"})
    res = workspace_service.run_tests(pid)
    assert res["passed"] is True  # PYTHONPATH includes .deps


# ── shared document folder ──────────────────────────────────────────────────
def test_save_and_digest_documents():
    pid = "p-docs"
    workspace_service.save_document(pid, "requirements.md", "The system shall allow login.")
    workspace_service.save_document(pid, "architecture.md", "Use FastAPI + Postgres.")
    digest = workspace_service.documents_digest(pid)
    assert "requirements.md" in digest
    assert "shall allow login" in digest
    assert "architecture.md" in digest


async def test_agent_run_saves_document_and_next_agent_retrieves_it(auth, project_id, monkeypatch):
    agents = (await auth.get("/api/v1/agents/")).json()["agents"]
    req = next(a["id"] for a in agents if a["role"] == "requirements")
    arch = next(a["id"] for a in agents if a["role"] == "architect")

    async def req_out(system, user, max_tokens=1200):
        return ("The system shall support SSO login and audit logging.", "ollama")
    monkeypatch.setattr(tasks_api.llm, "chat_complete", req_out)
    rtid = (await auth.post("/api/v1/tasks/", json={
        "project_id": project_id, "title": "Requirements", "assigned_agent_id": req})).json()["id"]
    await auth.post(f"/api/v1/tasks/{rtid}/run")

    # the requirements doc is now in the shared folder
    docs = (await auth.get(f"/api/v1/workspace/{project_id}/documents")).json()["documents"]
    assert any(d["name"] == "requirements.md" for d in docs)

    # the architect's run must RECEIVE the requirements doc in its prompt
    captured = {}
    async def arch_out(system, user, max_tokens=1200):
        captured["user"] = user
        return ("Architecture: a FastAPI service.", "ollama")
    monkeypatch.setattr(tasks_api.llm, "chat_complete", arch_out)
    atid = (await auth.post("/api/v1/tasks/", json={
        "project_id": project_id, "title": "Architecture", "assigned_agent_id": arch})).json()["id"]
    await auth.post(f"/api/v1/tasks/{atid}/run")

    assert "SSO login and audit logging" in captured["user"]
    assert "requirements.md" in captured["user"]


async def test_install_endpoint(auth, project_id):
    workspace_service.write_files(project_id, {"requirements.txt": ""})
    r = await auth.post(f"/api/v1/workspace/{project_id}/install")
    assert r.status_code == 200
    # empty requirements installs nothing but the machinery runs
    assert r.json()["enabled"] is True
