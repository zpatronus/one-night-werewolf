<script setup>
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { post } from '../api'
import { setAuth } from '../store'
import { errorText, localBoardForCreation } from '../gameConfig'
import { getMyAvatar } from '../avatar'
import { prefillIdentity, prefillRoomId, nextRoomId, randomRoomId, randomPsw } from '../random'
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
    board: localBoardForCreation(),
  })
  busy.value = false
  if (!res.ok) { err.value = errorText(res.error); return }
  setAuth({ roomid: roomid.value, userid: userid.value, userpsw: userpsw.value, avatar: res.avatar })
  router.push('/waitingroom')
}
</script>

<template>
  <form class="container entry-form" @submit.prevent="submit">
    <header class="entry-heading"><h1>创建房间</h1></header>
    <div class="entry-group">
      <label for="room-id">房间号</label>
      <div class="field-row room-field">
        <input id="room-id" v-model.trim="roomid" maxlength="6" placeholder="房间号" autocapitalize="off" spellcheck="false" aria-describedby="room-hint" />
        <button type="button" @click="roomid = randomRoomId()">随机</button>
        <button type="button" @click="nextId">下一个</button>
      </div>
      <p id="room-hint" class="field-hint">1–6 位字母或数字，区分大小写</p>
    </div>
    <div class="entry-divider"></div>
    <div class="entry-group">
      <label for="player-id">玩家名</label>
      <input id="player-id" v-model.trim="userid" maxlength="7" placeholder="玩家名" autocapitalize="off" spellcheck="false" aria-describedby="player-hint" />
      <p id="player-hint" class="field-hint">1–7 位字母、数字或下划线</p>
    </div>
    <div class="entry-group">
      <label for="player-password">玩家密码</label>
      <div class="field-row">
        <input id="player-password" v-model.trim="userpsw" maxlength="6" placeholder="玩家密码" autocapitalize="off" spellcheck="false" aria-describedby="password-hint" />
        <button type="button" @click="nextPsw">随机</button>
      </div>
      <p id="password-hint" class="field-hint">用于重新加入，非房间密码。1–6 位字母或数字。</p>
    </div>
    <div class="entry-avatar"><AvatarField v-model="avatar" /></div>
    <p class="entry-note">密码会明文保存在本机。请使用随机密码，勿使用常用密码。</p>
    <button type="submit" class="btn-primary btn-block entry-submit" :disabled="!canSave || busy">
      {{ busy ? '创建中…' : '创建房间' }}
    </button>
    <p v-if="err" class="error" role="alert">{{ err }}</p>
  </form>
</template>
