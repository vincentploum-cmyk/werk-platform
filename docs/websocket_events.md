# WebSocket Event Protocols: Werk Platform

## 1. Overview
Real-time updates are pushed from the backend to the frontend via WebSockets (`ws://<hostname>/ws/events`).

## 2. Event Payload Format
All events follow a standard JSON structure:

```json
{
  "event_type": "string",
  "project_id": "uuid",
  "timestamp": "iso8601",
  "payload": {}
}
```

## 3. Event Types

### 3.1 task.assigned
Fired when a task is moved to `in-progress` and assigned to an agent.
- **Payload:**
  ```json
  {
    "task_id": "uuid",
    "title": "string",
    "assigned_to": "agent-role"
  }
  ```

### 3.2 task.completed
Fired when an agent calls `finish_task`.
- **Payload:**
  ```json
  {
    "task_id": "uuid",
    "result_summary": "string",
    "artifacts": ["path/to/file1", "path/to/file2"]
  }
  ```

### 3.3 stage.transition
Fired when the LangGraph orchestrator moves the project to a new phase.
- **Payload:**
  ```json
  {
    "from_stage": "Initialization",
    "to_stage": "UX_Design"
  }
  ```

### 3.4 signoff.requested
Fired when a critical milestone requires Human Founder approval.
- **Payload:**
  ```json
  {
    "task_id": "uuid",
    "description": "string",
    "milestone": "PRD_Completion"
  }
  ```

### 3.5 blocker.raised
Fired when an agent is unable to proceed.
- **Payload:**
  ```json
  {
    "agent": "agent-role",
    "reason": "string",
    "context": {}
  }
  ```

## 4. Heartbeat
The client should send a `ping` every 30 seconds to keep the connection alive. The server will respond with `pong`.
