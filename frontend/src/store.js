import { reactive } from 'vue'

// Lightweight auth/session holder. Credentials live here after create/join and
// are sent in every API body (the backend authenticates each request by them —
// no server-side session beyond Django's CSRF cookie).
export const auth = reactive({
  roomid: localStorage.getItem('roomId') || '',
  userid: localStorage.getItem('userId') || '',
  userpsw: localStorage.getItem('userPsw') || '',
  avatar: localStorage.getItem('avatar') || '',
})

export function setAuth({ roomid, userid, userpsw, avatar } = {}) {
  if (roomid != null) { auth.roomid = roomid; localStorage.setItem('roomId', roomid) }
  if (userid != null) { auth.userid = userid; localStorage.setItem('userId', userid) }
  if (userpsw != null) { auth.userpsw = userpsw; localStorage.setItem('userPsw', userpsw) }
  if (avatar != null) { auth.avatar = avatar; localStorage.setItem('avatar', avatar) }
}

// The credentials object every API call includes.
export function creds() {
  return { roomid: auth.roomid, userid: auth.userid, userpsw: auth.userpsw }
}

// Site URL prefix (empty at root; nginx sub-path deploys fill it). All request
// URLs and asset URLs go through this so a prefix-mounted site still works.
export const base = import.meta.env.BASE_URL