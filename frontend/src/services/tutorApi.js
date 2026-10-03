const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

async function readResponse(response) {
  const result = await response.json().catch(() => ({}))

  if (!response.ok) {
    const message = typeof result.detail === 'string'
      ? result.detail
      : 'The tutor could not answer right now. Please try again.'
    const error = new Error(message)
    error.status = response.status
    throw error
  }

  return result
}

export async function checkTutorHealth(signal) {
  const response = await fetch(`${API_BASE_URL}/`, { signal })
  await readResponse(response)
}

export async function requestTutorAnswer(prompt, sessionId) {
  const request = { prompt }
  if (sessionId) request.session_id = sessionId

  const response = await fetch(`${API_BASE_URL}/api/gemini/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  const result = await readResponse(response)

  if (
    typeof result.text !== 'string' ||
    !result.text.trim() ||
    typeof result.session_id !== 'string' ||
    !result.session_id
  ) {
    throw new Error('The tutor returned an incomplete response. Please try again.')
  }

  return { text: result.text.trim(), sessionId: result.session_id }
}

export async function getTutorSession(sessionId, signal) {
  const response = await fetch(
    `${API_BASE_URL}/api/sessions/${encodeURIComponent(sessionId)}`,
    { signal },
  )
  const result = await readResponse(response)

  if (!Array.isArray(result.messages)) {
    throw new Error('The tutor returned an invalid session history.')
  }

  return result.messages
}

export async function clearTutorSession(sessionId) {
  const response = await fetch(
    `${API_BASE_URL}/api/sessions/${encodeURIComponent(sessionId)}`,
    { method: 'DELETE' },
  )
  if (response.status !== 404) await readResponse(response)
}