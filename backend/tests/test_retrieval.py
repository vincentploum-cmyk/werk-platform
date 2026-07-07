"""Semantic retrieval: agents pull the most relevant document chunks, not a full dump."""

import shutil

import pytest

from app.services import workspace_service, retrieval_service
from app.api import tasks as tasks_api


@pytest.fixture(autouse=True)
def _clean_ws():
    shutil.rmtree("/tmp/werk_ws_test", ignore_errors=True)
    yield
    shutil.rmtree("/tmp/werk_ws_test", ignore_errors=True)


def test_chunking_splits_long_docs():
    chunks = retrieval_service._chunk("para one.\n\n" + ("x" * 2000))
    assert len(chunks) >= 2


async def test_retrieval_ranks_relevant_doc_first():
    pid = "p-ret"
    workspace_service.save_document(pid, "auth.md",
        "Authentication and login. Users sign in with email and password and SSO. Sessions and tokens.")
    workspace_service.save_document(pid, "deploy.md",
        "Deployment and CI/CD. Containers, Kubernetes, release pipelines and rollouts to production.")

    ctx = await retrieval_service.retrieve_context(pid, "how do users authenticate and log in", k=1)
    assert "auth.md" in ctx
    assert "deploy.md" not in ctx  # only the most relevant chunk is returned at k=1


async def test_run_uses_relevant_context(auth, project_id, monkeypatch):
    agents = (await auth.get("/api/v1/agents/")).json()["agents"]
    req = next(a["id"] for a in agents if a["role"] == "requirements")
    arch = next(a["id"] for a in agents if a["role"] == "architect")

    # produce two requirements docs by running the requirements agent twice with different output
    async def out_auth(system, user, max_tokens=1200):
        return ("Authentication: the system shall support SSO and password login with MFA.", "ollama")
    monkeypatch.setattr(tasks_api.llm, "chat_complete", out_auth)
    t1 = (await auth.post("/api/v1/tasks/", json={
        "project_id": project_id, "title": "Auth requirements", "assigned_agent_id": req})).json()["id"]
    await auth.post(f"/api/v1/tasks/{t1}/run")  # saves requirements.md (latest wins)

    # architect asks about authentication → retrieval should surface the auth content
    captured = {}
    async def arch_out(system, user, max_tokens=1200):
        captured["user"] = user
        return ("Architecture for authentication.", "ollama")
    monkeypatch.setattr(tasks_api.llm, "chat_complete", arch_out)
    t2 = (await auth.post("/api/v1/tasks/", json={
        "project_id": project_id, "title": "Design the authentication architecture",
        "assigned_agent_id": arch})).json()["id"]
    await auth.post(f"/api/v1/tasks/{t2}/run")

    assert "SSO and password login" in captured["user"]
    assert "Relevant documents" in captured["user"]
