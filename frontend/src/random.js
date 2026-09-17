// Random credential generators, mirroring Avalon's `getRandomUserId()` /
// password randomisation UX: the join/create forms are always pre-filled,
// either from localStorage or with freshly generated values.

function pick(arr) {
  return arr[Math.floor(Math.random() * arr.length)]
}

// Friendly default usernames (letters/digits/underscore, <= 7 chars) so the
// form never starts blank.
const NAMES = [
  'Wolf', 'Moon', 'Night', 'Dark', 'Luna', 'Lupo', 'Villag', 'Seer',
  'Robin', 'Trick', 'Ghost', 'Storm', 'Raven', 'Ash', 'Fangs', 'Howl',
  'Mist', 'Dusk', 'Ember', 'Claw', 'Prowl', 'Hunter', 'Witch', 'Crow',
  'Scout', 'Bark', 'Den', 'Pack', 'Kuro', 'Miru',
]
const DIGITS = '0123456789'

export function randomUserId() {
  let name = pick(NAMES)
  name = name.length > 7 ? name.slice(0, 7) : name
  // usually keep the name; occasionally append a digit to reduce collisions
  if (Math.random() < 0.5) name += DIGITS[Math.floor(Math.random() * DIGITS.length)]
  return name.slice(0, 7)
}

// Password is a random 4-digit numeric string (matches backend `^[A-Za-z0-9]{1,6}$`).
export function randomPsw() {
  let s = ''
  for (let i = 0; i < 4; i++) s += DIGITS[Math.floor(Math.random() * DIGITS.length)]
  return s
}

// Room id: 6 characters from the full base-62 alphabet.
const ROOM_CHARS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
export function randomRoomId() {
  let s = ''
  for (let i = 0; i < 6; i++) s += ROOM_CHARS[Math.floor(Math.random() * ROOM_CHARS.length)]
  return s
}

// ---- Prefill rule shared by BOTH create-room and join-room ----
// A field that already has a saved value is RESTORED, never re-randomised:
// a returning player keeps their own identity so they're recognised and can log
// back in. Only a slot that is absent (null) or empty gets a freshly generated
// value, so a first-time visitor is never stuck with a blank form.
//
// The chosen values are PERSISTED IMMEDIATELY, not just on submit: otherwise a
// first-time visitor's freshly generated identity would be lost on the next
// refresh and they'd get a new random one every page load. Once written, the
// restore branch takes over and the fields stay stable across refreshes.
export function prefillIdentity() {
  const u = localStorage.getItem('userId')
  const p = localStorage.getItem('userPsw')
  const userid = (u !== null && u !== '') ? u : randomUserId()
  const userpsw = (p !== null && p !== '') ? p : randomPsw()
  localStorage.setItem('userId', userid)
  localStorage.setItem('userPsw', userpsw)
  return { userid, userpsw }
}

export function prefillRoomId() {
  const r = localStorage.getItem('roomId')
  const roomid = (r !== null && r !== '') ? r : randomRoomId()
  localStorage.setItem('roomId', roomid)
  return roomid
}

// Base 62, preserving leading zero digits and wrapping at the six-character limit.
const ROOM_DIGITS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
export function nextRoomId(currentId) {
  if (typeof currentId !== 'string' || !/^[A-Za-z0-9]{1,6}$/.test(currentId)) return 'a'
  const digits = [...currentId]
  for (let i = digits.length - 1; i >= 0; i--) {
    const next = ROOM_DIGITS.indexOf(digits[i]) + 1
    digits[i] = ROOM_DIGITS[next % 62]
    if (next < 62) return digits.join('')
  }
  return digits.length < 6 ? 'b' + digits.join('') : digits.join('')
}
