import { useEffect, useRef, useState } from 'react'
import {
  checkTutorHealth,
  clearTutorSession,
  getTutorSession,
  requestTutorAnswer,
} from '../services/tutorApi.js'

const SESSION_STORAGE_KEY = 'ai-tutor-session-id'

export function useTutorSession() {
  const [prompt, setPrompt] = useState('')
  const [messages, setMessages] = useState([])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [connection, setConnection] = useState('checking')
  const messageSequence = useRef(0)
  const restoreController = useRef(null)
  const [sessionId, setSessionId] = useState(
    () => window.localStorage.getItem(SESSION_STORAGE_KEY),
  )
  const [isRestoring, setIsRestoring] = useState(
    () => Boolean(window.localStorage.getItem(SESSION_STORAGE_KEY)),
  )

  function createMessageId() {
    messageSequence.current += 1
    return `message-${messageSequence.current}`
  }

  useEffect(() => {
    const healthController = new AbortController()

    checkTutorHealth(healthController.signal)
      .then(() => setConnection('connected'))
      .catch(() => {
        if (!healthController.signal.aborted) setConnection('disconnected')
      })

    const storedSessionId = window.localStorage.getItem(SESSION_STORAGE_KEY)
    if (!storedSessionId) {
      return () => healthController.abort()
    }

    const sessionController = new AbortController()
    restoreController.current = sessionController
    getTutorSession(storedSessionId, sessionController.signal)
      .then((history) => {
        if (sessionController.signal.aborted) return
        setMessages(
          history.map((message) => ({
            id: createMessageId(),
            role: message.role,
            content: message.content,
          })),
        )
      })
      .catch((restoreError) => {
        if (sessionController.signal.aborted) return
        if (restoreError.status === 404) {
          window.localStorage.removeItem(SESSION_STORAGE_KEY)
          setSessionId(null)
        } else {
          setConnection('disconnected')
        }
      })
      .finally(() => {
        if (!sessionController.signal.aborted) setIsRestoring(false)
      })

    return () => {
      healthController.abort()
      sessionController.abort()
    }
  }, [])

  async function askQuestion(question = prompt, { addQuestion = true } = {}) {
    const cleanedPrompt = question.trim()
    if (!cleanedPrompt || isSubmitting) return

    restoreController.current?.abort()
    restoreController.current = null
    setIsRestoring(false)

    if (addQuestion) {
      setMessages((currentMessages) => [
        ...currentMessages,
        { id: createMessageId(), role: 'user', content: cleanedPrompt },
      ])
      setPrompt('')
    }

    setIsSubmitting(true)

    try {
      const result = await requestTutorAnswer(cleanedPrompt, sessionId)
      setSessionId(result.sessionId)
      window.localStorage.setItem(SESSION_STORAGE_KEY, result.sessionId)
      setMessages((currentMessages) => [
        ...currentMessages,
        { id: createMessageId(), role: 'assistant', content: result.text },
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

  async function resetSession() {
    if (isSubmitting || isRestoring) return
    setIsSubmitting(true)

    try {
      if (sessionId) await clearTutorSession(sessionId)
      window.localStorage.removeItem(SESSION_STORAGE_KEY)
      setSessionId(null)
      setPrompt('')
      setMessages([])
    } catch (clearError) {
      setMessages((currentMessages) => [
        ...currentMessages,
        {
          id: createMessageId(),
          role: 'error',
          content: clearError.message || 'Could not clear this session. Please try again.',
        },
      ])
    } finally {
      setIsSubmitting(false)
    }
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
    isReady: !isRestoring,
    isSubmitting,
    messages,
    prompt,
    retryQuestion,
    resetSession,
    setPrompt,
  }
}