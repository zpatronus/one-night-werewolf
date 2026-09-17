<script setup>
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { post } from '../api'
import { base, creds } from '../store'
import { useRoomState } from '../useRoomState'
import { errorText, boardTemplate, roleName, roleIcon, ROLE_ORDER } from '../gameConfig'
import { avatarUrl, getMyAvatar } from '../avatar'
import { sortPlayers } from '../playerOrder'
import ConfirmDialog from '../components/ConfirmDialog.vue'

const router = useRouter()
const { state, applyState } = useRoomState()
const BOARD_LS_KEY = 'waitingBoard'
const board = ref(loadSavedBoard() ?? boardTemplate())   // {role_code: count}; editable by host
const err = ref('')
const starting = ref(false)
const saving = ref(false)
const confirmOpen = ref(false)    // start-confirmation dialog

// The host's board draft persists across refreshes (same pattern as roomId /
// userid / userPsw in localStorage): load it back if present, and write it back
// on every change. Only role keys present in ROLE_ORDER are kept, with sane,
// non-negative integer counts, so a stale or tampered value can't break the UI.
function loadSavedBoard() {
  try {
    const raw = JSON.parse(localStorage.getItem(BOARD_LS_KEY))
    if (!raw || typeof raw !== 'object') return null
    const b = {}
    for (const role of ROLE_ORDER) {
      const v = Math.floor(Number(raw[role]) || 0)
      b[role] = Number.isFinite(v) && v > 0 ? v : 0
    }
    return b
  } catch { return null }
}
function saveBoardLS(b) {
  if (b) localStorage.setItem(BOARD_LS_KEY, JSON.stringify(b))
}

const MIN = 3
const MAX = 10
const n = () => state.value?.userCount || 0
const isHost = () => state.value?.is_owner

// The editor belongs to this browser. Room snapshots and submit responses
// only update the public board; they must never replace this local draft.
// Persist immediately so navigating or refreshing cannot lose the latest edit.
watch(board, (b) => saveBoardLS(b), { deep: true, immediate: true, flush: 'sync' })

// Invite link that drops a friend straight onto the join form with this room
// already filled in (JoinRoomView reads the `room` query param on mount).
const copied = ref(false)
function inviteUrl() {
  return `${window.location.origin}${base}joinroom?room=${encodeURIComponent(creds().roomid)}`
}
async function copyInvite() {
  const url = inviteUrl()
  try {
    await navigator.clipboard.writeText(url)
  } catch {
    // Non-secure context / older browser fallback.
    const ta = document.createElement('textarea')
    ta.value = url
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
  }
  copied.value = true
  setTimeout(() => { copied.value = false }, 2000)
}

const users = computed(() => sortPlayers(creds().roomid, state.value?.users || []))

// Avatar for a given player id: the backend returns the authoritative file;
// fall back to our own avatar if a "me" entry happens to be missing.
function avatarOf(userid) {
  const entry = state.value?.users?.find((u) => u.userid === userid)
  const file = entry?.avatar || (userid === creds().userid ? getMyAvatar() : '')
  return avatarUrl(file)
}

function canStart() {
  return n() >= MIN && n() <= MAX && !dirty.value && !saving.value
    && Object.values(currentBoard()).reduce((a, b) => a + b, 0) === n() + 3
}

function cardsLeft() {
  return n() + 3 - Object.values(board.value || {}).reduce((a, b) => a + b, 0)
}

// Per-role hard caps enforced in the UI (mirrors the backend board rules):
// robber and troublemaker are unique — at most 1 each. Other roles are bounded
// only by the total player+center card count (cardsLeft).
const maxFor = (role) => (role === 'robber' || role === 'troublemaker') ? 1 : Number.MAX_SAFE_INTEGER

function atMax(role) {
  return (board.value?.[role] || 0) >= maxFor(role)
}

function adjust(role, delta) {
  if (starting.value || saving.value) return
  const b = { ...board.value }
  const next = Math.max(0, (b[role] || 0) + delta)
  if (delta > 0 && next > maxFor(role)) return   // enforce the hard cap
  b[role] = next
  board.value = b
}

async function saveBoard() {
  if (!isHost() || saving.value || starting.value) return
  saving.value = true
  err.value = ''
  try {
    const res = await post('set_board', { ...creds(), board: { ...board.value } })
    if (!res.ok) { err.value = errorText(res.error); return }
    // Invalidate any poll started before this save so it cannot undo the update.
    applyState({ ...state.value, board: res.board, ok: true })
  } finally { saving.value = false }
}

async function start() {
  if (starting.value || !canStart()) return
  starting.value = true
  err.value = ''
  confirmOpen.value = false
  const res = await post('start_game', creds())
  starting.value = false
  if (!res.ok) { err.value = errorText(res.error); return }
  // The response is the live op room state — jump straight off it, no poll.
  if (res.phase === 'op') router.push('/ops')
}

const usedCount = computed(() => Object.values(board.value || {}).reduce((a, b) => a + b, 0))
// The deck is well-formed only when it holds exactly playerCount + 3 cards.
const boardValid = computed(() => cardsLeft() === 0)

// The public board is the server's submitted template for every player.
function currentBoard() {
  return state.value?.board ?? boardTemplate()
}
const dirty = computed(() => ROLE_ORDER.some(role =>
  (board.value?.[role] || 0) !== (currentBoard()[role] || 0)))

// Only roles present on the board (count > 0) are displayed.
const liveBoard = computed(() => currentBoard())
const chips = computed(() => ROLE_ORDER.filter((r) => (liveBoard.value[r] || 0) > 0))

// Blink the border of any chip whose count changed since the last render, so
// players notice when the host tweaks the board. Class is removed after the
// animation so a later change can replay it.
const blinks = ref({})
watch(liveBoard, (b, prev) => {
  if (!prev) return        // skip the initial render
  const changed = Object.keys(b).filter((r) => (prev[r] || 0) !== (b[r] || 0))
  if (!changed.length) return
  changed.forEach((r) => { blinks.value[r] = true })
  setTimeout(() => changed.forEach((r) => { blinks.value[r] = false }), 900)
}, { deep: true })
</script>

<template>
  <div>
    <section class="container lobby-header">
      <div class="lobby-title"><h1>等待室</h1><span class="lobby-count">{{ n() }} / 10 人</span></div>
      <div class="lobby-room">
        <div><span class="lobby-label">房间号</span><strong>{{ creds().roomid }}</strong></div>
        <button id="copyInviteButton" class="lobby-invite" @click="copyInvite">
          {{ copied ? '已复制' : '复制邀请链接' }}
        </button>
      </div>
      <div class="lobby-roster-heading"><h2>玩家</h2><span>你是 {{ creds().userid }}</span></div>
      <div class="player-list">
        <div v-for="u in users" :key="u.userid" class="player-card">
          <img class="player-avatar" :src="avatarOf(u.userid)" :alt="u.userid" />
          <span class="player-name">{{ u.userid }}</span>
          <span class="player-tag">{{ state?.host === u.userid ? '房主' : u.userid === creds().userid ? '你' : '' }}</span>
        </div>
      </div>
    </section>

    <section class="container lobby-board">
      <div class="lobby-title"><h2>本局板子</h2><span class="lobby-label">玩家牌 + 3 张中央牌</span></div>
      <div class="board current-template">
        <span
          v-for="role in chips"
          :key="role"
          class="board-chip"
          :class="{ blink: blinks[role] }"
        >
          {{ roleIcon(role) }} {{ roleName(role) }} ×{{ liveBoard[role] }}
        </span>
      </div>

      <template v-if="isHost()">
        <h3 class="config-title">编辑板子</h3>
        <div class="config-panel">
          <div v-for="role in ROLE_ORDER" :key="role" class="board-row">
            <span>{{ roleIcon(role) }} {{ roleName(role) }}</span>
            <span class="board-stepper">
              <button :aria-label="`减少${roleName(role)}`" @click="adjust(role, -1)" :disabled="saving || starting || (board[role] || 0) <= 0">−</button>
              <span class="board-count">{{ board[role] || 0 }}</span>
              <button :aria-label="`增加${roleName(role)}`" @click="adjust(role, 1)" :disabled="saving || starting || atMax(role)">+</button>
            </span>
          </div>
          <p class="board-sum" :class="boardValid ? '' : 'error'">
            已配 {{ usedCount }} / {{ n() + 3 }} 张（玩家 {{ n() }} + 中央 3）
          </p>
          <p v-if="!boardValid" class="board-warn">
            {{ cardsLeft() > 0
              ? `板子不完整：还差 ${cardsLeft()} 张未分配`
              : `板子超量：超出 ${-cardsLeft()} 张` }}
          </p>
          <button class="btn-primary btn-block" :disabled="saving || starting || !dirty" @click="saveBoard">
            {{ saving ? '提交中…' : '提交板子' }}
          </button>
          <p v-if="dirty" class="muted">有未提交的修改。</p>
        </div>
      </template>
      <p v-else class="lobby-label">由房主配置</p>
    </section>

    <section class="container lobby-start">
    <p class="waiting-note">
      <template v-if="isHost()">
        {{ n() < MIN ? `还差 ${MIN - n()} 名玩家即可开始` : '请等待玩家到齐后再开始游戏' }}
      </template>
      <template v-else>
        等待房主开始游戏…
      </template>
    </p>

    <button v-if="isHost()" id="startGameButton" class="btn-primary btn-block" :class="{ disabledButton: !canStart() || !boardValid }"
      :disabled="!canStart() || starting || !boardValid" @click="confirmOpen = true">
      开始游戏
    </button>

    </section>

    <ConfirmDialog
      v-if="confirmOpen && isHost()"
      title="准备开始？"
      :message="`当前共有 ${n()} 名玩家，所有玩家都到齐了吗？开始后不可再修改板子。`"
      confirm-text="确认开始"
      cancel-text="再等等"
      :confirm-disabled="!canStart() || starting || !boardValid"
      @confirm="start"
      @cancel="confirmOpen = false"
    />

    <div v-if="err" class="error" role="alert">{{ err }}</div>
  </div>
</template>

<style scoped>
.current-template {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-start;
  gap: 6px;
  background: rgba(229, 189, 84, 0.05);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 12px;
}

.board-chip {
  display: inline-block;
  padding: 6px 12px;
  border-radius: 8px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--text);
  transition: border-color 0.15s, box-shadow 0.15s;
}

.board-chip.blink {
  border-color: var(--accent);
  animation: chipBlink 0.9s ease;
}

@keyframes chipBlink {
  0%, 100% { border-color: var(--border); box-shadow: none; }
  30% { border-color: var(--accent); box-shadow: 0 0 14px rgba(229, 189, 84, 0.65); }
}

.config-title { margin-top: 18px; }

.config-panel {
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 4px 14px;
}

.board-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 0;
  border-bottom: 1px dashed rgba(255, 255, 255, 0.06);
}
.board-row:last-child { border-bottom: none; }
.board-row span:first-child { color: var(--text); }
.board-stepper { display: flex; align-items: center; gap: 8px; }
.board-stepper button { padding: 6px 12px; margin: 0; }
.board-count { min-width: 28px; text-align: center; font-weight: 700; color: var(--accent); }
.board-sum { margin: 8px 0 0; color: var(--text-dim); font-size: 0.85rem; text-align: center; }
.board-warn {
  margin: 6px 0 0;
  color: var(--evil);
  font-size: 0.85rem;
  font-weight: 600;
  text-align: center;
}
.lobby-header, .lobby-board, .lobby-start { padding: 22px; }
.lobby-header { border-color: rgba(229, 189, 84, 0.25); background: radial-gradient(ellipse at 0 0, rgba(229, 189, 84, 0.08), transparent 65%), var(--surface); }
.lobby-title { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 18px; }
.lobby-title h1 { margin: 0; font-size: 1.5rem; }
.lobby-title h2, .lobby-roster-heading h2 { margin: 0; font-size: 1.05rem; }
.lobby-count { padding: 6px 10px; border: 1px solid var(--border); border-radius: 8px; color: var(--accent); font-size: 0.8rem; }
.lobby-room { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 16px; border: 1px solid rgba(229, 189, 84, 0.2); border-radius: 12px; background: rgba(229, 189, 84, 0.04); }
.lobby-label { color: var(--text-dim); font-size: 0.72rem; }
.lobby-room strong { display: block; margin-top: 5px; font-family: ui-monospace, monospace; font-size: 1.4rem; letter-spacing: 0.08em; color: var(--accent-hover); }
.lobby-invite { padding: 9px 10px; margin: 0; font-size: 0.75rem; flex-shrink: 0; }
.lobby-roster-heading { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin: 24px 0 14px; }
.lobby-roster-heading > span { font-size: 0.72rem; color: var(--text-dim); }
.player-list { display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; }
.player-card { flex: 0 0 calc((100% - 16px) / 3); align-items: center; text-align: center; min-width: 0; padding: 14px 6px 8px; background: var(--surface-2); border: 1px solid var(--border); border-radius: 12px; }
.player-avatar { display: block; width: 46px; height: 46px; margin-inline: auto; }
.player-name { font-size: 0.8rem; max-width: 100%; overflow-wrap: anywhere; }
.player-tag { min-height: 15px; font-size: 0.65rem; color: var(--accent); }
.config-title { font-size: 0.85rem; margin-bottom: 12px; }
.config-panel { border: 0; padding: 0; }
.board-row { padding: 10px 0; border-bottom-style: solid; font-size: 0.85rem; }
.board-stepper { gap: 4px; }
.board-stepper button { width: 34px; height: 34px; padding: 0; border-radius: 8px; }
.board-sum { margin-top: 16px; padding: 10px; border-radius: 8px; background: var(--surface-2); font-size: 0.78rem; }
.lobby-start .waiting-note { margin: 0; padding: 0; border: 0; background: none; box-shadow: none; backdrop-filter: none; font-size: 0.82rem; }
.lobby-start > button { margin-top: 14px; }
.lobby-header button:focus-visible, .board-stepper button:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
@media (max-width: 360px) {
  .lobby-header, .lobby-board, .lobby-start { padding: 18px 14px; }
  .lobby-room { padding: 12px; }
  .lobby-room strong { font-size: 1.2rem; }
}
@media (prefers-reduced-motion: reduce) {
  .board-chip.blink { animation: none; }
}
</style>
