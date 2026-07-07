# Multi-Agent Orchestration Frameworks — Research Report

**Date:** 2025-05-31  
**Author:** Software Engineer Agent  
**Purpose:** Evaluate existing multi-agent orchestration frameworks for adoption in the Werk platform.

---

## Executive Summary

Three major open-source frameworks dominate the multi-agent orchestration space: **LangGraph**, **CrewAI**, and **AutoGen (Microsoft)**. This report evaluates each on features relevant to Werk's needs: agent communication patterns, task execution models, memory management, production readiness, and alignment with the existing architecture design (FastAPI + Redis + PostgreSQL).

**Recommendation: LangGraph** is the strongest candidate for Werk's orchestration layer due to its graph-based state machine model, durable execution, comprehensive memory system, and seamless integration with Python ecosystems — all of which closely align with Werk's existing architecture design.

---

## 1. LangGraph (LangChain)

### Overview
- **Stars:** ~33,400 | **Forks:** ~5,200
- **License:** MIT
- **Language:** Python
- **Website:** [langchain.com/langgraph](https://www.langchain.com/langgraph)
- **Description:** Low-level orchestration framework for building, managing, and deploying long-running, stateful agents.

### Key Features

| Feature | Details |
|---|---|
| **Architecture** | Graph-based state machine (inspired by Pregel / Apache Beam) |
| **Communication** | Node-to-node message passing via graph edges; built-in state management |
| **Task Execution** | Durable execution — agents resume from failures automatically |
| **Memory** | Short-term (working memory) + long-term persistent memory across sessions |
| **Human-in-the-loop** | Built-in support for inspecting/modifying agent state mid-execution |
| **Debugging** | LangSmith integration for visualization, tracing, and runtime metrics |
| **Deployment** | LangSmith platform or standalone; scalable for production |
| **Ecosystem** | LangChain ecosystem (Deep Agents, LangSmith, LangServe) |

### Strengths for Werk
1. **Graph-based model** — Maps naturally to Werk's orchestration flow (Project Init → UX → Architecture → Development → Testing → Deployment)
2. **Durable execution** — Agents can survive failures without losing state, critical for long-running development workflows
3. **Comprehensive memory** — Both short-term (within-task) and long-term (cross-session) memory directly parallels Werk's "Memory & Context Store" requirement
4. **Redis + PostgreSQL compatible** — LangGraph's persistence backends align with Werk's chosen stack (PostgreSQL for state, Redis for pub/sub)
5. **Proven at scale** — Used by Klarna, Replit, Elastic in production
6. **Human-in-the-loop** — Enables lead-agent review gates between functional and technical stages

### Weaknesses
1. **Lower-level API** — Requires more manual graph/state definition compared to CrewAI's higher-level abstractions
2. **LangChain dependency** — Best when used within the LangChain ecosystem, though can run standalone
3. **Learning curve** — Graph-based state machines are more complex than linear sequential models

---

## 2. CrewAI

### Overview
- **Stars:** ~28,000+
- **License:** MIT
- **Language:** Python
- **Description:** Framework for orchestrating role-based AI agents as a "crew" to work together on tasks.

### Key Features

| Feature | Details |
|---|---|
| **Architecture** | Role-based agent teams ("crews") with sequential or hierarchical workflows |
| **Communication** | Agents share context via task outputs; built-in delegation between agents |
| **Task Execution** | Sequential task execution within a crew; hierarchical with manager agents |
| **Memory** | Short-term memory, entity memory, and summary memory; **long-term memory via SQLite/PostgreSQL** |
| **Human-in-the-loop** | Support for human input at specific task steps |
| **Tools** | Rich tool ecosystem (web search, file I/O, code execution) |
| **Deployment** | Self-hosted or via CrewAI Enterprise |

### Strengths for Werk
1. **Role-based model** — "Crews" of agents with specific roles (analyst, writer, reviewer) maps well to Werk's Functional/Technical agent distinction
2. **Easy to start** — Higher-level abstractions mean less boilerplate code
3. **Built-in memory backends** — Supports PostgreSQL and SQLite for persistent memory
4. **Hierarchical management** — Manager agents can oversee sub-agents, similar to Werk's Lead → Specialist pattern

### Weaknesses
1. **Less flexible** — Sequential/hierarchical workflows are more rigid than LangGraph's graph model
2. **Less production-proven** — Fewer large-scale production deployments vs LangGraph
3. **Weaker debugging/observability** — No LangSmith-equivalent tooling for deep agent traceability
4. **Memory management** — Less sophisticated than LangGraph's durable execution model
5. **Sequential by default** — Werk needs parallel agent collaboration (Functional + Technical agents working simultaneously)

---

## 3. AutoGen (Microsoft)

### Overview
- **Stars:** ~38,000+
- **License:** MIT (Creative Commons for docs)
- **Language:** Python / .NET
- **Description:** Multi-agent conversation framework enabling LLM agents to converse and collaborate on tasks.

### Key Features

| Feature | Details |
|---|---|
| **Architecture** | Conversational multi-agent — agents communicate via messages |
| **Communication** | Agent-to-agent conversation as the primary coordination mechanism |
| **Task Execution** | Agents delegate tasks to each other via conversations |
| **Memory** | Conversation history as implicit memory; no built-in persistent memory store |
| **Human-in-the-loop** | Excellent — agents can request human input at any point |
| **Code Execution** | Built-in Docker sandbox for safe code execution |
| **Deployment** | Self-hosted; Azure AI integration available |

### Strengths for Werk
1. **Conversational model** — Natural for agents that need to ask questions and clarify requirements (e.g., Developer asking UX for clarification)
2. **Excellent code sandboxing** — Built-in Docker execution aligns with Werk's Sandboxed Runner requirement
3. **Group chat patterns** — Enables multi-agent discussions, useful for design reviews
4. **Microsoft backing** — Strong corporate support and active development
5. **Large community** — Most stars of the three frameworks

### Weaknesses
1. **No persistent memory** — No built-in long-term memory store; relies on conversation history which grows unbounded
2. **Conversation overhead** — Agent-agent chat can become verbose and inefficient compared to structured task/artifact passing
3. **Less structured workflows** — No graph/state machine for defining sequential orchestration flows
4. **Heavier dependency** — Larger package size and more opinionated about LLM providers
5. **Azure bias** — Some features are Azure-specific, which may not align with Werk's stack-agnostic approach

---

## 4. Comparative Analysis

### Feature Comparison Matrix

| Feature | LangGraph | CrewAI | AutoGen |
|---|---|---|---|
| **Architecture Model** | Graph (state machine) | Role-based (sequential/hierarchical) | Conversational (peer-to-peer) |
| **Workflow Flexibility** | ★★★★★ (directed graphs) | ★★★☆☆ (sequential/hierarchical) | ★★★★☆ (conversation-driven) |
| **Memory/Persistence** | ★★★★★ (durable execution, short+long-term) | ★★★★☆ (SQLite/PG memory backend) | ★★☆☆☆ (no built-in persistent memory) |
| **Human-in-the-loop** | ★★★★★ (native interrupts) | ★★★★☆ (task-level input) | ★★★★★ (conversation-level input) |
| **Debugging/Observability** | ★★★★★ (LangSmith) | ★★★☆☆ (basic logging) | ★★★★☆ (logging + tracing) |
| **Production Readiness** | ★★★★★ (proven at scale) | ★★★☆☆ (growing) | ★★★★☆ (active development) |
| **Code Sandboxing** | Via LangChain tools | Via custom tools | ★★★★★ (built-in Docker) |
| **Learning Curve** | Moderate (graph model) | Low (role-based) | Low-Medium (conversation model) |
| **Python Ecosystem Fit** | ★★★★★ | ★★★★☆ | ★★★★☆ |
| **Redis/PostgreSQL Compat** | ★★★★★ | ★★★★☆ | ★★★☆☆ |

### Alignment with Werk Architecture

| Werk Component | LangGraph | CrewAI | AutoGen |
|---|---|---|---|
| **Agent Collaboration Bus (Redis Pub/Sub)** | ✓ Compatible | ✓ Compatible | ⚠️ Not native |
| **Memory & Context Store (PostgreSQL)** | ✓✓ Native support | ✓✓ Native support | ✗ Not built-in |
| **Project Manager (state machine)** | ✓✓ Native graph model | ⚠️ Sequential only | ✗ Conversation-driven |
| **Agent Registry** | Via LangChain | ✓ Built-in | ✓ Built-in |
| **Task Dispatcher** | Via graph edges | ✓ Built-in | Via conversations |
| **Human Review Gates** | ✓✓ Native interrupts | ✓ Task-level | ✓ Conversation-level |
| **Code Sandbox (Docker)** | ⚠️ Via tools | ⚠️ Via tools | ✓✓ Built-in |

---

## 5. Recommendation: LangGraph

### Why LangGraph for Werk

1. **Architecture Alignment** — Werk's orchestration flow (Project Init → UX → Architecture → Dev → Testing → Deploy) is inherently a **directed graph with conditional branches and parallel paths**. LangGraph's graph-based state machine models this naturally.

2. **Durable Execution** — Werk requires long-running multi-step workflows (hours/days). LangGraph's durable execution guarantees that if an agent crashes mid-task, it resumes from exactly where it left off — no lost work.

3. **Memory Strategy** — Werk's design calls for both short-term (within-task) and long-term (cross-project) memory. LangGraph supports both natively:
   - Short-term: Working memory within a graph run
   - Long-term: Persistent memory across sessions (PostgreSQL-backed)

4. **Human-in-the-Loop** — Werk requires review gates at each stage. LangGraph's interrupt model allows agents to pause execution and wait for lead approval — exactly matching the "Review" task state.

5. **Tech Stack Fit** — LangGraph works natively with Python, supports PostgreSQL for persistence, and integrates with Redis for state storage — matching Werk's chosen stack (FastAPI + PostgreSQL + Redis).

6. **Scalability & Production-Proven** — Used by Klarna, Replit, and Elastic; supported by LangSmith for production monitoring and debugging.

### Proposed Integration Approach

```
Werk Orchestrator (FastAPI)
    │
    ├── LangGraph SDK (Python)
    │       ├── Graph Definition (Werk workflow stages)
    │       ├── State Schema (project context, task state)
    │       ├── Node Implementations (agent callbacks)
    │       └── Conditional Edges (review gates, fallbacks)
    │
    ├── PostgreSQL (State persistence, context store)
    ├── Redis (Pub/Sub channels for real-time updates)
    └── LangSmith (Debugging, observability, KPI tracking)
```

**Implementation Steps:**
1. Define Werk's 7-stage workflow as a LangGraph graph
2. Implement each stage as a graph node calling the appropriate agent
3. Add conditional edges for review gates (approve/reject/revise)
4. Configure PostgreSQL-backed persistence for durable execution
5. Add Redis pub/sub integration for real-time dashboard updates

---

## 6. Alternative Considerations

### Hybrid Approach
If Werk wants a higher-level API for simpler workflows while retaining LangGraph's flexibility:
- **CrewAI for simple linear flows** (e.g., single-feature MVP builds)
- **LangGraph for complex branching flows** (e.g., multi-feature releases with parallel development)

### Fallback — Build Custom Orchestration
For maximum control, Werk could build its own lightweight orchestrator using:
- Redis Pub/Sub (already in the design) for agent communication
- PostgreSQL for state machine persistence
- Celery for async task execution
- Custom state machine for workflow transitions

However, this would require significantly more development effort and would miss out on LangGraph's battle-tested durable execution and debugging tooling.

---

## 7. Conclusion

**LangGraph** is the recommended multi-agent orchestration framework for Werk. It provides:
- The **most flexible workflow model** (graphs vs sequential/conversational)
- **Best memory/persistence** support for long-running development workflows
- **Production-proven durability** and observability
- **Closest alignment** with Werk's existing architecture design (FastAPI, PostgreSQL, Redis)

CrewAI is a strong alternative for simpler use cases, and AutoGen is worth evaluating specifically for its code sandboxing capabilities. However, as Werk's orchestration requirements grow in complexity, LangGraph's graph-based model will scale more naturally.

**Next Steps:**
1. Prototype a LangGraph-based orchestrator for the Werk development lifecycle
2. Integrate with existing Werk agent system (Functional/Technical agents)
3. Configure LangSmith for KPI tracking (Cycle Time, Autonomy Score)
4. Build dashboard integration via Redis pub/sub events