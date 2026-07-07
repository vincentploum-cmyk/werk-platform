# CLAUDE.md

Repository-level guardrails for the Consulting Agentic Platform (Werk Platform).

## Scope
This repo contains:
- `frontend/` React + Vite UI
- `backend/` FastAPI API and services
- `orchestrator/` multi-agent workflow engine
- `infrastructure/` compose, nginx, and deployment assets
- `docs/` product and architecture reference material

## Coding guardrails

### 1. Surface assumptions early
- Do not silently guess requirements or architecture intent.
- If there are multiple valid interpretations, name them.
- Prefer an explicit TODO or note over hidden behavior.

### 2. Minimum code only
- Do not add speculative abstractions.
- Do not add configurability that is not needed yet.
- Keep diffs surgical and tightly scoped to the task.

### 3. Keep orchestration policy explicit
- Avoid burying agent behavior in scattered string literals.
- Prefer repo-visible prompt and policy surfaces over hidden defaults.
- Keep workflow transitions, prompt policy, and persistence concerns clearly separated.

### 4. Respect architecture boundaries
- Do not call underscore-private orchestrator methods from service or API layers.
- Review and production approval state must be durable, not process-memory only.
- Prefer one clear source of truth for workflow state.

### 5. Verify before calling work done
For workflow changes, verify the exact path you touched:
- approval and rejection gates
- resume behavior
- persistence/restart behavior when relevant
- backend or frontend tests closest to the modified surface

## Change style
- Match local style.
- Do not perform drive-by refactors.
- If unrelated issues are spotted, mention them separately instead of folding them into the change.
