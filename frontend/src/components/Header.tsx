import { Link, useLocation } from 'react-router-dom'
import { useWerkStore } from '../stores/werkStore'

export function Header() {
  const location = useLocation()
  const wsConnected = useWerkStore((s) => s.wsConnected)

  return (
    <header className="border-b border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-6">
          <Link to="/" className="flex items-center gap-2">
            <span className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">Werk</span>
          </Link>
          <nav className="flex gap-4">
            <Link
              to="/"
              className={`text-sm font-medium ${
                location.pathname === '/'
                  ? 'text-indigo-600 dark:text-indigo-400'
                  : 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white'
              }`}
            >
              Canvas
            </Link>
            <Link
              to="/projects"
              className={`text-sm font-medium ${
                location.pathname.startsWith('/project')
                  ? 'text-indigo-600 dark:text-indigo-400'
                  : 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white'
              }`}
            >
              Projects
            </Link>
          </nav>
        </div>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
            <span
              className={`inline-block h-2 w-2 rounded-full ${
                wsConnected ? 'bg-green-500' : 'bg-red-400'
              }`}
            />
            {wsConnected ? 'Live' : 'Offline'}
          </span>
        </div>
      </div>
    </header>
  )
}

export default Header