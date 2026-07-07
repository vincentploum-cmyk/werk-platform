# Agent registry - Catalog of available agents

from typing import Optional, Dict
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class AgentInfo:
    id: str
    name: str
    type: str  # functional, technical, quality
    role: str
    capabilities: list[str] = field(default_factory=list)
    llm_model: str = "gpt-4o"
    status: str = "idle"
    registered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AgentRegistry:
    """Registry of all available agent types and their capabilities."""

    def __init__(self):
        self._agents: Dict[str, AgentInfo] = {}

    def register(self, agent: AgentInfo):
        self._agents[agent.id] = agent

    def get(self, agent_id: str) -> Optional[AgentInfo]:
        return self._agents.get(agent_id)

    def get_by_role(self, role: str) -> list[AgentInfo]:
        return [a for a in self._agents.values() if a.role == role]

    def get_by_type(self, agent_type: str) -> list[AgentInfo]:
        return [a for a in self._agents.values() if a.type == agent_type]

    def list_all(self) -> list[AgentInfo]:
        return list(self._agents.values())

    def update_status(self, agent_id: str, status: str) -> bool:
        if agent_id in self._agents:
            self._agents[agent_id].status = status
            return True
        return False

    def unregister(self, agent_id: str) -> bool:
        return self._agents.pop(agent_id, None) is not None