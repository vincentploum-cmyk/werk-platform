"""PMO agent + status reports, and the test/prod deploy agents with the production gate."""

import asyncio
import shutil

import pytest

from app.services import orchestrator_service as osvc, workspace_service


@pytest.fixture(autouse=True)
def _clean_ws():
    shutil.rmtree("/tmp/werk_ws_test", ignore_errors=True)
    yield
    shutil.rmtree("/tmp/werk_ws_test", ignore_errors=True)


async def _wait(predicate, timeout=10.0):
    elapsed = 0.0
    while elapsed < timeout:
        if predicate():
            return True
        await asyncio.sleep(0.2)
        elapsed += 0.2
    return predicate()


# ── roster ──────────────────────────────────────────────────────────────────
async def test_roster_includes_pmo_and_release(auth):
    roles = {a["role"] for a in (await auth.get("/api/v1/agents/")).json()["agents"]}
    assert {"pmo", "release", "devops"} <= roles


async def test_sow_staffs_pmo_and_both_deploy_agents(auth):
    sow = b"Hybrid delivery, 3 releases, deploy to production via CI/CD pipeline. GDPR compliance."
    plan = (await auth.post("/api/v1/sow/analyze", files={"file": ("sow.txt", sow, "text/plain")})).json()
    roles = {a["role"] for a in plan["agents"]}
    assert "pmo" in roles       # PMO always leads
    assert "devops" in roles    # test environment
    assert "release" in roles   # production environment


# ── production gate ─────────────────────────────────────────────────────────
async def test_prod_gate_splits_test_and_prod_deploys(auth, project_id):
    await osvc.run_project_workflow(project_id, "Acme MVP")
    assert project_id in osvc._pending_states  # paused at review

    assert await osvc.approve_review(project_id)
    # → deploys to TEST, then pauses at the production gate
    assert await _wait(lambda: project_id in osvc._pending_prod)
    assert project_id not in osvc._pending_states

    arts = (await auth.get(f"/api/v1/artifacts/?project_id={project_id}")).json()["artifacts"]
    assert any(a["filename"] == "deployment_test.md" for a in arts)
    assert not any(a["filename"] == "deployment_production.md" for a in arts)  # not yet

    # approve production → deploys to prod
    assert await osvc.approve_prod(project_id)
    assert await _wait(lambda: project_id not in osvc._pending_prod)
    arts2 = (await auth.get(f"/api/v1/artifacts/?project_id={project_id}")).json()["artifacts"]
    assert any(a["filename"] == "deployment_production.md" for a in arts2)


async def test_prod_reject_holds_production(auth, project_id):
    await osvc.run_project_workflow(project_id, "RejectProd")
    await osvc.approve_review(project_id)
    assert await _wait(lambda: project_id in osvc._pending_prod)
    assert await osvc.reject_prod(project_id, "hold prod")
    assert project_id not in osvc._pending_prod
    arts = (await auth.get(f"/api/v1/artifacts/?project_id={project_id}")).json()["artifacts"]
    assert not any(a["filename"] == "deployment_production.md" for a in arts)


async def test_prod_gate_survives_in_memory_reset(auth, project_id):
    await osvc.run_project_workflow(project_id, "Durable Prod Gate")
    await osvc.approve_review(project_id)
    assert await _wait(lambda: project_id in osvc._pending_prod)

    osvc._pending_prod.pop(project_id, None)

    assert await osvc.approve_prod(project_id)
    assert await _wait(lambda: project_id not in osvc._pending_prod)


# ── PMO status report ───────────────────────────────────────────────────────
async def test_pmo_status_report(auth, project_id):
    workspace_service.save_document(project_id, "requirements.md", "The system shall allow SSO login.")
    workspace_service.save_document(project_id, "architecture.md", "A FastAPI service on Postgres.")
    r = await auth.post(f"/api/v1/projects/{project_id}/status-report")
    assert r.status_code == 200
    assert r.json()["report"]

    arts = (await auth.get(f"/api/v1/artifacts/?project_id={project_id}")).json()["artifacts"]
    assert any(a["filename"] == "status_report.md" for a in arts)
