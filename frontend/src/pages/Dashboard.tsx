import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useWerkStore, type Project } from '../stores/werkStore'
import Header from '../components/Header'

function ProjectCard({ project }: { project: Project }) {
  const statusColors: Record<string, string> = {
    draft: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
    active: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    completed: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    archived: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400',
  }

  const colorClass = statusColors[project.status] || statusColors.draft

  return (
    <Link
      to={`/project/${project.id}`}
      className="block rounded-lg border border-gray-200 bg-white p-6 shadow-sm transition hover:shadow-md dark:border-gray-700 dark:bg-gray-800"
    >
      <div className="flex items-start justify-between">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{project.name}</h3>
        <span
          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${colorClass}`}
        >
          {project.status}
        </span>
      </div>
      {project.description && (
        <p className="mt-2 text-sm text-gray-600 line-clamp-2 dark:text-gray-400">
          {project.description}
        </p>
      )}
      <p className="mt-3 text-xs text-gray-500 dark:text-gray-500">
        Created: {new Date(project.created_at).toLocaleDateString()}
      </p>
    </Link>
  )
}

export function Dashboard() {
  const projects = useWerkStore((s) => s.projects)
  const projectsLoading = useWerkStore((s) => s.projectsLoading)
  const fetchProjects = useWerkStore((s) => s.fetchProjects)
  const connectWebSocket = useWerkStore((s) => s.connectWebSocket)

  useEffect(() => {
    fetchProjects()
    connectWebSocket()
  }, [fetchProjects, connectWebSocket])

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Header />
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Projects</h1>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
              AI-orchestrated software development platform
            </p>
          </div>
          <button
            onClick={fetchProjects}
            className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          >
            Refresh
          </button>
        </div>

        {projectsLoading ? (
          <div className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-32 animate-pulse rounded-lg bg-gray-200 dark:bg-gray-700"
              />
            ))}
          </div>
        ) : projects.length === 0 ? (
          <div className="mt-16 text-center">
            <p className="text-lg text-gray-500 dark:text-gray-400">No projects yet</p>
            <p className="mt-1 text-sm text-gray-400 dark:text-gray-500">
              Create a project via the API to get started
            </p>
          </div>
        ) : (
          <div className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {projects.map((project) => (
              <ProjectCard key={project.id} project={project} />
            ))}
          </div>
        )}
      </main>
    </div>
  )
}

export default Dashboard