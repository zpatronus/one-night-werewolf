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

// Room id: 5 letters from an unambiguous set (no 0/O/1/I).
const ROOM_CHARS = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
export function randomRoomId() {
  let s = ''
  for (let i = 0; i < 5; i++) s += ROOM_CHARS[Math.floor(Math.random() * ROOM_CHARS.length)]
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

// ---- The room-id "下一个" (next) button ----
// Mirrors Avalon's generateNextRoomId(): keep any letter prefix and STEP the
// trailing number (appending '0' when there is none), so repeated clicks walk
// the id forward predictably instead of jumping about. Only when stepping would
// exceed the 6-char [A-Za-z0-9] limit do we fall back to a fresh random id.
function isValidRoomId(id) {
  return /^[A-Za-z0-9]{1,6}$/.test(id)
}
export function nextRoomId(currentId) {
  if (currentId === '') return randomRoomId()

  let prefix = ''
  let numberPart = ''
  for (let i = 0; i < currentId.length; i++) {
    const c = currentId[i]
    if (isNaN(parseInt(c))) {
      prefix += c
    } else {
      numberPart = currentId.slice(i)
      break
    }
  }

  const stepped = numberPart ? prefix + (parseInt(numberPart) + 1) : prefix + '0'
  return isValidRoomId(stepped) ? stepped : randomRoomId()
}