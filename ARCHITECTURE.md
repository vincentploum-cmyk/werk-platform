# Werk Platform — Architecture

## Overview

Werk is a three-tier application — a React SPA, a FastAPI backend, and a workflow orchestrator —
backed by PostgreSQL and Redis, with an LLM provider (local Ollama by default) supplying agent
reasoning. Everything runs via Docker Compose.

```
                    ┌─────────────────────────────────────────────┐
   Browser  ──────► │  Frontend (React/Vite/Zustand)              │
                    │  Canvas · Project board · SOW modal         │
                    └───────────────┬─────────────────────────────┘
                                    │ REST + WebSocket (/api/v1, /ws)
                    ┌───────────────▼─────────────────────────────┐
                    │  Backend (FastAPI)                          │
                    │  api/        projects, agents, tasks,       │
                    │              artifacts, sow, orchestrator,  │
                    │              auth, ws                       │
                    │  services/   llm, sow_service, requirements │
                    │              _gen, artifact_service,        │
                    │              orchestrator_service, tasks    │
                    │  core/       config, auth (JWT/RBAC), sec.  │
                    │  models/     SQLAlchemy ORM                 │
                    └───┬─────────────┬───────────────┬───────────┘
                        │             │               │
              ┌─────────▼──┐   ┌──────▼──────┐  ┌─────▼───────────────┐
              │ PostgreSQL │   │   Redis     │  │ Orchestrator pkg    │
              │ (pgvector) │   │ (events)    │  │ 7-stage workflow    │
              └────────────┘   └─────────────┘  └─────┬───────────────┘
                                                      │ generate(system,user)
                                              ┌───────▼────────┐
                                              │ LLM provider   │
                                              │ Ollama / API   │
                                              └────────────────┘
```

## Components

**Frontend** (`frontend/src`). A Zustand store (`stores/werkStore.ts`) holds all state and wraps
the API with silent admin auto-login. Pages: the **Agent Canvas** (landing), **Projects**, and a
per-project **board**. Key components: `SowUploadModal` (intake + parameter form + config editor),
`AgentPanel` (status, instructions, examples, document analysis, chat, per-task Run), and
`NewTaskModal`. A WebSocket connection refreshes data live on `task.*`, `artifact.*`,
`workflow.*` events.

**Backend** (`backend/app`). FastAPI with JWT auth and RBAC (`core/auth.py`, roles
admin/lead/developer/viewer). Routers under `api/` are thin; logic lives in `services/`. The
`llm.py` service selects a provider in order **Ollama → Anthropic → OpenAI → deterministic
fallback**, so the platform always works offline.

**Orchestrator** (`orchestrator/`). A 7-stage workflow (`core.py`) — Init, UX, Architecture,
Development, Testing, Review, Deploy. It uses LangGraph if installed, otherwise a built-in
sequential runner. Stage prompts come from the project's deployed agents (their tuned
instructions + examples), injected as `system_overrides`. It calls a `generate` function passed
in by the backend, so it stays decoupled from the LLM and the DB.

## Key flows

**SOW intake.** `POST /sow/analyze` extracts text (`doc_extract`), then `sow_service.analyze_sow`
applies the configurable parameter **definitions** (stored in `app_settings`) to extract values
and derive a team via a small **rules engine** (`apply_rules`). `POST /sow/deploy` creates the
project (parameters saved to `config`) and project-scoped `Agent` rows. `POST /sow/team`
re-derives the team when parameters are edited.

**Agent tuning.** Each `Agent.llm_config` holds `instructions` and `examples`. `build_system()`
composes them into the system prompt used everywhere the agent generates.

**Per-task run.** `POST /tasks/{id}/run` builds the prompt from the agent's `build_system()` + the
task, calls the model, stores the result + an `Artifact`, and moves the task to review.

**Pipeline.** `POST /orchestrator/projects/{id}/run` runs in the background through Testing, then
**pauses** at the review gate (`workflow.review_pending`). Each stage is persisted as a done
`Task` + an `Artifact`. `review/approve` resumes into Deploy; `review/reject` stops for rework.

## Data model (`app/models/db_models.py`)

`Project` · `Agent` (nullable `project_id`: NULL = global template, set = deployed team) · `Task`
(state machine: backlog→in_progress→review→done/blocked) · `Artifact` (file_path, file_type,
`content`) · `AgentEvent` · `ContextEntry` (pgvector-ready shared memory) · `AppSetting`
(configurable parameter definitions).

Schema evolves via `ensure_schema()` — idempotent `create_all` + guarded `ALTER`s — so existing
databases upgrade on startup without Alembic.

## Security note

This is a research/dev configuration: an in-memory user store with seeded credentials, frontend
auto-login as admin, permissive CORS, and a default secret key. Harden auth, secrets, and network
policy before any shared or production use.
