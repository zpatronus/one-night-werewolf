<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { post } from '../api'
import { creds } from '../store'
import { useRoomState } from '../useRoomState'
import { roleName, roleIcon, errorText } from '../gameConfig'
import { avatarUrl } from '../avatar'
import { sortPlayers } from '../playerOrder'


const { state, error: pollError, applyState } = useRoomState()
const sel = reactive({ a: '', b: '', center: -1, picks: [] })  // a/b: players; center: lone-wolf; picks: seer center (1-2, ordered)
const mode = ref('player')  // seer toggle: 'player' | 'center'
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
const users = computed(() => sortPlayers(creds().roomid, state.value?.users || []))
// You can never target yourself (robber swap / troublemaker swap / seer peek).
const others = computed(() => users.value.filter((u) => u.userid !== creds().userid))

const isSeer = () => role.value === 'seer'
const isSelectPlayers = () => ['robber', 'troublemaker'].includes(role.value)
const isCenterPicker = () => role.value === 'werewolf' || (role.value === 'seer' && mode.value === 'center')

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
    else if (c.target) sel.a = c.target
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
  // flips to the submitted op instantly) and route straight to /reveal when
  // the server has reached the deadline.
  applyState(res)
}
</script>

<template>
  <div v-if="state">
    <div class="container countdown-ring">
      <div class="ring">{{ countdown }}</div>
      <div class="muted">剩余时间</div>
    </div>

    <!-- 操作面板：只显示"我"已提交到服务器的 ops（由服务器 response 渲染），
         其他玩家的操作一律保密，绝不展示谁已完成/未完成。 -->
    <div v-if="role" class="container role-banner">
      <span class="role-emoji">{{ roleIcon(role) }}</span>
      <div><b>你是 {{ roleName(role) }}</b></div>
      <p class="muted" style="font-size:13px;margin:6px 0 0">
        请按提示作出选择，夜间信息与行动结果将在下一阶段揭晓。
      </p>
      <div v-if="confirmed || state.my_choice?.type" class="submitted-card">
        <div class="submitted-head">✅ 我的行动已提交</div>
        <div class="submitted-body">{{ submittedOpsText() }}</div>
        <div class="muted submitted-foot">如需修改，重新提交即可。</div>
      </div>
    </div>

    <div v-if="!role" class="container">
      <h2>你的身份夜间无需操作</h2>
      <p class="muted">请随意点选下方选项，避免其他玩家从你的操作动作猜测身份。点选不会影响游戏结果。</p>
      <div class="dir">
        <button v-for="i in 3" :key="i" type="button" class="mode-btn"
          :class="{ selected: coverPick === i }" :aria-pressed="coverPick === i"
          @click="coverPick = i">选项 {{ i }}</button>
      </div>
      <p class="muted">{{ coverPick ? '已点选，可继续随意切换。' : '无需提交。' }} 倒计时结束后查看身份与夜间信息。</p>
      <p v-if="pollError" class="error">{{ errorText(pollError) }}</p>
    </div>

    <div v-else class="container">
      <template v-if="isSeer()">
        <div class="dir" style="margin-bottom:14px">
          <button class="mode-btn" :class="{ selected: mode === 'player' }" @click="mode = 'player'">看一名玩家</button>
          <button class="mode-btn" :class="{ selected: mode === 'center' }" @click="mode = 'center'">看中央 2 张</button>
        </div>
      </template>

      <template v-if="isSelectPlayers() || (isSeer() && mode === 'player')">
        <div class="muted" style="margin-bottom:8px">
          <span v-if="role === 'troublemaker'">选择两位玩家，交换他们手上的身份（不能选自己）</span>
          <span v-else-if="role === 'robber'">选择一位玩家，与他交换身份（不能选自己）</span>
          <span v-else>选择一位玩家窥视他的身份</span>
        </div>
        <div class="select-grid">
          <div
            v-for="u in others"
            :key="u.userid"
            class="select-card"
            :class="{ selected: sel.a === u.userid || sel.b === u.userid }"
            @click="pickPlayer(u.userid)"
          >
            <span v-if="sel.a === u.userid || sel.b === u.userid" class="pick-tag">
              {{ maxPicks() === 2 ? (sel.a === u.userid ? '①' : '②') : '✔' }}
            </span>
            <img :src="avatarUrl(u.avatar)" alt="" />
            <span class="select-name">{{ u.userid }}</span>
          </div>
        </div>
      </template>

      <template v-if="isCenterPicker()">
        <div class="muted" style="margin-bottom:8px">
          <span v-if="role === 'seer'">选择 2 张中央牌窥视（按顺序分别查看）</span>
          <span v-else-if="role === 'werewolf'">你是独狼，选择一张中央牌窥视</span>
        </div>
        <div class="dir" style="justify-content:space-around">
          <button
            v-for="i in 3"
            :key="i"
            class="center-btn"
            :class="{ selected: (role === 'seer' ? sel.picks.includes(i - 1) : sel.center === i - 1) }"
            @click="pickCenter(i - 1)"
          >
            <span class="center-tag">{{ role === 'seer' ? centerTag(i - 1) : '' }}</span>第 {{ i }} 张
          </button>
        </div>
      </template>

      <p class="status" style="margin-top:14px">{{ selectionText() }}</p>

      <button class="btn-primary btn-block" style="margin-top:6px" :disabled="!completed() || busy" @click="submit">
        {{ confirmed && completed() ? '更新提交' : '确认提交' }}
      </button>
      <p v-if="err || pollError" class="error">{{ err || errorText(pollError) }}</p>
    </div>
  </div>
</template>

<style scoped>
.mode-btn.selected,
.center-btn.selected {
  border-color: var(--accent);
  background: rgba(229, 189, 84, 0.14);
  color: var(--accent);
}
.mode-btn { flex: 1; white-space: nowrap; }
.center-btn { min-width: 92px; min-height: 64px; font-size: 1rem; position: relative; }
.center-tag { color: var(--accent); font-weight: 800; }
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
.select-grid {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 6px;
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
  font-size: 1rem;
}
.submitted-card {
  margin-top: 14px;
  padding: 12px 14px;
  border: 1px solid var(--good);
  border-radius: 12px;
  background: rgba(52, 168, 83, 0.08);
}
.submitted-head {
  font-size: 0.8rem;
  font-weight: 800;
  letter-spacing: 0.04em;
  color: var(--good);
  margin-bottom: 6px;
}
.submitted-body {
  font-size: 1.05rem;
  font-weight: 700;
  line-height: 1.5;
  color: var(--text);
}
.submitted-foot {
  margin-top: 6px;
  font-size: 0.78rem;
}
</style>
