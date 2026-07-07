import { useEffect, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useWerkStore, type Task } from '../stores/werkStore'
import Header from '../components/Header'

const STATUS_COLUMNS = ['backlog', 'in_progress', 'review', 'done'] as const

const STATUS_LABELS: Record<string, string> = {
  backlog: 'Backlog',
  in_progress: 'In Progress',
  review: 'Review',
  done: 'Done',
}

const STATUS_COLORS: Record<string, string> = {
  backlog: 'border-t-gray-400',
  in_progress: 'border-t-indigo-500',
  review: 'border-t-amber-500',
  done: 'border-t-green-500',
}

const STATUS_BG: Record<string, string> = {
  backlog: 'bg-gray-50 dark:bg-gray-800/50',
  in_progress: 'bg-indigo-50 dark:bg-indigo-900/20',
  review: 'bg-amber-50 dark:bg-amber-900/20',
  done: 'bg-green-50 dark:bg-green-900/20',
}

function TaskCard({
  task,
  onStatusChange,
}: {
  task: Task
  onStatusChange: (taskId: string, status: string) => void
}) {
  const nextActions: Record<string, { label: string; status: string; color: string }[]> = {
    backlog: [{ label: '→ Start', status: 'in_progress', color: 'bg-indigo-600 hover:bg-indigo-700' }],
    in_progress: [{ label: 'Request Review →', status: 'review', color: 'bg-amber-600 hover:bg-amber-700' }],
    review: [
      { label: '✓ Approve', status: 'done', color: 'bg-green-600 hover:bg-green-700' },
      { label: '↩ Reject', status: 'in_progress', color: 'bg-red-500 hover:bg-red-600' },
    ],
    done: [],
    blocked: [{ label: '↩ Unblock', status: 'in_progress', color: 'bg-gray-500 hover:bg-gray-600' }],
  }

  const actions = nextActions[task.status] ?? []

  return (
    <div
      className={`rounded-lg border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-700 dark:bg-gray-800`}
    >
      <div className="flex items-start justify-between gap-2">
        <h4 className="text-sm font-semibold text-gray-900 dark:text-white">{task.title}</h4>
        {task.priority > 0 && (
          <span className="shrink-0 rounded bg-red-100 px-1.5 py-0.5 text-xs font-medium text-red-700 dark:bg-red-900 dark:text-red-300">
            P{task.priority}
          </span>
        )}
      </div>
      {task.description && (
        <p className="mt-1 text-xs text-gray-600 line-clamp-2 dark:text-gray-400">
          {task.description}
        </p>
      )}
      {task.assigned_agent_id && (
        <p className="mt-2 text-xs text-gray-500 dark:text-gray-500">
          Agent: <span className="font-mono">{task.assigned_agent_id.slice(0, 8)}...</span>
        </p>
      )}
      {task.result && (
        <p className="mt-2 text-xs text-green-700 dark:text-green-400">
          Result: {task.result}
        </p>
      )}

      {/* Action buttons */}
      {actions.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {actions.map((action) => (
            <button
              key={action.status}
              onClick={() => onStatusChange(task.id, action.status)}
              className={`rounded px-2.5 py-1 text-xs font-medium text-white transition ${action.color}`}
            >
              {action.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function KanbanColumn({
  status,
  tasks,
  onStatusChange,
}: {
  status: string
  tasks: Task[]
  onStatusChange: (taskId: string, status: string) => void
}) {
  return (
    <div className={`rounded-lg border-t-4 ${STATUS_COLORS[status] || 'border-t-gray-400'} ${STATUS_BG[status]}`}>
      <div className="flex items-center justify-between p-4 pb-2">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
          {STATUS_LABELS[status] || status}
        </h3>
        <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-gray-200 text-xs font-medium text-gray-600 dark:bg-gray-700 dark:text-gray-400">
          {tasks.length}
        </span>
      </div>
      <div className="space-y-3 p-4 pt-2">
        {tasks.length === 0 ? (
          <p className="py-8 text-center text-xs text-gray-400 dark:text-gray-500">No tasks</p>
        ) : (
          tasks.map((task) => (
            <TaskCard key={task.id} task={task} onStatusChange={onStatusChange} />
          ))
        )}
      </div>
    </div>
  )
}

function ActivityFeed({ tasks }: { tasks: Task[] }) {
  // Build a simple activity log from task changes
  const recent = [...tasks]
    .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
    .slice(0, 10)

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Activity</h3>
      <div className="mt-3 space-y-2">
        {recent.length === 0 ? (
          <p className="py-4 text-center text-xs text-gray-400">No activity yet</p>
        ) : (
          recent.map((task) => (
            <div key={task.id} className="flex items-start gap-2 text-xs">
              <span
                className={`mt-0.5 inline-block h-2 w-2 shrink-0 rounded-full ${
                  task.status === 'done'
                    ? 'bg-green-500'
                    : task.status === 'review'
                      ? 'bg-amber-500'
                      : task.status === 'in_progress'
                        ? 'bg-indigo-500'
                        : 'bg-gray-400'
                }`}
              />
              <div>
                <p className="text-gray-700 dark:text-gray-300">
                  <span className="font-medium">{task.title}</span> → {STATUS_LABELS[task.status] || task.status}
                </p>
                <p className="text-gray-400 dark:text-gray-500">
                  {new Date(task.updated_at).toLocaleTimeString()}
                </p>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export function ProjectView() {
  const { id } = useParams<{ id: string }>()
  const tasks = useWerkStore((s) => s.tasks)
  const tasksLoading = useWerkStore((s) => s.tasksLoading)
  const projects = useWerkStore((s) => s.projects)
  const fetchTasks = useWerkStore((s) => s.fetchTasks)
  const setSelectedProject = useWerkStore((s) => s.setSelectedProject)
  const updateTaskStatus = useWerkStore((s) => s.updateTaskStatus)
  const connectWebSocket = useWerkStore((s) => s.connectWebSocket)
  const runWorkflow = useWerkStore((s) => s.runWorkflow)
  const workflowRunning = useWerkStore((s) => s.workflowRunning)
  const workflowReview = useWerkStore((s) => s.workflowReview)
  const approveWorkflow = useWerkStore((s) => s.approveWorkflow)
  const rejectWorkflow = useWerkStore((s) => s.rejectWorkflow)
  const workflowProdReview = useWerkStore((s) => s.workflowProdReview)
  const approveProd = useWerkStore((s) => s.approveProd)
  const rejectProd = useWerkStore((s) => s.rejectProd)
  const statusReport = useWerkStore((s) => s.statusReport)
  const statusReportLoading = useWerkStore((s) => s.statusReportLoading)
  const generateStatusReport = useWerkStore((s) => s.generateStatusReport)
  const artifacts = useWerkStore((s) => s.artifacts)
  const fetchArtifacts = useWerkStore((s) => s.fetchArtifacts)
  const downloadArtifact = useWerkStore((s) => s.downloadArtifact)
  const workspaceFiles = useWerkStore((s) => s.workspaceFiles)
  const fetchWorkspace = useWerkStore((s) => s.fetchWorkspace)
  const testResult = useWerkStore((s) => s.testResult)
  const runTests = useWerkStore((s) => s.runTests)
  const testsRunning = useWerkStore((s) => s.testsRunning)
  const installResult = useWerkStore((s) => s.installResult)
  const installDeps = useWerkStore((s) => s.installDeps)
  const installing = useWerkStore((s) => s.installing)
  const healthResult = useWerkStore((s) => s.healthResult)
  const healthCheck = useWerkStore((s) => s.healthCheck)
  const healthChecking = useWerkStore((s) => s.healthChecking)

  useEffect(() => {
    if (id) {
      setSelectedProject(id)
      fetchTasks(id)
      fetchArtifacts(id)
      fetchWorkspace(id)
      connectWebSocket()
    }
    return () => setSelectedProject(null)
  }, [id, setSelectedProject, fetchTasks, fetchArtifacts, fetchWorkspace, connectWebSocket])

  const project = projects.find((p) => p.id === id)

  const handleStatusChange = useCallback(
    async (taskId: string, newStatus: string) => {
      const task = tasks.find((t) => t.id === taskId)

      // If moving to review from done, ask for feedback
      if (newStatus === 'done' && task?.status === 'review') {
        const result = prompt('Sign-off result / feedback:')
        await updateTaskStatus(taskId, newStatus, result || 'Approved')
      } else if (newStatus === 'in_progress' && task?.status === 'review') {
        const result = prompt('Rejection feedback:')
        await updateTaskStatus(taskId, newStatus, result || 'Rework requested')
      } else {
        await updateTaskStatus(taskId, newStatus)
      }

      // Refresh tasks
      if (id) fetchTasks(id)
    },
    [tasks, updateTaskStatus, fetchTasks, id],
  )

  const groupedTasks = STATUS_COLUMNS.reduce(
    (acc, status) => {
      acc[status] = tasks.filter((t) => t.status === status)
      return acc
    },
    {} as Record<string, Task[]>,
  )

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Header />
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {/* Breadcrumb */}
        <div className="mb-6">
          <Link
            to="/projects"
            className="text-sm text-indigo-600 hover:text-indigo-800 dark:text-indigo-400"
          >
            ← Projects
          </Link>
          <div className="mt-1 flex flex-wrap items-center justify-between gap-3">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              {project?.name || `Project ${id?.slice(0, 8)}`}
            </h1>
            <div className="flex gap-2">
              <button
                onClick={() => id && generateStatusReport(id)}
                disabled={statusReportLoading}
                className="rounded-md border border-indigo-300 bg-white px-4 py-2 text-sm font-medium text-indigo-700 hover:bg-indigo-50 disabled:opacity-50"
              >
                {statusReportLoading ? 'PMO writing…' : '🧭 Status report'}
              </button>
              <button
                onClick={() => id && runWorkflow(id, project?.name || `Project ${id.slice(0, 8)}`)}
                disabled={!id || (!!id && workflowRunning[id])}
                className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {id && workflowRunning[id] ? 'Running pipeline…' : '▶ Run full workflow'}
              </button>
            </div>
          </div>
          {project && (
            <span className="mt-1 inline-flex items-center rounded-full bg-indigo-100 px-2.5 py-0.5 text-xs font-medium text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200">
              {project.status}
            </span>
          )}
          {id && workflowRunning[id] && (
            <div className="mt-3 rounded-lg border border-indigo-100 bg-indigo-50 px-4 py-3 text-sm text-indigo-700 dark:border-indigo-900 dark:bg-indigo-900/20 dark:text-indigo-300">
              The agents are working through the pipeline (Requirements → UX → Architecture →
              Development → Testing). On a local model this can take a few minutes — stage outputs
              appear as completed tasks below as they finish.
            </div>
          )}
          {id && workflowReview[id] && (
            <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 dark:border-amber-900 dark:bg-amber-900/20">
              <p className="text-sm font-medium text-amber-800 dark:text-amber-200">
                Review gate — your sign-off is needed
              </p>
              <p className="mt-1 text-sm text-amber-700 dark:text-amber-300">
                The agents finished Requirements through Testing. Review the stage outputs below,
                then approve to deploy to the <strong>test</strong> environment, or reject for rework.
              </p>
              <div className="mt-3 flex gap-2">
                <button
                  onClick={() => id && approveWorkflow(id)}
                  className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700"
                >
                  ✓ Approve & deploy to test
                </button>
                <button
                  onClick={() => {
                    const fb = prompt('Reason for rejection (optional):') ?? ''
                    if (id) rejectWorkflow(id, fb)
                  }}
                  className="rounded-md border border-amber-300 bg-white px-4 py-2 text-sm font-medium text-amber-800 hover:bg-amber-50"
                >
                  Reject
                </button>
              </div>
            </div>
          )}
          {id && workflowProdReview[id] && (
            <div className="mt-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 dark:border-red-900 dark:bg-red-900/20">
              <p className="text-sm font-medium text-red-800 dark:text-red-200">
                Production gate — sign-off required
              </p>
              <p className="mt-1 text-sm text-red-700 dark:text-red-300">
                Deployed to the <strong>test</strong> environment and verified healthy. Approve to
                have the Release Agent deploy to <strong>production</strong>, or hold.
              </p>
              <div className="mt-3 flex gap-2">
                <button
                  onClick={() => id && approveProd(id)}
                  className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
                >
                  🏭 Approve & deploy to production
                </button>
                <button
                  onClick={() => {
                    const fb = prompt('Reason for holding production (optional):') ?? ''
                    if (id) rejectProd(id, fb)
                  }}
                  className="rounded-md border border-red-300 bg-white px-4 py-2 text-sm font-medium text-red-800 hover:bg-red-50"
                >
                  Hold
                </button>
              </div>
            </div>
          )}
          {statusReport && (
            <div className="mt-3 rounded-lg border border-indigo-100 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
              <h3 className="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
                🧭 PMO status report
              </h3>
              <pre className="max-h-72 overflow-auto whitespace-pre-wrap text-xs leading-relaxed text-gray-700 dark:text-gray-300">
                {statusReport}
              </pre>
            </div>
          )}
        </div>

        {/* Kanban Board + Activity */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
          {/* Kanban columns */}
          <div className="lg:col-span-3">
            {tasksLoading ? (
              <div className="grid grid-cols-4 gap-4">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="h-64 animate-pulse rounded-lg bg-gray-200 dark:bg-gray-700" />
                ))}
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {STATUS_COLUMNS.map((status) => (
                  <KanbanColumn
                    key={status}
                    status={status}
                    tasks={groupedTasks[status] || []}
                    onStatusChange={handleStatusChange}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Activity Feed Sidebar */}
          <div className="lg:col-span-1">
            <ActivityFeed tasks={tasks} />

            {/* Quick Stats */}
            <div className="mt-4 rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Stats</h3>
              <div className="mt-3 space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-gray-500">Total Tasks</span>
                  <span className="font-medium text-gray-900 dark:text-white">{tasks.length}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-gray-500">Completed</span>
                  <span className="font-medium text-green-600 dark:text-green-400">
                    {tasks.filter((t) => t.status === 'done').length}
                  </span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-gray-500">In Progress</span>
                  <span className="font-medium text-indigo-600 dark:text-indigo-400">
                    {tasks.filter((t) => t.status === 'in_progress').length}
                  </span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-gray-500">Review</span>
                  <span className="font-medium text-amber-600 dark:text-amber-400">
                    {tasks.filter((t) => t.status === 'review').length}
                  </span>
                </div>
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
                  <div
                    className="h-full rounded-full bg-green-500 transition-all"
                    style={{
                      width: `${tasks.length > 0 ? (tasks.filter((t) => t.status === 'done').length / tasks.length) * 100 : 0}%`,
                    }}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Artifacts — downloadable deliverables the agents produced */}
        <div className="mt-8 rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
              Artifacts{' '}
              <span className="ml-1 rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500 dark:bg-gray-700">
                {artifacts.length}
              </span>
            </h2>
            <span className="text-xs text-gray-400">deliverables produced by the agents</span>
          </div>
          {artifacts.length === 0 ? (
            <p className="text-sm text-gray-400">
              No artifacts yet. Run an agent task or the full workflow to generate deliverables.
            </p>
          ) : (
            <ul className="divide-y divide-gray-100 dark:divide-gray-700">
              {artifacts.map((a) => (
                <li key={a.id} className="flex items-center justify-between gap-3 py-2">
                  <div className="flex min-w-0 items-center gap-2">
                    <span className="rounded bg-indigo-50 px-1.5 py-0.5 text-[10px] font-medium uppercase text-indigo-600 dark:bg-indigo-900/30">
                      {a.file_type || 'file'}
                    </span>
                    <span className="truncate text-sm text-gray-800 dark:text-gray-200">{a.filename}</span>
                    <span className="shrink-0 text-xs text-gray-400">{a.size} chars</span>
                  </div>
                  <button
                    onClick={() => downloadArtifact(a.id, a.filename)}
                    className="shrink-0 rounded-md border border-gray-300 bg-white px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
                  >
                    Download
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Workspace — real code the Developer wrote, run by the Tester */}
        <div className="mt-8 rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
              Workspace{' '}
              <span className="ml-1 rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500 dark:bg-gray-700">
                {workspaceFiles.length} files
              </span>
            </h2>
            <div className="flex gap-2">
              <button
                onClick={() => id && installDeps(id)}
                disabled={installing}
                className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
              >
                {installing ? 'Installing…' : 'Install deps'}
              </button>
              <button
                onClick={() => id && healthCheck(id)}
                disabled={healthChecking}
                className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
              >
                {healthChecking ? 'Checking…' : 'Health check'}
              </button>
              <button
                onClick={() => id && runTests(id)}
                disabled={testsRunning}
                className="rounded-md bg-gray-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-gray-700 disabled:opacity-50 dark:bg-gray-100 dark:text-gray-900"
              >
                {testsRunning ? 'Running tests…' : '▶ Run tests'}
              </button>
            </div>
          </div>
          {workspaceFiles.length === 0 ? (
            <p className="text-sm text-gray-400">
              No code yet. When the Developer agent runs a task, the files it writes appear here;
              the Tester agent runs them.
            </p>
          ) : (
            <ul className="mb-3 flex flex-wrap gap-2">
              {workspaceFiles.map((f) => (
                <li key={f.path} className="rounded-md bg-gray-50 px-2 py-1 font-mono text-xs text-gray-700 dark:bg-gray-700 dark:text-gray-200">
                  {f.path} <span className="text-gray-400">· {f.size}B</span>
                </li>
              ))}
            </ul>
          )}
          {installResult && (
            <p className={`mt-2 text-xs ${installResult.installed ? 'text-emerald-600' : 'text-amber-600'}`}>
              {installResult.installed ? 'Dependencies installed. ' : ''}
              {installResult.output}
            </p>
          )}
          {healthResult && (
            <div className="mt-2">
              {healthResult.enabled === false ? (
                <p className="text-xs text-amber-600">{healthResult.output}</p>
              ) : (
                <>
                  <span
                    className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                      healthResult.healthy
                        ? 'bg-emerald-100 text-emerald-700'
                        : healthResult.healthy === false
                          ? 'bg-red-100 text-red-700'
                          : 'bg-gray-100 text-gray-600'
                    }`}
                  >
                    {healthResult.healthy
                      ? 'Environment healthy ✓'
                      : healthResult.healthy === false
                        ? 'Environment unhealthy ✗'
                        : 'No runnable app'}
                  </span>
                  <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap rounded-md bg-gray-900 p-3 text-[11px] leading-relaxed text-gray-100">
                    {healthResult.output}
                  </pre>
                </>
              )}
            </div>
          )}
          {testResult && (
            <div className="mt-2">
              {testResult.enabled === false ? (
                <p className="text-xs text-amber-600">{testResult.output}</p>
              ) : (
                <>
                  <span
                    className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                      testResult.passed
                        ? 'bg-emerald-100 text-emerald-700'
                        : testResult.passed === false
                          ? 'bg-red-100 text-red-700'
                          : 'bg-gray-100 text-gray-600'
                    }`}
                  >
                    {testResult.passed ? 'Tests passed ✓' : testResult.passed === false ? 'Tests failed ✗' : 'No tests'}
                  </span>
                  <pre className="mt-2 max-h-60 overflow-auto whitespace-pre-wrap rounded-md bg-gray-900 p-3 text-[11px] leading-relaxed text-gray-100">
                    {testResult.output}
                  </pre>
                </>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

export default ProjectView