import test from 'node:test'
import assert from 'node:assert/strict'
import { cachedImage, cacheImage, IMAGE_CACHE_TTL } from '../src/imageCache.js'

test('image cache uses filename keys, rejects stale data, and tolerates storage failures', async () => {
  const entries = new Map()
  const data = 'data:image/webp;base64,UklGRg=='
  const original = { storage: globalThis.localStorage, fetch: globalThis.fetch, reader: globalThis.FileReader }
  let requests = 0
  try {
    globalThis.localStorage = {
      getItem: key => entries.get(key) ?? null,
      setItem: (key, value) => entries.set(key, value),
      removeItem: key => entries.delete(key),
    }
    globalThis.fetch = async () => {
      requests++
      return { ok: true, blob: async () => ({ type: 'image/webp' }) }
    }
    globalThis.FileReader = class {
      readAsDataURL() { this.result = data; this.onload() }
    }
    await Promise.all([cacheImage('werewolf.webp', '/wolf-v1.webp'), cacheImage('werewolf.webp', '/wolf-v1.webp')])
    assert.equal(requests, 1)
    assert.equal(cachedImage('werewolf.webp', '/wolf-v1.webp'), data)
    assert.equal(entries.size, 1)
    await cacheImage('werewolf.webp', '/wolf-v1.webp')
    assert.equal(requests, 1)
    assert.equal(cachedImage('werewolf.webp', '/wolf-v2.webp'), null)
    await cacheImage('werewolf.webp', '/wolf-v2.webp')
    assert.equal(cachedImage('werewolf.webp', '/wolf-v2.webp'), data)
    const fresh = JSON.parse(entries.get('werewolf.webp'))
    const now = Date.now
    try {
      Date.now = () => fresh.savedAt + IMAGE_CACHE_TTL - 1
      assert.equal(cachedImage('werewolf.webp', '/wolf-v2.webp'), data)
      Date.now = () => fresh.savedAt + IMAGE_CACHE_TTL
      assert.equal(cachedImage('werewolf.webp', '/wolf-v2.webp'), null)
      assert.equal(entries.has('werewolf.webp'), false)
      await cacheImage('werewolf.webp', '/wolf-v2.webp')
      assert.equal(cachedImage('werewolf.webp', '/wolf-v2.webp'), data)
    } finally { Date.now = now }
    entries.set('werewolf.webp', JSON.stringify({ url: '/wolf-v2.webp', data }))
    assert.equal(cachedImage('werewolf.webp', '/wolf-v2.webp'), null)
    entries.set('werewolf.webp', '{broken')
    assert.equal(cachedImage('werewolf.webp', '/wolf-v2.webp'), null)
    globalThis.localStorage = {
      getItem() { throw new Error('blocked') },
      setItem() { throw new Error('quota') },
    }
    assert.equal(cachedImage('werewolf.webp', '/wolf-v2.webp'), null)
    await assert.doesNotReject(cacheImage('werewolf.webp', '/wolf-v2.webp'))
  } finally {
    globalThis.localStorage = original.storage
    globalThis.fetch = original.fetch
    globalThis.FileReader = original.reader
  }
})
