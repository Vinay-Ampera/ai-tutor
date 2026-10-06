import { useRef } from 'react'
import './QuestionForm.css'

const starterQuestions = [
  'Explain Python loops simply',
  'What is recursion?',
  'How do variables work?',
]

function QuestionForm({
  hasMessages,
  isReady,
  isSubmitting,
  onAsk,
  onPromptChange,
  prompt,
  showStarterQuestions,
}) {
  const questionInput = useRef(null)

  function handleSubmit(event) {
    event.preventDefault()
    onAsk(prompt)
  }

  function handleStarterQuestion(question) {
    onPromptChange(question)
    questionInput.current?.focus()
  }

  return (
    <form className="question-form" onSubmit={handleSubmit}>
      {showStarterQuestions && !hasMessages && (
        <div className="starter-prompts">
          <span className="starter-label">A few starting points</span>
          <div className="starter-list">
            {starterQuestions.map((question) => (
              <button
                className="starter-button"
                key={question}
                onClick={() => handleStarterQuestion(question)}
                type="button"
              >
                {question}<span aria-hidden="true">↗</span>
              </button>
            ))}
          </div>
        </div>
      )}

        <label className="visually-hidden" htmlFor="question-input">Your question</label>
        <textarea
          ref={questionInput}
          id="question-input"
          value={prompt}
          onChange={(event) => onPromptChange(event.target.value)}
          placeholder="Type here.."
          maxLength={2000}
          rows={4}
          disabled={isSubmitting}
          required
        />
        <div className="form-footer">
          <span className="character-count">{prompt.length} / 2000</span>
          <button className="submit-button" type="submit" disabled={!prompt.trim() || isSubmitting || !isReady}>
            {isSubmitting ? (
              <><span className="button-spinner" aria-hidden="true" /> Thinking</>
            ) : (
              <>Ask tutor <span aria-hidden="true">↗</span></>
            )}
          </button>
        </div>
    </form>
  )
}

export default QuestionForm