import './WorkspaceHeader.css'

const pageTitles = {
  dashboard: 'Home',
  tutor: 'Tutor',
}

const connectionLabels = {
  checking: 'Checking tutor',
  connected: 'Tutor connected',
  disconnected: 'Tutor unavailable',
}

function WorkspaceHeader({ activePage, connection }) {
  return (
    <header className="topbar">
      <div className="breadcrumb">
        <span>Workspace</span>
        <span aria-hidden="true">/</span>
        <strong>{pageTitles[activePage]}</strong>
      </div>
      <div className={`connection-status is-${connection}`} role="status">
        <span className="connection-dot" aria-hidden="true" />
        {connectionLabels[connection]}
      </div>
    </header>
  )
}

export default WorkspaceHeader