const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

async function readResponse(response) {
  const result = await response.json().catch(() => ({}))

  if (!response.ok) {
    const message = typeof result.detail === 'string'
      ? result.detail
      : 'The tutor could not answer right now. Please try again.'
    throw new Error(message)
  }

  return result
}

export async function checkTutorHealth(signal) {
  const response = await fetch(`${API_BASE_URL}/`, { signal })
  return readResponse(response)
}

export async function clearTutorSession(sessionId) {
  const response = await fetch(
    `${API_BASE_URL}/api/sessions/${encodeURIComponent(sessionId)}`,
    { method: 'DELETE' },
  )
  await readResponse(response)
}

export async function requestTutorAnswer(prompt, sessionId) {
  const response = await fetch(`${API_BASE_URL}/api/gemini/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, session_id: sessionId }),
  })
  const result = await readResponse(response)

  if (typeof result.text !== 'string' || !result.text.trim()) {
    throw new Error('The tutor returned an empty response. Please try again.')
  }

  return result.text.trim()
}