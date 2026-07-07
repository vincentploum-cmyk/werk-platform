"""
Werk Core Orchestrator — LangGraph-based multi-agent workflow engine.

Implements the 7-stage development lifecycle as a stateful graph:
  Init → UX Design → Architecture → Development → Testing → Review → Deploy

Each stage is a graph node backed by the Werk agents (Functional → Technical).
Human-in-the-loop review gates pause the workflow at each sign-off point.
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional, Literal

# LangGraph imports (lightweight — no heavy dependencies beyond langgraph-core)
try:
    from langgraph.graph import StateGraph, END
    from langgraph.checkpoint.memory import MemorySaver
    from typing_extensions import TypedDict
except ImportError:
    # Fallback stub for type checking without langgraph installed
    StateGraph = None  # type: ignore
    END = None  # type: ignore
    MemorySaver = None  # type: ignore

    class TypedDict(dict):  # type: ignore
        pass


from orchestrator.bus.event_bus import EventBus
from orchestrator.registry.agent_registry import AgentRegistry, AgentInfo
from orchestrator.memory.context_store import ContextStore
from orchestrator.dispatcher.dispatcher import TaskDispatcher

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Constants & Enums
# ═══════════════════════════════════════════════════════════════════════════════

class Stage(str, enum.Enum):
    INIT = "init"
    UX_DESIGN = "ux_design"
    ARCHITECTURE = "architecture"
    DEVELOPMENT = "development"
    TESTING = "testing"
    REVIEW = "review"
    DEPLOY = "deploy"           # to the test/staging environment
    DEPLOY_PROD = "deploy_prod"  # to the production environment

    def description(self) -> str:
        descriptions = {
            Stage.INIT: "Requirements Agent creates PRD → artifact.created",
            Stage.UX_DESIGN: "UX Agent reads PRD → creates wireframes → review.needed",
            Stage.ARCHITECTURE: "Architect Agent reads PRD + wireframes → creates architecture design",
            Stage.DEVELOPMENT: "Developer Agent reads architecture → implements code → artifact.created",
            Stage.TESTING: "Tester Agent reads code → creates tests → review.needed",
            Stage.REVIEW: "All artifacts reviewed → review.approved → handoff to DevOps",
            Stage.DEPLOY: "DevOps Agent packages and deploys → artifact.created (deployment URL)",
        }
        return descriptions.get(self, "")

    def agent_roles(self) -> list[str]:
        """Which agent roles are primarily responsible in this stage."""
        mapping = {
            Stage.INIT: ["requirements"],
            Stage.UX_DESIGN: ["ux"],
            Stage.ARCHITECTURE: ["architect"],
            Stage.DEVELOPMENT: ["developer"],
            Stage.TESTING: ["tester"],
            Stage.REVIEW: ["developer", "architect"],
            Stage.DEPLOY: ["devops"],
        }
        return mapping.get(self, [])


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Event Types (matching the architecture design)
# ═══════════════════════════════════════════════════════════════════════════════

EVENT_TASK_ASSIGNED = "task.assigned"
EVENT_ARTIFACT_CREATED = "artifact.created"
EVENT_REVIEW_NEEDED = "review.needed"
EVENT_REVIEW_APPROVED = "review.approved"
EVENT_REVIEW_REJECTED = "review.rejected"
EVENT_CONTEXT_UPDATED = "context.updated"
EVENT_BLOCKER_RAISED = "blocker.raised"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Orchestrator State Schema (TypedDict for LangGraph)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class StageResult:
    """Output produced by a stage node."""
    stage: str
    agent_id: str
    artifacts: list[dict] = field(default_factory=list)
    summary: str = ""
    status: Literal["success", "failed", "blocked"] = "success"
    completed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class OrchestratorState(TypedDict):
    """Shared state that flows through the LangGraph graph."""

    # Project identity
    project_id: str
    project_name: str

    # Current stage tracking
    current_stage: str  # One of Stage enum values
    previous_stage: str  # The stage we just came from
    error: Optional[str]

    # Results from each stage (built up as we traverse the graph)
    init_result: Optional[StageResult]
    ux_design_result: Optional[StageResult]
    architecture_result: Optional[StageResult]
    development_result: Optional[StageResult]
    testing_result: Optional[StageResult]
    review_result: Optional[StageResult]
    deploy_result: Optional[StageResult]

    # Review gate state
    review_approved: bool  # Set to True by the Human-in-the-Loop approval
    review_feedback: str

    # Artifact paths accumulated during the workflow
    artifacts: list[dict]

    # Blockers that need human intervention
    blockers: list[dict]


def initial_state(project_id: str, project_name: str) -> OrchestratorState:
    """Create a fresh orchestrator state for a new project."""
    return {
        "project_id": project_id,
        "project_name": project_name,
        "current_stage": Stage.INIT.value,
        "previous_stage": "",
        "error": None,
        "init_result": None,
        "ux_design_result": None,
        "architecture_result": None,
        "development_result": None,
        "testing_result": None,
        "review_result": None,
        "deploy_result": None,
        "review_approved": False,
        "review_feedback": "",
        "artifacts": [],
        "blockers": [],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Stage Node Implementations
# ═══════════════════════════════════════════════════════════════════════════════

class WerkOrchestrator:
    """Orchestrates the Werk agent workflow using LangGraph.

    Usage:
        orch = WerkOrchestrator(event_bus, registry, dispatcher, context_store)
        result = await orch.run_project(project_id, "My Project")
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        registry: Optional[AgentRegistry] = None,
        dispatcher: Optional[TaskDispatcher] = None,
        context_store: Optional[ContextStore] = None,
        generate: Optional[Callable[[str, str], Awaitable[Optional[str]]]] = None,
    ):
        self.event_bus = event_bus or EventBus()
        self.registry = registry or AgentRegistry()
        self.dispatcher = dispatcher or TaskDispatcher()
        self.context = context_store or ContextStore()
        # Async callable (system, user) -> text. When set, stages produce real
        # model output instead of simulated placeholders.
        self.generate = generate
        self._graph = self._build_graph()

        # Register default Werk agents
        self._register_default_agents()

    def _register_default_agents(self):
        """Register the standard Werk agent types with their capabilities."""
        defaults = [
            AgentInfo(
                id="agent-req-1", name="Requirements Agent", type="functional",
                role="requirements", capabilities=["user-story-writing", "prd-generation", "acceptance-criteria"],
            ),
            AgentInfo(
                id="agent-ux-1", name="UX Agent", type="functional",
                role="ux", capabilities=["wireframing", "user-flow-design", "design-systems"],
            ),
            AgentInfo(
                id="agent-biz-1", name="Business Logic Agent", type="functional",
                role="business", capabilities=["data-modeling", "business-rule-definition", "validation-logic"],
            ),
            AgentInfo(
                id="agent-arch-1", name="Architect Agent", type="technical",
                role="architect", capabilities=["system-design", "tech-selection", "schema-design"],
            ),
            AgentInfo(
                id="agent-dev-1", name="Developer Agent", type="technical",
                role="developer", capabilities=["code-generation", "implementation", "refactoring"],
            ),
            AgentInfo(
                id="agent-test-1", name="Tester Agent", type="technical",
                role="tester", capabilities=["unit-testing", "integration-testing", "e2e-testing"],
            ),
            AgentInfo(
                id="agent-devops-1", name="DevOps Agent", type="technical",
                role="devops", capabilities=["ci-cd-config", "test-env-deploy", "health-checks"],
            ),
            AgentInfo(
                id="agent-release-1", name="Release Agent", type="technical",
                role="release", capabilities=["production-deploy", "rollback-planning", "uptime-monitoring"],
            ),
            AgentInfo(
                id="agent-pmo-1", name="PMO Agent", type="leadership",
                role="pmo", capabilities=["status-reporting", "coordination", "risk-tracking"],
            ),
        ]
        for agent in defaults:
            self.registry.register(agent)
            # Also register with the dispatcher for capability matching
            from orchestrator.dispatcher.dispatcher import AgentCapability
            cap = AgentCapability(
                agent_id=agent.id,
                role=agent.role,
                capabilities=agent.capabilities,
            )
            self.dispatcher.register_agent(cap)

    # ── Stage Node Logic ─────────────────────────────────────────────────────

    async def _run_stage_init(self, state: OrchestratorState) -> dict:
        """Stage 1: Requirements Agent creates PRD."""
        logger.info(f"[{state['project_id']}] Stage INIT: Generating PRD")
        return await self._execute_stage(
            state,
            stage=Stage.INIT,
            agent_role="requirements",
            task_title="Generate PRD and user stories",
            task_desc="Analyze the business plan and produce a comprehensive PRD with features, "
                      "functional requirements, and KPIs.",
            artifact_types=["md"],
        )

    async def _run_stage_ux(self, state: OrchestratorState) -> dict:
        """Stage 2: UX Agent reads PRD and creates wireframes."""
        logger.info(f"[{state['project_id']}] Stage UX_DESIGN: Creating wireframes")
        return await self._execute_stage(
            state,
            stage=Stage.UX_DESIGN,
            agent_role="ux",
            task_title="Design user flows and wireframes",
            task_desc="Based on the PRD, create wireframes, user journeys, and design systems.",
            artifact_types=["md", "diagram"],
        )

    async def _run_stage_architecture(self, state: OrchestratorState) -> dict:
        """Stage 3: Architect Agent creates system design."""
        logger.info(f"[{state['project_id']}] Stage ARCHITECTURE: Designing architecture")
        return await self._execute_stage(
            state,
            stage=Stage.ARCHITECTURE,
            agent_role="architect",
            task_title="Design system architecture",
            task_desc="Read PRD and wireframes, design the system architecture, data models, "
                      "API endpoints, and tech stack.",
            artifact_types=["md", "sql"],
        )

    async def _run_stage_development(self, state: OrchestratorState) -> dict:
        """Stage 4: Developer Agent implements code."""
        logger.info(f"[{state['project_id']}] Stage DEVELOPMENT: Implementing code")
        return await self._execute_stage(
            state,
            stage=Stage.DEVELOPMENT,
            agent_role="developer",
            task_title="Implement features from architecture",
            task_desc="Read the architecture design and implement the required code, "
                      "including project structure, API endpoints, and core logic.",
            artifact_types=["py", "ts", "js", "json"],
        )

    async def _run_stage_testing(self, state: OrchestratorState) -> dict:
        """Stage 5: Tester Agent creates and runs tests."""
        logger.info(f"[{state['project_id']}] Stage TESTING: Running tests")
        result = await self._execute_stage(
            state,
            stage=Stage.TESTING,
            agent_role="tester",
            task_title="Write and execute tests",
            task_desc="Read the implemented code, create unit tests, integration tests, "
                      "and E2E tests to validate correctness.",
            artifact_types=["py", "json"],
        )
        # Attach a review request automatically
        if result.get("testing_result") and result["testing_result"].status == "success":
            await self._publish_event(
                state["project_id"],
                EVENT_REVIEW_NEEDED,
                source_role="tester",
                target_role="developer",
                payload={"stage": "testing", "artifacts": result["testing_result"].artifacts},
            )
        return result

    async def _run_stage_review(self, state: OrchestratorState) -> dict:
        """Stage 6: Review & Approval gate (Human-in-the-loop)."""
        logger.info(f"[{state['project_id']}] Stage REVIEW: Awaiting approval")

        if not state.get("review_approved"):
            # Publish review needed event — a human (or lead agent) must approve
            await self._publish_event(
                state["project_id"],
                EVENT_REVIEW_NEEDED,
                source_role="orchestrator",
                target_role="lead",
                payload={
                    "stage": "review",
                    "project_id": state["project_id"],
                    "artifact_summary": [
                        a.get("summary", a.get("file_path", ""))
                        for a in state.get("artifacts", [])
                    ],
                },
            )

        review_result = StageResult(
            stage=Stage.REVIEW.value,
            agent_id="orchestrator",
            status="success" if state.get("review_approved") else "blocked",
            summary=f"Review {'approved' if state.get('review_approved') else 'pending approval'}",
        )
        if state.get("review_feedback"):
            review_result.summary += f": {state['review_feedback']}"

        return {"review_result": review_result, "error": None}

    async def _run_stage_deploy(self, state: OrchestratorState) -> dict:
        """Stage 7a: DevOps Agent deploys to the TEST/staging environment."""
        logger.info(f"[{state['project_id']}] Stage DEPLOY (test): Deploying")
        return await self._execute_stage(
            state,
            stage=Stage.DEPLOY,
            agent_role="devops",
            task_title="Deploy to the test environment",
            task_desc="Build containers, configure CI/CD, deploy to the TEST/staging environment, "
                      "run health checks, and confirm the test environment is up and running.",
            artifact_types=["yaml", "sh", "url"],
        )

    async def _run_stage_deploy_prod(self, state: OrchestratorState) -> dict:
        """Stage 7b: Release Agent deploys to the PRODUCTION environment (after prod sign-off)."""
        logger.info(f"[{state['project_id']}] Stage DEPLOY (production): Releasing")
        return await self._execute_stage(
            state,
            stage=Stage.DEPLOY_PROD,
            agent_role="release",
            task_title="Deploy to the production environment",
            task_desc="Promote the release to PRODUCTION with a rollout and rollback plan, run "
                      "post-deploy health checks, and confirm production is up and running.",
            artifact_types=["yaml", "sh", "url"],
        )

    # ── Shared Stage Execution ───────────────────────────────────────────────

    async def _execute_stage(
        self,
        state: OrchestratorState,
        stage: Stage,
        agent_role: str,
        task_title: str,
        task_desc: str,
        artifact_types: list[str],
    ) -> dict:
        """Execute a generic stage: find agent → assign task → execute → record artifacts."""
        try:
            # Find an available agent
            agent = self.dispatcher.find_agent_for_task(
                task_type=agent_role,
                required_capabilities=[f"{agent_role}"],
            )
            if not agent:
                # Fallback: use registry
                agents = self.registry.get_by_role(agent_role)
                if not agents:
                    return self._stage_error(state, stage, f"No agent available for role '{agent_role}'")
                agent_id = agents[0].id
            else:
                agent_id = agent.agent_id

            # Assign the task
            task_id = f"{stage.value}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
            self.dispatcher.assign_task(agent_id, task_id)

            # Publish task assigned event
            await self._publish_event(
                state["project_id"],
                EVENT_TASK_ASSIGNED,
                source_role="orchestrator",
                target_role=agent_role,
                payload={
                    "task_id": task_id,
                    "project_id": state["project_id"],
                    "title": task_title,
                    "description": task_desc,
                },
            )

            # Store the task in context
            context_key = f"task:{stage.value}"
            self.context.set(state["project_id"], context_key, {
                "task_id": task_id,
                "agent_id": agent_id,
                "title": task_title,
                "status": "in_progress",
            })

            # Real agent work when a model is wired in; otherwise a simulated placeholder.
            content = None
            source = "simulated"
            if self.generate is not None:
                prior = "\n\n".join(
                    f"## {a.get('title', a.get('stage', ''))}\n{a.get('content') or a.get('summary', '')}"
                    for a in state.get("artifacts", [])
                )[:6000]
                base = (state.get("system_overrides") or {}).get(agent_role)
                if base:
                    # Use the agent's tuned instructions + few-shot examples from the platform.
                    system = (
                        f"{base}\n\n"
                        f"You are working on project '{state.get('project_name', '')}'. "
                        f"Deliver this stage's work concretely and completely, ready to hand off."
                    )
                else:
                    system = (
                        f"You are the {agent_role} agent on the Werk software delivery platform, "
                        f"working on project '{state.get('project_name', '')}'. "
                        f"Deliver your stage's work concretely, completely, and ready to hand off."
                    )
                user = (
                    f"Task: {task_title}\n{task_desc}\n\n"
                    + (f"Work completed in earlier stages:\n{prior}\n\n" if prior else "")
                    + "Produce your deliverable now."
                )
                try:
                    content = await self.generate(system, user)
                except Exception as gen_err:
                    logger.warning(f"generate() failed at stage {stage.value}: {gen_err}")
                if content:
                    source = "model"

            artifact_entry = {
                "stage": stage.value,
                "title": task_title,
                "agent_id": agent_id,
                "task_id": task_id,
                "file_type": artifact_types[0] if artifact_types else "md",
                "summary": (content[:280] if content else f"{task_title} completed by agent {agent_id}"),
                "content": content or "",
                "source": source,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            # Publish artifact created event
            await self._publish_event(
                state["project_id"],
                EVENT_ARTIFACT_CREATED,
                source_role=agent_role,
                target_role="",
                payload=artifact_entry,
            )

            # Release the agent
            self.dispatcher.release_agent(agent_id)

            result = StageResult(
                stage=stage.value,
                agent_id=agent_id,
                artifacts=[artifact_entry],
                summary=artifact_entry["summary"],
                status="success",
            )

            return {
                f"{stage.value}_result": result,
                "error": None,
                "artifacts": state.get("artifacts", []) + [artifact_entry],
                "current_stage": stage.value,
            }

        except Exception as e:
            logger.error(f"Stage {stage.value} failed: {e}")
            return self._stage_error(state, stage, str(e))

    def _stage_error(self, state: OrchestratorState, stage: Stage, error: str) -> dict:
        """Return an error result for a failed stage."""
        return {
            f"{stage.value}_result": StageResult(
                stage=stage.value,
                agent_id="",
                status="failed",
                summary=f"Stage {stage.value} failed: {error}",
            ),
            "error": error,
        }

    # ── Routing / Edge Decision Logic ────────────────────────────────────────

    @staticmethod
    def route_after_init(state: OrchestratorState) -> str:
        """After init → proceed to UX design."""
        if state.get("error"):
            return END  # type: ignore
        return Stage.UX_DESIGN.value

    @staticmethod
    def route_after_ux(state: OrchestratorState) -> str:
        """After UX → proceed to Architecture."""
        if state.get("error"):
            return END
        return Stage.ARCHITECTURE.value

    @staticmethod
    def route_after_architecture(state: OrchestratorState) -> str:
        """After architecture → proceed to Development."""
        if state.get("error"):
            return END
        return Stage.DEVELOPMENT.value

    @staticmethod
    def route_after_development(state: OrchestratorState) -> str:
        """After development → proceed to Testing."""
        if state.get("error"):
            return END
        return Stage.TESTING.value

    @staticmethod
    def route_after_testing(state: OrchestratorState) -> str:
        """After testing → proceed to Review."""
        if state.get("error"):
            return END
        return Stage.REVIEW.value

    @staticmethod
    def route_after_review(state: OrchestratorState) -> str:
        """After review → either deploy or loop back for rework."""
        if state.get("error"):
            return END
        if state.get("review_approved"):
            return Stage.DEPLOY.value
        # Not approved yet — stay in review (human must approve)
        return Stage.REVIEW.value

    @staticmethod
    def route_after_deploy(state: OrchestratorState) -> str:
        """After deploy → end of workflow."""
        return END

    # ── Event Publishing ─────────────────────────────────────────────────────

    async def _publish_event(
        self,
        project_id: str,
        event_type: str,
        source_role: str,
        target_role: str,
        payload: dict,
    ):
        """Publish an event to the Redis pub/sub event bus."""
        if self.event_bus:
            channel = f"werk:project:{project_id}:events"
            event = {
                "type": event_type,
                "source": source_role,
                "target": target_role,
                "payload": payload,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            await self.event_bus.publish(channel, event)

    # ── LangGraph Graph Construction ─────────────────────────────────────────

    def _build_graph(self):
        """Build the LangGraph state graph for the Werk workflow.

        The graph mirrors the 7-stage orchestration flow from the architecture design:
          Init → UX → Architecture → Development → Testing → Review → Deploy

        Review is a human-in-the-loop gate that loops until approved.
        """
        if StateGraph is None:
            logger.warning("LangGraph not installed; returning None for graph. "
                           "Install with: pip install langgraph")
            return None

        workflow = StateGraph(OrchestratorState)

        # Add all stage nodes
        async def node_init(state: OrchestratorState) -> dict:
            return await self._run_stage_init(state)
        workflow.add_node(Stage.INIT.value, node_init)

        async def node_ux(state: OrchestratorState) -> dict:
            return await self._run_stage_ux(state)
        workflow.add_node(Stage.UX_DESIGN.value, node_ux)

        async def node_architecture(state: OrchestratorState) -> dict:
            return await self._run_stage_architecture(state)
        workflow.add_node(Stage.ARCHITECTURE.value, node_architecture)

        async def node_development(state: OrchestratorState) -> dict:
            return await self._run_stage_development(state)
        workflow.add_node(Stage.DEVELOPMENT.value, node_development)

        async def node_testing(state: OrchestratorState) -> dict:
            return await self._run_stage_testing(state)
        workflow.add_node(Stage.TESTING.value, node_testing)

        async def node_review(state: OrchestratorState) -> dict:
            return await self._run_stage_review(state)
        workflow.add_node(Stage.REVIEW.value, node_review)

        async def node_deploy(state: OrchestratorState) -> dict:
            return await self._run_stage_deploy(state)
        workflow.add_node(Stage.DEPLOY.value, node_deploy)

        # Set the entry point
        workflow.set_entry_point(Stage.INIT.value)

        # Add conditional edges for the sequential flow + review loop
        workflow.add_conditional_edges(
            Stage.INIT.value,
            self.route_after_init,
            {Stage.UX_DESIGN.value: Stage.UX_DESIGN.value, END: END},
        )
        workflow.add_conditional_edges(
            Stage.UX_DESIGN.value,
            self.route_after_ux,
            {Stage.ARCHITECTURE.value: Stage.ARCHITECTURE.value, END: END},
        )
        workflow.add_conditional_edges(
            Stage.ARCHITECTURE.value,
            self.route_after_architecture,
            {Stage.DEVELOPMENT.value: Stage.DEVELOPMENT.value, END: END},
        )
        workflow.add_conditional_edges(
            Stage.DEVELOPMENT.value,
            self.route_after_development,
            {Stage.TESTING.value: Stage.TESTING.value, END: END},
        )
        workflow.add_conditional_edges(
            Stage.TESTING.value,
            self.route_after_testing,
            {Stage.REVIEW.value: Stage.REVIEW.value, END: END},
        )
        workflow.add_conditional_edges(
            Stage.REVIEW.value,
            self.route_after_review,
            {
                Stage.DEPLOY.value: Stage.DEPLOY.value,
                Stage.REVIEW.value: Stage.REVIEW.value,  # Loop for re-approval
                END: END,
            },
        )
        workflow.add_conditional_edges(
            Stage.DEPLOY.value,
            self.route_after_deploy,
            {END: END},
        )

        # Compile with in-memory checkpointer for durable execution
        checkpointer = MemorySaver() if MemorySaver else None
        return workflow.compile(checkpointer=checkpointer)

    # ── Public API ───────────────────────────────────────────────────────────

    async def run_project(
        self,
        project_id: str,
        project_name: str,
        thread_id: Optional[str] = None,
        auto_approve: bool = False,
        system_overrides: Optional[dict] = None,
    ) -> OrchestratorState:
        """Execute the full project workflow from init to deploy.

        Args:
            project_id: UUID of the project.
            project_name: Human-readable project name.
            thread_id: Optional LangGraph thread ID for resumability.

        Returns:
            Final OrchestratorState with all stage results populated.
        """
        state = initial_state(project_id, project_name)
        if system_overrides:
            state["system_overrides"] = system_overrides

        if self._graph is None:
            # Fallback: run sequentially without LangGraph
            logger.info("Running orchestrator without LangGraph (sequential fallback)")
            return await self._run_sequential(state, auto_approve=auto_approve)

        config = {"configurable": {"thread_id": thread_id or project_id}}
        result = await self._graph.ainvoke(state, config)
        return result

    async def _run_sequential(
        self, state: OrchestratorState, auto_approve: bool = False
    ) -> OrchestratorState:
        """Fallback sequential execution without LangGraph."""
        if auto_approve:
            state["review_approved"] = True
        stages = [
            self._run_stage_init,
            self._run_stage_ux,
            self._run_stage_architecture,
            self._run_stage_development,
            self._run_stage_testing,
            self._run_stage_review,
        ]
        for stage_fn in stages:
            update = await stage_fn(state)
            state.update(update)
            if state.get("error"):
                break
            # For review, wait for approval (auto-approved above when requested)
            if state.get("current_stage") == Stage.REVIEW.value and not state.get("review_approved"):
                break

        if not state.get("error") and state.get("review_approved"):
            update = await self.resume_after_review(state)
            state.update(update)

        return state

    async def resume_after_review(
        self,
        state: OrchestratorState,
        feedback: str = "",
    ) -> dict:
        """Resume the workflow from the review gate into the test deploy stage."""
        state["review_approved"] = True
        if feedback:
            state["review_feedback"] = feedback
        return await self._run_stage_deploy(state)

    async def resume_after_prod_approval(
        self,
        state: OrchestratorState,
        feedback: str = "",
    ) -> dict:
        """Resume the workflow from the production gate into the production deploy stage."""
        if feedback:
            state["prod_feedback"] = feedback
        return await self._run_stage_deploy_prod(state)

    # ── Review Approval (Human-in-the-Loop) ──────────────────────────────────

    async def approve_review(
        self,
        project_id: str,
        feedback: str = "",
        thread_id: Optional[str] = None,
    ):
        """Approve the review gate, allowing the workflow to proceed to deploy.

        Call this from the lead agent or API when the review is satisfactory.
        """
        # Update context with the approval
        self.context.set(project_id, "review.approved", True)
        self.context.set(project_id, "review.feedback", feedback)

        # Publish approval event
        await self._publish_event(
            project_id,
            EVENT_REVIEW_APPROVED,
            source_role="lead",
            target_role="orchestrator",
            payload={"feedback": feedback, "approved": True},
        )

    async def reject_review(
        self,
        project_id: str,
        feedback: str,
        thread_id: Optional[str] = None,
    ):
        """Reject the review, requiring rework."""
        self.context.set(project_id, "review.approved", False)
        self.context.set(project_id, "review.feedback", feedback)

        await self._publish_event(
            project_id,
            EVENT_REVIEW_REJECTED,
            source_role="lead",
            target_role="orchestrator",
            payload={"feedback": feedback, "approved": False},
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Convenience Factory
# ═══════════════════════════════════════════════════════════════════════════════

def create_orchestrator(
    redis_url: str = "redis://localhost:6379/0",
    generate: Optional[Callable[[str, str], Awaitable[Optional[str]]]] = None,
) -> WerkOrchestrator:
    """Create a fully wired WerkOrchestrator with default dependencies."""
    bus = EventBus(redis_url=redis_url)
    registry = AgentRegistry()
    dispatcher = TaskDispatcher()
    context_store = ContextStore()
    return WerkOrchestrator(
        event_bus=bus,
        registry=registry,
        dispatcher=dispatcher,
        context_store=context_store,
        generate=generate,
    )