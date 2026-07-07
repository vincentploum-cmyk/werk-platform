import { useState, useRef, useEffect } from 'react'
import {
  useWerkStore,
  type Agent,
  type RequirementItem,
  type AgentExample,
} from '../stores/werkStore'
import { metaFor, statusOf, STATE_LABEL, STATE_DOT } from '../lib/agentMeta'

const STATUS_PILL: Record<string, string> = {
  backlog: 'bg-gray-100 text-gray-700',
  in_progress: 'bg-amber-100 text-amber-800',
  review: 'bg-violet-100 text-violet-800',
  done: 'bg-emerald-100 text-emerald-800',
  blocked: 'bg-red-100 text-red-700',
}

export default function AgentPanel({ agent, onClose }: { agent: Agent; onClose: () => void }) {
  const allTasks = useWerkStore((s) => s.allTasks)
  const projects = useWerkStore((s) => s.projects)
  const chatHistory = useWerkStore((s) => s.chatHistory)
  const chatPending = useWerkStore((s) => s.chatPending)
  const chat = useWerkStore((s) => s.chat)
  const createTask = useWerkStore((s) => s.createTask)
  const createTasksBulk = useWerkStore((s) => s.createTasksBulk)
  const updateTaskStatus = useWerkStore((s) => s.updateTaskStatus)
  const runTask = useWerkStore((s) => s.runTask)
  const analyzeDocument = useWerkStore((s) => s.analyzeDocument)
  const downloadRequirementsDoc = useWerkStore((s) => s.downloadRequirementsDoc)
  const saveInstructions = useWerkStore((s) => s.saveInstructions)
  const saveExamples = useWerkStore((s) => s.saveExamples)
  const selectedProjectId = useWerkStore((s) => s.selectedProjectId)

  const meta = metaFor(agent.role)
  const status = statusOf(agent, allTasks)
  const isRequirements = agent.role.toLowerCase() === 'requirements'

  const [title, setTitle] = useState('')
  const [projectId, setProjectId] = useState(selectedProjectId ?? '')
  const [message, setMessage] = useState('')
  const chatEndRef = useRef<HTMLDivElement>(null)
  const [runningId, setRunningId] = useState<string | null>(null)
  const [openResult, setOpenResult] = useState<Record<string, boolean>>({})

  const handleRun = async (taskId: string) => {
    setRunningId(taskId)
    await runTask(taskId)
    setRunningId(null)
    setOpenResult((o) => ({ ...o, [taskId]: true }))
  }

  // document analysis state
  const [file, setFile] = useState<File | null>(null)
  const [instruction, setInstruction] = useState('')
  const [analyzing, setAnalyzing] = useState(false)
  const [analysisErr, setAnalysisErr] = useState('')
  const [reqs, setReqs] = useState<RequirementItem[]>([])
  const [analysisSource, setAnalysisSource] = useState('')
  const [analysisFilename, setAnalysisFilename] = useState('')
  const [docMsg, setDocMsg] = useState('')

  const handleAnalyze = async () => {
    if (!file) return
    setAnalyzing(true)
    setAnalysisErr('')
    setDocMsg('')
    try {
      const result = await analyzeDocument(agent.id, file, instruction)
      if (result) {
        setReqs(result.requirements)
        setAnalysisSource(result.source)
        setAnalysisFilename(result.filename)
        if (result.requirements.length === 0) {
          setAnalysisErr('No requirements could be drafted from that document.')
        }
      }
    } catch (e) {
      setAnalysisErr(e instanceof Error ? e.message : 'Analysis failed.')
    } finally {
      setAnalyzing(false)
    }
  }

  const handleCreateTasksFromReqs = async () => {
    if (!projectId || reqs.length === 0) return
    setDocMsg('')
    const n = await createTasksBulk(projectId, reqs.map((r) => r.text), agent.id)
    setDocMsg(`Created ${n} task${n === 1 ? '' : 's'} for ${agent.name}.`)
  }

  const handleDownloadDoc = async () => {
    if (reqs.length === 0) return
    const docTitle = `Functional Requirements${analysisFilename ? ' — ' + analysisFilename : ''}`
    await downloadRequirementsDoc(agent.id, reqs.map((r) => r.text), docTitle)
  }

  // instructions ("tuning") state
  const [showInstr, setShowInstr] = useState(false)
  const [instrText, setInstrText] = useState(agent.instructions ?? '')
  const [instrSaving, setInstrSaving] = useState(false)
  const [instrMsg, setInstrMsg] = useState('')

  useEffect(() => {
    setInstrText(agent.instructions ?? '')
    setInstrMsg('')
  }, [agent.id, agent.instructions])

  const handleSaveInstr = async () => {
    setInstrSaving(true)
    setInstrMsg('')
    const updated = await saveInstructions(agent.id, instrText)
    setInstrSaving(false)
    setInstrMsg(updated ? 'Saved — applies to new replies immediately.' : 'Could not save.')
  }

  const handleResetInstr = async () => {
    setInstrSaving(true)
    setInstrMsg('')
    const updated = await saveInstructions(agent.id, '')
    setInstrSaving(false)
    if (updated) {
      setInstrText(updated.instructions ?? '')
      setInstrMsg('Reset to the default instructions.')
    }
  }

  // few-shot examples state
  const [showExamples, setShowExamples] = useState(false)
  const [examples, setExamples] = useState<AgentExample[]>(agent.examples ?? [])
  const [exSaving, setExSaving] = useState(false)
  const [exMsg, setExMsg] = useState('')

  useEffect(() => {
    setExamples(agent.examples ?? [])
    setExMsg('')
  }, [agent.id, agent.examples])

  const handleSaveExamples = async () => {
    setExSaving(true)
    setExMsg('')
    const cleaned = examples.filter((e) => e.output.trim())
    const updated = await saveExamples(agent.id, cleaned)
    setExSaving(false)
    setExMsg(updated ? `Saved ${cleaned.length} example(s) — now used in this agent's prompts.` : 'Could not save.')
  }

  useEffect(() => {
    if (!projectId && projects.length) setProjectId(projects[0].id)
  }, [projects, projectId])

  const history = chatHistory[agent.id] ?? []
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [history.length, chatPending])

  const handleAssign = async () => {
    if (!title.trim() || !projectId) return
    const ok = await createTask(projectId, title.trim(), agent.id)
    if (ok) setTitle('')
  }

  const handleSend = async () => {
    if (!message.trim() || chatPending) return
    const m = message.trim()
    setMessage('')
    await chat(agent.id, m)
  }

  return (
    <>
      {/* backdrop */}
      <div className="fixed inset-0 z-40 bg-black/20" onClick={onClose} />
      <aside className="fixed right-0 top-0 z-50 flex h-full w-full max-w-md flex-col border-l border-gray-200 bg-white shadow-2xl">
        {/* header */}
        <div className="flex items-start justify-between border-b border-gray-100 p-5">
          <div className="flex items-center gap-3">
            <div
              className="flex h-12 w-12 items-center justify-center rounded-xl text-2xl"
              style={{ backgroundColor: meta.soft }}
            >
              {meta.glyph}
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">{agent.name}</h2>
              <div className="mt-0.5 flex items-center gap-2">
                <span
                  className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium"
                  style={{ backgroundColor: meta.soft, color: meta.color }}
                >
                  {meta.label}
                </span>
                <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs capitalize text-gray-500">
                  {agent.type}
                </span>
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        <div className="flex-1 space-y-6 overflow-y-auto p-5">
          {/* status */}
          <div className="flex items-center gap-2 text-sm">
            <span
              className="inline-block h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: STATE_DOT[status.state] }}
            />
            <span className="font-medium text-gray-700">{STATE_LABEL[status.state]}</span>
            {status.current && (
              <span className="truncate text-gray-500">· {status.current.title}</span>
            )}
          </div>

          {/* capabilities */}
          <div>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
              Capabilities
            </h3>
            <div className="flex flex-wrap gap-1.5">
              {(agent.capabilities ?? []).map((c) => (
                <span
                  key={c}
                  className="rounded-md bg-gray-100 px-2 py-1 text-xs text-gray-600"
                >
                  {c}
                </span>
              ))}
            </div>
          </div>

          {/* instructions ("tuning") */}
          <div>
            <button
              onClick={() => setShowInstr((v) => !v)}
              className="flex w-full items-center justify-between text-left"
            >
              <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-400">
                Instructions{' '}
                {agent.instructions_custom && (
                  <span className="ml-1 rounded-full bg-emerald-100 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700">
                    customized
                  </span>
                )}
              </h3>
              <span className="text-xs text-gray-400">{showInstr ? 'Hide ▾' : 'Edit ▸'}</span>
            </button>
            <p className="mt-1 text-xs text-gray-500">
              How this agent thinks and responds. Edit to tune its behavior — changes apply
              instantly to chat and analysis.
            </p>
            {showInstr && (
              <div className="mt-2">
                <textarea
                  value={instrText}
                  onChange={(e) => setInstrText(e.target.value)}
                  rows={8}
                  className="w-full rounded-md border border-gray-300 px-2 py-1.5 font-mono text-xs leading-relaxed focus:border-indigo-500 focus:outline-none"
                />
                <div className="mt-2 flex items-center gap-2">
                  <button
                    onClick={handleSaveInstr}
                    disabled={instrSaving}
                    className="rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-40"
                  >
                    {instrSaving ? 'Saving…' : 'Save instructions'}
                  </button>
                  <button
                    onClick={handleResetInstr}
                    disabled={instrSaving}
                    className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-40"
                  >
                    Reset to default
                  </button>
                </div>
                {instrMsg && <p className="mt-2 text-xs text-emerald-600">{instrMsg}</p>}
              </div>
            )}
          </div>

          {/* few-shot examples */}
          <div>
            <button
              onClick={() => setShowExamples((v) => !v)}
              className="flex w-full items-center justify-between text-left"
            >
              <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-400">
                Examples{' '}
                {(agent.examples?.length ?? 0) > 0 && (
                  <span className="ml-1 rounded-full bg-emerald-100 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700">
                    {agent.examples!.length}
                  </span>
                )}
              </h3>
              <span className="text-xs text-gray-400">{showExamples ? 'Hide ▾' : 'Edit ▸'}</span>
            </button>
            <p className="mt-1 text-xs text-gray-500">
              Good-output samples the agent matches for style and format. Used in chat, document
              analysis, and the pipeline.
            </p>
            {showExamples && (
              <div className="mt-2 space-y-3">
                {examples.map((ex, i) => (
                  <div key={i} className="rounded-lg border border-gray-200 bg-gray-50 p-2">
                    <div className="mb-1 flex items-center justify-between">
                      <span className="text-[11px] font-medium text-gray-500">Example {i + 1}</span>
                      <button
                        onClick={() => setExamples((p) => p.filter((_, j) => j !== i))}
                        className="rounded p-0.5 text-gray-300 hover:text-red-500"
                        aria-label="Remove"
                      >
                        ✕
                      </button>
                    </div>
                    <input
                      value={ex.input ?? ''}
                      onChange={(e) =>
                        setExamples((p) =>
                          p.map((x, j) => (j === i ? { ...x, input: e.target.value } : x)),
                        )
                      }
                      placeholder="When asked to… (optional context)"
                      className="mb-1 w-full rounded-md border border-gray-200 px-2 py-1 text-xs focus:border-indigo-500 focus:outline-none"
                    />
                    <textarea
                      value={ex.output}
                      rows={3}
                      onChange={(e) =>
                        setExamples((p) =>
                          p.map((x, j) => (j === i ? { ...x, output: e.target.value } : x)),
                        )
                      }
                      placeholder="…this is a good output."
                      className="w-full rounded-md border border-gray-200 px-2 py-1 text-xs focus:border-indigo-500 focus:outline-none"
                    />
                  </div>
                ))}
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setExamples((p) => [...p, { input: '', output: '' }])}
                    className="text-xs font-medium text-indigo-600 hover:text-indigo-800"
                  >
                    + Add example
                  </button>
                  <button
                    onClick={handleSaveExamples}
                    disabled={exSaving}
                    className="ml-auto rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-40"
                  >
                    {exSaving ? 'Saving…' : 'Save examples'}
                  </button>
                </div>
                {exMsg && <p className="text-xs text-emerald-600">{exMsg}</p>}
              </div>
            )}
          </div>

          {/* analyze a document */}
          <div className="rounded-xl border border-indigo-100 bg-indigo-50/40 p-3">
            <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-indigo-500">
              {isRequirements ? 'Draft requirements from a document' : 'Analyze a document'}
            </h3>
            <p className="mb-2 text-xs text-gray-500">
              {isRequirements
                ? 'Upload your requirements-gathering deck (PPT, PDF, Word, or text) and I’ll draft functional requirements.'
                : 'Upload a document (PPT, PDF, Word, or text) for analysis.'}
            </p>

            <label className="flex cursor-pointer items-center gap-2 rounded-md border border-dashed border-indigo-300 bg-white px-3 py-2 text-sm text-gray-600 hover:border-indigo-400">
              <span>📎</span>
              <span className="truncate">{file ? file.name : 'Choose a file…'}</span>
              <input
                type="file"
                accept=".pptx,.pdf,.docx,.txt,.md"
                className="hidden"
                onChange={(e) => {
                  setFile(e.target.files?.[0] ?? null)
                  setReqs([])
                  setAnalysisErr('')
                  setDocMsg('')
                }}
              />
            </label>

            <input
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
              placeholder="Optional: focus or scope…"
              className="mt-2 w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:border-indigo-500 focus:outline-none"
            />

            <button
              onClick={handleAnalyze}
              disabled={!file || analyzing}
              className="mt-2 w-full rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-40"
            >
              {analyzing ? 'Reading the document…' : isRequirements ? 'Draft requirements' : 'Analyze'}
            </button>

            {analysisErr && <p className="mt-2 text-sm text-red-600">{analysisErr}</p>}

            {reqs.length > 0 && (
              <div className="mt-3">
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-xs font-medium text-gray-600">
                    {reqs.length} requirement{reqs.length === 1 ? '' : 's'}
                  </span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                      analysisSource === 'llm'
                        ? 'bg-emerald-100 text-emerald-700'
                        : 'bg-amber-100 text-amber-700'
                    }`}
                  >
                    {analysisSource === 'llm' ? 'LLM-drafted' : 'auto-drafted'}
                  </span>
                </div>

                <ul className="space-y-1.5">
                  {reqs.map((r, i) => (
                    <li key={r.id} className="flex items-start gap-1.5">
                      <span className="mt-2 text-[10px] font-semibold text-gray-400">FR-{i + 1}</span>
                      <textarea
                        value={r.text}
                        rows={2}
                        onChange={(e) =>
                          setReqs((prev) =>
                            prev.map((x, j) => (j === i ? { ...x, text: e.target.value } : x)),
                          )
                        }
                        className="flex-1 rounded-md border border-gray-200 px-2 py-1 text-xs focus:border-indigo-500 focus:outline-none"
                      />
                      <button
                        onClick={() => setReqs((prev) => prev.filter((_, j) => j !== i))}
                        className="mt-1 rounded p-0.5 text-gray-300 hover:text-red-500"
                        aria-label="Remove"
                      >
                        ✕
                      </button>
                    </li>
                  ))}
                </ul>

                <button
                  onClick={() =>
                    setReqs((prev) => [...prev, { id: `FR-${prev.length + 1}`, text: '' }])
                  }
                  className="mt-2 text-xs font-medium text-indigo-600 hover:text-indigo-800"
                >
                  + Add requirement
                </button>

                {projects.length > 0 && (
                  <select
                    value={projectId}
                    onChange={(e) => setProjectId(e.target.value)}
                    className="mt-3 w-full rounded-md border border-gray-300 px-2 py-1.5 text-xs focus:border-indigo-500 focus:outline-none"
                  >
                    <option value="">Select a project for the tasks…</option>
                    {projects.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                )}

                <div className="mt-2 flex gap-2">
                  <button
                    onClick={handleCreateTasksFromReqs}
                    disabled={!projectId}
                    className="flex-1 rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-40"
                    title={!projectId ? 'Pick a project first' : ''}
                  >
                    Create {reqs.length} task{reqs.length === 1 ? '' : 's'}
                  </button>
                  <button
                    onClick={handleDownloadDoc}
                    className="flex-1 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
                  >
                    Download .docx
                  </button>
                </div>
                {docMsg && <p className="mt-2 text-xs text-emerald-600">{docMsg}</p>}
              </div>
            )}
          </div>

          {/* assigned work */}
          <div>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
              Assigned work ({status.tasks.length})
            </h3>
            {status.tasks.length === 0 ? (
              <p className="text-sm text-gray-400">Nothing assigned yet.</p>
            ) : (
              <ul className="space-y-2">
                {status.tasks.map((t) => {
                  const canRun = t.status === 'backlog' || t.status === 'in_progress'
                  const isRunning = runningId === t.id
                  return (
                    <li
                      key={t.id}
                      className="rounded-lg border border-gray-100 bg-gray-50 px-3 py-2"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium text-gray-800">{t.title}</p>
                          <span
                            className={`mt-1 inline-block rounded px-1.5 py-0.5 text-[11px] font-medium ${
                              STATUS_PILL[t.status] ?? 'bg-gray-100 text-gray-600'
                            }`}
                          >
                            {isRunning ? 'working…' : t.status.replace('_', ' ')}
                          </span>
                        </div>
                        <div className="flex shrink-0 items-center gap-1.5">
                          {canRun && (
                            <button
                              onClick={() => handleRun(t.id)}
                              disabled={isRunning}
                              className="rounded-md bg-indigo-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
                            >
                              {isRunning ? 'Running…' : '▶ Run'}
                            </button>
                          )}
                          {t.status === 'review' && (
                            <button
                              onClick={() => updateTaskStatus(t.id, 'done')}
                              className="rounded-md bg-emerald-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-emerald-700"
                            >
                              Approve
                            </button>
                          )}
                        </div>
                      </div>
                      {t.result && (
                        <div className="mt-1.5">
                          <button
                            onClick={() =>
                              setOpenResult((o) => ({ ...o, [t.id]: !o[t.id] }))
                            }
                            className="text-xs font-medium text-indigo-600 hover:text-indigo-800"
                          >
                            {openResult[t.id] ? 'Hide output' : 'View output'}
                          </button>
                          {openResult[t.id] && (
                            <pre className="mt-1 max-h-60 overflow-auto whitespace-pre-wrap rounded-md bg-white p-2 text-[11px] leading-relaxed text-gray-700 ring-1 ring-gray-100">
                              {t.result}
                            </pre>
                          )}
                        </div>
                      )}
                    </li>
                  )
                })}
              </ul>
            )}
          </div>

          {/* assign new task */}
          <div>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
              Assign a new task
            </h3>
            {projects.length === 0 ? (
              <p className="text-sm text-gray-400">Create a project first (Projects tab).</p>
            ) : (
              <div className="space-y-2">
                <select
                  value={projectId}
                  onChange={(e) => setProjectId(e.target.value)}
                  className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:border-indigo-500 focus:outline-none"
                >
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
                <div className="flex gap-2">
                  <input
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleAssign()}
                    placeholder={`Task for the ${meta.label} agent…`}
                    className="flex-1 rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:border-indigo-500 focus:outline-none"
                  />
                  <button
                    onClick={handleAssign}
                    disabled={!title.trim()}
                    className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-40"
                  >
                    Assign
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* chat */}
          <div>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
              Chat with {meta.label}
            </h3>
            <div className="mb-2 max-h-64 space-y-2 overflow-y-auto rounded-lg bg-gray-50 p-3">
              {history.length === 0 && (
                <p className="text-sm text-gray-400">
                  Ask this agent about its part of the work.
                </p>
              )}
              {history.map((m, i) => (
                <div
                  key={i}
                  className={`flex ${m.from === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm ${
                      m.from === 'user'
                        ? 'bg-indigo-600 text-white'
                        : 'bg-white text-gray-800 shadow-sm ring-1 ring-gray-100'
                    }`}
                  >
                    {m.text}
                    {m.from === 'agent' && m.source === 'persona' && (
                      <span className="mt-1 block text-[10px] italic text-gray-400">
                        simulated · enable a model (local Ollama or an API key) for live replies
                      </span>
                    )}
                  </div>
                </div>
              ))}
              {chatPending && (
                <div className="flex justify-start">
                  <div className="rounded-2xl bg-white px-3 py-2 text-sm text-gray-400 shadow-sm ring-1 ring-gray-100">
                    thinking…
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>
            <div className="flex gap-2">
              <input
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                placeholder="Type a message…"
                className="flex-1 rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:border-indigo-500 focus:outline-none"
              />
              <button
                onClick={handleSend}
                disabled={!message.trim() || chatPending}
                className="rounded-md bg-gray-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-gray-700 disabled:opacity-40"
              >
                Send
              </button>
            </div>
          </div>
        </div>
      </aside>
    </>
  )
}
