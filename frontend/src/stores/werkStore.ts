import { create } from 'zustand'

export interface Project {
  id: string
  name: string
  description: string | null
  status: string
  config: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface Task {
  id: string
  project_id: string | null
  title: string
  description: string | null
  status: string
  assigned_agent_id: string | null
  parent_task_id: string | null
  priority: number
  artifacts: Record<string, unknown>[]
  result: string | null
  created_at: string
  updated_at: string
}

export interface AgentExample {
  input?: string
  output: string
}

export interface Agent {
  id: string
  name: string
  type: string // functional | technical
  role: string
  project_id?: string | null
  capabilities: string[]
  status: string
  created_at: string
  instructions?: string
  instructions_custom?: boolean
  examples?: AgentExample[]
}

export interface PlannedAgent {
  role: string
  name: string
  rationale: string
  instructions: string
}

export interface ParamDefinition {
  key: string
  label: string
  type: string // number | text | select | list
  options?: string[]
  default?: unknown
  keywords?: string[]
  staffing?: unknown[]
}

export type ParamValues = Record<string, unknown>

export interface SowPlan {
  project_name: string
  summary: string
  parameters: ParamValues
  definitions: ParamDefinition[]
  agents: PlannedAgent[]
  source: string // 'llm' | 'heuristic'
  filename: string
  char_count: number
}

export interface ArtifactMeta {
  id: string
  project_id: string | null
  task_id: string | null
  agent_id: string | null
  file_path: string
  filename: string
  file_type: string | null
  size: number
  metadata: Record<string, unknown>
  created_at: string | null
}

export interface WorkspaceFile {
  path: string
  size: number
}

export interface TestResult {
  enabled?: boolean
  passed: boolean | null
  output: string
}

export interface InstallResult {
  enabled?: boolean
  installed: boolean
  output: string
}

export interface HealthResult {
  enabled?: boolean
  healthy: boolean | null
  output: string
  port?: number
  entrypoint?: string
}

export interface ChatMessage {
  from: 'user' | 'agent'
  text: string
  source?: string // 'llm' | 'persona'
}

export interface WsEvent {
  type: string
  payload: Record<string, unknown>
}

export interface RequirementItem {
  id: string
  text: string
}

export interface AnalysisResult {
  agent_id: string
  agent_name: string
  source: string // 'llm' | 'heuristic'
  filename: string
  char_count: number
  preview: string
  requirements: RequirementItem[]
}

interface WerkStore {
  // Auth
  token: string | null
  authReady: boolean
  login: () => Promise<void>

  // Bootstrap
  init: () => Promise<void>

  // Projects
  projects: Project[]
  projectsLoading: boolean
  fetchProjects: () => Promise<void>

  // Agents
  agents: Agent[]
  agentsLoading: boolean
  fetchAgents: () => Promise<void>
  teamProjectId: string | null // null = global roster; set = a project's deployed team
  setTeam: (projectId: string | null) => Promise<void>

  // SOW intake
  analyzeSow: (file: File) => Promise<SowPlan | null>
  deriveTeam: (parameters: ParamValues, summary: string) => Promise<PlannedAgent[] | null>
  deploySow: (
    plan: {
      project_name: string
      summary: string
      parameters: ParamValues
      agents: PlannedAgent[]
      create_kickoff_tasks: boolean
    },
  ) => Promise<string | null>
  fetchParamDefinitions: () => Promise<ParamDefinition[] | null>
  saveParamDefinitions: (definitions: ParamDefinition[]) => Promise<boolean>

  // Tasks (per-project, used by Kanban) + all tasks (used by canvas)
  tasks: Task[]
  tasksLoading: boolean
  fetchTasks: (projectId: string) => Promise<void>
  allTasks: Task[]
  fetchAllTasks: () => Promise<void>

  // Selected project
  selectedProjectId: string | null
  setSelectedProject: (id: string | null) => void

  // WebSocket
  wsConnected: boolean
  wsEvents: WsEvent[]
  connectWebSocket: () => void
  disconnectWebSocket: () => void

  // Task / agent actions
  updateTaskStatus: (taskId: string, status: string, result?: string) => Promise<boolean>
  assignTask: (taskId: string, agentId: string) => Promise<boolean>
  createTask: (
    projectId: string,
    title: string,
    agentId?: string,
    description?: string,
  ) => Promise<boolean>
  createTasksBulk: (projectId: string, titles: string[], agentId?: string) => Promise<number>
  startTask: (taskId: string) => Promise<boolean>
  runTask: (taskId: string) => Promise<boolean>

  // Projects
  createProject: (name: string, description?: string) => Promise<Project | null>

  // Agent tuning
  saveInstructions: (agentId: string, instructions: string) => Promise<Agent | null>
  saveExamples: (agentId: string, examples: AgentExample[]) => Promise<Agent | null>

  // Orchestrator workflow (autonomous 7-stage pipeline)
  workflowRunning: Record<string, boolean>
  workflowReview: Record<string, boolean>
  runWorkflow: (projectId: string, projectName: string) => Promise<boolean>
  approveWorkflow: (projectId: string, feedback?: string) => Promise<boolean>
  rejectWorkflow: (projectId: string, feedback?: string) => Promise<boolean>
  workflowProdReview: Record<string, boolean>
  approveProd: (projectId: string, feedback?: string) => Promise<boolean>
  rejectProd: (projectId: string, feedback?: string) => Promise<boolean>

  // PMO status report
  statusReport: string | null
  statusReportLoading: boolean
  generateStatusReport: (projectId: string) => Promise<void>

  // Document analysis (requirements upload → functional requirements)
  analyzeDocument: (
    agentId: string,
    file: File,
    instruction?: string,
  ) => Promise<AnalysisResult | null>
  downloadRequirementsDoc: (
    agentId: string,
    requirements: string[],
    title: string,
  ) => Promise<boolean>

  // Artifacts (deliverables agents produce)
  artifacts: ArtifactMeta[]
  fetchArtifacts: (projectId: string) => Promise<void>
  downloadArtifact: (id: string, filename: string) => Promise<void>

  // Execution workspace (Developer writes files, Tester runs them)
  workspaceFiles: WorkspaceFile[]
  fetchWorkspace: (projectId: string) => Promise<void>
  testResult: TestResult | null
  runTests: (projectId: string) => Promise<void>
  testsRunning: boolean
  installResult: InstallResult | null
  installDeps: (projectId: string) => Promise<void>
  installing: boolean
  healthResult: HealthResult | null
  healthCheck: (projectId: string) => Promise<void>
  healthChecking: boolean

  // Chat
  chatHistory: Record<string, ChatMessage[]>
  chat: (agentId: string, message: string) => Promise<void>
  chatPending: boolean
}

const API_BASE = '/api/v1'
const WS_URL = `ws://${window.location.hostname}:8000/ws/events`

// Module-level token so authFetch can read it without prop drilling.
let authToken: string | null = null

async function doLogin(): Promise<string | null> {
  try {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: 'admin', password: 'admin123' }),
    })
    if (!res.ok) throw new Error(`login HTTP ${res.status}`)
    const data = await res.json()
    authToken = data.access_token ?? null
    return authToken
  } catch (err) {
    console.error('Auto-login failed:', err)
    return null
  }
}

async function authFetch(path: string, opts: RequestInit = {}, retry = true): Promise<Response> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(opts.headers as Record<string, string> | undefined),
  }
  if (authToken) headers['Authorization'] = `Bearer ${authToken}`
  const res = await fetch(`${API_BASE}${path}`, { ...opts, headers })
  if (res.status === 401 && retry) {
    await doLogin()
    return authFetch(path, opts, false)
  }
  return res
}

export const useWerkStore = create<WerkStore>((set, get) => ({
  token: null,
  authReady: false,

  projects: [],
  projectsLoading: false,
  agents: [],
  agentsLoading: false,
  tasks: [],
  tasksLoading: false,
  allTasks: [],
  selectedProjectId: null,
  wsConnected: false,
  wsEvents: [],
  chatHistory: {},
  chatPending: false,
  workflowRunning: {},
  workflowReview: {},
  workflowProdReview: {},
  statusReport: null,
  statusReportLoading: false,
  artifacts: [],
  workspaceFiles: [],
  testResult: null,
  testsRunning: false,
  installResult: null,
  installing: false,
  healthResult: null,
  healthChecking: false,

  login: async () => {
    const t = await doLogin()
    set({ token: t, authReady: true })
  },

  init: async () => {
    if (!get().token) await get().login()
    await Promise.all([get().fetchAgents(), get().fetchAllTasks(), get().fetchProjects()])
    if (!get().wsConnected) get().connectWebSocket()
  },

  fetchProjects: async () => {
    set({ projectsLoading: true })
    try {
      const res = await authFetch('/projects/')
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      set({ projects: data.projects ?? [], projectsLoading: false })
    } catch (err) {
      console.error('Failed to fetch projects:', err)
      set({ projectsLoading: false })
    }
  },

  teamProjectId: null,

  fetchAgents: async () => {
    set({ agentsLoading: true })
    try {
      const pid = get().teamProjectId
      const qs = pid ? `?project_id=${pid}` : ''
      const res = await authFetch(`/agents/${qs}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      set({ agents: data.agents ?? [], agentsLoading: false })
    } catch (err) {
      console.error('Failed to fetch agents:', err)
      set({ agentsLoading: false })
    }
  },

  setTeam: async (projectId) => {
    set({ teamProjectId: projectId })
    await get().fetchAgents()
  },

  analyzeSow: async (file) => {
    try {
      if (!authToken) await doLogin()
      const form = new FormData()
      form.append('file', file)
      const headers: Record<string, string> = {}
      if (authToken) headers['Authorization'] = `Bearer ${authToken}`
      const res = await fetch(`${API_BASE}/sow/analyze`, { method: 'POST', headers, body: form })
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}))
        throw new Error(detail.detail || `HTTP ${res.status}`)
      }
      return (await res.json()) as SowPlan
    } catch (err) {
      console.error('Failed to analyze SOW:', err)
      throw err
    }
  },

  deriveTeam: async (parameters, summary) => {
    try {
      const res = await authFetch('/sow/team', {
        method: 'POST',
        body: JSON.stringify({ parameters, summary }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      return (data.agents ?? []) as PlannedAgent[]
    } catch (err) {
      console.error('Failed to derive team:', err)
      return null
    }
  },

  fetchParamDefinitions: async () => {
    try {
      const res = await authFetch('/sow/parameters/definitions')
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      return (data.definitions ?? []) as ParamDefinition[]
    } catch (err) {
      console.error('Failed to fetch parameter definitions:', err)
      return null
    }
  },

  saveParamDefinitions: async (definitions) => {
    try {
      const res = await authFetch('/sow/parameters/definitions', {
        method: 'PUT',
        body: JSON.stringify({ definitions }),
      })
      return res.ok
    } catch (err) {
      console.error('Failed to save parameter definitions:', err)
      return false
    }
  },

  deploySow: async (plan) => {
    try {
      const res = await authFetch('/sow/deploy', { method: 'POST', body: JSON.stringify(plan) })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      await get().fetchProjects()
      await get().fetchAllTasks()
      return data.project_id as string
    } catch (err) {
      console.error('Failed to deploy SOW:', err)
      return null
    }
  },

  fetchTasks: async (projectId: string) => {
    set({ tasksLoading: true })
    try {
      const res = await authFetch(`/tasks/?project_id=${projectId}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      set({ tasks: data.tasks ?? [], tasksLoading: false })
    } catch (err) {
      console.error('Failed to fetch tasks:', err)
      set({ tasksLoading: false })
    }
  },

  fetchAllTasks: async () => {
    try {
      const res = await authFetch('/tasks/')
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      set({ allTasks: data.tasks ?? [] })
    } catch (err) {
      console.error('Failed to fetch all tasks:', err)
    }
  },

  setSelectedProject: (id) => set({ selectedProjectId: id }),

  updateTaskStatus: async (taskId, status, result) => {
    try {
      const body: Record<string, unknown> = { status }
      if (result) body.result = result
      const res = await authFetch(`/tasks/${taskId}`, { method: 'PUT', body: JSON.stringify(body) })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const updated = await res.json()
      set((state) => ({
        tasks: state.tasks.map((t) => (t.id === taskId ? { ...t, ...updated } : t)),
        allTasks: state.allTasks.map((t) => (t.id === taskId ? { ...t, ...updated } : t)),
      }))
      return true
    } catch (err) {
      console.error('Failed to update task:', err)
      return false
    }
  },

  assignTask: async (taskId, agentId) => {
    try {
      const res = await authFetch(`/tasks/${taskId}`, {
        method: 'PUT',
        body: JSON.stringify({ assigned_agent_id: agentId }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      await get().fetchAllTasks()
      return true
    } catch (err) {
      console.error('Failed to assign task:', err)
      return false
    }
  },

  createTask: async (projectId, title, agentId, description) => {
    try {
      const body: Record<string, unknown> = { project_id: projectId, title }
      if (agentId) body.assigned_agent_id = agentId
      if (description) body.description = description
      const res = await authFetch('/tasks/', { method: 'POST', body: JSON.stringify(body) })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      await get().fetchAllTasks()
      return true
    } catch (err) {
      console.error('Failed to create task:', err)
      return false
    }
  },

  createTasksBulk: async (projectId, titles, agentId) => {
    let created = 0
    for (const title of titles) {
      if (!title.trim()) continue
      try {
        const body: Record<string, unknown> = { project_id: projectId, title: title.trim() }
        if (agentId) body.assigned_agent_id = agentId
        const res = await authFetch('/tasks/', { method: 'POST', body: JSON.stringify(body) })
        if (res.ok) created += 1
      } catch (err) {
        console.error('Failed to create task in bulk:', err)
      }
    }
    await get().fetchAllTasks()
    return created
  },

  createProject: async (name, description) => {
    try {
      const body: Record<string, unknown> = { name }
      if (description) body.description = description
      const res = await authFetch('/projects/', { method: 'POST', body: JSON.stringify(body) })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const project = (await res.json()) as Project
      await get().fetchProjects()
      return project
    } catch (err) {
      console.error('Failed to create project:', err)
      return null
    }
  },

  runWorkflow: async (projectId, projectName) => {
    set((s) => ({
      workflowRunning: { ...s.workflowRunning, [projectId]: true },
      workflowReview: { ...s.workflowReview, [projectId]: false },
    }))
    try {
      const res = await authFetch(
        `/orchestrator/projects/${projectId}/run?project_name=${encodeURIComponent(projectName)}`,
        { method: 'POST' },
      )
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      return true
    } catch (err) {
      console.error('Failed to start workflow:', err)
      set((s) => ({ workflowRunning: { ...s.workflowRunning, [projectId]: false } }))
      return false
    }
  },

  approveWorkflow: async (projectId, feedback) => {
    set((s) => ({
      workflowReview: { ...s.workflowReview, [projectId]: false },
      workflowRunning: { ...s.workflowRunning, [projectId]: true },
    }))
    try {
      const res = await authFetch(
        `/orchestrator/projects/${projectId}/review/approve?feedback=${encodeURIComponent(feedback ?? '')}`,
        { method: 'POST' },
      )
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      return true
    } catch (err) {
      console.error('Failed to approve workflow:', err)
      set((s) => ({ workflowRunning: { ...s.workflowRunning, [projectId]: false } }))
      return false
    }
  },

  rejectWorkflow: async (projectId, feedback) => {
    set((s) => ({
      workflowReview: { ...s.workflowReview, [projectId]: false },
      workflowRunning: { ...s.workflowRunning, [projectId]: false },
    }))
    try {
      const res = await authFetch(
        `/orchestrator/projects/${projectId}/review/reject?feedback=${encodeURIComponent(feedback ?? 'Rework requested')}`,
        { method: 'POST' },
      )
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      return true
    } catch (err) {
      console.error('Failed to reject workflow:', err)
      return false
    }
  },

  approveProd: async (projectId, feedback) => {
    set((s) => ({
      workflowProdReview: { ...s.workflowProdReview, [projectId]: false },
      workflowRunning: { ...s.workflowRunning, [projectId]: true },
    }))
    try {
      const res = await authFetch(
        `/orchestrator/projects/${projectId}/prod/approve?feedback=${encodeURIComponent(feedback ?? '')}`,
        { method: 'POST' },
      )
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      return true
    } catch (err) {
      console.error('Failed to approve production:', err)
      set((s) => ({ workflowRunning: { ...s.workflowRunning, [projectId]: false } }))
      return false
    }
  },

  rejectProd: async (projectId, feedback) => {
    set((s) => ({
      workflowProdReview: { ...s.workflowProdReview, [projectId]: false },
      workflowRunning: { ...s.workflowRunning, [projectId]: false },
    }))
    try {
      const res = await authFetch(
        `/orchestrator/projects/${projectId}/prod/reject?feedback=${encodeURIComponent(feedback ?? 'Production deploy held')}`,
        { method: 'POST' },
      )
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      return true
    } catch (err) {
      console.error('Failed to reject production:', err)
      return false
    }
  },

  generateStatusReport: async (projectId) => {
    set({ statusReportLoading: true })
    try {
      const res = await authFetch(`/projects/${projectId}/status-report`, { method: 'POST' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      set({ statusReport: data.report ?? '', statusReportLoading: false })
      await get().fetchArtifacts(projectId)
    } catch (err) {
      console.error('Failed to generate status report:', err)
      set({ statusReportLoading: false })
    }
  },

  saveInstructions: async (agentId, instructions) => {
    try {
      const res = await authFetch(`/agents/${agentId}/instructions`, {
        method: 'PUT',
        body: JSON.stringify({ instructions }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const updated = (await res.json()) as Agent
      set((s) => ({ agents: s.agents.map((a) => (a.id === agentId ? { ...a, ...updated } : a)) }))
      return updated
    } catch (err) {
      console.error('Failed to save instructions:', err)
      return null
    }
  },

  saveExamples: async (agentId, examples) => {
    try {
      const res = await authFetch(`/agents/${agentId}/examples`, {
        method: 'PUT',
        body: JSON.stringify({ examples }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const updated = (await res.json()) as Agent
      set((s) => ({ agents: s.agents.map((a) => (a.id === agentId ? { ...a, ...updated } : a)) }))
      return updated
    } catch (err) {
      console.error('Failed to save examples:', err)
      return null
    }
  },

  analyzeDocument: async (agentId, file, instruction) => {
    try {
      if (!authToken) await doLogin()
      const form = new FormData()
      form.append('file', file)
      if (instruction) form.append('instruction', instruction)
      const headers: Record<string, string> = {}
      if (authToken) headers['Authorization'] = `Bearer ${authToken}`
      // NOTE: do not set Content-Type — the browser adds the multipart boundary.
      const res = await fetch(`${API_BASE}/agents/${agentId}/analyze`, {
        method: 'POST',
        headers,
        body: form,
      })
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}))
        throw new Error(detail.detail || `HTTP ${res.status}`)
      }
      return (await res.json()) as AnalysisResult
    } catch (err) {
      console.error('Failed to analyze document:', err)
      throw err
    }
  },

  downloadRequirementsDoc: async (agentId, requirements, title) => {
    try {
      const res = await authFetch(`/agents/${agentId}/requirements-doc`, {
        method: 'POST',
        body: JSON.stringify({ title, requirements }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${(title || 'requirements').toLowerCase().replace(/\s+/g, '_').slice(0, 40)}.docx`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
      return true
    } catch (err) {
      console.error('Failed to download requirements doc:', err)
      return false
    }
  },

  startTask: async (taskId) => {
    // backlog -> in_progress (per the Werk state machine)
    try {
      const res = await authFetch(`/tasks/${taskId}`, {
        method: 'PUT',
        body: JSON.stringify({ status: 'in_progress' }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      await get().fetchAllTasks()
      return true
    } catch (err) {
      console.error('Failed to start task:', err)
      return false
    }
  },

  runTask: async (taskId) => {
    // Have the assigned agent actually do the work with the model.
    try {
      const res = await authFetch(`/tasks/${taskId}/run`, { method: 'POST' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      await get().fetchAllTasks()
      const projectId = get().selectedProjectId
      if (projectId) await get().fetchTasks(projectId)
      return true
    } catch (err) {
      console.error('Failed to run task:', err)
      return false
    }
  },

  fetchArtifacts: async (projectId) => {
    try {
      const res = await authFetch(`/artifacts/?project_id=${projectId}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      set({ artifacts: data.artifacts ?? [] })
    } catch (err) {
      console.error('Failed to fetch artifacts:', err)
    }
  },

  downloadArtifact: async (id, filename) => {
    try {
      const res = await authFetch(`/artifacts/${id}/download`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename || 'deliverable'
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Failed to download artifact:', err)
    }
  },

  fetchWorkspace: async (projectId) => {
    try {
      const res = await authFetch(`/workspace/${projectId}/files`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      set({ workspaceFiles: data.files ?? [] })
    } catch (err) {
      console.error('Failed to fetch workspace:', err)
    }
  },

  runTests: async (projectId) => {
    set({ testsRunning: true })
    try {
      const res = await authFetch(`/workspace/${projectId}/run-tests`, { method: 'POST' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = (await res.json()) as TestResult
      set({ testResult: data, testsRunning: false })
      await get().fetchWorkspace(projectId)
    } catch (err) {
      console.error('Failed to run tests:', err)
      set({ testsRunning: false })
    }
  },

  installDeps: async (projectId) => {
    set({ installing: true })
    try {
      const res = await authFetch(`/workspace/${projectId}/install`, { method: 'POST' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = (await res.json()) as InstallResult
      set({ installResult: data, installing: false })
      await get().fetchWorkspace(projectId)
    } catch (err) {
      console.error('Failed to install deps:', err)
      set({ installing: false })
    }
  },

  healthCheck: async (projectId) => {
    set({ healthChecking: true })
    try {
      const res = await authFetch(`/workspace/${projectId}/health-check`, { method: 'POST' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = (await res.json()) as HealthResult
      set({ healthResult: data, healthChecking: false })
    } catch (err) {
      console.error('Failed to health-check:', err)
      set({ healthChecking: false })
    }
  },

  chat: async (agentId, message) => {
    set((s) => ({
      chatPending: true,
      chatHistory: {
        ...s.chatHistory,
        [agentId]: [...(s.chatHistory[agentId] ?? []), { from: 'user', text: message }],
      },
    }))
    try {
      const res = await authFetch(`/agents/${agentId}/chat`, {
        method: 'POST',
        body: JSON.stringify({ message }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      set((s) => ({
        chatPending: false,
        chatHistory: {
          ...s.chatHistory,
          [agentId]: [
            ...(s.chatHistory[agentId] ?? []),
            { from: 'agent', text: data.reply, source: data.source },
          ],
        },
      }))
    } catch (err) {
      console.error('Chat failed:', err)
      set((s) => ({
        chatPending: false,
        chatHistory: {
          ...s.chatHistory,
          [agentId]: [
            ...(s.chatHistory[agentId] ?? []),
            { from: 'agent', text: '(Could not reach the agent — is the backend running?)' },
          ],
        },
      }))
    }
  },

  // WebSocket connection for real-time updates
  connectWebSocket: () => {
    if (get().wsConnected) return // avoid duplicate sockets across page navigations
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null
    let ws: WebSocket | null = null

    const connect = () => {
      try {
        ws = new WebSocket(WS_URL)

        ws.onopen = () => set({ wsConnected: true })

        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data)
            if (msg.type === 'ping') return
            set((s) => ({ wsEvents: [...s.wsEvents.slice(-49), msg] }))
            // Any task/agent/artifact change → refresh the canvas data live.
            const t: string = msg.type ?? ''
            if (
              t.startsWith('task.') ||
              t.startsWith('artifact.') ||
              t.startsWith('agent.') ||
              t.startsWith('review.') ||
              t.startsWith('workflow.')
            ) {
              get().fetchAllTasks()
              get().fetchAgents()
              const projectId = get().selectedProjectId
              if (projectId) {
                get().fetchTasks(projectId)
                get().fetchArtifacts(projectId)
                get().fetchWorkspace(projectId)
              }
            }
            const payloadPid = (msg.payload &&
              (msg.payload as Record<string, unknown>).project_id) as string | undefined
            if (t === 'workflow.review_pending' && payloadPid) {
              set((s) => ({
                workflowRunning: { ...s.workflowRunning, [payloadPid]: false },
                workflowReview: { ...s.workflowReview, [payloadPid]: true },
              }))
            }
            if (t === 'workflow.prod_pending' && payloadPid) {
              set((s) => ({
                workflowRunning: { ...s.workflowRunning, [payloadPid]: false },
                workflowProdReview: { ...s.workflowProdReview, [payloadPid]: true },
              }))
            }
            if (t === 'workflow.completed' && payloadPid) {
              set((s) => ({
                workflowRunning: { ...s.workflowRunning, [payloadPid]: false },
                workflowReview: { ...s.workflowReview, [payloadPid]: false },
                workflowProdReview: { ...s.workflowProdReview, [payloadPid]: false },
              }))
            }
          } catch {
            // ignore parse errors
          }
        }

        ws.onclose = () => {
          set({ wsConnected: false })
          reconnectTimer = setTimeout(connect, 3000)
        }

        ws.onerror = () => ws?.close()
      } catch {
        reconnectTimer = setTimeout(connect, 5000)
      }
    }

    connect()

    set({
      disconnectWebSocket: () => {
        if (reconnectTimer) clearTimeout(reconnectTimer)
        ws?.close()
        set({ wsConnected: false })
      },
    })
  },

  disconnectWebSocket: () => {
    // Placeholder - overridden by connectWebSocket
  },
}))
