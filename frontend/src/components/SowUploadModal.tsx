import { useState } from 'react'
import {
  useWerkStore,
  type PlannedAgent,
  type ParamValues,
  type ParamDefinition,
} from '../stores/werkStore'
import { metaFor } from '../lib/agentMeta'

type EditableAgent = PlannedAgent & { include: boolean }

export default function SowUploadModal({
  onClose,
  onDeployed,
}: {
  onClose: () => void
  onDeployed: (projectId: string) => void
}) {
  const analyzeSow = useWerkStore((s) => s.analyzeSow)
  const deriveTeam = useWerkStore((s) => s.deriveTeam)
  const deploySow = useWerkStore((s) => s.deploySow)
  const fetchParamDefinitions = useWerkStore((s) => s.fetchParamDefinitions)
  const saveParamDefinitions = useWerkStore((s) => s.saveParamDefinitions)

  const [file, setFile] = useState<File | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [error, setError] = useState('')
  const [source, setSource] = useState('')
  const [projectName, setProjectName] = useState('')
  const [summary, setSummary] = useState('')
  const [definitions, setDefinitions] = useState<ParamDefinition[]>([])
  const [params, setParams] = useState<ParamValues>({})
  const [agents, setAgents] = useState<EditableAgent[]>([])
  const [kickoff, setKickoff] = useState(true)
  const [deploying, setDeploying] = useState(false)
  const [recomputing, setRecomputing] = useState(false)
  const [expanded, setExpanded] = useState<Record<number, boolean>>({})

  // config editor
  const [showConfig, setShowConfig] = useState(false)
  const [defsJson, setDefsJson] = useState('')
  const [configMsg, setConfigMsg] = useState('')

  const analyzed = agents.length > 0 || (!!projectName && !analyzing)

  const handleAnalyze = async () => {
    if (!file) return
    setAnalyzing(true)
    setError('')
    try {
      const plan = await analyzeSow(file)
      if (plan) {
        setProjectName(plan.project_name)
        setSummary(plan.summary)
        setSource(plan.source)
        setDefinitions(plan.definitions)
        setParams(plan.parameters)
        setAgents(plan.agents.map((a) => ({ ...a, include: true })))
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not read the SOW.')
    } finally {
      setAnalyzing(false)
    }
  }

  const patchParam = (key: string, value: unknown) => setParams((p) => ({ ...p, [key]: value }))

  const handleRecompute = async () => {
    setRecomputing(true)
    const team = await deriveTeam(params, summary)
    setRecomputing(false)
    if (team) setAgents(team.map((a) => ({ ...a, include: true })))
  }

  const openConfig = async () => {
    setShowConfig((v) => !v)
    setConfigMsg('')
    if (!showConfig) {
      const defs = definitions.length ? definitions : (await fetchParamDefinitions()) ?? []
      setDefsJson(JSON.stringify(defs, null, 2))
    }
  }

  const handleSaveConfig = async () => {
    setConfigMsg('')
    try {
      const parsed = JSON.parse(defsJson) as ParamDefinition[]
      const ok = await saveParamDefinitions(parsed)
      setConfigMsg(ok ? 'Saved. Re-upload the SOW to use the new parameters.' : 'Save failed.')
    } catch {
      setConfigMsg('Invalid JSON.')
    }
  }

  const handleDeploy = async () => {
    const included = agents.filter((a) => a.include)
    if (!projectName.trim() || included.length === 0) {
      setError('Name the engagement and keep at least one agent.')
      return
    }
    setDeploying(true)
    setError('')
    const pid = await deploySow({
      project_name: projectName.trim(),
      summary,
      parameters: params,
      agents: included.map(({ include: _i, ...a }) => a),
      create_kickoff_tasks: kickoff,
    })
    setDeploying(false)
    if (pid) onDeployed(pid)
    else setError('Deployment failed.')
  }

  const renderField = (d: ParamDefinition) => {
    const v = params[d.key]
    if (d.type === 'select') {
      return (
        <select value={String(v ?? d.default ?? '')} onChange={(e) => patchParam(d.key, e.target.value)}
          className="mt-1 w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm capitalize focus:border-indigo-500 focus:outline-none">
          {(d.options ?? []).map((o) => <option key={o} value={o} className="capitalize">{o}</option>)}
        </select>
      )
    }
    if (d.type === 'number') {
      return (
        <input type="number" value={Number(v ?? 0)} onChange={(e) => patchParam(d.key, Number(e.target.value) || 0)}
          className="mt-1 w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:border-indigo-500 focus:outline-none" />
      )
    }
    if (d.type === 'list') {
      const arr = Array.isArray(v) ? (v as string[]) : []
      return (
        <input value={arr.join(', ')} placeholder={d.options ? d.options.join(', ') : 'comma-separated'}
          onChange={(e) => patchParam(d.key, e.target.value.split(',').map((x) => x.trim()).filter(Boolean))}
          className="mt-1 w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:border-indigo-500 focus:outline-none" />
      )
    }
    return (
      <input value={String(v ?? '')} onChange={(e) => patchParam(d.key, e.target.value)}
        className="mt-1 w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:border-indigo-500 focus:outline-none" />
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" onClick={onClose}>
      <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}>
        <div className="mb-1 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Deploy a team from a signed SOW</h2>
          <button onClick={onClose} className="rounded-md p-1 text-gray-400 hover:bg-gray-100">✕</button>
        </div>
        <p className="mb-4 text-sm text-gray-500">
          Upload the signed SOW. The platform extracts the configured parameters, you confirm or
          override them, and the right team is staffed accordingly.
        </p>

        {!analyzed && (
          <div className="space-y-3">
            <label className="flex cursor-pointer items-center gap-2 rounded-md border border-dashed border-indigo-300 bg-indigo-50/40 px-3 py-3 text-sm text-gray-600 hover:border-indigo-400">
              <span>📄</span>
              <span className="truncate">{file ? file.name : 'Choose a signed SOW (.pptx, .pdf, .docx, .txt)…'}</span>
              <input type="file" accept=".pptx,.pdf,.docx,.txt,.md" className="hidden"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
            </label>
            <button onClick={handleAnalyze} disabled={!file || analyzing}
              className="w-full rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-40">
              {analyzing ? 'Reading the SOW…' : 'Analyze SOW'}
            </button>
            <button onClick={openConfig} className="w-full text-xs font-medium text-gray-500 hover:text-gray-700">
              {showConfig ? 'Hide parameter configuration' : 'Configure parameters (advanced)'}
            </button>
            {showConfig && (
              <div>
                <textarea value={defsJson} onChange={(e) => setDefsJson(e.target.value)} rows={10}
                  className="w-full rounded-md border border-gray-300 px-2 py-1.5 font-mono text-[11px] focus:border-indigo-500 focus:outline-none" />
                <div className="mt-1 flex items-center gap-2">
                  <button onClick={handleSaveConfig}
                    className="rounded-md bg-gray-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-gray-700">
                    Save parameter definitions
                  </button>
                  {configMsg && <span className="text-xs text-emerald-600">{configMsg}</span>}
                </div>
              </div>
            )}
          </div>
        )}

        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

        {analyzed && (
          <div className="space-y-5">
            <div>
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-gray-400">Engagement name</label>
              <input value={projectName} onChange={(e) => setProjectName(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none" />
            </div>

            <div className="rounded-xl border border-indigo-100 bg-indigo-50/40 p-3">
              <div className="mb-2 flex items-center justify-between">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-indigo-500">
                  Project parameters <span className="text-red-400">*</span>
                </h3>
                <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                  source === 'llm' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
                  {source === 'llm' ? 'model-extracted' : 'auto-extracted'}
                </span>
              </div>
              <p className="mb-2 text-xs text-gray-500">Extracted from the SOW. Override as needed — these drive the team.</p>
              <div className="grid grid-cols-2 gap-3">
                {definitions.map((d) => (
                  <label key={d.key} className="text-xs text-gray-600">
                    {d.label}
                    {renderField(d)}
                  </label>
                ))}
              </div>
              <button onClick={handleRecompute} disabled={recomputing}
                className="mt-3 w-full rounded-md border border-indigo-300 bg-white px-3 py-1.5 text-xs font-medium text-indigo-700 hover:bg-indigo-50 disabled:opacity-50">
                {recomputing ? 'Updating team…' : 'Update recommended team from parameters'}
              </button>
            </div>

            <div>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
                Recommended team ({agents.filter((a) => a.include).length}/{agents.length})
              </h3>
              <ul className="space-y-2">
                {agents.map((a, i) => {
                  const meta = metaFor(a.role)
                  return (
                    <li key={i} className="rounded-lg border border-gray-200 p-3">
                      <div className="flex items-start gap-3">
                        <input type="checkbox" checked={a.include} className="mt-1"
                          onChange={(e) => setAgents((p) => p.map((x, j) => (j === i ? { ...x, include: e.target.checked } : x)))} />
                        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-lg" style={{ backgroundColor: meta.soft }}>
                          {meta.glyph}
                        </div>
                        <div className="min-w-0 flex-1">
                          <input value={a.name}
                            onChange={(e) => setAgents((p) => p.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)))}
                            className="w-full rounded border border-transparent bg-transparent text-sm font-semibold text-gray-900 hover:border-gray-200 focus:border-indigo-400 focus:outline-none" />
                          <p className="text-xs" style={{ color: meta.color }}>{meta.label}</p>
                          {a.rationale && <p className="mt-1 text-xs text-gray-500">{a.rationale}</p>}
                          <button onClick={() => setExpanded((e) => ({ ...e, [i]: !e[i] }))}
                            className="mt-1 text-[11px] font-medium text-indigo-600 hover:text-indigo-800">
                            {expanded[i] ? 'Hide instructions' : 'Edit instructions'}
                          </button>
                          {expanded[i] && (
                            <textarea value={a.instructions} rows={4}
                              onChange={(e) => setAgents((p) => p.map((x, j) => (j === i ? { ...x, instructions: e.target.value } : x)))}
                              className="mt-1 w-full rounded-md border border-gray-200 px-2 py-1 font-mono text-[11px] focus:border-indigo-500 focus:outline-none" />
                          )}
                        </div>
                      </div>
                    </li>
                  )
                })}
              </ul>
            </div>

            <label className="flex items-center gap-2 text-sm text-gray-600">
              <input type="checkbox" checked={kickoff} onChange={(e) => setKickoff(e.target.checked)} />
              Create a kickoff task for each deployed agent
            </label>

            <div className="flex justify-end gap-2 border-t border-gray-100 pt-4">
              <button onClick={onClose} className="rounded-md px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100">Cancel</button>
              <button onClick={handleDeploy} disabled={deploying}
                className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
                {deploying ? 'Deploying…' : `Deploy ${agents.filter((a) => a.include).length} agents`}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
