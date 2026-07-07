import { BrowserRouter, Routes, Route } from 'react-router-dom'
import AgentCanvas from './pages/AgentCanvas'
import Dashboard from './pages/Dashboard'
import ProjectView from './pages/ProjectView'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AgentCanvas />} />
        <Route path="/projects" element={<Dashboard />} />
        <Route path="/project/:id" element={<ProjectView />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
