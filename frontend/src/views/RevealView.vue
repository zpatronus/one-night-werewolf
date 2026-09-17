<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { post } from '../api'
import { creds } from '../store'
import { useRoomState } from '../useRoomState'
import { roleName, roleIcon, errorText, ROLE_ORDER } from '../gameConfig'
import { avatarUrl, getMyAvatar } from '../avatar'
import { sortPlayers } from '../playerOrder'
import ConfirmDialog from '../components/ConfirmDialog.vue'

const { state, poll, applyState } = useRoomState()   // polls + routes to /result when voting ends
const me = ref(null)               // one-shot POST /reveal body
const err = ref('')
const busy = ref(false)
const loading = ref(false)
const target = ref('')             // "" = abstain
const confirmOpen = ref(false)     // vote double-check dialog
const showRole = ref(true)         // role info shown by default, hide on demand

async function loadReveal() {
  if (loading.value) return
  loading.value = true
  err.value = ''
  try {
    const snapshot = await poll()
    if (!snapshot || snapshot.phase !== 'reveal') {
      if (!snapshot) err.value = errorText('network_error')
      return
    }
    const res = await post('reveal', creds())
    if (!res.ok) { err.value = errorText(res.error); return }
    me.value = res
  } finally { loading.value = false }
}
onMounted(loadReveal)

const users = computed(() => sortPlayers(creds().roomid, (me.value?.users || []).filter(u => u.userid !== creds().userid)))
const voted = computed(() => state.value?.voted ?? me.value?.voted)
// The board (template) and room info are one-shot from /reveal, never polled.
const boardChips = computed(() =>
  ROLE_ORDER.filter((r) => (me.value?.board?.[r] || 0) > 0))
const meCard = computed(() => ({
  ...(me.value?.me || {}),
  avatar: avatarUrl(me.value?.me?.avatar || getMyAvatar()),
}))

// After a refresh/rejoin the local selection is lost; re-highlight the caller's
// own vote from the server. Only hydrate once we actually voted (vote_target
// set) so we never clobber an in-progress pick before submitting.
watch(state, (s) => {
  if (s?.vote_target !== undefined && s?.vote_target !== null) {
    target.value = s.vote_target
  }
}, { immediate: true })

function pick(u) {
  if (voted.value) return
  target.value = target.value === u ? '' : u
}
function abstain() { pick('') }

function openConfirm() {
  if (voted.value || busy.value) return
  confirmOpen.value = true
}
function confirmVote() {
  confirmOpen.value = false
  vote()
}

// Avalon-style selection status line.
function selectionText() {
  return target.value ? `已选择：${target.value}` : '（弃权）当前未选择处决对象'
}

function describe() {
  const r = me.value
  if (!r) return ''
  const info = r.info || {}
  const peek = (c) => `${roleIcon(c)} ${roleName(c)}`
  switch (r.role) {
    case 'werewolf':
      // a lone wolf actually peeked (info.peek set); a pack wolf only knows its pack.
      if (info.peek) {
        return `你是独狼。你选择窥视中央第 ${(parseInt(String(info.target).split('_')[1]) || 0) + 1} 张，它是 ${peek(info.peek)}。`
      }
      return `你是狼人，狼队友：${(info.teammates || []).join('、')}。`
    case 'minion':
      return info.teammates?.length
        ? `你是爪牙。夜晚开始时，狼人玩家是：${info.teammates.join('、')}。`
        : '你是爪牙。夜晚开始时，场上没有狼人玩家。'
    case 'seer':
      if (info.center_picks && info.center_picks.length) {
        const items = info.center_picks.map((idx, k) => `中央第 ${idx + 1} 张`)
        const cards = info.center_picks.map((idx, k) => peek(info.peeked[k]))
        return `你是预言家。你选择窥视${items.join('、')}，牌面分别是 ${cards.join('、')}。`
      }
      return `你是预言家。你选择窥视 ${info.target} 的身份，他的初始身份（换牌前）是 ${peek(info.peeked?.[0])}。`
    case 'robber':
      return `你是强盗。你选择与 ${info.target} 交换身份，交换完成当时看到的牌是 ${peek(info.new_role)}。`
    case 'troublemaker':
      return `你是捣蛋鬼。你选择交换 ${info.target} 与 ${info.target2} 的牌。`
    case 'insomniac':
      return `你是失眠者，你在熬夜中知晓了自己的最终身份。`
    case 'villager':
      return `你是村民，夜里没有行动。`
    default:
      return ''
  }
}

async function vote() {
  if (voted.value || busy.value) return
  busy.value = true
  err.value = ''
  const res = await post('vote', { ...creds(), target: target.value })
  busy.value = false
  if (!res.ok) { err.value = errorText(res.error); return }
  // The response is the live room-room status — render it now instead of
  // waiting for the next poll tick. Voting ends reveal immediately when this
  // was the final vote, so route to /result on the spot.
  applyState(res)
}
</script>

<template>
  <div v-if="me">
    <h1 class="subtitle surface-panel">讨论与投票</h1>

    <!-- One-time context (from /reveal, not the poll): who I am + room + template. -->
    <div class="container room-info">
      <div class="me-card">
        <img class="me-avatar" :src="meCard.avatar" :alt="meCard.userid" />
        <span class="me-name">{{ meCard.userid }}</span>
      </div>
      <div class="info-grid">
        <div class="info-row">
          <span class="info-label">房间ID</span>
          <span class="info-value">{{ me.roomid }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">玩家数量</span>
          <span class="info-value">{{ me.user_count }}</span>
        </div>
      </div>
      <div class="board current-template">
        <span v-for="role in boardChips" :key="role" class="board-chip">
          {{ roleIcon(role) }} {{ roleName(role) }} ×{{ me.board[role] }}
        </span>
      </div>
    </div>

    <div class="container role-banner">
      <button type="button" class="toggle-role" @click="showRole = !showRole">
        {{ showRole ? '👁 隐藏身份' : '🔒 身份已隐藏' }}
      </button>
      <template v-if="showRole">
        <span class="role-emoji">{{ roleIcon(me.role) }}</span>
        <div><b>你最初的身份：{{ roleName(me.role) }}</b></div>
        <!-- 只有失眠者拥有知道最终身份的夜技能；其他人都不知道自己的最终身份。 -->
        <div v-if="me.role === 'insomniac' && me.info?.final_role" class="final-role">
          <b>你的最终身份：</b>{{ roleIcon(me.info.final_role) }} {{ roleName(me.info.final_role) }}
        </div>
        <p style="line-height:1.8">{{ describe() }}</p>
      </template>
      <p v-else class="muted" style="text-align:center;margin:8px 0 0">
        你的身份与夜间信息已隐藏，点击上方按钮查看。
      </p>
    </div>

    <div class="container">
      <div class="subtitle">投出处决对象</div>
      <p class="muted" style="font-size:13px">选择一位玩家投出去，或弃权。每人只能投一次。</p>

      <div class="select-grid">
        <div
          v-for="u in users"
          :key="u.userid"
          class="select-card"
          :class="{ selected: target === u.userid }"
          @click="pick(u.userid)"
        >
          <span v-if="target === u.userid" class="pick-tag">✔ 处决</span>
          <img :src="avatarUrl(u.avatar)" alt="" />
          <span class="select-name">{{ u.userid }}</span>
        </div>
      </div>

      <p class="status" style="margin-top:14px">{{ selectionText() }}</p>

      <div class="vote-actions">
        <button class="btn-primary btn-block" :disabled="voted || busy" @click="openConfirm">
          {{ voted ? '你已投票 ✓' : target ? `确认投票（${target}）` : '确认弃权' }}
        </button>
      </div>
      <p v-if="err" class="error">{{ err }}</p>
    </div>

    <ConfirmDialog
      v-if="confirmOpen"
      title="确认你的投票？"
      :message="target ? `你选择处决 ${target}。投票提交后不可更改。` : '你选择弃权，不处决任何玩家。投票提交后不可更改。'"
      confirm-text="确认投票"
      cancel-text="再想想"
      @confirm="confirmVote"
      @cancel="confirmOpen = false"
    />
  </div>
  <div v-else-if="err" class="container error">{{ err }}
    <button :disabled="loading" @click="loadReveal">重试</button>
  </div>
  <div class="status surface-panel" v-else>正在揭晓…</div>
</template>

<style scoped>
.toggle-role {
  align-self: center;
  margin-bottom: 10px;
  padding: 8px 18px;
  border-radius: 999px;
  border: 1px solid rgba(229, 189, 84, 0.4);
  background: rgba(229, 189, 84, 0.10);
  color: var(--accent);
  font-weight: 700;
  cursor: pointer;
}
.select-grid {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 6px;
}
.select-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  width: 96px;
  padding: 10px 6px 8px;
  border: 2px solid transparent;
  border-radius: 12px;
  cursor: pointer;
}
.select-card.selected {
  border-color: var(--accent);
  background: rgba(229, 189, 84, 0.10);
}
.select-card img {
  width: 65px;
  height: 65px;
  border-radius: 50%;
  pointer-events: none;
}
.select-name {
  font-size: 1rem;
  font-weight: 600;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pick-tag {
  position: absolute;
  top: 4px;
  right: 6px;
  color: var(--accent);
  font-weight: 800;
  font-size: 0.8rem;
}
.room-info {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.me-card {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
}
.me-avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid var(--accent);
}
.me-name {
  font-size: 1.3rem;
  font-weight: 800;
}
.board {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
  background: rgba(229, 189, 84, 0.05);
  border: 1px dashed rgba(229, 189, 84, 0.3);
  border-radius: var(--radius-sm);
  padding: 12px;
}
.board-chip {
  display: inline-block;
  padding: 6px 12px;
  border-radius: 999px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text);
}
.final-role {
  display: inline-block;
  margin: 10px 0 4px;
  padding: 8px 16px;
  border-radius: var(--radius-sm);
  background: rgba(229, 189, 84, 0.10);
  border: 1px solid rgba(229, 189, 84, 0.4);
  color: var(--accent);
  font-size: 1.05rem;
}
</style>
