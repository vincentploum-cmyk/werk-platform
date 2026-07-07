# AGENTS.md

Repository instructions for coding agents working in this repo.

Read `CLAUDE.md` first. The core expectations here are:
- surface assumptions instead of guessing
- prefer the simplest change that solves the task
- keep edits surgical
- avoid hidden prompt or workflow behavior
- verify the exact execution path you changed before calling it done

Repo hotspots:
- `orchestrator/` workflow and state transitions
- `backend/app/services/orchestrator_service.py` API bridge and gate handling
- `backend/app/api/agents.py` prompt and agent behavior surface
- `frontend/src/` operator UI and workflow state rendering
