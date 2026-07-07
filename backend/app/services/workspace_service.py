"""Per-project code workspace: write the Developer agent's files and run the Tester's tests.

Code execution runs model-generated code in a subprocess and is therefore gated behind
settings.enable_code_execution. Tests are plain Python files using `assert` (run via the
Python interpreter), so no pytest dependency is required and a non-zero exit means failure.
"""

from __future__ import annotations

import os
import re
import signal
import socket
import subprocess
import sys
import time

from app.core.config import settings

DEPS_DIR = ".deps"   # pip --target install dir (added to PYTHONPATH at run time)
DOCS_DIR = "docs"    # shared document folder agents read from / write to


def _root() -> str:
    os.makedirs(settings.workspace_root, exist_ok=True)
    return settings.workspace_root


def workspace_dir(project_id) -> str:
    d = os.path.join(_root(), str(project_id))
    os.makedirs(d, exist_ok=True)
    return d


def _safe_rel(path: str) -> str:
    p = os.path.normpath(path).lstrip("/")
    parts = p.split(os.sep)
    if os.path.isabs(path) or ".." in parts:
        raise ValueError(f"unsafe path: {path}")
    return p


def write_files(project_id, files: dict[str, str]) -> list[str]:
    base = workspace_dir(project_id)
    written = []
    for path, content in files.items():
        rel = _safe_rel(path)
        full = os.path.join(base, rel)
        os.makedirs(os.path.dirname(full) or base, exist_ok=True)
        with open(full, "w") as f:
            f.write(content or "")
        written.append(rel)
    return written


def list_files(project_id) -> list[dict]:
    base = workspace_dir(project_id)
    out = []
    for root, _, files in os.walk(base):
        for f in files:
            full = os.path.join(root, f)
            out.append({"path": os.path.relpath(full, base), "size": os.path.getsize(full)})
    return sorted(out, key=lambda x: x["path"])


def read_file(project_id, path: str) -> str | None:
    full = os.path.join(workspace_dir(project_id), _safe_rel(path))
    if not os.path.isfile(full):
        return None
    with open(full) as f:
        return f.read()


# ── extract code files from a model reply ───────────────────────────────────
_FENCE = re.compile(r"```([^\n]*)\n(.*?)```", re.DOTALL)
_NAME_IN_INFO = re.compile(r"(?:name=|title=|file=)?([\w./-]+\.\w+)")
_FILE_HINT = re.compile(r"^\s*(?:#|//)\s*file:\s*([\w./-]+)", re.IGNORECASE)


def extract_code_files(text: str) -> dict[str, str]:
    """Parse fenced code blocks into {path: content}. Recognizes a path on the fence info
    line (```python app/foo.py) or a leading `# file: path` comment."""
    files: dict[str, str] = {}
    idx = 0
    for m in _FENCE.finditer(text or ""):
        info, body = m.group(1).strip(), m.group(2)
        name = None
        hit = _NAME_IN_INFO.search(info)
        if hit:
            name = hit.group(1)
        if not name:
            fh = _FILE_HINT.match(body)
            if fh:
                name = fh.group(1)
        if not name:
            idx += 1
            name = f"snippet_{idx}.py"
        try:
            _safe_rel(name)
        except ValueError:
            continue
        files[name] = body
    return files


# ── run tests ───────────────────────────────────────────────────────────────
def run_tests(project_id, timeout: int | None = None) -> dict:
    """Run test_*.py / *_test.py files (or main.py) via the Python interpreter."""
    if not settings.enable_code_execution:
        return {"enabled": False, "passed": None,
                "output": "Code execution is disabled. Set ENABLE_CODE_EXECUTION=true to run tests."}

    base = workspace_dir(project_id)
    timeout = timeout or settings.code_execution_timeout
    files = [f["path"] for f in list_files(project_id) if f["path"].endswith(".py")]
    tests = [p for p in files if os.path.basename(p).startswith("test_") or p.endswith("_test.py")]
    targets = tests or ([p for p in files if os.path.basename(p) == "main.py"] or files[:1])
    if not targets:
        return {"enabled": True, "passed": None, "output": "No runnable Python files in the workspace."}

    # Make workspace code + installed dependencies importable.
    env = os.environ.copy()
    deps = os.path.join(base, DEPS_DIR)
    path_parts = [base] + ([deps] if os.path.isdir(deps) else [])
    if env.get("PYTHONPATH"):
        path_parts.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(path_parts)

    results = []
    all_passed = True
    for t in targets:
        try:
            proc = subprocess.run(
                [sys.executable, t], cwd=base, env=env, capture_output=True, text=True, timeout=timeout
            )
            ok = proc.returncode == 0
            all_passed = all_passed and ok
            out = (proc.stdout + proc.stderr).strip()
            results.append(f"[{'PASS' if ok else 'FAIL'}] {t}\n{out[-1500:]}")
        except subprocess.TimeoutExpired:
            all_passed = False
            results.append(f"[FAIL] {t}\nTimed out after {timeout}s.")
        except Exception as exc:
            all_passed = False
            results.append(f"[FAIL] {t}\n{exc}")

    return {"enabled": True, "passed": all_passed, "ran": targets, "output": "\n\n".join(results)}


# ── dependency installation (pip --target .deps) ────────────────────────────
def install_dependencies(project_id, timeout: int = 180) -> dict:
    """Install requirements.txt into the project's .deps dir so agents can use real libraries."""
    if not settings.enable_code_execution:
        return {"enabled": False, "installed": False,
                "output": "Code execution is disabled. Set ENABLE_CODE_EXECUTION=true to install deps."}
    base = workspace_dir(project_id)
    req = os.path.join(base, "requirements.txt")
    if not os.path.isfile(req):
        return {"enabled": True, "installed": False, "output": "No requirements.txt in the workspace."}
    deps = os.path.join(base, DEPS_DIR)
    os.makedirs(deps, exist_ok=True)
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", req, "--target", deps,
             "--quiet", "--disable-pip-version-check"],
            cwd=base, capture_output=True, text=True, timeout=timeout,
        )
        ok = proc.returncode == 0
        out = (proc.stdout + proc.stderr).strip()
        return {"enabled": True, "installed": ok,
                "output": out[-3000:] or ("Dependencies installed." if ok else "pip failed.")}
    except subprocess.TimeoutExpired:
        return {"enabled": True, "installed": False, "output": f"pip timed out after {timeout}s."}
    except Exception as exc:
        return {"enabled": True, "installed": False, "output": str(exc)}


def has_requirements(project_id) -> bool:
    return os.path.isfile(os.path.join(workspace_dir(project_id), "requirements.txt"))


# ── shared document folder (agents read each other's docs) ──────────────────
def save_document(project_id, name: str, content: str) -> str:
    """Save an agent's document into the shared docs/ folder. Returns the relative path."""
    safe = os.path.basename(name)  # docs are flat
    write_files(project_id, {f"{DOCS_DIR}/{safe}": content})
    return f"{DOCS_DIR}/{safe}"


def list_documents(project_id) -> list[dict]:
    base = os.path.join(workspace_dir(project_id), DOCS_DIR)
    out = []
    if os.path.isdir(base):
        for f in sorted(os.listdir(base)):
            full = os.path.join(base, f)
            if os.path.isfile(full):
                with open(full) as fh:
                    out.append({"name": f, "content": fh.read()})
    return out


def documents_digest(project_id, exclude: str | None = None, max_chars: int = 4000,
                     per_doc: int = 1200) -> str:
    """A digest of the team's documents so far, for an agent to build on."""
    parts = []
    for doc in list_documents(project_id):
        if exclude and doc["name"] == exclude:
            continue
        parts.append(f"### {doc['name']}\n{doc['content'][:per_doc]}")
    return "\n\n".join(parts)[:max_chars]


# ── stand the app up in an environment and health-check it ──────────────────
_ENTRYPOINTS = ("app.py", "main.py", "server.py", "run.py", "wsgi.py", "asgi.py")


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def find_entrypoint(project_id) -> str | None:
    """Pick the file that starts the app: a known entrypoint name, else one with __main__."""
    pys = [f["path"] for f in list_files(project_id) if f["path"].endswith(".py")
           and not os.path.basename(f["path"]).startswith("test_")]
    for name in _ENTRYPOINTS:
        for p in pys:
            if os.path.basename(p) == name:
                return p
    for p in pys:
        if "__main__" in (read_file(project_id, p) or ""):
            return p
    return None


def health_check(project_id, timeout: int | None = None) -> dict:
    """Start the workspace app on a free PORT and probe GET /health (then /).

    Returns whether the environment came up healthy. Gated behind code execution.
    """
    if not settings.enable_code_execution:
        return {"enabled": False, "healthy": None,
                "output": "Code execution is disabled. Set ENABLE_CODE_EXECUTION=true."}
    base = workspace_dir(project_id)
    timeout = timeout or settings.code_execution_timeout
    entry = find_entrypoint(project_id)
    if not entry:
        return {"enabled": True, "healthy": None,
                "output": "No runnable app entrypoint (app.py / main.py / server.py …) in the workspace."}

    port = _free_port()
    env = os.environ.copy()
    deps = os.path.join(base, DEPS_DIR)
    env["PYTHONPATH"] = os.pathsep.join([base] + ([deps] if os.path.isdir(deps) else []))
    env["PORT"] = str(port)

    try:
        proc = subprocess.Popen(
            [sys.executable, entry], cwd=base, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True,
        )
    except Exception as exc:
        return {"enabled": True, "healthy": False, "port": port, "output": f"Failed to start: {exc}"}

    import httpx

    healthy, detail = False, ""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            detail = f"Process exited (code {proc.returncode}) before becoming healthy."
            break
        for path in ("/health", "/"):
            try:
                r = httpx.get(f"http://127.0.0.1:{port}{path}", timeout=2.0)
                if r.status_code < 500:
                    healthy, detail = True, f"GET {path} → {r.status_code} on port {port}"
                    break
            except Exception:
                continue
        if healthy:
            break
        time.sleep(0.5)

    # Tear the environment down.
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except Exception:
        try:
            proc.terminate()
        except Exception:
            pass
    try:
        logs = proc.communicate(timeout=3)[0] or ""
    except Exception:
        logs = ""
    if not detail:
        detail = "Did not become healthy within the timeout."
    return {"enabled": True, "healthy": healthy, "port": port, "entrypoint": entry,
            "output": (detail + ("\n--- logs ---\n" + logs[-1500:] if logs.strip() else "")).strip()}
