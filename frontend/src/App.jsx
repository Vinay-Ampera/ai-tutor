import { useEffect, useState } from 'react'
import Sidebar from './components/Sidebar.jsx'
import WorkspaceHeader from './components/WorkspaceHeader.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import TutorPage from './pages/TutorPage.jsx'
import { useTutorSession } from './hooks/useTutorSession.js'
import './App.css'

function getPageFromHash() {
  return window.location.hash === '#tutor' ? 'tutor' : 'dashboard'
}

function App() {
  const [activePage, setActivePage] = useState(getPageFromHash)
  const tutorSession = useTutorSession()

  useEffect(() => {
    function handleHashChange() {
      setActivePage(getPageFromHash())
    }

    window.addEventListener('hashchange', handleHashChange)
    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [])

  useEffect(() => {
    document.title = activePage === 'tutor'
      ? 'Tutor | AI Tutor'
      : 'Dashboard | AI Tutor'
  }, [activePage])

  return (
    <div className="app-shell">
      <Sidebar activePage={activePage} />

      <div className="workspace">
        <WorkspaceHeader activePage={activePage} connection={tutorSession.connection} />
        <DashboardPage isActive={activePage === 'dashboard'} />
        <TutorPage isActive={activePage === 'tutor'} tutorSession={tutorSession} />
      </div>
    </div>
  )
}

export default App