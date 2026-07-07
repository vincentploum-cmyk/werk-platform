-- Werk Platform Database Initialization
-- This script runs on first container startup (docker-entrypoint-initdb.d)

-- Enable pgvector extension for semantic search
CREATE EXTENSION IF NOT EXISTS vector;

-- Projects
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    config JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agents Registry
CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    role TEXT NOT NULL,
    llm_config JSONB DEFAULT '{}',
    capabilities JSONB DEFAULT '[]',
    status TEXT DEFAULT 'idle',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tasks
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id),
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'backlog',
    assigned_agent_id UUID REFERENCES agents(id),
    parent_task_id UUID REFERENCES tasks(id),
    priority INTEGER DEFAULT 0,
    artifacts JSONB DEFAULT '[]',
    result TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Artifacts
CREATE TABLE IF NOT EXISTS artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id),
    task_id UUID REFERENCES tasks(id),
    agent_id UUID REFERENCES agents(id),
    file_path TEXT NOT NULL,
    file_type TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agent Communication Log
CREATE TABLE IF NOT EXISTS agent_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id),
    event_type TEXT NOT NULL,
    source_agent_id UUID REFERENCES agents(id),
    target_agent_id UUID REFERENCES agents(id),
    payload JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Project Context (Shared Memory)
CREATE TABLE IF NOT EXISTS context_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id),
    agent_id UUID REFERENCES agents(id),
    key TEXT NOT NULL,
    value JSONB NOT NULL,
    version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, key)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_tasks_project_status ON tasks(project_id, status);
CREATE INDEX IF NOT EXISTS idx_tasks_assigned_agent ON tasks(assigned_agent_id, status);
CREATE INDEX IF NOT EXISTS idx_artifacts_project ON artifacts(project_id);
CREATE INDEX IF NOT EXISTS idx_agent_events_project ON agent_events(project_id, created_at);
CREATE INDEX IF NOT EXISTS idx_context_project ON context_entries(project_id, key);

-- Seed data: default Werk agent types
INSERT INTO agents (name, type, role, capabilities) VALUES
    ('Requirements Agent', 'functional', 'requirements', '["user-story-writing","prd-generation","acceptance-criteria"]'),
    ('UX Agent', 'functional', 'ux', '["wireframing","user-flow-design","design-systems"]'),
    ('Business Logic Agent', 'functional', 'business', '["data-modeling","business-rule-definition","validation-logic"]'),
    ('Architect Agent', 'technical', 'architect', '["system-design","tech-selection","schema-design"]'),
    ('Developer Agent', 'technical', 'developer', '["code-generation","implementation","refactoring"]'),
    ('Tester Agent', 'technical', 'tester', '["unit-testing","integration-testing","e2e-testing"]'),
    ('DevOps Agent', 'technical', 'devops', '["ci-cd-config","docker-config","deployment-scripting"]')
ON CONFLICT DO NOTHING;