# Business Logic & Process Flows: Werk Platform

## 1. Task Transition Logic
The orchestration engine follows a strict state machine for task management, implemented via **LangGraph**.

### States:
1. **Backlog:** Task is defined but not yet ready for work.
2. **In-Progress:** Agent is currently working on the task.
3. **Review:** Work is completed and waiting for Lead approval.
4. **Approval Required:** Critical task waiting for Human Founder sign-off.
5. **Done:** Work is approved and archived.

### Transitions:
- **Lead Agent:** Can move tasks between most states.
- **Specialized Agent:** Can move tasks from `In-Progress` to `Review` (via `finish_task`).
- **Founder (Human):** Must move tasks from `Approval Required` to `Done` for P0 milestones.

## 2. Agent Awakening Logic
- When a task is assigned or a message is sent, the recipient agent must be "activated."
- The system checks the `agents` table to determine the agent's capabilities and status.

## 3. Deployment Flow (High Level)
1. **Functional Lead** finalizes PRD.
2. **Technical Lead** designs Architecture.
3. **Software Engineer** implements feature.
4. **QA Agent** (if present) runs tests.
5. **Technical Lead** approves and triggers deployment script.

## 4. Resource Usage Logic
- **Credits:** Each agent action (LLM call, bash command) consumes credits.
- **Limits:** Users can set daily/project caps on credit consumption to manage costs.
