import './Sidebar.css'

const navigationItems = [
  { id: 'dashboard', label: 'Home', number: '01' },
  { id: 'tutor', label: 'Tutor', number: '02' },
]

function Sidebar({ activePage }) {
  return (
    <aside className="sidebar" aria-label="Main navigation">
      <a className="brand" href="#dashboard" aria-label="AI Tutor home">
        <span className="brand-mark" aria-hidden="true">A</span>
        <span className="brand-name">AI Tutor</span>
      </a>

      <div className="sidebar-label">YOUR SPACE</div>
      <nav className="primary-nav">
        {navigationItems.map((item) => (
          <a
            aria-current={activePage === item.id ? 'page' : undefined}
            className={`nav-link${activePage === item.id ? ' is-active' : ''}`}
            href={`#${item.id}`}
            key={item.id}
          >
            <span aria-hidden="true">{item.number}</span> {item.label}
          </a>
        ))}
      </nav>

      <div className="sidebar-bottom">
        <div className="sidebar-rule" />
        <p>One question at a time.</p>
        <span>LEARN AT YOUR PACE</span>
      </div>
    </aside>
  )
}

export default Sidebar