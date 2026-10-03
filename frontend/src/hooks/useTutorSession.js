import { useEffect, useRef, useState } from 'react'
import {
  checkTutorHealth,
  clearTutorSession,
  requestTutorAnswer,
} from '../services/tutorApi.js'

const SESSION_ID_KEY = 'ai-tutor.session-id'
const SERVER_INSTANCE_ID_KEY = 'ai-tutor.server-instance-id'
const CHAT_MESSAGES_KEY = 'ai-tutor.chat-messages'

function getStoredMessages() {
  const storedMessages = window.localStorage.getItem(CHAT_MESSAGES_KEY)
  if (!storedMessages) return []

  try {
    const messages = JSON.parse(storedMessages)
    const isValid = Array.isArray(messages) && messages.every((message) =>
      message &&
      typeof message.id === 'string' &&
      typeof message.content === 'string' &&
      ['user', 'assistant', 'error'].includes(message.role),
    )
    if (isValid) return messages
  } catch (error) {
    if (!(error instanceof SyntaxError)) throw error
  }

  window.localStorage.removeItem(CHAT_MESSAGES_KEY)
  return []
}

function getOrCreateSessionId() {
  const storedSessionId = window.localStorage.getItem(SESSION_ID_KEY)
  if (storedSessionId) return storedSessionId

  const sessionId = crypto.randomUUID()
  window.localStorage.setItem(SESSION_ID_KEY, sessionId)
  return sessionId
}

export function useTutorSession() {
  const [prompt, setPrompt] = useState('')
  const [messages, setMessages] = useState(getStoredMessages)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [connection, setConnection] = useState('checking')
  const [sessionNotice, setSessionNotice] = useState('')
  const [sessionId, setSessionId] = useState(getOrCreateSessionId)
  const messageSequence = useRef(0)

  useEffect(() => {
    window.localStorage.setItem(CHAT_MESSAGES_KEY, JSON.stringify(messages))
  }, [messages])

  function createMessageId() {
    messageSequence.current += 1
    return `message-${messageSequence.current}`
  }

  useEffect(() => {
    const controller = new AbortController()

    checkTutorHealth(controller.signal)
      .then((health) => {
        const previousServerInstanceId = window.localStorage.getItem(
          SERVER_INSTANCE_ID_KEY,
        )
        if (
          previousServerInstanceId &&
          previousServerInstanceId !== health.server_instance_id
        ) {
          const nextSessionId = crypto.randomUUID()
          window.localStorage.setItem(SESSION_ID_KEY, nextSessionId)
          window.localStorage.removeItem(CHAT_MESSAGES_KEY)
          setSessionId(nextSessionId)
          setMessages([])
          setPrompt('')
        }
        window.localStorage.setItem(
          SERVER_INSTANCE_ID_KEY,
          health.server_instance_id,
        )
        setConnection('connected')
      })
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
    setSessionNotice('')

    try {
      const answer = await requestTutorAnswer(cleanedPrompt, sessionId)
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

  async function resetSession() {
    const previousSessionId = sessionId
    const nextSessionId = crypto.randomUUID()
    setPrompt('')
    setMessages([])
    setSessionId(nextSessionId)
    setSessionNotice('')
    window.localStorage.setItem(SESSION_ID_KEY, nextSessionId)
    window.localStorage.removeItem(CHAT_MESSAGES_KEY)

    try {
      await clearTutorSession(previousSessionId)
    } catch {
      setSessionNotice(
        'Chat cleared here, but the previous session could not be removed from the tutor service.',
      )
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
    isSubmitting,
    messages,
    prompt,
    retryQuestion,
    resetSession,
    sessionNotice,
    setPrompt,
  }
}