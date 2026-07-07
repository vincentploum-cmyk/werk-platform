"""Health + service bootstrap."""


async def test_health_ok(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body


async def test_hello_public(client):
    resp = await client.get("/api/hello?name=Vincent")
    assert resp.status_code == 200
    assert "Vincent" in resp.json().get("message", "")
