import QuestionForm from '../components/QuestionForm.jsx'
import PageFooter from '../components/PageFooter.jsx'
import TutorResponse from '../components/TutorResponse.jsx'
import './TutorPage.css'

function TutorPage({ isActive, tutorSession }) {
  const {
    askQuestion,
    isReady,
    isSubmitting,
    messages,
    prompt,
    retryQuestion,
    resetSession,
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
            <button className="text-button" type="button" onClick={resetSession} disabled={isSubmitting || !isReady}>
              Clear Chat
            </button>
          )}
        </div>

        <TutorResponse
          isSubmitting={isSubmitting}
          isReady={isReady}
          messages={messages}
          onRetry={retryQuestion}
        />
        <QuestionForm
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