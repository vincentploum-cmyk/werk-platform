from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utcnow():
    return datetime.now(timezone.utc)


def new_uuid():
    return str(uuid.uuid4())


class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), default="draft")  # draft, active, completed, archived
    config = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Agent(Base):
    __tablename__ = "agents"

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # functional, technical, quality
    role = Column(String(50), nullable=False)  # requirements, ux, architect, developer, etc.
    # NULL = global template agent; set = deployed for a specific project (e.g. from an SOW).
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=True)
    llm_config = Column(JSON, default=dict)
    capabilities = Column(JSON, default=list)
    status = Column(String(50), default="idle")  # idle, busy, offline
    created_at = Column(DateTime(timezone=True), default=utcnow)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"))
    title = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), default="backlog")  # backlog, in_progress, review, done, blocked
    assigned_agent_id = Column(UUID(as_uuid=False), ForeignKey("agents.id"))
    parent_task_id = Column(UUID(as_uuid=False), ForeignKey("tasks.id"))
    priority = Column(Integer, default=0)
    artifacts = Column(JSON, default=list)
    result = Column(Text)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    project = relationship("Project", backref="tasks")
    assigned_agent = relationship("Agent", backref="assigned_tasks")


class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"))
    task_id = Column(UUID(as_uuid=False), ForeignKey("tasks.id"))
    agent_id = Column(UUID(as_uuid=False), ForeignKey("agents.id"))
    file_path = Column(Text, nullable=False)
    file_type = Column(String(50))  # md, py, yml, json, ...
    content = Column(Text)  # the generated deliverable text
    metadata_json = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class AgentEvent(Base):
    __tablename__ = "agent_events"

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"))
    event_type = Column(String(100), nullable=False)  # task.assigned, artifact.created, etc.
    source_agent_id = Column(UUID(as_uuid=False), ForeignKey("agents.id"))
    target_agent_id = Column(UUID(as_uuid=False), ForeignKey("agents.id"))
    payload = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class ContextEntry(Base):
    __tablename__ = "context_entries"

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"))
    agent_id = Column(UUID(as_uuid=False), ForeignKey("agents.id"))
    key = Column(String(255), nullable=False)
    value = Column(JSON, nullable=False)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (
        UniqueConstraint("project_id", "key", name="uq_project_key"),
    )


class AppSetting(Base):
    """Singleton-style key/value store for editable platform configuration
    (e.g. the configurable SOW parameter definitions)."""
    __tablename__ = "app_settings"

    key = Column(String(100), primary_key=True)
    value = Column(JSON, default=dict)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class WorkflowGateState(Base):
    """Durable workflow state for review and production approval gates."""

    __tablename__ = "workflow_gate_states"

    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), primary_key=True)
    gate_type = Column(String(50), nullable=False)  # review | production
    state_json = Column("state", JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
