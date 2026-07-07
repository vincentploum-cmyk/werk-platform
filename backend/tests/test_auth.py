"""Authentication + RBAC."""


async def test_login_success(client):
    r = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200
    assert r.json()["access_token"]
    assert r.json()["token_type"] == "bearer"


async def test_login_bad_password(client):
    r = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "nope"})
    assert r.status_code == 401


async def test_register_then_login(client):
    r = await client.post(
        "/api/v1/auth/register",
        json={"username": "alice", "password": "pw1", "role": "developer"},
    )
    assert r.status_code == 200
    assert r.json()["role"] == "developer"
    r2 = await client.post("/api/v1/auth/login", json={"username": "alice", "password": "pw1"})
    assert r2.status_code == 200


async def test_protected_endpoint_requires_auth(client):
    r = await client.post("/api/v1/projects/", json={"name": "X"})
    assert r.status_code == 401


async def test_viewer_lacks_create_permission(client, viewer_token):
    r = await client.post(
        "/api/v1/projects/",
        json={"name": "Blocked"},
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert r.status_code == 403
