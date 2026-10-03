import { useEffect, useRef, useState } from 'react'
import { checkTutorHealth, requestTutorAnswer } from '../services/tutorApi.js'

export function useTutorSession() {
  const [prompt, setPrompt] = useState('')
  const [messages, setMessages] = useState([])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [connection, setConnection] = useState('checking')
  const messageSequence = useRef(0)
  const sessionId = useRef(crypto.randomUUID())

  function createMessageId() {
    messageSequence.current += 1
    return `message-${messageSequence.current}`
  }

  useEffect(() => {
    const controller = new AbortController()

    checkTutorHealth(controller.signal)
      .then(() => setConnection('connected'))
      .catch(() => {
        if (!controller.signal.aborted) setConnection('disconnected')
      })

    return () => controller.abort()
  }, [])

  async function askQuestion(question = prompt, { addQuestion = true } = {}) {
    const cleanedPrompt = question.trim()
    if (!cleanedPrompt || isSubmitting) return

    if (addQuestion) {
      setMessages((currentMessages) => [
        ...currentMessages,
        { id: createMessageId(), role: 'user', content: cleanedPrompt },
      ])
      setPrompt('')
    }

    setIsSubmitting(true)

    try {
      const answer = await requestTutorAnswer(cleanedPrompt, sessionId.current)
      setMessages((currentMessages) => [
        ...currentMessages,
        { id: createMessageId(), role: 'assistant', content: answer },
      ])
    } catch (requestError) {
      const message =
        requestError instanceof TypeError
          ? 'Could not reach the tutor service. Check that the backend is running and try again.'
          : requestError.message || 'Something went wrong. Please try again.'

      setMessages((currentMessages) => [
        ...currentMessages,
        {
          id: createMessageId(),
          role: 'error',
          content: message,
          retryPrompt: cleanedPrompt,
        },
      ])
    } finally {
      setIsSubmitting(false)
    }
  }

  function resetSession() {
    setPrompt('')
    setMessages([])
    sessionId.current = crypto.randomUUID()
  }

  function retryQuestion(errorMessageId, question) {
    setMessages((currentMessages) =>
      currentMessages.filter((message) => message.id !== errorMessageId),
    )
    return askQuestion(question, { addQuestion: false })
  }

  return {
    askQuestion,
    connection,
    isSubmitting,
    messages,
    prompt,
    retryQuestion,
    resetSession,
    setPrompt,
  }
}