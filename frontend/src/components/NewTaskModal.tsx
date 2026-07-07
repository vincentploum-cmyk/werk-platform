import { useState } from 'react'
import { useWerkStore } from '../stores/werkStore'
import { metaFor } from '../lib/agentMeta'

export default function NewTaskModal({
  onClose,
  defaultAgentId,
}: {
  onClose: () => void
  defaultAgentId?: string
}) {
  const projects = useWerkStore((s) => s.projects)
  const agents = useWerkStore((s) => s.agents)
  const createTask = useWerkStore((s) => s.createTask)
  const createProject = useWerkStore((s) => s.createProject)

  const NEW = '__new__'
  const [projectId, setProjectId] = useState(projects[0]?.id ?? NEW)
  const [newProjectName, setNewProjectName] = useState('')
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [agentId, setAgentId] = useState(defaultAgentId ?? '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const creatingProject = projectId === NEW || projects.length === 0

  const handleCreate = async () => {
    setError('')
    if (!title.trim()) {
      setError('Give the task a title.')
      return
    }
    setSaving(true)
    try {
      let pid = projectId
      if (creatingProject) {
        if (!newProjectName.trim()) {
          setError('Name the new project.')
          setSaving(false)
          return
        }
        const project = await createProject(newProjectName.trim())
        if (!project) {
          setError('Could not create the project.')
          setSaving(false)
          return
        }
        pid = project.id
      }
      const ok = await createTask(pid, title.trim(), agentId || undefined, description.trim() || undefined)
      if (!ok) {
        setError('Could not create the task.')
        setSaving(false)
        return
      }
      onClose()
    } catch {
      setError('Something went wrong.')
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" onClick={onClose}>
      <div
        className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">New task</h2>
          <button onClick={onClose} className="rounded-md p-1 text-gray-400 hover:bg-gray-100">
            ✕
          </button>
        </div>

        <div className="space-y-4">
          {/* project */}
          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-gray-400">
              Project
            </label>
            <select
              value={creatingProject ? NEW : projectId}
              onChange={(e) => setProjectId(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
            >
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
              <option value={NEW}>+ New project…</option>
            </select>
            {creatingProject && (
              <input
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
                placeholder="New project name"
                className="mt-2 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
              />
            )}
          </div>

          {/* title */}
          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-gray-400">
              Title
            </label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              autoFocus
              placeholder="What needs to be done?"
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
            />
          </div>

          {/* description */}
          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-gray-400">
              Description <span className="font-normal normal-case text-gray-300">(optional)</span>
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              placeholder="Add detail or context…"
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
            />
          </div>

          {/* assign */}
          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-gray-400">
              Assign to <span className="font-normal normal-case text-gray-300">(optional)</span>
            </label>
            <select
              value={agentId}
              onChange={(e) => setAgentId(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
            >
              <option value="">Unassigned (drop on an agent later)</option>
              {agents.map((a) => (
                <option key={a.id} value={a.id}>
                  {metaFor(a.role).glyph} {a.name}
                </option>
              ))}
            </select>
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded-md px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100"
          >
            Cancel
          </button>
          <button
            onClick={handleCreate}
            disabled={saving}
            className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {saving ? 'Creating…' : 'Create task'}
          </button>
        </div>
      </div>
    </div>
  )
}
