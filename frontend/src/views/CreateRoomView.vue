<script setup>
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { post } from '../api'
import { setAuth } from '../store'
import { errorText } from '../gameConfig'
import { getMyAvatar } from '../avatar'
import { prefillIdentity, prefillRoomId, nextRoomId, randomPsw } from '../random'
import AvatarField from './AvatarField.vue'

const router = useRouter()
// Restore stored creds; only an absent slot gets a fresh random value, so a
// returning player keeps their identity. True for create AND join alike.
const roomid = ref(prefillRoomId())
const identity = prefillIdentity()
const userid = ref(identity.userid)
const userpsw = ref(identity.userpsw)
const avatar = ref(getMyAvatar())
const err = ref('')
const busy = ref(false)

// Sync every change to localStorage immediately — human typing AND the random
// buttons alike (mirrors Avalon's per-field updateRoomInfo()). So whatever is
// on screen right now is what a refresh will restore.
watch([roomid, userid, userpsw], ([r, u, p]) => {
  localStorage.setItem('roomId', r)
  localStorage.setItem('userId', u)
  localStorage.setItem('userPsw', p)
})

const canSave = computed(
  () => /^[A-Za-z0-9]{1,6}$/.test(roomid.value)
    && /^[A-Za-z0-9_]{1,7}$/.test(userid.value)
    && /^[A-Za-z0-9]{1,6}$/.test(userpsw.value),
)

// Room id "下一个" button — step to the next id (same as Avalon).
function nextId() {
  roomid.value = nextRoomId(roomid.value)
}
// Password button (suggested random 4-digit number).
function nextPsw() {
  userpsw.value = randomPsw()
}

async function submit() {
  if (!canSave.value || busy.value) return
  busy.value = true
  err.value = ''
  const res = await post('create_room', {
    roomid: roomid.value, userid: userid.value, userpsw: userpsw.value, avatar: avatar.value,
  })
  busy.value = false
  if (!res.ok) { err.value = errorText(res.error); return }
  setAuth({ roomid: roomid.value, userid: userid.value, userpsw: userpsw.value, avatar: res.avatar })
  router.push('/waitingroom')
}
</script>

<template>
  <div class="container">
    <div class="subtitle">房间ID</div>
    <div class="field-row">
      <input v-model.trim="roomid" maxlength="6" placeholder="房间ID" />
      <button type="button" @click="nextId">下一个</button>
    </div>
    <div class="subtitle">玩家ID</div>
    <input v-model.trim="userid" maxlength="7" placeholder="玩家ID" />
    <div class="subtitle">玩家密码</div>
    <div class="field-row">
      <input v-model.trim="userpsw" maxlength="6" placeholder="玩家密码" />
      <button type="button" @click="nextPsw">随机</button>
    </div>
    <AvatarField v-model="avatar" />
    <ul class="tips">
      <li>不要使用常用密码，建议点击“随机”。</li>
      <li>玩家密码不是房间密码，网站不存在房间密码。</li>
      <li>密码会明文保存在本地，刷新后自动填入，防止同房间他人窥探你的身份。</li>
    </ul>
    <button class="btn-primary btn-block" :disabled="!canSave || busy" @click="submit">
      {{ busy ? '创建中…' : '创建房间' }}
    </button>
    <div class="status">{{ err }}</div>
  </div>
</template>