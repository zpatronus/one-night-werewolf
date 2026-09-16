<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { post } from '../api'
import { setAuth } from '../store'
import { errorText } from '../gameConfig'
import { getMyAvatar } from '../avatar'
import { prefillIdentity, prefillRoomId, nextRoomId, randomPsw } from '../random'
import AvatarField from './AvatarField.vue'

const router = useRouter()
const route = useRoute()
const PHASE_ROUTE = { waiting: '/waitingroom', op: '/ops', reveal: '/reveal', result: '/result' }
// Identical prefill to CreateRoomView: restore stored creds verbatim; only an
// absent slot gets a fresh random value, so a returning player is never given
// a new identity. Values persist only on a successful join (see submit).
const roomid = ref(prefillRoomId())
const identity = prefillIdentity()
const userid = ref(identity.userid)
const userpsw = ref(identity.userpsw)
const avatar = ref(getMyAvatar())
const err = ref('')
const busy = ref(false)

// Sync every change to localStorage immediately — human typing AND the "下一个" /
// "随机" buttons alike (mirrors Avalon's per-field updateRoomInfo()). Whatever is
// on screen right now is what a refresh will restore.
watch([roomid, userid, userpsw], ([r, u, p]) => {
  localStorage.setItem('roomId', r)
  localStorage.setItem('userId', u)
  localStorage.setItem('userPsw', p)
})

// An invite link (`/joinroom?room=ABC12`) drops the visitor straight onto this
// room: override whatever was pre-filled with the shared room id. The watch above
// persists it to localStorage so it sticks on refresh.
onMounted(() => {
  const room = route.query.room
  if (room !== undefined && /^[A-Za-z0-9]{1,6}$/.test(String(room))) {
    roomid.value = String(room)
  }
})

const canSave = computed(
  () => /^[A-Za-z0-9]{1,6}$/.test(roomid.value)
    && /^[A-Za-z0-9_]{1,7}$/.test(userid.value)
    && /^[A-Za-z0-9]{1,6}$/.test(userpsw.value),
)

async function submit() {
  if (!canSave.value || busy.value) return
  busy.value = true
  err.value = ''
  const res = await post('join_room', {
    roomid: roomid.value, userid: userid.value, userpsw: userpsw.value, avatar: avatar.value,
  })
  busy.value = false
  if (!res.ok) { err.value = errorText(res.error); return }
  setAuth({ roomid: roomid.value, userid: userid.value, userpsw: userpsw.value, avatar: res.avatar })
  // Route by the game's current phase (from the join response) so a returning
  // player lands directly where the game is — e.g. straight on the result page —
  // instead of being dumped into the waiting room.
  router.push(PHASE_ROUTE[res.phase] || '/waitingroom')
}
</script>

<template>
  <div class="container">
    <div class="subtitle">房间ID</div>
    <div class="field-row">
      <input v-model.trim="roomid" maxlength="6" placeholder="房间ID" />
      <button type="button" @click="roomid = nextRoomId(roomid)">下一个</button>
    </div>
    <div class="subtitle">玩家ID</div>
    <input v-model.trim="userid" maxlength="7" placeholder="玩家ID" />
    <div class="subtitle">玩家密码</div>
    <div class="field-row">
      <input v-model.trim="userpsw" maxlength="6" placeholder="玩家密码" />
      <button type="button" @click="userpsw = randomPsw()">随机</button>
    </div>
    <AvatarField v-model="avatar" />
    <ul class="tips">
      <li>不要使用常用密码，建议点击“随机”。</li>
      <li>玩家密码不是房间密码，网站不存在房间密码。</li>
      <li>建议随机输入，密码会明文保存在本地，刷新后自动填入，防止同房间他人窥探你的身份。</li>
    </ul>
    <button class="btn-primary btn-block" :disabled="!canSave || busy" @click="submit">
      {{ busy ? '加入中…' : '加入房间' }}
    </button>
    <div class="status">{{ err }}</div>
  </div>
</template>