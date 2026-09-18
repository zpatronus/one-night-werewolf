export function localDateKey(date = new Date()) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

// No session state or random seed: reconnecting on any device preserves the choice.
export function roleVariant(role, { roomid = '', userid = '', date = localDateKey() } = {}) {
  const key = JSON.stringify(roomid && userid ? ['room', roomid, userid, role] : ['day', date, role])
  let hash = 2166136261
  for (let i = 0; i < key.length; i++) hash = Math.imul(hash ^ key.charCodeAt(i), 16777619)
  // Mix high bits into low bits so each role gets an independent-looking choice.
  hash ^= hash >>> 16
  hash = Math.imul(hash, 0x85ebca6b)
  hash ^= hash >>> 13
  return (hash >>> 0) % 3 + 1
}
