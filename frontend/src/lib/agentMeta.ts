// Shared visual + layout metadata for the Agent Canvas.
import type { Agent, Task } from '../stores/werkStore'

export interface RoleMeta {
  label: string
  glyph: string
  color: string // hex — used for avatars and SVG edges
  soft: string // light bg tint for cards
}

// Keyed by agent.role (see db seed data).
// Colors double as text on white cards, so every value is ≥4.5:1 (WCAG AA).
export const ROLE_META: Record<string, RoleMeta> = {
  pmo: { label: 'PMO', glyph: '🧭', color: '#4f46e5', soft: '#eef2ff' },
  requirements: { label: 'Requirements', glyph: '📋', color: '#4338ca', soft: '#eef2ff' },
  ux: { label: 'UX', glyph: '🎨', color: '#be185d', soft: '#fdf2f8' },
  business: { label: 'Business Logic', glyph: '📊', color: '#b45309', soft: '#fffbeb' },
  architect: { label: 'Architecture', glyph: '📐', color: '#6d28d9', soft: '#f5f3ff' },
  developer: { label: 'Developer', glyph: '💻', color: '#0369a1', soft: '#f0f9ff' },
  tester: { label: 'Tester', glyph: '🧪', color: '#047857', soft: '#ecfdf5' },
  devops: { label: 'DevOps · Test', glyph: '🚀', color: '#c2410c', soft: '#fff7ed' },
  release: { label: 'Release · Prod', glyph: '🏭', color: '#b91c1c', soft: '#fef2f2' },
}

export const DEFAULT_META: RoleMeta = {
  label: 'Agent',
  glyph: '🤖',
  color: '#475569',
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

// Status dot colors — kept ≥3:1 against white cards (WCAG 1.4.11 for UI graphics).
export const STATE_DOT: Record<AgentState, string> = {
  idle: '#6b7280',
  working: '#d97706',
  review: '#8b5cf6',
}
