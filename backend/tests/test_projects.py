"""Project CRUD."""


async def test_project_full_lifecycle(auth):
    # create
    r = await auth.post("/api/v1/projects/", json={"name": "Proj A", "description": "d"})
    assert r.status_code == 201
    pid = r.json()["id"]
    assert r.json()["status"] == "draft"

    # get
    g = await auth.get(f"/api/v1/projects/{pid}")
    assert g.status_code == 200
    assert g.json()["name"] == "Proj A"

    # list contains it
    lst = await auth.get("/api/v1/projects/")
    assert lst.status_code == 200
    assert any(p["id"] == pid for p in lst.json()["projects"])

    # update
    u = await auth.put(f"/api/v1/projects/{pid}", json={"status": "active"})
    assert u.status_code == 200
    assert u.json()["status"] == "active"

    # delete
    d = await auth.delete(f"/api/v1/projects/{pid}")
    assert d.status_code == 200
    assert (await auth.get(f"/api/v1/projects/{pid}")).status_code == 404


async def test_get_missing_project_404(auth):
    assert (await auth.get("/api/v1/projects/does-not-exist")).status_code == 404
