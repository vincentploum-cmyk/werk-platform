"""Artifacts: agents produce named, typed, downloadable deliverable files."""

from app.services import orchestrator_service as osvc


async def _developer_id(auth):
    agents = (await auth.get("/api/v1/agents/")).json()["agents"]
    return next(a["id"] for a in agents if a["role"] == "developer")


async def test_running_a_task_produces_an_artifact(auth, project_id):
    aid = await _developer_id(auth)
    r = await auth.post(
        "/api/v1/tasks/",
        json={"project_id": project_id, "title": "Implement the API", "assigned_agent_id": aid},
    )
    tid = r.json()["id"]
    await auth.post(f"/api/v1/tasks/{tid}/run")

    arts = (await auth.get(f"/api/v1/artifacts/?project_id={project_id}")).json()["artifacts"]
    assert len(arts) >= 1
    art = next(a for a in arts if a["task_id"] == tid)
    assert art["filename"] == "implementation.md"
    assert art["file_type"] == "md"
    assert art["size"] > 0


async def test_get_and_download_artifact(auth, project_id):
    aid = await _developer_id(auth)
    tid = (await auth.post("/api/v1/tasks/", json={
        "project_id": project_id, "title": "Build it", "assigned_agent_id": aid,
    })).json()["id"]
    await auth.post(f"/api/v1/tasks/{tid}/run")
    art = (await auth.get(f"/api/v1/artifacts/?task_id={tid}")).json()["artifacts"][0]

    # detail includes content
    detail = await auth.get(f"/api/v1/artifacts/{art['id']}")
    assert detail.status_code == 200
    assert detail.json()["content"]

    # download returns a file
    dl = await auth.get(f"/api/v1/artifacts/{art['id']}/download")
    assert dl.status_code == 200
    assert dl.headers["content-type"].startswith("text/markdown")
    assert "attachment" in dl.headers["content-disposition"]
    assert len(dl.content) > 0


async def test_workflow_produces_artifacts_per_stage(auth, project_id):
    await osvc.run_project_workflow(project_id, "Acme MVP")
    arts = (await auth.get(f"/api/v1/artifacts/?project_id={project_id}")).json()["artifacts"]
    # init..testing → 5 artifacts, named by stage role
    assert len(arts) >= 5
    names = {a["filename"] for a in arts}
    assert "functional_requirements.md" in names
    assert "architecture.md" in names
    assert "test_plan.md" in names
