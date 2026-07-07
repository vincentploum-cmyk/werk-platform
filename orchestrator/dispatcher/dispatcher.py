# Task dispatcher - Assigns tasks to agents based on capability matching

from typing import Optional
from dataclasses import dataclass, field


@dataclass
class AgentCapability:
    agent_id: str
    role: str
    capabilities: list[str] = field(default_factory=list)
    status: str = "idle"


class TaskDispatcher:
    """Matches tasks to agents based on capability and availability."""

    def __init__(self):
        self._agents: dict[str, AgentCapability] = {}

    def register_agent(self, agent: AgentCapability):
        self._agents[agent.agent_id] = agent

    def find_agent_for_task(self, task_type: str, required_capabilities: list[str]) -> Optional[AgentCapability]:
        """Find the best available agent for a task."""
        for agent in self._agents.values():
            if agent.status != "idle":
                continue
            if all(cap in agent.capabilities for cap in required_capabilities):
                return agent
        return None

    def assign_task(self, agent_id: str, task_id: str) -> bool:
        """Mark an agent as busy with a task."""
        if agent_id in self._agents:
            self._agents[agent_id].status = "busy"
            return True
        return False

    def release_agent(self, agent_id: str):
        """Mark an agent as idle after completing a task."""
        if agent_id in self._agents:
            self._agents[agent_id].status = "idle"