"""The autonomous 7-stage workflow + the human review gate (pause / approve / reject)."""

import asyncio

from app.services import orchestrator_service as osvc


async def _wait_until(predicate, timeout=8.0, interval=0.2):
    elapsed = 0.0
    while elapsed < timeout:
        if predicate():
            return True
        await asyncio.sleep(interval)
        elapsed += interval
    return predicate()


async def test_workflow_runs_through_review_then_pauses(auth, project_id):
    # Run the pipeline directly for determinism (runs through Testing, then pauses).
    await osvc.run_project_workflow(project_id, "Acme MVP")

    # The workflow is held awaiting human sign-off.
    assert project_id in osvc._pending_states

    # The pre-deploy stages were persisted as completed tasks.
    tasks = (await auth.get(f"/api/v1/tasks/?project_id={project_id}")).json()["tasks"]
    done = [t for t in tasks if t["status"] == "done"]
    assert len(done) >= 5  # init, ux, architecture, development, testing


async def test_approve_resumes_into_deploy(auth, project_id):
    await osvc.run_project_workflow(project_id, "Acme MVP")
    before = (await auth.get(f"/api/v1/tasks/?project_id={project_id}")).json()["tasks"]

    ok = await osvc.approve_review(project_id, feedback="looks good")
    assert ok

    # Deploy runs in the background after approval; wait for the gate to clear.
    cleared = await _wait_until(lambda: project_id not in osvc._pending_states)
    assert cleared

    after = (await auth.get(f"/api/v1/tasks/?project_id={project_id}")).json()["tasks"]
    assert len(after) > len(before)  # a deploy task was added


async def test_review_gate_survives_in_memory_reset(auth, project_id):
    await osvc.run_project_workflow(project_id, "Durable Review Gate")
    assert project_id in osvc._pending_states

    osvc._pending_states.pop(project_id, None)

    ok = await osvc.approve_review(project_id, feedback="resume from durable state")
    assert ok
    promoted = await _wait_until(lambda: project_id in osvc._pending_prod)
    assert promoted


async def test_reject_clears_the_gate(auth, project_id):
    await osvc.run_project_workflow(project_id, "RejectMe")
    assert project_id in osvc._pending_states
    ok = await osvc.reject_review(project_id, "needs rework")
    assert ok
    assert project_id not in osvc._pending_states


async def test_run_endpoint_returns_started(auth, project_id):
    r = await auth.post(f"/api/v1/orchestrator/projects/{project_id}/run?project_name=Acme")
    assert r.status_code == 200
    assert r.json()["status"] == "started"
    # let the background run settle so it doesn't leak into other tests
    await _wait_until(lambda: project_id in osvc._pending_states, timeout=8.0)
