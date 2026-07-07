"""DevOps/Release agents stand the app up in an environment and health-check it."""

import shutil

import pytest

from app.services import workspace_service

# A real stdlib HTTP server that reads PORT and answers GET /health with 200.
SERVER = (
    "import os, http.server\n"
    "class H(http.server.BaseHTTPRequestHandler):\n"
    "    def do_GET(self):\n"
    "        if self.path == '/health':\n"
    "            self.send_response(200); self.end_headers(); self.wfile.write(b'ok')\n"
    "        else:\n"
    "            self.send_response(404); self.end_headers()\n"
    "    def log_message(self, *a):\n"
    "        pass\n"
    "port = int(os.environ.get('PORT', '8000'))\n"
    "http.server.HTTPServer(('127.0.0.1', port), H).serve_forever()\n"
)


@pytest.fixture(autouse=True)
def _clean_ws():
    shutil.rmtree("/tmp/werk_ws_test", ignore_errors=True)
    yield
    shutil.rmtree("/tmp/werk_ws_test", ignore_errors=True)


def test_health_check_app_comes_up():
    pid = "p-up"
    workspace_service.write_files(pid, {"server.py": SERVER})
    res = workspace_service.health_check(pid, timeout=15)
    assert res["enabled"] is True
    assert res["healthy"] is True
    assert "/health" in res["output"]


def test_health_check_app_that_crashes():
    pid = "p-down"
    workspace_service.write_files(pid, {"app.py": "import sys\nsys.exit(1)\n"})
    res = workspace_service.health_check(pid, timeout=8)
    assert res["healthy"] in (False, None)


def test_health_check_no_entrypoint():
    pid = "p-none"
    workspace_service.write_files(pid, {"notes.txt": "nothing runnable"})
    res = workspace_service.health_check(pid)
    assert res["healthy"] is None


async def test_health_check_endpoint(auth, project_id):
    workspace_service.write_files(project_id, {"server.py": SERVER})
    r = await auth.post(f"/api/v1/workspace/{project_id}/health-check")
    assert r.status_code == 200
    assert r.json()["healthy"] is True
