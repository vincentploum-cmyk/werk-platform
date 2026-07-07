// Shared visual + layout metadata for the Agent Canvas.
import type { Agent, Task } from '../stores/werkStore'

export interface RoleMeta {
  label: string
  glyph: string
  color: string // hex — used for avatars and SVG edges
  soft: string // light bg tint for cards
}

// Keyed by agent.role (see db seed data).
export const ROLE_META: Record<string, RoleMeta> = {
  pmo: { label: 'PMO', glyph: '🧭', color: '#4f46e5', soft: '#eef2ff' },
  requirements: { label: 'Requirements', glyph: '📋', color: '#6366f1', soft: '#eef2ff' },
  ux: { label: 'UX', glyph: '🎨', color: '#ec4899', soft: '#fdf2f8' },
  business: { label: 'Business Logic', glyph: '📊', color: '#f59e0b', soft: '#fffbeb' },
  architect: { label: 'Architecture', glyph: '📐', color: '#8b5cf6', soft: '#f5f3ff' },
  developer: { label: 'Developer', glyph: '💻', color: '#0ea5e9', soft: '#f0f9ff' },
  tester: { label: 'Tester', glyph: '🧪', color: '#10b981', soft: '#ecfdf5' },
  devops: { label: 'DevOps · Test', glyph: '🚀', color: '#f97316', soft: '#fff7ed' },
  release: { label: 'Release · Prod', glyph: '🏭', color: '#dc2626', soft: '#fef2f2' },
}

export const DEFAULT_META: RoleMeta = {
  label: 'Agent',
  glyph: '🤖',
  color: '#64748b',
  soft: '#f1f5f9',
}

export function metaFor(role: string): RoleMeta {
  return ROLE_META[(role || '').toLowerCase()] ?? DEFAULT_META
}

// Canvas positions as percentages of the canvas box (x → left, y → top).
export const LAYOUT: Record<string, { x: number; y: number }> = {
  pmo: { x: 45, y: 7 },
  requirements: { x: 9, y: 38 },
  ux: { x: 27, y: 22 },
  business: { x: 27, y: 56 },
  architect: { x: 45, y: 39 },
  developer: { x: 62, y: 39 },
  tester: { x: 80, y: 20 },
  devops: { x: 80, y: 52 },
  release: { x: 80, y: 78 },
}

// Pipeline handoffs (from-role → to-role) drawn as connecting edges.
export const PIPELINE: [string, string][] = [
  ['pmo', 'requirements'],
  ['requirements', 'ux'],
  ['requirements', 'business'],
  ['ux', 'architect'],
  ['business', 'architect'],
  ['architect', 'developer'],
  ['developer', 'tester'],
  ['developer', 'devops'],
  ['tester', 'devops'],
  ['devops', 'release'],
]

export type AgentState = 'idle' | 'working' | 'review'

export interface AgentStatus {
  state: AgentState
  current?: Task
  tasks: Task[]
}

// Derive an agent's live status from the tasks assigned to it.
export function statusOf(agent: Agent, allTasks: Task[]): AgentStatus {
  const tasks = allTasks.filter((t) => t.assigned_agent_id === agent.id)
  const working = tasks.find((t) => t.status === 'in_progress')
  const review = tasks.find((t) => t.status === 'review')
  const backlog = tasks.find((t) => t.status === 'backlog')
  let state: AgentState = 'idle'
  if (working) state = 'working'
  else if (review) state = 'review'
  return { state, current: working ?? review ?? backlog, tasks }
}

export const STATE_LABEL: Record<AgentState, string> = {
  idle: 'Idle',
  working: 'Working',
  review: 'In Review',
}

export const STATE_DOT: Record<AgentState, string> = {
  idle: '#9ca3af',
  working: '#f59e0b',
  review: '#8b5cf6',
}
