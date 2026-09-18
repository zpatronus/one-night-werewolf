const pending = new Map()
export const IMAGE_CACHE_TTL = 24 * 60 * 60 * 1000
const isImage = value => typeof value === 'string' && /^data:image\/webp;base64,[A-Za-z0-9+/]+={0,2}$/.test(value)

export function cachedImage(filename, url) {
  try {
    const entry = JSON.parse(localStorage.getItem(filename))
    // The bundled URL changes when Vite fingerprints new artwork.
    const age = Date.now() - entry?.savedAt
    if (entry?.url === url && isImage(entry.data) && Number.isFinite(age) && age >= 0 && age < IMAGE_CACHE_TTL) return entry.data
    forgetImage(filename)
    return null
  } catch {
    return null
  }
}

export function forgetImage(filename) {
  try { localStorage.removeItem(filename) } catch { /* Storage may be blocked. */ }
}

// Called after an image loads, preserving native lazy loading for closed panels.
export function cacheImage(filename, url) {
  if (cachedImage(filename, url)) return Promise.resolve()
  if (pending.has(url)) return pending.get(url)
  const job = (async () => {
    try {
      const response = await fetch(url)
      if (!response.ok) return
      const blob = await response.blob()
      if (blob.type !== 'image/webp') return
      const data = await new Promise((resolve, reject) => {
        const reader = new FileReader()
        reader.onload = () => resolve(reader.result)
        reader.onerror = () => reject(reader.error)
        reader.readAsDataURL(blob)
      })
      if (isImage(data)) localStorage.setItem(filename, JSON.stringify({ url, data, savedAt: Date.now() }))
    } catch {
      // Network errors, unavailable storage, and quota limits leave the asset usable.
    }
  })().finally(() => pending.delete(url))
  pending.set(url, job)
  return job
}
