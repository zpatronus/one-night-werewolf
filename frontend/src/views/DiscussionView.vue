<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { post } from '../api'
import { creds } from '../store'
import { useRoomState } from '../useRoomState'
import { roleName, roleIcon, errorText, ROLE_ORDER } from '../gameConfig'
import { avatarUrl, getMyAvatar } from '../avatar'
import { sortPlayers } from '../playerOrder'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import RoleCard from '../components/RoleCard.vue'

const props = defineProps({ infoOnly: Boolean })
const router = useRouter()
const { state, poll, applyState } = useRoomState(null, props.infoOnly ? { reveal: '/showinfo' } : undefined)
const remaining = ref(10)
let infoTimer = null
let active = true
function startInfoCountdown() {
  if (!props.infoOnly || infoTimer !== null || !active) return
  const deadline = Date.now() + 10000
  function tick() {
    infoTimer = null
    remaining.value = Math.max(0, Math.ceil((deadline - Date.now()) / 1000))
    if (remaining.value === 0) router.replace('/discussion')
    else infoTimer = setTimeout(tick, 100)
  }
  infoTimer = setTimeout(tick, 100)
}
onUnmounted(() => {
  active = false
  if (infoTimer !== null) clearTimeout(infoTimer)
})
const me = ref(null)               // one-shot POST /reveal body
const err = ref('')
const busy = ref(false)
const loading = ref(false)
const target = ref('')             // "" = abstain
const confirmOpen = ref(false)     // vote double-check dialog
const showRole = ref(false)        // discussion info stays hidden until requested

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
    if (!active) return
    me.value = res
    startInfoCountdown()
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

// Only illustrate cards explicitly returned by this player's reveal response.
const revealedCards = computed(() => {
  const info = me.value?.info || {}
  switch (me.value?.role) {
    case 'werewolf':
      return info.peek ? [{ role: info.peek, label: '查验的中央牌' }] : []
    case 'seer':
      return (info.peeked || []).map((role, i) => ({
        role,
        label: info.center_picks?.length ? `中央第 ${info.center_picks[i] + 1} 张` : `${info.target} 的初始身份`,
      }))
    case 'robber':
      return info.new_role ? [{ role: info.new_role, label: '交换当时获得的身份' }] : []
    case 'insomniac':
      return info.final_role ? [{ role: info.final_role, label: '你的最终身份' }] : []
    default:
      return []
  }
})

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
  if (props.infoOnly || voted.value || busy.value) return
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
  if (props.infoOnly || voted.value || busy.value) return
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
    <section v-if="props.infoOnly" class="container night-info" aria-labelledby="night-info-title">
      <header class="night-heading">
        <span class="night-eyebrow">夜间信息</span>
        <h1 id="night-info-title">查看结果</h1>
        <p>请安静阅读，管理好表情。</p>
      </header>

      <div class="night-identity">
        <RoleCard :role="me.role" eager class="night-role-art" />
        <div>
          <span class="night-label">你的初始身份</span>
          <h2>{{ roleName(me.role) }}</h2>
        </div>
      </div>

      <div class="night-observation">
        <span class="night-label">夜间信息</span>
        <p>{{ describe() }}</p>
        <div v-if="revealedCards.length" class="revealed-cards">
          <figure v-for="(card, index) in revealedCards" :key="index">
            <figcaption>{{ card.label }}</figcaption>
            <RoleCard :role="card.role" eager />
          </figure>
        </div>
      </div>

      <footer class="night-countdown">
        <div class="night-clock" role="timer" :aria-label="`${remaining} 秒后开始讨论`">
          <svg viewBox="0 0 64 64" aria-hidden="true">
            <circle class="clock-track" cx="32" cy="32" r="28" />
            <circle class="clock-progress" cx="32" cy="32" r="28" pathLength="100"
              :style="{ strokeDashoffset: 100 - remaining * 10 }" />
          </svg>
          <span>{{ remaining }}<small>秒</small></span>
        </div>
        <div class="night-countdown-copy">
          <strong>即将开始讨论</strong>
          <p>倒计时结束后自动进入</p>
        </div>
      </footer>
    </section>
    <section v-else class="container discussion-header">
      <h1>讨论与投票</h1>
      <div class="discussion-context">
        <div class="discussion-player">
          <img :src="meCard.avatar" :alt="meCard.userid" />
          <strong>{{ meCard.userid }}</strong>
        </div>
        <div class="discussion-room"><span>房间 {{ me.roomid }}</span><span>{{ me.user_count }} 位玩家</span></div>
      </div>
      <details class="discussion-board">
        <summary>本局身份牌 <span>查看配置</span></summary>
        <div class="board-chips">
          <div v-for="role in boardChips" :key="role" class="board-chip">
            <RoleCard :role="role" />
            <span>{{ roleName(role) }} ×{{ me.board[role] }}</span>
          </div>
        </div>
      </details>
    </section>

    <section v-if="!props.infoOnly" class="container discussion-private">
      <div class="section-heading">
        <div><span class="night-label">仅自己可见</span><h2>我的夜间信息</h2></div>
        <button type="button" class="toggle-role" :aria-expanded="showRole" aria-controls="private-information" @click="showRole = !showRole">
          {{ showRole ? '隐藏信息' : '查看信息' }}
        </button>
      </div>
      <div v-if="showRole" id="private-information">
        <div class="night-identity">
          <RoleCard :role="me.role" eager class="night-role-art" />
          <div><span class="night-label">你的初始身份</span><h2>{{ roleName(me.role) }}</h2></div>
        </div>
        <div class="night-observation">
          <p>{{ describe() }}</p>
          <div v-if="revealedCards.length" class="revealed-cards">
          <figure v-for="(card, index) in revealedCards" :key="index">
            <figcaption>{{ card.label }}</figcaption>
            <RoleCard :role="card.role" eager />
          </figure>
        </div>
        </div>
      </div>
      <p v-else class="private-hidden">信息已收起，需要时可随时回看。</p>
    </section>

    <section v-if="!props.infoOnly" class="container discussion-vote">
      <div class="section-heading">
        <div><h2>投票</h2></div>
      </div>
      <p class="vote-help">选择玩家或弃权，提交后不可更改。</p>

      <div class="select-grid" aria-label="选择投票对象">
        <button v-for="u in users" :key="u.userid" type="button"
          class="select-card" :class="{ selected: target === u.userid }"
          :aria-pressed="target === u.userid" :disabled="voted || busy" @click="pick(u.userid)">
          <span class="pick-tag" aria-hidden="true">{{ target === u.userid ? '✓' : '' }}</span>
          <img :src="avatarUrl(u.avatar)" alt="" />
          <span class="select-name">{{ u.userid }}</span>
        </button>
      </div>
      <button type="button" class="abstain-choice" :class="{ selected: !target }"
        :aria-pressed="!target" :disabled="voted || busy" @click="abstain">
        <span class="abstain-symbol" aria-hidden="true">—</span>
        <span><strong>弃权</strong><small>不选择处决对象</small></span>
        <span class="abstain-check" aria-hidden="true">{{ !target ? '✓' : '' }}</span>
      </button>

      <div class="vote-footer">
        <p class="vote-selection" role="status">{{ voted ? '投票已提交，等待其他玩家。' : selectionText() }}</p>
        <button class="btn-primary btn-block" :disabled="voted || busy" @click="openConfirm">
          {{ voted ? '已投票 ✓' : busy ? '正在提交…' : target ? `确认投票 · ${target}` : '确认弃权' }}
        </button>
      </div>
      <p v-if="err" class="error">{{ err }}</p>
    </section>

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
.night-info {
  padding: 28px 24px 20px;
  overflow: hidden;
  border-color: rgba(229, 189, 84, 0.28);
  background: radial-gradient(ellipse at 100% 0, rgba(229, 189, 84, 0.09), transparent 55%), var(--surface);
}
.night-heading { text-align: center; }
.night-eyebrow { color: var(--accent); font-size: 0.7rem; letter-spacing: 0.16em; }
.night-heading h1 { margin: 12px 0 8px; font-size: clamp(1.25rem, 5vw, 1.55rem); font-weight: 700; }
.night-heading p { margin: 0; color: var(--text-dim); font-size: 0.85rem; }
.night-identity { display: flex; flex-direction: column; align-items: stretch; gap: 16px; margin: 26px 0 20px; }
.night-role-art { width: 100%; }
.night-label { display: block; color: var(--text-dim); font-size: 0.72rem; letter-spacing: 0.06em; }
.night-identity h2 { margin: 5px 0 0; font-size: 1.3rem; }
.night-observation {
  padding: 18px;
  border: 1px solid var(--border);
  border-left: 2px solid var(--accent);
  border-radius: 4px 12px 12px 4px;
  background: rgba(5, 12, 23, 0.35);
}
.night-observation p { margin: 10px 0 0; font-size: 1rem; line-height: 1.85; overflow-wrap: anywhere; }
.revealed-cards { display: grid; grid-template-columns: minmax(0, 1fr); gap: 12px; margin-top: 16px; }
.revealed-cards figure { min-width: 0; margin: 0; }
.revealed-cards figcaption { margin-bottom: 8px; font-size: 0.75rem; line-height: 1.6; color: var(--accent-hover); overflow-wrap: anywhere; }
.night-countdown { display: flex; align-items: center; justify-content: center; gap: 16px; margin-top: 24px; }
.night-clock { position: relative; flex: 0 0 64px; height: 64px; }
.night-clock svg { width: 100%; height: 100%; transform: rotate(-90deg); }
.night-clock circle { fill: none; stroke-width: 2; }
.clock-track { stroke: rgba(229, 189, 84, 0.12); }
.clock-progress { stroke: var(--accent); stroke-dasharray: 100; stroke-linecap: round; transition: stroke-dashoffset 0.5s linear; }
.night-clock > span { position: absolute; inset: 0; display: flex; align-items: baseline; justify-content: center; padding-top: 17px; gap: 2px; font-size: 1.4rem; font-variant-numeric: tabular-nums; color: var(--accent-hover); }
.night-clock small { color: var(--text-dim); font-size: 0.65rem; }
.night-countdown-copy strong { font-size: 0.88rem; font-weight: 600; }
.night-countdown-copy p { margin: 6px 0 0; color: var(--text-dim); font-size: 0.75rem; }
@media (max-width: 360px) {
  .night-info { padding: 22px 16px 18px; }
  .night-observation { padding: 14px; }
}
@media (prefers-reduced-motion: reduce) {
  .clock-progress { transition: none; }
}

.discussion-header {
  padding: 26px 22px 18px;
  border-color: rgba(229, 189, 84, 0.25);
  background: radial-gradient(ellipse at 0 0, rgba(229, 189, 84, 0.10), transparent 65%), var(--surface);
}
.discussion-header h1 { margin: 10px 0 8px; font-size: 1.6rem; }
.discussion-intro { margin: 0; color: var(--text-dim); font-size: 0.85rem; }
.discussion-context { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 24px; }
.discussion-player { display: flex; align-items: center; gap: 10px; min-width: 0; }
.discussion-player img { width: 40px; height: 40px; border-radius: 50%; border: 1px solid var(--border-strong); }
.discussion-player strong { font-size: 0.95rem; overflow-wrap: anywhere; }
.discussion-room { display: grid; gap: 4px; text-align: right; flex-shrink: 0; }
.discussion-room span { color: var(--text-dim); font-size: 0.72rem; }
.discussion-board { margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--border); }
.discussion-board summary { cursor: pointer; color: var(--text-dim); font-size: 0.78rem; }
.discussion-board summary span { float: right; font-size: 0.7rem; color: var(--accent); }
.board-chips { display: grid; grid-template-columns: minmax(0, 1fr); gap: 12px; padding-top: 12px; }
.board-chip { text-align: center; padding: 6px; border: 1px solid var(--border); border-radius: 8px; background: var(--surface-2); font-size: 0.72rem; }
.board-chip > span { display: block; margin-top: 6px; }
.discussion-private, .discussion-vote { padding: 22px; }
.section-heading { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.section-heading h2 { margin: 5px 0 0; font-size: 1.1rem; }
.toggle-role { flex-shrink: 0; margin: 0; padding: 8px 12px; border-radius: 999px; color: var(--accent); border-color: rgba(229, 189, 84, 0.25); background: rgba(229, 189, 84, 0.06); font-size: 0.75rem; }
.discussion-private .night-identity { margin: 20px 0 16px; gap: 12px; }
.discussion-private .night-identity h2 { font-size: 1.1rem; }
.discussion-private .night-observation p { margin: 0; font-size: 0.9rem; }
.private-hidden { margin: 16px 0 0; color: var(--text-dim); font-size: 0.8rem; }
.vote-help { color: var(--text-dim); font-size: 0.78rem; line-height: 1.7; margin: 14px 0 18px; }
.select-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 9px; }
.select-card { position: relative; display: flex; align-items: center; gap: 9px; min-width: 0; margin: 0; padding: 14px 10px; text-align: left; border: 1px solid var(--border); border-radius: 12px; background: var(--surface-2); }
.select-card.selected, .abstain-choice.selected { border-color: var(--accent); background: rgba(229, 189, 84, 0.09); }
.select-card img { width: 38px; height: 38px; flex-shrink: 0; border-radius: 50%; object-fit: cover; }
.select-name { font-size: 0.85rem; font-weight: 600; max-width: 100%; overflow-wrap: anywhere; }
.pick-tag { position: absolute; top: 5px; right: 6px; color: var(--accent); font-size: 0.75rem; }
.abstain-choice { display: flex; align-items: center; width: 100%; gap: 12px; margin: 12px 0 0; padding: 12px 14px; text-align: left; background: var(--surface-2); border: 1px solid var(--border); border-radius: 12px; }
.abstain-symbol { display: grid; place-items: center; width: 32px; height: 32px; border-radius: 50%; background: var(--surface-2); color: var(--text-dim); }
.abstain-choice strong { display: block; font-size: 0.85rem; }
.abstain-choice small { display: block; margin-top: 3px; color: var(--text-dim); font-size: 0.7rem; }
.abstain-check { margin-left: auto; color: var(--accent); }
.vote-footer { margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--border); }
.vote-selection { color: var(--text-dim); text-align: center; margin: 0 0 12px; font-size: 0.8rem; overflow-wrap: anywhere; }
.discussion-vote button:focus-visible, .toggle-role:focus-visible, .discussion-board summary:focus-visible { outline: 2px solid var(--accent-hover); outline-offset: 3px; }
@media (max-width: 360px) {
  .discussion-header, .discussion-private, .discussion-vote { padding: 18px 14px; }
  .select-grid { gap: 6px; }
  .select-card img { width: 32px; height: 32px; }
}
</style>
