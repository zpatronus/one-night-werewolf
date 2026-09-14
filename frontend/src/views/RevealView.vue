<script setup>
import { computed, onMounted, ref } from 'vue'
import { post } from '../api'
import { creds } from '../store'
import { useRoomState } from '../useRoomState'
import { roleName, roleIcon, errorText } from '../gameConfig'
import { avatarUrl } from '../avatar'
import { sortPlayers } from '../playerOrder'

const { state, poll, applyState } = useRoomState()   // polls + routes to /result when voting ends
const me = ref(null)               // one-shot POST /reveal body
const err = ref('')
const busy = ref(false)
const loading = ref(false)
const target = ref('')             // "" = abstain

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

function pick(u) {
  if (voted.value) return
  target.value = target.value === u ? '' : u
}
function abstain() { pick('') }

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
      return `你是爪牙。狼人是：${(info.teammates || []).join('、')}（他们不知道是你）。`
    case 'seer':
      if (info.center_picks && info.center_picks.length) {
        const items = info.center_picks.map((idx, k) => `中央第 ${idx + 1} 张`)
        const cards = info.center_picks.map((idx, k) => peek(info.peeked[k]))
        return `你是预言家。你选择窥视${items.join('、')}，它们分别是 ${cards.join('、')}。`
      }
      return `你是预言家。你选择窥视 ${info.target} 的身份，他的牌是 ${peek(info.peeked?.[0])}。`
    case 'robber':
      return `你是强盗。你选择与 ${info.target} 交换身份，交换完成当时看到的牌是 ${peek(info.new_role)}。`
    case 'troublemaker':
      return `你是捣蛋鬼。你选择交换 ${info.target} 与 ${info.target2} 的牌。`
    case 'insomniac':
      return `你是失眠者，睡醒后回想了自己的身份。`
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
    <div class="container role-banner">
      <span class="role-emoji">{{ roleIcon(me.role) }}</span>
      <div><b>你最初的身份：{{ roleName(me.role) }}</b></div>
      <p v-if="me.action_was_fake" class="muted">
        刚才是伪装操作，不会产生实际效果。你真正的初始身份是 {{ roleName(me.role) }}，夜间信息如下。
      </p>
      <!-- 只有失眠者拥有知道最终身份的夜技能；其他人都不知道自己的最终身份。 -->
      <div v-if="me.role === 'insomniac' && me.info?.final_role" class="final-role">
        <b>你的最终身份：</b>{{ roleIcon(me.info.final_role) }} {{ roleName(me.info.final_role) }}
      </div>
      <p style="line-height:1.8">{{ describe() }}</p>
    </div>

    <div class="container">
      <div class="subtitle">投出处决对象</div>
      <p class="muted" style="font-size:13px">选择一位玩家投出去，或弃权。每人只能投一次。</p>

      <div
        v-for="u in users"
        :key="u.userid"
        class="player-row"
        :class="{ selected: target === u.userid }"
        @click="pick(u.userid)"
      >
        <img :src="avatarUrl(u.avatar)" alt="" />
        <span>{{ u.userid }}</span>
        <span v-if="target === u.userid" class="pick-tag">✔ 处决</span>
      </div>

      <p class="status" style="margin-top:14px">{{ selectionText() }}</p>

      <div class="vote-actions">
        <button class="btn-primary btn-block" :disabled="voted || busy" @click="vote">
          {{ voted ? '你已投票 ✓' : target ? `确认投票（${target}）` : '确认弃权' }}
        </button>
      </div>
      <p v-if="err" class="error">{{ err }}</p>
    </div>
  </div>
  <div v-else-if="err" class="container error">{{ err }}
    <button :disabled="loading" @click="loadReveal">重试</button>
  </div>
  <div class="muted" style="text-align:center" v-else>正在揭晓…</div>
</template>

<style scoped>
.pick-tag { margin-left: auto; color: var(--accent); font-weight: 700; }
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