import { useState } from 'react'
import { useWerkStore } from '../stores/werkStore'
import { metaFor } from '../lib/agentMeta'
import { useDialog } from '../lib/useDialog'

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
  const dialogRef = useDialog<HTMLDivElement>(onClose)

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
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label="New task"
        tabIndex={-1}
        className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">New task</h2>
          <button onClick={onClose} aria-label="Close" className="flex h-10 w-10 items-center justify-center rounded-md text-gray-500 hover:bg-gray-100">
            ✕
          </button>
        </div>

        <div className="space-y-4">
          {/* project */}
          <div>
            <label htmlFor="nt-project" className="mb-1 block text-xs font-semibold uppercase tracking-wide text-gray-500">
              Project
            </label>
            <select
              id="nt-project"
              value={creatingProject ? NEW : projectId}
              onChange={(e) => setProjectId(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500"
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
                aria-label="New project name"
                className="mt-2 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500"
              />
            )}
          </div>

          {/* title */}
          <div>
            <label htmlFor="nt-title" className="mb-1 block text-xs font-semibold uppercase tracking-wide text-gray-500">
              Title
            </label>
            <input
              id="nt-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              data-autofocus
              placeholder="What needs to be done?"
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500"
            />
          </div>

          {/* description */}
          <div>
            <label htmlFor="nt-desc" className="mb-1 block text-xs font-semibold uppercase tracking-wide text-gray-500">
              Description <span className="font-normal normal-case text-gray-500">(optional)</span>
            </label>
            <textarea
              id="nt-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              placeholder="Add detail or context…"
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500"
            />
          </div>

          {/* assign */}
          <div>
            <label htmlFor="nt-assign" className="mb-1 block text-xs font-semibold uppercase tracking-wide text-gray-500">
              Assign to <span className="font-normal normal-case text-gray-500">(optional)</span>
            </label>
            <select
              id="nt-assign"
              value={agentId}
              onChange={(e) => setAgentId(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500"
            >
              <option value="">Unassigned (assign later from the tray)</option>
              {agents.map((a) => (
                <option key={a.id} value={a.id}>
                  {metaFor(a.role).glyph} {a.name}
                </option>
              ))}
            </select>
          </div>

          {error && (
            <p role="alert" className="text-sm text-red-600">
              {error}
            </p>
          )}
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
            className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover disabled:opacity-50"
          >
            {saving ? 'Creating…' : 'Create task'}
          </button>
        </div>
      </div>
    </div>
  )
}
