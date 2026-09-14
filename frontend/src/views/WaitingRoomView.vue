<script setup>
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { post } from '../api'
import { creds } from '../store'
import { useRoomState } from '../useRoomState'
import { errorText, boardTemplate, roleName, roleIcon, ROLE_ORDER } from '../gameConfig'
import { avatarUrl, getMyAvatar } from '../avatar'
import { sortPlayers } from '../playerOrder'
import ConfirmDialog from '../components/ConfirmDialog.vue'

const router = useRouter()
const { state, applyState } = useRoomState()
const board = ref(null)           // {role_code: count}; editable by host
const err = ref('')
const starting = ref(false)
const saving = ref(false)
const draftEdited = ref(false)
const confirmOpen = ref(false)    // start-confirmation dialog

const MIN = 3
const MAX = 10
const n = () => state.value?.userCount || 0
const isHost = () => state.value?.is_owner

// Polls update the public board without overwriting an unsaved host draft.
watch(state, (s) => {
  if (!s || s.phase !== 'waiting' || draftEdited.value || saving.value) return
  board.value = { ...(s.board ?? boardTemplate()) }
}, { immediate: true })

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
  draftEdited.value = true
}

async function saveBoard() {
  if (!isHost() || saving.value || starting.value) return
  saving.value = true
  err.value = ''
  try {
    const res = await post('set_board', { ...creds(), board: { ...board.value } })
    if (!res.ok) { err.value = errorText(res.error); return }
    board.value = { ...res.board }
    draftEdited.value = false
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
    <div class="container">
      <div class="info-grid">
        <div class="info-row">
          <span class="info-label">房间ID</span>
          <span class="info-value">{{ creds().roomid }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">你的玩家ID</span>
          <span class="info-value">{{ creds().userid }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">玩家数量</span>
          <span class="info-value">{{ n() }}</span>
        </div>
      </div>

      <div class="subtitle">房间内的玩家</div>
      <div class="player-list">
        <div v-for="u in users" :key="u.userid" class="player-card">
          <img class="player-avatar" :src="avatarOf(u.userid)" :alt="u.userid" />
          <span class="player-name">{{ u.userid }}{{ state.host === u.userid ? ' 👑' : '' }}</span>
        </div>
      </div>
    </div>

    <div class="container">
      <div class="subtitle">当前板子</div>
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
        <div class="subtitle config-title">配置板子</div>
        <div class="config-panel">
          <div v-for="role in ROLE_ORDER" :key="role" class="board-row">
            <span>{{ roleIcon(role) }} {{ roleName(role) }}</span>
            <span class="board-stepper">
              <button @click="adjust(role, -1)" :disabled="saving || starting || (board[role] || 0) <= 0">−</button>
              <span class="board-count">{{ board[role] || 0 }}</span>
              <button @click="adjust(role, 1)" :disabled="saving || starting || atMax(role)">+</button>
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
          <p v-if="dirty" class="muted">修改尚未提交，请提交后再开始游戏。</p>
        </div>
      </template>
      <p v-else class="subsubtitle" style="text-align:center">板子由房主配置，上方为当前内容。</p>
    </div>

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

    <div class="status">{{ err }}</div>
  </div>
</template>

<style scoped>
.current-template {
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
</style>