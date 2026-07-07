# Werk Platform

[![CI — Backend](https://github.com/vincentploum-cmyk/Consulting-Agentic-Platform/actions/workflows/ci-backend.yml/badge.svg)](https://github.com/vincentploum-cmyk/Consulting-Agentic-Platform/actions/workflows/ci-backend.yml)
[![CI — Frontend](https://github.com/vincentploum-cmyk/Consulting-Agentic-Platform/actions/workflows/ci-frontend.yml/badge.svg)](https://github.com/vincentploum-cmyk/Consulting-Agentic-Platform/actions/workflows/ci-frontend.yml)
[![Security Scan](https://github.com/vincentploum-cmyk/Consulting-Agentic-Platform/actions/workflows/security-scan.yml/badge.svg)](https://github.com/vincentploum-cmyk/Consulting-Agentic-Platform/actions/workflows/security-scan.yml)

An AI-orchestrated consulting delivery platform. Upload a signed Statement of Work and the
platform staffs a tailored team of specialized agents, lets a consultant configure each one,
runs the delivery lifecycle, and produces downloadable deliverables — driven by a **local model**
(Ollama) at no per-call cost, or a hosted API if you prefer.

> Research preview. See `docs/` for design notes and `TESTING.md` for the test suite.

## What it does

**1. SOW intake → tailored team.** Upload a signed SOW (`.pptx/.pdf/.docx/.txt`). The platform
extracts the critical project parameters and staffs the right agents from them.

- **Configurable parameters.** The parameter set is data-driven and editable (a registry stored
  in the DB). Seeded with **approach** (agile/waterfall/devops/hybrid), **releases**,
  **test cycles**, **countries**, **budget**, **duration**, and **compliance**. Each parameter
  carries staffing rules, so adding a new parameter changes the team with no code change.
- **Rules-driven staffing.** Approach sets the base roster; multiple countries add a UX agent;
  multiple releases or long duration add DevOps; budget/compliance thresholds add the Business
  Logic agent; test cycles scale the number of Tester agents.

**2. Configure each agent.** Every agent has editable **instructions** (its system prompt) and
**few-shot examples**, tuned live in the UI. Changes apply immediately to chat, document
analysis, per-task runs, and the pipeline.

**3. Run the work.**

- **Per-task execution** — assign a task to an agent and hit **Run**; the agent does the work
  with the model and produces a result.
- **Autonomous pipeline** — the 7-stage lifecycle (Requirements → UX → Architecture →
  Development → Testing → **Review gate** → Deploy) with a real human approve/reject gate before
  deploy.

**4. Deliverables.** Every task-run and pipeline stage produces a named, typed, **downloadable
artifact** (`functional_requirements.md`, `architecture.md`, `test_plan.md`, …), listed on the
project with one-click download.

**5. Visual canvas.** The agents live on a canvas with live status, drag-to-assign, and a team
selector to switch between the global roster and any engagement's deployed team.

## Quick start

```bash
cp .env.example .env                              # defaults work as-is (local model, debug mode)
cd infrastructure
./scripts/generate_certs.sh                       # self-signed TLS certs for nginx (never committed)
docker-compose up -d --build
docker-compose exec ollama ollama pull llama3.2   # one-time: the local model
```

Then open **http://localhost:5173**. The default login is wired automatically (`admin` — demo
seed data; the backend refuses to start with a placeholder `SECRET_KEY` outside debug mode).

Want to try it immediately? Click **Deploy from SOW** on the canvas and upload
`docs/SAMPLE_SOW.md`. See `WALKTHROUGH.md` for the full happy path.

### Local model (no API key, no cost)

Ollama runs as a container in the stack. `USE_OLLAMA=true` is set in `.env`; pull a model once
(`llama3.2` is a good CPU default, `llama3.1` is higher quality but slower). With no model and no
API key, agents fall back to clearly-labeled deterministic output so everything still works.

To use a hosted model instead, set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in `.env`.

## Repository structure

```
frontend/         React 18 + TypeScript + Vite SPA (canvas, project board, modals)
backend/          FastAPI app (app/api routers, services, models)
orchestrator/     LangGraph-or-fallback 7-stage workflow engine
infrastructure/   docker-compose (postgres, redis, minio, ollama, backend, frontend, nginx)
docs/             PRD, design, architecture, sample SOW
ARCHITECTURE.md   System architecture overview
TESTING.md        Test suite (59 backend tests + Playwright specs)
ORGANIZATION.md   How the flat cto.new export was organized
```

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + TypeScript + Vite + Zustand + Tailwind |
| Backend | FastAPI (Python 3.11) |
| Database | PostgreSQL 16 (+ pgvector) |
| Cache / events | Redis |
| Orchestration | LangGraph (with a built-in sequential fallback) |
| Model | Ollama (local) · OpenAI · Anthropic — auto-selected |
| Containerization | Docker + Docker Compose |

## Testing

```bash
bash infrastructure/scripts/run_tests.sh     # backend (offline) + Playwright
cd backend && python -m pytest tests/        # backend only — 59 tests, ~12s, no external services
```

See `TESTING.md`.

## Execution layer

The Developer agent writes its generated code as **real files** into a per-project workspace
(`/tmp/werk_workspaces/<project>`), and the Tester agent **actually runs** them in a sandboxed
subprocess and reports real pass/fail. The project view has a **Workspace** panel listing the
files with a **Run tests** button showing the live output.

> **Security:** this executes model-generated code. It is gated behind `ENABLE_CODE_EXECUTION`
> (on in `.env`, off in `.env.example`) with a per-run timeout. Enable only for local/trusted
> use. Tests are plain Python `assert` files run via the interpreter — no pytest dependency.

**Dependencies.** If an agent writes a `requirements.txt`, the workspace installs it into a
`.deps/` directory (`pip --target`) which is added to `PYTHONPATH` when tests run — so agents can
use real third-party libraries. There's an **Install deps** button on the Workspace panel.

**Shared document folder.** Every document an agent produces is saved into the project's `docs/`
folder. Before each run, an agent **retrieves the team's existing documents** and they're included
in its prompt — so the Architect builds on the Requirements doc, the Developer on the
architecture, and so on. Pipeline stages write to `docs/` too, so per-task agents can read them.

## Status & roadmap

Built and working: SOW intake, configurable parameters, rules-driven staffing, per-agent tuning,
per-task execution, the autonomous pipeline with a human review gate, downloadable artifacts, and
the code-execution workspace (Developer writes files → Tester runs them).

Further work toward full autonomous delivery: installing dependencies into the workspace, running
multi-file projects and richer test frameworks, persisting workspaces to a volume, stronger
sandboxing (network isolation, resource limits), and a real deploy step.
