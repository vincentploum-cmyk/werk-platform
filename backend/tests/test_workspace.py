"""Execution layer: Developer writes real files, Tester runs them, real pass/fail."""

import shutil

import pytest

from app.services import workspace_service, llm
from app.api import tasks as tasks_api


@pytest.fixture(autouse=True)
def _clean_ws():
    shutil.rmtree("/tmp/werk_ws_test", ignore_errors=True)
    yield
    shutil.rmtree("/tmp/werk_ws_test", ignore_errors=True)


# ── unit: workspace service ─────────────────────────────────────────────────
def test_extract_code_files_from_fenced_blocks():
    text = (
        "Here is the code:\n"
        "```python app/calc.py\n"
        "def add(a, b):\n    return a + b\n"
        "```\n"
        "and a test:\n"
        "```python test_calc.py\n"
        "from app.calc import add\nassert add(2, 3) == 5\n"
        "```\n"
    )
    files = workspace_service.extract_code_files(text)
    assert set(files) == {"app/calc.py", "test_calc.py"}
    assert "def add" in files["app/calc.py"]


def test_rejects_unsafe_paths():
    import pytest as _pytest
    with _pytest.raises(ValueError):
        workspace_service.write_files("p-unsafe", {"../escape.py": "x"})


def test_run_tests_pass_and_fail():
    pid = "p-exec"
    workspace_service.write_files(pid, {
        "app/calc.py": "def add(a, b):\n    return a + b\n",
        "test_calc.py": "import sys; sys.path.insert(0, '.')\nfrom app.calc import add\nassert add(2, 3) == 5\n",
    })
    res = workspace_service.run_tests(pid)
    assert res["enabled"] is True
    assert res["passed"] is True

    # now a failing test
    workspace_service.write_files(pid, {"test_calc.py": "assert 1 == 2\n"})
    res2 = workspace_service.run_tests(pid)
    assert res2["passed"] is False
    assert "FAIL" in res2["output"]


# ── integration: developer writes, tester runs (model patched) ──────────────
async def test_developer_run_writes_files(auth, project_id, monkeypatch):
    agents = (await auth.get("/api/v1/agents/")).json()["agents"]
    dev = next(a["id"] for a in agents if a["role"] == "developer")

    async def fake(system, user, max_tokens=1200):
        return ("```python app/calc.py\ndef add(a, b):\n    return a + b\n```", "ollama")
    monkeypatch.setattr(llm, "chat_complete", fake)
    monkeypatch.setattr(tasks_api.llm, "chat_complete", fake)

    tid = (await auth.post("/api/v1/tasks/", json={
        "project_id": project_id, "title": "Build calc", "assigned_agent_id": dev,
    })).json()["id"]
    await auth.post(f"/api/v1/tasks/{tid}/run")

    files = (await auth.get(f"/api/v1/workspace/{project_id}/files")).json()["files"]
    assert any(f["path"] == "app/calc.py" for f in files)
    # the real source file is also an artifact
    arts = (await auth.get(f"/api/v1/artifacts/?project_id={project_id}")).json()["artifacts"]
    assert any(a["filename"] == "calc.py" for a in arts)


async def test_tester_run_executes_and_reports(auth, project_id, monkeypatch):
    agents = (await auth.get("/api/v1/agents/")).json()["agents"]
    dev = next(a["id"] for a in agents if a["role"] == "developer")
    tester = next(a["id"] for a in agents if a["role"] == "tester")

    async def dev_code(system, user, max_tokens=1200):
        return ("```python app/calc.py\ndef add(a, b):\n    return a + b\n```", "ollama")

    async def test_code(system, user, max_tokens=1200):
        return ("```python test_calc.py\nimport sys; sys.path.insert(0, '.')\n"
                "from app.calc import add\nassert add(2, 3) == 5\n```", "ollama")

    # developer writes the code
    monkeypatch.setattr(tasks_api.llm, "chat_complete", dev_code)
    dtid = (await auth.post("/api/v1/tasks/", json={
        "project_id": project_id, "title": "Code", "assigned_agent_id": dev})).json()["id"]
    await auth.post(f"/api/v1/tasks/{dtid}/run")

    # tester writes the test and runs it
    monkeypatch.setattr(tasks_api.llm, "chat_complete", test_code)
    ttid = (await auth.post("/api/v1/tasks/", json={
        "project_id": project_id, "title": "Test", "assigned_agent_id": tester})).json()["id"]
    run = await auth.post(f"/api/v1/tasks/{ttid}/run")
    assert run.status_code == 200
    assert "PASSED" in run.json()["result"]

    # the test run produced a results artifact
    arts = (await auth.get(f"/api/v1/artifacts/?task_id={ttid}")).json()["artifacts"]
    assert any(a["filename"] == "test_results.txt" for a in arts)


async def test_run_tests_endpoint(auth, project_id):
    workspace_service.write_files(project_id, {"test_x.py": "assert True\n"})
    r = await auth.post(f"/api/v1/workspace/{project_id}/run-tests")
    assert r.status_code == 200
    assert r.json()["passed"] is True
