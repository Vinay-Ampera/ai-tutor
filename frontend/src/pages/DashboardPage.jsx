import tutorArtwork from '../assets/hero.png'
import PageFooter from '../components/PageFooter.jsx'
import './DashboardPage.css'

function DashboardPage({ isActive }) {
  return (
    <main id="dashboard" className="page-content dashboard-page" hidden={!isActive}>
      <section className="dashboard-welcome" aria-labelledby="dashboard-title">
        <div className="dashboard-copy">
          <p className="eyebrow"><span className="eyebrow-line" /> YOUR LEARNING SPACE</p>
          <h1 id="dashboard-title">A good question can take you anywhere.</h1>
          <p className="welcome-description">Bring a subject you’re curious about and start with one clear explanation.</p>
          <a className="dashboard-action" href="#tutor">
            Open the tutor <span aria-hidden="true">↗</span>
          </a>
        </div>
        <div className="dashboard-artwork-wrap" aria-hidden="true">
          <img src={tutorArtwork} alt="" className="dashboard-artwork" />
        </div>
      </section>

      <section className="dashboard-start" aria-labelledby="dashboard-start-title">
        <div>
          <p className="section-kicker">READY WHEN YOU ARE</p>
          <h2 id="dashboard-start-title">What would you like to understand?</h2>
        </div>
        <a className="dashboard-text-link" href="#tutor">Ask your first question <span aria-hidden="true">→</span></a>
      </section>

      <PageFooter />
    </main>
  )
}

export default DashboardPage