import QuestionForm from '../components/QuestionForm.jsx'
import PageFooter from '../components/PageFooter.jsx'
import TutorResponse from '../components/TutorResponse.jsx'
import './TutorPage.css'

function TutorPage({ isActive, tutorSession }) {
  const {
    askQuestion,
    connection,
    followUpAvailable,
    isSubmitting,
    messages,
    prompt,
    requestFollowUp,
    retryQuestion,
    resetSession,
    sessionNotice,
    setPrompt,
  } = tutorSession

  return (
    <main id="tutor" className="page-content tutor-page" hidden={!isActive}>
      <section className="tutor-section" aria-labelledby="question-title">
        <div className="section-heading">
          <div>
            <p className="section-kicker">START A CONVERSATION</p>
            <h1 id="question-title">Ask your tutor</h1>
          </div>
          {messages.length > 0 && (
            <button className="text-button" type="button" onClick={resetSession} disabled={isSubmitting}>
              Start over
            </button>
          )}
        </div>

        <TutorResponse
          followUpAvailable={followUpAvailable}
          isReady={connection !== 'checking'}
          isSubmitting={isSubmitting}
          messages={messages}
          onAnotherExample={() => requestFollowUp('another_example')}
          onExplainMore={() => requestFollowUp('explain_more')}
          onRetry={retryQuestion}
        />
        {sessionNotice && (
          <p className="session-notice" role="status">{sessionNotice}</p>
        )}
        <QuestionForm
          isReady={connection !== 'checking'}
          isSubmitting={isSubmitting}
          hasMessages={messages.length > 0}
          onAsk={askQuestion}
          onPromptChange={setPrompt}
          prompt={prompt}
          showStarterQuestions={messages.length === 0}
        />
      </section>

      <PageFooter />
    </main>
  )
}

export default TutorPage