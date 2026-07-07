# Werk Platform — File Organization

The cto.new export was a flat dump of 80 files. They have been reorganized in place
into the nested structure defined by the README and the actual Python/TypeScript import paths.

## Final structure

```
Consulting Agentic Platform/
├── README.md
├── .env, .env.example, .gitignore        # root config (docker-compose reads ../.env)
├── .github/workflows/                    # CI/CD — must live here for GitHub Actions to run
│   ├── ci-backend.yml
│   ├── ci-frontend.yml
│   ├── cd-deploy.yml
│   └── security-scan.yml
│
├── frontend/                             # React 18 + Vite + TypeScript SPA
│   ├── index.html
│   ├── package.json, package-lock.json
│   ├── vite.config.ts, tsconfig.json
│   ├── tailwind.config.js, postcss.config.js
│   ├── playwright.config.ts
│   ├── Dockerfile                        # node build -> nginx serve
│   ├── nginx.conf                        # frontend container server block
│   ├── src/
│   │   ├── main.tsx, App.tsx, index.css
│   │   ├── pages/        Dashboard.tsx, ProjectView.tsx
│   │   ├── components/   Header.tsx
│   │   └── stores/       werkStore.ts    # zustand store
│   ├── tests/           dashboard.spec.ts, kanban.spec.ts   # Playwright e2e
│   └── dist/                             # prebuilt output from the export
│       ├── index.html
│       └── assets/index--xYjWosW.js, index-DkLqkK-B.css
│
├── backend/                             # FastAPI (Python) — COMPLETE
│   ├── Dockerfile                        # python:3.11-slim -> uvicorn app.main:app
│   ├── requirements.txt
│   └── app/
│       ├── __init__.py                   # FastAPI app factory + router registration
│       ├── main.py                       # uvicorn entrypoint (app.main:app)
│       ├── database.py                   # async SQLAlchemy engine/session
│       ├── schemas.py                    # Pydantic schemas + task state machine
│       ├── api/      projects.py, agents.py, tasks.py, artifacts.py,
│       │             ws.py, auth.py, orchestrator.py, hello.py
│       ├── core/     config.py (settings), auth.py, security.py
│       ├── models/   db_models.py (Base, Project, Task, Agent, Artifact, ...)
│       └── services/ project_service.py, task_service.py, orchestrator_service.py
│
├── orchestrator/                        # LangGraph multi-agent engine (COMPLETE)
│   ├── core.py                           # 7-stage WerkOrchestrator graph
│   ├── cicd.py                           # deploy-node CI/CD integration
│   ├── bus/event_bus.py                  # Redis pub/sub
│   ├── registry/agent_registry.py
│   ├── memory/context_store.py
│   └── dispatcher/dispatcher.py
│
├── infrastructure/
│   ├── docker-compose.yml                # postgres, redis, minio, backend, frontend, nginx
│   ├── prometheus.yml
│   ├── nginx/nginx.conf                  # reverse proxy
│   ├── nginx/ssl/werk.crt, werk.key
│   ├── db/init/01-schema.sql, init-db.sql  # postgres init (mounted by compose)
│   └── scripts/  deploy.sh, setup.sh, gen_certs.py, generate_certs.sh,
│                 run_tests.sh, run_security_checks.sh
│
├── benchmarks/                          # perf/load testing
│   ├── benchmark_orchestrator.py, benchmark_ws.py
│   ├── perf_locustfile.py, start_perf_backend.py
│   └── performance_report_stats_history.csv
│
└── docs/                               # all markdown + schemas
    ├── PRD.md, PRD_Final.md, UserStories.md, BusinessLogic.md
    ├── design.md, orchestration_frameworks.md, websocket_events.md
    ├── security.md, security_policy.md, security_report.md
    ├── validation_plan.md, PERFORMANCE_REPORT.md, QA_HELLO_WORLD.md
    ├── onboarding_guide.md, agent_marketplace.md, agent_persona_guide.md, listing_strategy.md
    └── artifact_metadata.json, shared_context_schema.json
```

## Notes on placement decisions
- **GitHub workflows** went to `.github/workflows/` (not `infrastructure/`). GitHub Actions only
  runs workflows from that exact path. The README's "infrastructure/CI-CD" is conceptual.
- **Two nginx configs** were disambiguated: the small server block (`nginx-2.conf`) is the
  frontend container config (`frontend/nginx.conf`); the large reverse proxy is
  `infrastructure/nginx/nginx.conf`.
- **`dist/`** is the prebuilt frontend bundle from the export (`index-2.html` + hashed assets).
- **`.env`** came from the file named `env`; `ALLOWED_HOSTS` differs slightly from `.env.example`.
- Empty `__init__.py` files were added to make `orchestrator/*` and `backend/app/services/`
  importable Python packages.

## Status: COMPLETE

All exported files have been organized, and the final batch (`config.py`, `auth.py`,
`security.py`, `db_models.py`, `requirements.txt`) is in place. Every Python import across
`backend/` and `orchestrator/` now resolves, and all `.py` files pass `py_compile`.

The one file cto.new never produced — `backend/Dockerfile` — was written here to match the
stack (python:3.11-slim, installs `requirements.txt`, non-root user `1000:1000` per
docker-compose, runs `uvicorn app.main:app` on :8000). Nothing else is missing.

### To run
```bash
cd infrastructure && docker-compose up -d        # full stack
# or locally:
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload
cd frontend && npm install && npm run dev
```
