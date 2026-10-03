import { useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import './TutorResponse.css'

function TutorResponse({
  followUpAvailable,
  isReady,
  messages,
  isSubmitting,
  onAnotherExample,
  onExplainMore,
  onRetry,
}) {
  const historyRef = useRef(null)

  useEffect(() => {
    const history = historyRef.current
    if (history) history.scrollTo({ top: history.scrollHeight, behavior: 'smooth' })
  }, [messages, isSubmitting])

  return (
    <section
      ref={historyRef}
      className="conversation-history"
      aria-live="polite"
      aria-busy={isSubmitting}
      aria-label="Conversation"
    >
      {messages.map((message) => (
        <article className={`chat-message ${message.role}-message`} key={message.id}>
          {message.role === 'user' ? (
            <>
              <p className="message-label">You</p>
              <p className="message-content">{message.content}</p>
            </>
          ) : (
            <>
              <div className="answer-heading">
                <span className={`answer-mark${message.role === 'error' ? ' is-error' : ''}`} aria-hidden="true">
                  {message.role === 'error' ? '!' : 'A'}
                </span>
                <p className="answer-kicker">{message.role === 'error' ? 'TUTOR STATUS' : 'YOUR TUTOR'}</p>
              </div>
              {message.role === 'assistant' ? (
                <div className="message-content assistant-markdown">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {message.content}
                  </ReactMarkdown>
                </div>
              ) : (
                <p className="message-content">{message.content}</p>
              )}
              {message.role === 'error' && (
                <button
                  className="retry-button"
                  type="button"
                  onClick={() =>
                    onRetry(message.id, message.retryPrompt, message.retryAction)
                  }
                  disabled={isSubmitting}
                >
                  Try again
                </button>
              )}
            </>
          )}
        </article>
      ))}

      {isSubmitting && (
        <div className="chat-message assistant-message loading-message">
          <div className="answer-heading">
            <span className="answer-mark" aria-hidden="true">A</span>
            <p className="answer-kicker">YOUR TUTOR</p>
          </div>
          <div className="loading-copy">
            <span className="response-indicator" aria-hidden="true"><span /></span>
            <p>Thinking it through…</p>
          </div>
        </div>
      )}

      {followUpAvailable && (
        <div className="follow-up-actions" aria-label="Learning follow-ups">
          <button
            className="follow-up-button"
            type="button"
            onClick={onExplainMore}
            disabled={isSubmitting || !isReady}
          >
            Explain More
          </button>
          <button
            className="follow-up-button"
            type="button"
            onClick={onAnotherExample}
            disabled={isSubmitting || !isReady}
          >
            Another Example
          </button>
        </div>
      )}
    </section>
  )
}

export default TutorResponse