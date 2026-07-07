"""SOW intake: configurable parameters + rules-driven, project-scoped staffing."""

from app.services import orchestrator_service as osvc

SOW_TEXT = """Project Phoenix - Customer Portal
Delivery approach: hybrid. The programme spans 3 releases across the United States and
the United Kingdom. We will run 5 test cycles before go-live. Budget 750000 USD over a
12 months duration. Must meet GDPR and SOC2 compliance.
We need a customer-facing web application with a polished UI, a REST API and a database.
"""


def _sow_file():
    return {"file": ("sow.txt", SOW_TEXT.encode(), "text/plain")}


async def test_definitions_default_and_editable(auth):
    g = await auth.get("/api/v1/sow/parameters/definitions")
    assert g.status_code == 200
    keys = {d["key"] for d in g.json()["definitions"]}
    assert {"approach", "releases", "test_cycles", "countries", "budget_usd", "duration_months", "compliance"} <= keys

    # add a custom parameter and confirm it persists
    defs = g.json()["definitions"] + [
        {"key": "vendor_count", "label": "Vendors", "type": "number", "default": 1,
         "keywords": ["vendors"], "staffing": [{"type": "add_roles_if_gt", "threshold": 2, "roles": ["business"]}]}
    ]
    p = await auth.put("/api/v1/sow/parameters/definitions", json={"definitions": defs})
    assert p.status_code == 200
    g2 = await auth.get("/api/v1/sow/parameters/definitions")
    assert any(d["key"] == "vendor_count" for d in g2.json()["definitions"])
    # restore defaults for other tests
    await auth.put("/api/v1/sow/parameters/definitions", json={"definitions": g.json()["definitions"]})


async def test_analyze_extracts_all_configured_parameters(auth):
    r = await auth.post("/api/v1/sow/analyze", files=_sow_file())
    assert r.status_code == 200
    plan = r.json()
    p = plan["parameters"]
    assert p["approach"] == "hybrid"
    assert p["releases"] == 3
    assert p["test_cycles"] == 5
    assert {"United States", "United Kingdom"} <= set(p["countries"])
    assert p["budget_usd"] == 750000
    assert p["duration_months"] == 12
    assert set(p["compliance"]) >= {"GDPR", "SOC2"}
    assert plan["definitions"]  # the schema travels with the plan


async def test_rules_drive_team_composition(auth):
    plan = (await auth.post("/api/v1/sow/analyze", files=_sow_file())).json()
    roles = [a["role"] for a in plan["agents"]]
    assert "devops" in roles            # >1 release and >6 months
    assert "ux" in roles                # >1 country
    assert "business" in roles          # budget>250k and compliance present
    assert roles.count("tester") == 3   # 5 cycles, capped at 3


async def test_team_endpoint_reflects_edited_parameters(auth):
    # agile, single everything, no compliance/budget → lean team, 1 tester, no devops
    body = {"parameters": {"approach": "agile", "releases": 1, "test_cycles": 1, "countries": [],
                           "budget_usd": 0, "duration_months": 1, "compliance": []}}
    r = await auth.post("/api/v1/sow/team", json=body)
    roles = [a["role"] for a in r.json()["agents"]]
    assert "devops" not in roles
    assert roles.count("tester") == 1
    # waterfall brings business analysis even without budget/compliance
    r2 = await auth.post("/api/v1/sow/team", json={"parameters": {"approach": "waterfall"}})
    assert "business" in [a["role"] for a in r2.json()["agents"]]


async def test_deploy_persists_parameters_and_scoped_team(auth):
    plan = (await auth.post("/api/v1/sow/analyze", files=_sow_file())).json()
    d = await auth.post("/api/v1/sow/deploy", json={
        "project_name": plan["project_name"], "summary": plan["summary"],
        "parameters": plan["parameters"], "agents": plan["agents"], "create_kickoff_tasks": True,
    })
    assert d.status_code == 200
    res = d.json()
    pid = res["project_id"]
    assert len(res["agents"]) == len(plan["agents"])
    proj = (await auth.get(f"/api/v1/projects/{pid}")).json()
    assert proj["config"]["parameters"]["budget_usd"] == 750000
    team = (await auth.get(f"/api/v1/agents/?project_id={pid}")).json()["agents"]
    assert all(a["project_id"] == pid for a in team)
    glob = (await auth.get("/api/v1/agents/")).json()["agents"]
    assert len(glob) == 9


async def test_deploy_requires_agents(auth):
    r = await auth.post("/api/v1/sow/deploy",
                        json={"project_name": "Empty", "summary": "", "parameters": {}, "agents": []})
    assert r.status_code == 422


async def test_workflow_uses_deployed_team(auth):
    plan = (await auth.post("/api/v1/sow/analyze", files=_sow_file())).json()
    res = (await auth.post("/api/v1/sow/deploy", json={
        "project_name": plan["project_name"], "summary": plan["summary"],
        "parameters": plan["parameters"], "agents": plan["agents"], "create_kickoff_tasks": False,
    })).json()
    pid = res["project_id"]
    team_ids = {a["id"] for a in res["agents"]}
    await osvc.run_project_workflow(pid, plan["project_name"])
    tasks = (await auth.get(f"/api/v1/tasks/?project_id={pid}")).json()["tasks"]
    done = [t for t in tasks if t["status"] == "done"]
    assert len(done) >= 5
    assert {t["assigned_agent_id"] for t in done if t["assigned_agent_id"]} & team_ids
