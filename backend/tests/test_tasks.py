"""Tasks: CRUD, the status state machine, and model-driven Run."""


async def _developer_id(auth):
    agents = (await auth.get("/api/v1/agents/")).json()["agents"]
    return next(a["id"] for a in agents if a["role"] == "developer")


async def test_task_crud_and_state_machine(auth, project_id):
    r = await auth.post("/api/v1/tasks/", json={"project_id": project_id, "title": "Build login"})
    assert r.status_code == 201
    tid = r.json()["id"]
    assert r.json()["status"] == "backlog"

    # invalid transition backlog -> done is rejected
    bad = await auth.put(f"/api/v1/tasks/{tid}", json={"status": "done"})
    assert bad.status_code == 422

    # valid path backlog -> in_progress -> review
    assert (await auth.put(f"/api/v1/tasks/{tid}", json={"status": "in_progress"})).status_code == 200
    assert (await auth.put(f"/api/v1/tasks/{tid}", json={"status": "review"})).status_code == 200

    # filtered list
    lst = await auth.get(f"/api/v1/tasks/?project_id={project_id}")
    assert any(t["id"] == tid for t in lst.json()["tasks"])

    # delete
    assert (await auth.delete(f"/api/v1/tasks/{tid}")).status_code == 200


async def test_run_requires_assigned_agent(auth, project_id):
    r = await auth.post("/api/v1/tasks/", json={"project_id": project_id, "title": "Unassigned"})
    tid = r.json()["id"]
    run = await auth.post(f"/api/v1/tasks/{tid}/run")
    assert run.status_code == 400


async def test_run_task_produces_result_and_moves_to_review(auth, project_id):
    aid = await _developer_id(auth)
    r = await auth.post(
        "/api/v1/tasks/",
        json={"project_id": project_id, "title": "Implement endpoint", "assigned_agent_id": aid},
    )
    tid = r.json()["id"]
    run = await auth.post(f"/api/v1/tasks/{tid}/run")
    assert run.status_code == 200
    body = run.json()
    assert body["status"] == "review"
    assert body["result"]  # simulated deliverable present
    assert len(body["artifacts"]) >= 1
