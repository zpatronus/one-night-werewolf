// Stable, deterministic player ordering used across a game, based on a hash of
// (roomId, username). Two clients see the same seat order without a DB field.
export function orderKey(roomid, userid) {
  let h = 2166136261 >>> 0
  const s = `${roomid}|${userid}`
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i)
    h = Math.imul(h, 16777619) >>> 0
  }
  return h
}

export function sortPlayers(roomid, users) {
  return [...users].sort((a, b) => orderKey(roomid, a.userid) - orderKey(roomid, b.userid))
}