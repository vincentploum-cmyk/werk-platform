import { useEffect, useState } from 'react'
import Header from '../components/Header'
import AgentPanel from '../components/AgentPanel'
import NewTaskModal from '../components/NewTaskModal'
import SowUploadModal from '../components/SowUploadModal'
import { useWerkStore, type Agent } from '../stores/werkStore'
import { useMediaQuery } from '../lib/useMediaQuery'
import {
  metaFor,
  statusOf,
  LAYOUT,
  PIPELINE,
  STATE_LABEL,
  STATE_DOT,
  type AgentState,
} from '../lib/agentMeta'

// Pipeline flow order — drives the stacked layout on narrow screens.
const ROLE_ORDER = [
  'pmo',
  'requirements',
  'ux',
  'business',
  'architect',
  'developer',
  'tester',
  'devops',
  'release',
]

function orderIndex(role: string): number {
  const i = ROLE_ORDER.indexOf(role.toLowerCase())
  return i === -1 ? ROLE_ORDER.length : i
}

// Which roles read as "functional" on the canvas (matches the desktop grouping).
// Grouping by role is more reliable than the DB `type` field (PMO isn't tagged
// functional there).
const FUNCTIONAL_ROLES = new Set(['pmo', 'requirements', 'ux', 'business'])

const CANVAS_CSS = `
@keyframes werk-pulse-ring {
  0% { box-shadow: 0 0 0 0 var(--ring); }
  70% { box-shadow: 0 0 0 10px rgba(0,0,0,0); }
  100% { box-shadow: 0 0 0 0 rgba(0,0,0,0); }
}
.werk-working { animation: werk-pulse-ring 1.8s infinite; }
@keyframes werk-dash { to { stroke-dashoffset: -4; } }
.werk-edge-active { animation: werk-dash 0.6s linear infinite; }
@keyframes werk-shimmer { 0% { transform: translateX(-100%); } 100% { transform: translateX(250%); } }
.werk-shimmer { animation: werk-shimmer 1.4s ease-in-out infinite; }
@media (prefers-reduced-motion: reduce) {
  .werk-working, .werk-edge-active, .werk-shimmer { animation: none; }
}
`

// Fallback positions for any agent whose role isn't in the pipeline layout.
function positionFor(role: string, index: number): { x: number; y: number } {
  return LAYOUT[role] ?? { x: 12 + (index % 6) * 15, y: 78 }
}

function AgentNode({
  agent,
  index,
  onSelect,
  onDropTask,
}: {
  agent: Agent
  index: number
  onSelect: (a: Agent) => void
  onDropTask: (taskId: string, agent: Agent) => void
}) {
  const allTasks = useWerkStore((s) => s.allTasks)
  const meta = metaFor(agent.role)
  const status = statusOf(agent, allTasks)
  const pos = positionFor(agent.role.toLowerCase(), index)
  const [dragOver, setDragOver] = useState(false)
  const working = status.state === 'working'

  return (
    <div
      className="absolute"
      style={{ left: `${pos.x}%`, top: `${pos.y}%`, transform: 'translate(-50%, -50%)' }}
    >
      <button
        onClick={() => onSelect(agent)}
        onDragOver={(e) => {
          e.preventDefault()
          setDragOver(true)
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragOver(false)
          const taskId = e.dataTransfer.getData('text/plain')
          if (taskId) onDropTask(taskId, agent)
        }}
        className={`${working ? 'werk-working ' : ''}group w-44 rounded-2xl border bg-white p-3 text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-md ${
          dragOver ? 'scale-105 border-indigo-400 ring-2 ring-indigo-300' : 'border-gray-200'
        }`}
        style={
          working
            ? ({ '--ring': `${meta.color}55`, borderColor: meta.color } as React.CSSProperties)
            : ({ '--ring': 'rgba(0,0,0,0)' } as React.CSSProperties)
        }
      >
        <div className="flex items-center justify-between">
          <div
            className="flex h-10 w-10 items-center justify-center rounded-xl text-xl"
            style={{ backgroundColor: meta.soft }}
          >
            {meta.glyph}
          </div>
          <span
            className="inline-block h-2.5 w-2.5 rounded-full"
            style={{ backgroundColor: STATE_DOT[status.state] }}
            title={STATE_LABEL[status.state]}
          />
        </div>
        <p className="mt-2 truncate text-sm font-semibold text-gray-900">{agent.name}</p>
        <p className="text-xs font-medium" style={{ color: meta.color }}>
          {meta.label}
        </p>

        {status.current ? (
          <div className="mt-2 rounded-md bg-gray-50 px-2 py-1">
            <p className="truncate text-[11px] text-gray-600">{status.current.title}</p>
            {working && (
              <div className="mt-1 h-1 overflow-hidden rounded bg-gray-200">
                <div
                  className="werk-shimmer h-full w-1/3 rounded"
                  style={{ backgroundColor: meta.color }}
                />
              </div>
            )}
          </div>
        ) : (
          <p className="mt-2 text-[11px] text-gray-500">Idle · drop a task here</p>
        )}
      </button>
    </div>
  )
}

// Stacked, tappable agent row for narrow screens — same information as a node,
// laid out for touch (full-width, comfortable target height) instead of a graph.
function AgentRow({ agent, onSelect }: { agent: Agent; onSelect: (a: Agent) => void }) {
  const allTasks = useWerkStore((s) => s.allTasks)
  const meta = metaFor(agent.role)
  const status = statusOf(agent, allTasks)
  const working = status.state === 'working'

  return (
    <button
      onClick={() => onSelect(agent)}
      className={`${working ? 'werk-working ' : ''}flex w-full items-center gap-3 rounded-xl border bg-white p-3 text-left shadow-sm transition active:scale-[0.99]`}
      style={
        working
          ? ({ '--ring': `${meta.color}55`, borderColor: meta.color } as React.CSSProperties)
          : ({ '--ring': 'rgba(0,0,0,0)' } as React.CSSProperties)
      }
    >
      <div
        className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-xl"
        style={{ backgroundColor: meta.soft }}
      >
        {meta.glyph}
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-gray-900">{agent.name}</p>
        <p className="truncate text-xs">
          <span className="font-medium" style={{ color: meta.color }}>
            {meta.label}
          </span>
          {status.current && <span className="text-gray-500"> · {status.current.title}</span>}
        </p>
      </div>
      <span className="flex shrink-0 items-center gap-1.5 text-xs text-gray-600">
        <span
          className="inline-block h-2.5 w-2.5 rounded-full"
          style={{ backgroundColor: STATE_DOT[status.state] }}
        />
        {STATE_LABEL[status.state]}
      </span>
    </button>
  )
}

export default function AgentCanvas() {
  const init = useWerkStore((s) => s.init)
  const agents = useWerkStore((s) => s.agents)
  const agentsLoading = useWerkStore((s) => s.agentsLoading)
  const allTasks = useWerkStore((s) => s.allTasks)
  const assignTask = useWerkStore((s) => s.assignTask)
  const fetchAgents = useWerkStore((s) => s.fetchAgents)
  const fetchAllTasks = useWerkStore((s) => s.fetchAllTasks)
  const projects = useWerkStore((s) => s.projects)
  const teamProjectId = useWerkStore((s) => s.teamProjectId)
  const setTeam = useWerkStore((s) => s.setTeam)

  const [selected, setSelected] = useState<Agent | null>(null)
  const [showNewTask, setShowNewTask] = useState(false)
  const [showSow, setShowSow] = useState(false)
  // Below lg the absolute-positioned graph would overlap; use a stacked list.
  const isWide = useMediaQuery('(min-width: 1024px)')

  useEffect(() => {
    init()
  }, [init])

  const unassigned = allTasks.filter((t) => !t.assigned_agent_id)
  const orderedAgents = [...agents].sort((a, b) => orderIndex(a.role) - orderIndex(b.role))
  const functional = orderedAgents.filter((a) => FUNCTIONAL_ROLES.has(a.role.toLowerCase()))
  const technical = orderedAgents.filter((a) => !FUNCTIONAL_ROLES.has(a.role.toLowerCase()))

  // role → status for coloring/animating the pipeline edges
  const statusByRole: Record<string, AgentState> = {}
  agents.forEach((a) => {
    statusByRole[a.role.toLowerCase()] = statusOf(a, allTasks).state
  })

  return (
    <div className="min-h-screen bg-gray-50">
      <style>{CANVAS_CSS}</style>
      <Header />
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Agent Canvas</h1>
            <p className="mt-1 text-sm text-gray-600">
              {isWide
                ? 'Your consulting team. Drag a task onto an agent to assign it, or click an agent to assign work and chat.'
                : 'Your consulting team. Tap an agent to assign work and chat; assign a queued task from the tray below.'}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <select
              value={teamProjectId ?? ''}
              onChange={(e) => setTeam(e.target.value || null)}
              className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 focus:border-indigo-500"
              aria-label="Which team to show on the canvas"
              title="Whose team to show on the canvas"
            >
              <option value="">Global roster</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  Team · {p.name}
                </option>
              ))}
            </select>
            <button
              onClick={() => {
                fetchAgents()
                fetchAllTasks()
              }}
              className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Refresh
            </button>
            <button
              onClick={() => setShowNewTask(true)}
              className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              + New task
            </button>
            <button
              onClick={() => setShowSow(true)}
              className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover"
            >
              Deploy from SOW
            </button>
          </div>
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-500">
          <span className="font-medium text-gray-600">
            {teamProjectId
              ? `Showing the deployed team for ${projects.find((p) => p.id === teamProjectId)?.name ?? 'this engagement'}`
              : 'Showing the global agent roster'}
          </span>
          <span className="text-gray-300">·</span>
          {(['idle', 'working', 'review'] as AgentState[]).map((s) => (
            <span key={s} className="flex items-center gap-1.5">
              <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: STATE_DOT[s] }} />
              {STATE_LABEL[s]}
            </span>
          ))}
        </div>

        {/* Canvas — interactive graph on wide screens, stacked list on narrow */}
        {agentsLoading && agents.length === 0 ? (
          <div className="mt-6 flex h-40 items-center justify-center rounded-2xl border border-gray-200 bg-white text-gray-500">
            Loading your agents…
          </div>
        ) : agents.length === 0 ? (
          <div className="mt-6 flex h-40 flex-col items-center justify-center rounded-2xl border border-gray-200 bg-white text-gray-500">
            <p>No agents found.</p>
            <p className="text-sm">The database seeds a full team on first run.</p>
          </div>
        ) : isWide ? (
          <div
            className="relative mt-6 h-[560px] w-full overflow-hidden rounded-2xl border border-gray-200 bg-white"
            style={{
              backgroundImage: 'radial-gradient(#e5e7eb 1px, transparent 1px)',
              backgroundSize: '22px 22px',
            }}
          >
            {/* pipeline edges */}
            <svg
              className="absolute inset-0 h-full w-full"
              viewBox="0 0 100 100"
              preserveAspectRatio="none"
            >
              {PIPELINE.map(([from, to]) => {
                const a = LAYOUT[from]
                const b = LAYOUT[to]
                if (!a || !b) return null
                const active = statusByRole[from] === 'working'
                const m = metaFor(from)
                return (
                  <line
                    key={`${from}-${to}`}
                    x1={a.x}
                    y1={a.y}
                    x2={b.x}
                    y2={b.y}
                    stroke={active ? m.color : '#d1d5db'}
                    strokeWidth={active ? 0.5 : 0.35}
                    strokeDasharray={active ? '1.6 1.4' : undefined}
                    className={active ? 'werk-edge-active' : undefined}
                    vectorEffect="non-scaling-stroke"
                  />
                )
              })}
            </svg>

            {/* group labels */}
            <span className="absolute left-4 top-3 rounded-full bg-indigo-50 px-2.5 py-1 text-[11px] font-medium text-indigo-600">
              Functional
            </span>
            <span className="absolute right-4 top-3 rounded-full bg-sky-50 px-2.5 py-1 text-[11px] font-medium text-sky-800">
              Technical
            </span>

            {/* agent nodes */}
            {agents.map((agent, i) => (
              <AgentNode
                key={agent.id}
                agent={agent}
                index={i}
                onSelect={setSelected}
                onDropTask={(taskId, a) => assignTask(taskId, a.id)}
              />
            ))}
          </div>
        ) : (
          <div className="mt-6 space-y-5">
            {[
              { label: 'Functional', list: functional },
              { label: 'Technical', list: technical },
            ]
              .filter((g) => g.list.length > 0)
              .map((g) => (
                <section key={g.label}>
                  <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
                    {g.label}
                  </h2>
                  <div className="space-y-2">
                    {g.list.map((agent) => (
                      <AgentRow key={agent.id} agent={agent} onSelect={setSelected} />
                    ))}
                  </div>
                </section>
              ))}
          </div>
        )}

        {/* Unassigned task tray */}
        <div className="mt-6 rounded-2xl border border-gray-200 bg-white p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-700">
              Unassigned tasks{' '}
              <span className="ml-1 rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                {unassigned.length}
              </span>
            </h2>
            <span className="hidden text-xs text-gray-500 lg:inline">drag a chip onto an agent ↑</span>
          </div>
          {unassigned.length === 0 ? (
            <p className="text-sm text-gray-500">
              No unassigned tasks. Click an agent to create one, or add tasks from the Projects tab.
            </p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {unassigned.map((t) => (
                <div
                  key={t.id}
                  draggable
                  onDragStart={(e) => e.dataTransfer.setData('text/plain', t.id)}
                  className="flex w-full items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-700 shadow-sm sm:w-auto lg:cursor-grab lg:active:cursor-grabbing"
                >
                  <span aria-hidden="true" className="hidden text-gray-300 lg:inline">⠿</span>
                  <span className="min-w-0 flex-1 truncate sm:max-w-[220px] sm:flex-none">{t.title}</span>
                  {/* keyboard/touch path — dragging isn't the only way to assign */}
                  <select
                    value=""
                    aria-label={`Assign "${t.title}" to an agent`}
                    onChange={(e) => e.target.value && assignTask(t.id, e.target.value)}
                    className="min-h-[44px] w-36 shrink-0 rounded border border-gray-200 bg-white px-2 py-1 text-xs text-gray-600 focus:border-indigo-500"
                  >
                    <option value="">Assign…</option>
                    {agents.map((a) => (
                      <option key={a.id} value={a.id}>
                        {metaFor(a.role).glyph} {a.name} · {metaFor(a.role).label}
                      </option>
                    ))}
                  </select>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>

      {selected && <AgentPanel agent={selected} onClose={() => setSelected(null)} />}
      {showNewTask && <NewTaskModal onClose={() => setShowNewTask(false)} />}
      {showSow && (
        <SowUploadModal
          onClose={() => setShowSow(false)}
          onDeployed={(pid) => {
            setShowSow(false)
            setTeam(pid) // switch the canvas to show the newly deployed team
          }}
        />
      )}
    </div>
  )
}
