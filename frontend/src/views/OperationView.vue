<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { post } from '../api'
import { creds } from '../store'
import { useRoomState } from '../useRoomState'
import { roleName, errorText } from '../gameConfig'
import { avatarUrl } from '../avatar'
import { sortPlayers } from '../playerOrder'
import RoleCard from '../components/RoleCard.vue'


const { state, error: pollError, applyState } = useRoomState(null, { reveal: '/showinfo' })
const sel = reactive({ a: '', b: '', center: -1, picks: [] })  // a/b: players; center: lone-wolf; picks: seer center (1-2, ordered)
const mode = ref('center')  // seer toggle: 'player' | 'center'
const coverPick = ref(null)
const confirmed = ref(false)
const err = ref('')
const busy = ref(false)
const now = ref(Date.now())
let countdownTimer
onMounted(() => {
  now.value = Date.now()
  countdownTimer = setInterval(() => { now.value = Date.now() }, 10)
})
onUnmounted(() => clearInterval(countdownTimer))

const countdown = computed(() => {
  const end = state.value?.op_end_time_ms
  if (!Number.isFinite(end)) return '加载中...'
  const hundredths = Math.ceil(Math.max(0, end - now.value) / 10)
  if (hundredths === 0) return '跳转中...'
  return `${Math.floor(hundredths / 100)}.${String(hundredths % 100).padStart(2, '0')}`
})

const role = computed(() => state.value?.role)
const requiresAction = computed(() => state.value?.requires_action === true)
const roleHint = computed(() => {
  if (requiresAction.value) return '请按提示作出选择，夜间信息与行动结果将在揭晓阶段显示。'
  if (role.value === 'insomniac') return '你无需选择目标，最终身份将在揭晓阶段显示。'
  if (role.value === 'minion') return '你无需选择目标，狼人名单将在揭晓阶段显示。'
  if (role.value === 'werewolf') return '你有狼人同伴，无需选择目标；同伴名单将在揭晓阶段显示。'
  return '你没有夜间能力，请等待进入讨论与投票。'
})
const users = computed(() => sortPlayers(creds().roomid, state.value?.users || []))
// You can never target yourself (robber swap / troublemaker swap / seer peek).
const others = computed(() => users.value.filter((u) => u.userid !== creds().userid))

const isSeer = () => role.value === 'seer'
const isSelectPlayers = () => ['robber', 'troublemaker'].includes(role.value)
const isCenterPicker = () => requiresAction.value && (role.value === 'werewolf' || (role.value === 'seer' && mode.value === 'center'))

// How many players this operating identity picks (0 = center pickers / none).
function maxPicks() {
  if (role.value === 'troublemaker') return 2
  if (role.value === 'robber') return 1
  if (role.value === 'seer' && mode.value === 'player') return 1
  return 0
}

// Keep the N(=2) most recently selected ("select last as 2"). Selecting a
// third evicts the oldest -- the "1" slot -- and shifts "2" up to "1", so the
// ring always holds the two newest picks in selection order.
function mostRecent2(arr, item) {
  return arr.filter((x) => x !== item).concat(item).slice(-2)
}

function pickPlayer(uid) {
  const m = maxPicks()
  if (m === 1) {
    // single-pick role (robber, seer-player): only one highlighted at a time.
    sel.b = ''
    sel.a = sel.a === uid ? '' : uid
    return
  }
  // two-pick role (troublemaker): keep the two most recently selected players.
  const ordered = mostRecent2([sel.a, sel.b].filter(Boolean), uid)
  sel.a = ordered[0] || ''
  sel.b = ordered[1] || ''
}

// Seer center keeps the two most recent cards in order; lone wolf is a single toggle.
function pickCenter(i) {
  if (role.value === 'seer') {
    sel.picks = mostRecent2(sel.picks.slice(), i)
    return
  }
  if (role.value === 'werewolf') sel.center = sel.center === i ? -1 : i
}

function centerSel(i, isCenterMode) {
  if (!isCenterMode) return false
  if (role.value === 'seer') return sel.picks.includes(i)
  return sel.center === i
}
function centerTag(i) {
  const k = sel.picks.indexOf(i)
  return k >= 0 ? `${'①②'[k]} ` : ''
}

function completed() {
  if (!requiresAction.value) return false
  const t = role.value
  if (t === 'troublemaker') return !!(sel.a && sel.b && sel.a !== sel.b)
  if (t === 'seer') return mode.value === 'center' ? sel.picks.length === 2 : !!sel.a
  if (t === 'robber') return !!sel.a
  if (t === 'werewolf') return sel.center >= 0
  return false
}

// Avalon-style status line telling the player exactly what they have selected.
function selectionText() {
  const t = role.value
  if (t === 'troublemaker') {
    if (sel.a && sel.b) return `已选择：${sel.a} 和 ${sel.b}，将交换他们的身份。`
    if (sel.a) return `已选择 ${sel.a}（1/2），请再选一位要交换的玩家。`
    return '请选择两位玩家以交换他们的身份。'
  }
  if (t === 'robber') return sel.a ? `已选择 ${sel.a}，你将取走他的牌。` : '请选择一位玩家以交换身份。'
  if (t === 'seer') {
    if (mode.value === 'center') {
      if (sel.picks.length) return `已选择：中央第 ${sel.picks.map((i) => i + 1).join('、')} 张（${sel.picks.length}/2）。`
      return '请选择 2 张中央牌查看。'
    }
    return sel.a ? `已选择 ${sel.a}，查看其身份。` : '请选择一位玩家查看身份。'
  }
  if (t === 'werewolf') return sel.center >= 0 ? `已选择：中央第 ${sel.center + 1} 张牌。` : '你是独狼，选择一张中央牌查看。'
  return ''
}

// Render the ops this caller has actually submitted to the server (reads
// ``state.my_choice`` — the server's authoritative copy), so the top panel is
// always a truthful server snapshot, not a local guess.
function submittedOpsText() {
  const c = state.value?.my_choice
  if (!c || typeof c !== 'object' || !c.type) return '已提交。'
  switch (c.type) {
    case 'troublemaker':
      return `🍬 已提交：交换 ${c.target} 与 ${c.target2} 的身份。`
    case 'robber':
      return `🔪 已提交：与 ${c.target} 交换身份。`
    case 'seer': {
      const picks = Array.isArray(c.center_picks) && c.center_picks.length
        ? `中央第 ${c.center_picks.map((i) => i + 1).join('、')} 张`
        : c.target || ''
      return `🔍 已提交：窥视 ${picks}。`
    }
    case 'wolf': {
      // target is 0-based ("center_0"), but humans count from 1.
      const i = parseInt(String(c.target || '').split('_')[1], 10)
      const n = Number.isInteger(i) ? i + 1 : ''
      return `🐺 已提交：窥视中央第 ${n} 张。`
    }
    default:
      return '✓ 已提交。'
  }
}

// Reflect a choice already submitted (server returns it in every op poll), so
// the player can review and — until the round locks — change it.
let hydrated = false
watch(state, (s) => {
  const c = s?.my_choice
  if (hydrated || !c) return
  if (role.value === 'troublemaker' && c.type === 'troublemaker') {
    sel.a = c.target || ''; sel.b = c.target2 || ''
    hydrated = true
  } else if (role.value === 'seer' && c.type === 'seer') {
    if (Array.isArray(c.center_picks)) { mode.value = 'center'; sel.picks = c.center_picks.slice(0, 2) }
    else if (c.target) { mode.value = 'player'; sel.a = c.target }
    hydrated = true
  } else if (role.value === 'robber' && c.type === 'robber' && c.target) {
    sel.a = c.target; hydrated = true
  } else if (role.value === 'werewolf' && c.type === 'wolf' && typeof c.target === 'string') {
    const i = parseInt(c.target.split('_')[1], 10)
    if (Number.isInteger(i)) sel.center = i
    hydrated = true
  }
}, { immediate: true })

function buildChoice() {
  if (!requiresAction.value) return null
  const t = role.value
  if (t === 'troublemaker') return { type: 'troublemaker', target: sel.a, target2: sel.b }
  if (t === 'robber') return { type: 'robber', target: sel.a }
  if (t === 'seer') {
    if (mode.value === 'center') return { type: 'seer', center_picks: sel.picks.slice() }
    return { type: 'seer', target: sel.a }
  }
  if (t === 'werewolf') return { type: 'wolf', target: `center_${sel.center}` }
  return null
}

async function submit() {
  if (busy.value || !completed()) return
  busy.value = true
  err.value = ''
  const res = await post('night_action', { ...creds(), choice: buildChoice() })
  busy.value = false
  if (!res.ok) { err.value = errorText(res.error); return }
  confirmed.value = true
  // The response is the live room status: render it now (the "我的操作" panel
  // flips to the submitted op instantly) and route to /showinfo when
  // the server has reached the deadline.
  applyState(res)
}
</script>

<template>
  <div v-if="state">
    <header class="container ops-header">
      <h1>夜间操作</h1>
      <div class="ops-clock" role="timer" aria-label="夜间操作剩余时间">
        <span>剩余时间</span><strong>{{ countdown }}</strong>
      </div>
    </header>

    <!-- 操作面板：只显示"我"已提交到服务器的 ops（由服务器 response 渲染），
         其他玩家的操作一律保密，绝不展示谁已完成/未完成。 -->
    <div v-if="role" class="container ops-identity">
      <div class="ops-role">
        <RoleCard :role="role" eager class="ops-role-art" />
        <div><span class="ops-label">你的初始身份</span><h2>{{ roleName(role) }}</h2></div>
      </div>
      <p class="ops-hint">
        {{ roleHint }}
      </p>
      <div v-if="requiresAction && (confirmed || state.my_choice?.type)" class="submitted-card">
        <div class="submitted-head">✓ 已提交</div>
        <div class="submitted-body">{{ submittedOpsText() }}</div>
        <div class="muted submitted-foot">如需修改，重新提交即可。</div>
      </div>
    </div>

    <div v-if="!requiresAction" class="container ops-panel">
      <h2>无需夜间操作</h2>
      <p class="muted">可随意点选，避免他人从动作猜测身份。点选不影响结果。</p>
      <div class="dir">
        <button v-for="i in 3" :key="i" type="button" class="mode-btn"
          :class="{ selected: coverPick === i }" :aria-pressed="coverPick === i"
          @click="coverPick = i">选项 {{ i }}</button>
      </div>
      <p class="muted">{{ coverPick ? '已点选，可继续随意切换。' : '无需提交。' }} 请等待倒计时结束。</p>
      <p v-if="pollError" class="error">{{ errorText(pollError) }}</p>
    </div>

    <div v-else class="container ops-panel">
      <h2>选择目标</h2>
      <template v-if="isSeer()">
        <div class="ops-modes">
          <button class="mode-btn" :class="{ selected: mode === 'player' }" @click="mode = 'player'">看一名玩家</button>
          <button class="mode-btn" :class="{ selected: mode === 'center' }" @click="mode = 'center'">看中央 2 张</button>
        </div>
      </template>

      <template v-if="isSelectPlayers() || (isSeer() && mode === 'player')">
        <div class="ops-help">
          <span v-if="role === 'troublemaker'">选择两位玩家，交换他们手上的身份（不能选自己）</span>
          <span v-else-if="role === 'robber'">选择一位玩家，与他交换身份（不能选自己）</span>
          <span v-else>选择一位玩家窥视他的身份</span>
        </div>
        <div class="select-grid">
          <button type="button"
            v-for="u in others"
            :key="u.userid"
            class="select-card"
            :class="{ selected: sel.a === u.userid || sel.b === u.userid }"
            :aria-pressed="sel.a === u.userid || sel.b === u.userid"
            @click="pickPlayer(u.userid)"
          >
            <span v-if="sel.a === u.userid || sel.b === u.userid" class="pick-tag">
              {{ maxPicks() === 2 ? (sel.a === u.userid ? '①' : '②') : '✔' }}
            </span>
            <img :src="avatarUrl(u.avatar)" alt="" />
            <span class="select-name">{{ u.userid }}</span>
          </button>
        </div>
      </template>

      <template v-if="isCenterPicker()">
        <div class="ops-help">
          <span v-if="role === 'seer'">选择 2 张中央牌窥视（按顺序分别查看）</span>
          <span v-else-if="role === 'werewolf'">你是独狼，选择一张中央牌窥视</span>
        </div>
        <div class="center-grid">
          <button
            v-for="i in 3"
            :key="i"
            class="center-btn" type="button"
            :aria-pressed="role === 'seer' ? sel.picks.includes(i - 1) : sel.center === i - 1"
            :class="{ selected: (role === 'seer' ? sel.picks.includes(i - 1) : sel.center === i - 1) }"
            @click="pickCenter(i - 1)"
          >
            <span class="card-moon" aria-hidden="true">☾</span>
            <span class="center-tag">{{ role === 'seer' ? centerTag(i - 1) : '' }}</span>第 {{ i }} 张
          </button>
        </div>
      </template>

      <p class="ops-selection" role="status">{{ selectionText() }}</p>

      <button class="btn-primary btn-block" style="margin-top:6px" :disabled="!completed() || busy" @click="submit">
        {{ busy ? '提交中…' : confirmed && completed() ? '更新提交' : '确认提交' }}
      </button>
      <p v-if="err || pollError" class="error">{{ err || errorText(pollError) }}</p>
    </div>
  </div>
</template>

<style scoped>
.ops-header { display: flex; justify-content: space-between; align-items: center; gap: 12px; padding: 20px 22px; border-color: rgba(229, 189, 84, 0.25); background: radial-gradient(ellipse at 0 0, rgba(229, 189, 84, 0.08), transparent 65%), var(--surface); }
.ops-header h1 { margin: 0; font-size: 1.4rem; }
.ops-clock { text-align: right; }
.ops-clock > span { display: block; color: var(--text-dim); font-size: 0.68rem; margin-bottom: 4px; }
.ops-clock strong { display: block; min-width: 6ch; color: var(--accent-hover); font-size: 1.5rem; font-variant-numeric: tabular-nums; font-weight: 600; }
.ops-identity, .ops-panel { padding: 22px; }
.ops-role { display: flex; flex-direction: column; align-items: stretch; gap: 14px; }
.ops-role-art { width: 100%; }
.ops-label { font-size: 0.72rem; color: var(--text-dim); }
.ops-role h2 { margin: 5px 0 0; font-size: 1.25rem; }
.ops-hint { margin: 16px 0 0; font-size: 0.8rem; color: var(--text-dim); line-height: 1.75; }
.ops-panel h2 { margin: 0 0 16px; font-size: 1.05rem; }
.ops-panel > .muted { font-size: 0.8rem; line-height: 1.75; }
.ops-modes { display: flex; gap: 5px; padding: 4px; border: 1px solid var(--border); border-radius: 12px; background: rgba(5, 12, 23, 0.3); margin-bottom: 18px; }
.mode-btn { flex: 1; white-space: nowrap; margin: 0; min-height: 42px; padding: 10px 8px; font-size: 0.78rem; border-radius: 8px; }
.mode-btn.selected, .center-btn.selected, .select-card.selected { border-color: var(--accent); background: rgba(229, 189, 84, 0.10); color: var(--accent-hover); }
.ops-help { font-size: 0.78rem; line-height: 1.7; color: var(--text-dim); margin-bottom: 14px; }
.ops-help span { color: inherit; }
.select-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 9px; }
.select-card { position: relative; display: flex; align-items: center; gap: 9px; min-width: 0; margin: 0; padding: 14px 10px; border: 1px solid var(--border); border-radius: 12px; background: var(--surface-2); text-align: left; }
.select-card img { width: 38px; height: 38px; flex-shrink: 0; border-radius: 50%; object-fit: cover; }
.select-name { font-size: 0.82rem; font-weight: 600; overflow-wrap: anywhere; min-width: 0; }
.pick-tag { position: absolute; top: 3px; right: 5px; color: var(--accent); font-size: 0.75rem; }
.center-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
.center-btn { position: relative; min-width: 0; min-height: 120px; padding: 14px 4px; margin: 0; font-size: 0.8rem; border: 1px solid var(--border-strong); border-radius: 12px; background: linear-gradient(145deg, rgba(229, 189, 84, 0.06), transparent), var(--surface-2); }
.card-moon { display: block; color: var(--accent); font-size: 2rem; margin-bottom: 14px; }
.center-tag { color: var(--accent); font-weight: 700; }
.ops-selection { margin: 20px 0 12px; padding-top: 16px; border-top: 1px solid var(--border); color: var(--text-dim); font-size: 0.8rem; line-height: 1.7; overflow-wrap: anywhere; }
.submitted-card { margin-top: 18px; padding: 14px; border: 1px solid rgba(229, 189, 84, 0.25); border-left: 2px solid var(--accent); border-radius: 4px 10px 10px 4px; background: rgba(229, 189, 84, 0.04); }
.submitted-head { color: var(--accent); font-size: 0.75rem; margin-bottom: 8px; }
.submitted-body { font-size: 0.9rem; font-weight: 600; line-height: 1.7; overflow-wrap: anywhere; }
.submitted-foot { margin-top: 8px; font-size: 0.72rem; }
.ops-panel button:focus-visible { outline: 2px solid var(--accent-hover); outline-offset: 3px; }
@media (max-width: 360px) {
  .ops-header, .ops-identity, .ops-panel { padding: 18px 14px; }
  .ops-header h1 { font-size: 1.2rem; }
  .select-card { padding: 14px 8px; gap: 7px; }
  .select-card img { width: 32px; height: 32px; }
  .center-grid { gap: 7px; }
}
</style>
