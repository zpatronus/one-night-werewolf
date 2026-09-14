import { base } from './store'

// Minimal HTTP layer: credentials go in the JSON body (never the URL), CSRF
// token lazily fetched once and sent as X-CSRFToken, cookies always included so
// the CSRF/session cookie round-trips. In Vite dev a proxy forwards /api -> the
// Django dev server, so everything is same-origin (no CORS in dev or prod).
let csrfToken = ''

export async function ensureToken() {
  if (csrfToken) return csrfToken
  try {
    const res = await fetch(`${base}api/csrf/`, { credentials: 'include' })
    const data = await res.json()
    csrfToken = data.csrf_token || ''
  } catch {
    csrfToken = ''
  }
  return csrfToken
}

export async function post(path, body = {}) {
  await ensureToken()
  let res
  try {
    res = await fetch(`${base}api/${path}/`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...(csrfToken ? { 'X-CSRFToken': csrfToken } : {}),
      },
      body: JSON.stringify(body),
    })
  } catch (e) {
    return { ok: false, error: 'network_error' }
  }
  let data
  try {
    data = await res.json()
  } catch {
    return { ok: false, error: `http_${res.status}` }
  }
  // If we got a fresh CSRF cookie/token, keep it for next time.
  if (data && data.csrf_token) csrfToken = data.csrf_token
  return data
}