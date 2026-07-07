# Werk Platform — Test Suite

End-to-end tests covering every layer of the platform.

## Backend (`backend/tests/`)

In-process integration tests that boot the **whole FastAPI app against SQLite + a fake
Redis** — no Postgres, Redis, MinIO, or model server required. They run in a few seconds
and exercise real request → service → database paths.

| File | Covers |
|---|---|
| `test_health.py` | `/health`, public hello |
| `test_auth.py` | login (ok/fail), register, auth required, RBAC (viewer denied) |
| `test_projects.py` | project create / get / list / update / delete, 404s |
| `test_agents.py` | list & get, chat (persona fallback), instructions get/set/reset, examples, **PPTX → functional requirements**, `.docx` export, unsupported-file rejection |
| `test_tasks.py` | task CRUD, **status state machine** (valid + rejected transitions), **model-driven Run** (assign → run → result → review) |
| `test_orchestrator.py` | **7-stage workflow**, run-through-review **pause**, **approve → deploy resume**, **reject** clears the gate, run endpoint returns `started` |
| `test_sow.py` | **SOW intake**: configurable parameter registry (editable definitions), parameter extraction (releases/countries/cycles/approach/budget/duration/compliance), rules-driven staffing, project-scoped team + kickoff tasks, workflow uses the deployed team |
| `test_artifacts.py` | **Artifacts**: task-run produces a named/typed artifact, get + download endpoints, the workflow produces one artifact per stage |
| `test_workspace.py` | **Execution layer**: code-block extraction, unsafe-path rejection, real test run (pass + fail), Developer writes files, Tester runs them and reports PASS, run-tests endpoint |
| `test_deps_docs.py` | **Dependencies + document store**: install machinery, tests import from `.deps` (PYTHONPATH), shared `docs/` folder — an agent saves a document and the next agent retrieves it in its prompt, install endpoint |

### Run it

```bash
cd backend
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest tests/
```

The suite is deterministic and offline: with no model configured, agents fall back to the
persona/heuristic/simulated paths, so output is stable.

## Frontend (`frontend/tests/`)

Playwright specs that drive the real UI with the backend API **mocked** (see `mock.ts`), so
they run against just the dev server.

| File | Covers |
|---|---|
| `canvas.spec.ts` | canvas renders all 7 agents, unassigned-task tray, agent panel opens, New Task modal |
| `agent-tuning.spec.ts` | edit/save instructions, add a few-shot example, chat reply |
| `sow.spec.ts` | **SOW upload → analyze → review plan → deploy team** |
| `dashboard.spec.ts` | Projects page + Canvas/Projects navigation |
| `kanban.spec.ts` | project board, **Run full workflow** control, back-link |

### Run it

```bash
cd frontend
npm install
npx playwright install chromium   # one-time
npx playwright test
```

## Everything at once

```bash
bash infrastructure/scripts/run_tests.sh
```

## Not yet covered (future work)

- **Live full-stack E2E** (real backend + real model) as a separate, slower CI lane.
- **Load/perf**: see `benchmarks/` (Locust) for the existing performance harness.
