"""
Orchestrator integration service — bridges the FastAPI backend with WerkOrchestrator.

Provides:
 - Initialization of the orchestrator on app startup
 - Project workflow execution via the orchestrator
 - Auto-creation of orchestration tasks when a project is created
 - Broadcasting orchestrator events to WebSocket clients
"""

import asyncio
import logging
from typing import Optional

from app.api.ws import broadcast_event
from app.core.config import settings
from app.database import async_session_factory
from app.models.db_models import WorkflowGateState

logger = logging.getLogger(__name__)

# Lazy import of orchestrator (it depends on langgraph which may not be installed)
_orchestrator = None


async def get_orchestrator():
    """Get or create the WerkOrchestrator singleton."""
    global _orchestrator
    if _orchestrator is not None:
        return _orchestrator

    try:
        from orchestrator.core import create_orchestrator
        from app.services import llm

        async def _generate(system: str, user: str):
            text, _provider = await llm.chat_complete(system, user, max_tokens=1000)
            return text

        _orchestrator = create_orchestrator(redis_url=settings.redis_url, generate=_generate)
        logger.info("WerkOrchestrator initialized successfully (model-driven)")
    except ImportError as e:
        logger.warning(f"Orchestrator not available (import error: {e})")
        _orchestrator = None
    except Exception as e:
        logger.error(f"Failed to initialize orchestrator: {e}")
        _orchestrator = None

    return _orchestrator


async def run_project_workflow(project_id: str, project_name: str) -> dict:
    """Execute the full project workflow via the orchestrator.

    Called when a project is created and activated.
    Returns the final OrchestratorState as a dict.
    """
    orch = await get_orchestrator()
    if orch is None:
        logger.info(f"[{project_id}] Orchestrator not available; skipping workflow")
        return {
            "project_id": project_id,
            "status": "skipped",
            "message": "Orchestrator not available (install langgraph)",
        }

    try:
        logger.info(f"[{project_id}] Starting workflow for '{project_name}'")
        await broadcast_event("workflow.started", {
            "project_id": project_id,
            "project_name": project_name,
        })

        # Per-agent tuned instructions + few-shot examples drive each stage
        # (prefer this project's deployed team, fall back to global templates).
        overrides = await _build_system_overrides(project_id)

        # Run through Review only (auto_approve=False) — pause for human sign-off before Deploy.
        result = await orch.run_project(
            project_id, project_name, auto_approve=False, system_overrides=overrides
        )

        artifacts = result.get("artifacts", []) if isinstance(result, dict) else []
        created = await _persist_workflow_artifacts(project_id, artifacts)
        for c in created:
            await broadcast_event("task.updated", {
                "task_id": c["task_id"], "project_id": project_id,
                "title": c["title"], "status": "done", "assigned_agent_id": c["agent_id"],
            })
            await broadcast_event("artifact.created", {
                "task_id": c["task_id"], "project_id": project_id, "stage": c["stage"],
            })

        # Hold the state and wait for a human to approve or reject the review gate.
        await _save_gate_state(project_id, "review", result)
        await broadcast_event("workflow.review_pending", {
            "project_id": project_id, "project_name": project_name, "stages": len(created),
        })
        return _serialize_state(result)
    except Exception as e:
        logger.error(f"[{project_id}] Workflow failed: {e}")
        await broadcast_event("workflow.completed", {"project_id": project_id, "error": str(e)})
        return {
            "project_id": project_id,
            "status": "error",
            "error": str(e),
        }


# In-memory workflow states awaiting human review (keyed by project_id).
_pending_states: dict = {}


async def _agents_for_project(db, project_id: str) -> list:
    """The project's deployed agents if any, otherwise the global template roster."""
    from sqlalchemy import select
    from app.models.db_models import Agent

    scoped = (
        await db.execute(select(Agent).where(Agent.project_id == project_id))
    ).scalars().all()
    if scoped:
        return list(scoped)
    return list(
        (await db.execute(select(Agent).where(Agent.project_id.is_(None)))).scalars().all()
    )


async def _build_system_overrides(project_id: str) -> dict:
    """Build {role: system_prompt} from each agent's tuned instructions + examples."""
    from app.database import async_session_factory
    from app.api.agents import build_system

    overrides: dict = {}
    async with async_session_factory() as db:
        for a in await _agents_for_project(db, project_id):
            overrides[a.role] = build_system(a)
    return overrides


# Maps each orchestrator stage to the agent role that owns it.
_STAGE_ROLE = {
    "init": "requirements",
    "ux_design": "ux",
    "architecture": "architect",
    "development": "developer",
    "testing": "tester",
    "review": "requirements",
    "deploy": "devops",       # test/staging
    "deploy_prod": "release",  # production
}

# Workflow states awaiting the production sign-off (after test deploy).
_pending_prod: dict = {}


async def _save_gate_state(project_id: str, gate_type: str, state: dict) -> dict:
    """Persist the actionable workflow gate state and mirror it in memory."""
    payload = _serialize_state(state)
    async with async_session_factory() as db:
        row = await db.get(WorkflowGateState, project_id)
        if row is None:
            row = WorkflowGateState(project_id=project_id, gate_type=gate_type, state_json=payload)
            db.add(row)
        else:
            row.gate_type = gate_type
            row.state_json = payload
        await db.commit()

    if gate_type == "review":
        _pending_states[project_id] = payload
        _pending_prod.pop(project_id, None)
    else:
        _pending_prod[project_id] = payload
        _pending_states.pop(project_id, None)
    return payload


async def _load_gate_state(project_id: str, gate_type: str) -> Optional[dict]:
    """Load gate state from memory first, then durable storage."""
    cache = _pending_states if gate_type == "review" else _pending_prod
    cached = cache.get(project_id)
    if cached is not None:
        return cached

    async with async_session_factory() as db:
        row = await db.get(WorkflowGateState, project_id)

    if row is None or row.gate_type != gate_type:
        return None

    payload = dict(row.state_json or {})
    cache[project_id] = payload
    if gate_type == "review":
        _pending_prod.pop(project_id, None)
    else:
        _pending_states.pop(project_id, None)
    return payload


async def _clear_gate_state(project_id: str, gate_type: Optional[str] = None) -> bool:
    """Delete the durable gate state and clear any in-memory mirrors."""
    existed = False
    async with async_session_factory() as db:
        row = await db.get(WorkflowGateState, project_id)
        if row is not None and (gate_type is None or row.gate_type == gate_type):
            await db.delete(row)
            await db.commit()
            existed = True

    _pending_states.pop(project_id, None)
    _pending_prod.pop(project_id, None)
    return existed


async def _get_gate_info(project_id: str) -> Optional[dict]:
    async with async_session_factory() as db:
        row = await db.get(WorkflowGateState, project_id)
    if row is None:
        return None
    return {
        "gate_type": row.gate_type,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


async def _broadcast_created(project_id: str, created: list) -> None:
    for c in created:
        await broadcast_event("task.updated", {
            "task_id": c["task_id"], "project_id": project_id,
            "title": c["title"], "status": "done", "assigned_agent_id": c["agent_id"],
        })
        await broadcast_event("artifact.created", {
            "task_id": c["task_id"], "project_id": project_id, "stage": c["stage"],
        })


async def _persist_workflow_artifacts(project_id: str, artifacts: list) -> list:
    """Write each stage artifact as a completed Task assigned to its agent."""
    from app.database import async_session_factory
    from app.models.db_models import Task
    from app.services import artifact_service, workspace_service

    created = []
    async with async_session_factory() as db:
        agents = await _agents_for_project(db, project_id)
        by_role = {a.role: str(a.id) for a in agents}
        by_role_name = {a.role: a.name for a in agents}
        for a in artifacts:
            stage = a.get("stage")
            role = _STAGE_ROLE.get(stage)
            agent_id = by_role.get(role)
            content = a.get("content") or a.get("summary") or ""
            task = Task(
                project_id=project_id,
                title=a.get("title") or stage or "Workflow stage",
                description=f"Generated by the {role} agent (stage: {stage})",
                status="done",
                assigned_agent_id=agent_id,
                result=content,
                artifacts=[a],
            )
            db.add(task)
            await db.flush()
            # Persist the stage output as a downloadable artifact file.
            await artifact_service.create_output_artifact(
                db, project_id=project_id, task_id=task.id, agent_id=agent_id,
                role=role or "requirements", content=content, stage=stage,
                created_by=by_role_name.get(role),
            )
            # And into the shared document folder, retrievable by per-task agents.
            workspace_service.save_document(project_id, f"{role or stage}.md", content)
            created.append(
                {"task_id": str(task.id), "title": task.title, "agent_id": agent_id, "stage": stage}
            )
        await db.commit()
    return created


async def approve_review(project_id: str, feedback: str = "") -> bool:
    """Approve the review gate and resume the workflow into the Deploy stage."""
    orch = await get_orchestrator()
    state = await _load_gate_state(project_id, "review")
    if orch is None or state is None:
        return False
    await broadcast_event("review.approved", {"project_id": project_id, "feedback": feedback})
    asyncio.create_task(_resume_deploy(orch, project_id, state, feedback))
    return True


async def _resume_deploy(orch, project_id: str, state: dict, feedback: str) -> None:
    """Run the TEST deploy after review sign-off, then PAUSE for the production gate."""
    try:
        update = await orch.resume_after_review(state, feedback=feedback)
        state.update(update)

        deploy_arts = [a for a in state.get("artifacts", []) if a.get("stage") == "deploy"]
        created = await _persist_workflow_artifacts(project_id, deploy_arts)
        await _broadcast_created(project_id, created)

        # The review gate is done; hold for a dedicated production sign-off before prod.
        await _save_gate_state(project_id, "production", state)
        await broadcast_event("workflow.prod_pending", {"project_id": project_id})
    except Exception as e:
        await _clear_gate_state(project_id, gate_type="review")
        logger.error(f"[{project_id}] Test deploy after approval failed: {e}")
        await broadcast_event("workflow.completed", {"project_id": project_id, "error": str(e)})


async def approve_prod(project_id: str, feedback: str = "") -> bool:
    """Approve the production gate and deploy to production."""
    orch = await get_orchestrator()
    state = await _load_gate_state(project_id, "production")
    if orch is None or state is None:
        return False
    await broadcast_event("review.approved", {"project_id": project_id, "stage": "production"})
    asyncio.create_task(_resume_deploy_prod(orch, project_id, state, feedback))
    return True


async def _resume_deploy_prod(orch, project_id: str, state: dict, feedback: str) -> None:
    """Run the PRODUCTION deploy after the prod sign-off, persist its artifact, and finish."""
    try:
        update = await orch.resume_after_prod_approval(state, feedback=feedback)
        state.update(update)

        prod_arts = [a for a in state.get("artifacts", []) if a.get("stage") == "deploy_prod"]
        created = await _persist_workflow_artifacts(project_id, prod_arts)
        await _broadcast_created(project_id, created)
        await _clear_gate_state(project_id, gate_type="production")
    except Exception as e:
        logger.error(f"[{project_id}] Production deploy failed: {e}")
    finally:
        await broadcast_event("workflow.completed", {
            "project_id": project_id, "stages": len(state.get("artifacts", [])),
        })


async def reject_prod(project_id: str, feedback: str) -> bool:
    """Reject the production gate — stop before deploying to prod. Test deploy remains."""
    existed = await _clear_gate_state(project_id, gate_type="production")
    await broadcast_event("review.rejected", {"project_id": project_id, "stage": "production"})
    await broadcast_event("workflow.completed", {"project_id": project_id, "rejected_prod": True})
    return existed


async def reject_review(project_id: str, feedback: str) -> bool:
    """Reject the review gate — stop the workflow before deploy. Stage tasks remain for rework."""
    existed = await _clear_gate_state(project_id, gate_type="review")
    await broadcast_event("review.rejected", {"project_id": project_id, "feedback": feedback})
    await broadcast_event("workflow.completed", {"project_id": project_id, "rejected": True})
    return existed


async def get_workflow_status(project_id: str) -> dict:
    """Get the current workflow status from the orchestrator context store."""
    orch = await get_orchestrator()
    if orch is None:
        return {"project_id": project_id, "status": "unknown", "message": "Orchestrator not available"}

    try:
        context = orch.context.get_all(project_id)
        gate = await _get_gate_info(project_id)
        return {
            "project_id": project_id,
            "context": context,
            "agents": [vars(a) for a in orch.registry.list_all()],
            "pending_gate": gate,
        }
    except Exception as e:
        return {"project_id": project_id, "status": "error", "error": str(e)}


async def subscribe_to_orchestrator_events():
    """Subscribe to Redis EventBus and forward events to WebSocket clients.

    Runs as a background task during the app lifecycle.
    """
    orch = await get_orchestrator()
    if orch is None or orch.event_bus is None:
        logger.info("Event bus not available; skipping subscription")
        return

    try:
        await orch.event_bus.connect()
        await orch.event_bus.subscribe("werk:*")

        logger.info("Subscribed to orchestrator event bus")
        while True:
            msg = await orch.event_bus.get_message(timeout=1.0)
            if msg:
                event_type = msg.get("type", "orchestrator.event")
                await broadcast_event(event_type, msg.get("payload", msg))
            await asyncio.sleep(0.01)
    except asyncio.CancelledError:
        logger.info("Event bus subscription cancelled")
    except Exception as e:
        logger.error(f"Event bus subscription error: {e}")
    finally:
        if orch.event_bus:
            await orch.event_bus.close()


def _serialize_state(state) -> dict:
    """Convert an OrchestratorState (TypedDict with dataclasses) to a plain dict."""
    if state is None:
        return {}
    result = {}
    for key, value in state.items():
        if hasattr(value, "__dataclass_fields__"):
            # Serialize dataclass
            result[key] = {
                f: getattr(value, f)
                for f in value.__dataclass_fields__
                if not f.startswith("_")
            }
            # Handle nested dataclass fields
            for field_name in result[key]:
                field_val = result[key][field_name]
                if hasattr(field_val, "__dataclass_fields__"):
                    result[key][field_name] = {
                        f: getattr(field_val, f) for f in field_val.__dataclass_fields__ if not f.startswith("_")
                    }
                elif isinstance(field_val, list):
                    result[key][field_name] = [
                        {f: getattr(item, f) for f in item.__dataclass_fields__ if not f.startswith("_")}
                        if hasattr(item, "__dataclass_fields__") else item
                        for item in field_val
                    ]
        elif isinstance(value, list):
            result[key] = [
                {f: getattr(item, f) for f in item.__dataclass_fields__ if not f.startswith("_")}
                if hasattr(item, "__dataclass_fields__") else item
                for item in value
            ]
        else:
            result[key] = value
    return result