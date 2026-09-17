<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { post } from '../api'
import { calculateResult } from '../result'
import { useRouter } from 'vue-router'
import { nextRoomId } from '../random'
import { getMyAvatar } from '../avatar'
import { creds, setAuth } from '../store'
import { roleName, roleIcon, errorText, localBoardForCreation, verdictText, ROLE_DISPLAY } from '../gameConfig'
import { avatarUrl } from '../avatar'
import { sortPlayers } from '../playerOrder'

const router = useRouter()
const nextId = nextRoomId(creds().roomid)
const nextBusy = ref(false)
const autoJoin = ref(false)
const nextMessage = ref('')
const phaseRoute = { waiting: '/waitingroom', op: '/ops', reveal: '/discussion', result: '/result' }
let nextTimer = null
let nextRevision = 0

function cancelAutoJoin() {
  nextRevision++
  clearTimeout(nextTimer)
  autoJoin.value = false
  nextBusy.value = false
  nextMessage.value = ''
}
onUnmounted(cancelAutoJoin)

async function enterNext(create = false) {
  if (nextBusy.value || autoJoin.value) return
  const revision = ++nextRevision
  const identity = { ...creds(), roomid: nextId, avatar: getMyAvatar() }
  nextBusy.value = true
  nextMessage.value = ''
  async function attempt() {
    let res = await post(create ? 'create_room' : 'join_room',
      create ? { ...identity, board: localBoardForCreation() } : identity)
    if (revision !== nextRevision) return
    if (create && !res.ok && res.error === 'roomid_taken') {
      res = await post('join_room', identity)
      if (revision !== nextRevision) return
    }
    nextBusy.value = false
    if (res.ok) {
      autoJoin.value = false
      setAuth({ ...identity, avatar: res.avatar })
      router.push(phaseRoute[res.phase] || '/waitingroom')
    } else if (!create && ['room_not_found', 'network_error'].includes(res.error)) {
      autoJoin.value = true
      nextMessage.value = res.error === 'room_not_found'
        ? '等待房主创建房间中，届时会自动加入。'
        : '网络连接失败，正在重试自动加入…'
      nextTimer = setTimeout(attempt, 2000)
    } else {
      autoJoin.value = false
      nextMessage.value = errorText(res.error)
    }
  }
  await attempt()
}

const data = ref(null)
const err = ref('')
const loading = ref(false)

async function loadResult() {
  if (loading.value) return
  loading.value = true
  err.value = ''
  const res = await post('result', creds())
  loading.value = false
  if (!res.ok) { err.value = errorText(res.error); return }
  data.value = calculateResult(res)
}
onMounted(loadResult)

const players = computed(() => sortPlayers(creds().roomid, data.value?.players || []))
const ops = computed(() => data.value?.ops || [])
const avatarMap = computed(() => Object.fromEntries(players.value.map((p) => [p.userid, p.avatar])))
// The viewer's own row, for "your final role / did you win".
const me = computed(() => players.value.find((p) => p.userid === creds().userid))

// Final role per userid, so vote targets can be colored by their faction.
const finalRoleByUser = computed(() =>
  Object.fromEntries(players.value.map((p) => [p.userid, p.final_role]))
)
const roleFaction = (role) => ROLE_DISPLAY[role]?.faction || 'good'
const targetFaction = (uid) => roleFaction(finalRoleByUser.value[uid])

const peek = (c) => `${roleIcon(c)} ${roleName(c)}`

// Render one night-action entry (JSON from the backend, language-free codes).
function opSentence(op) {
  switch (op.type) {
    case 'wolf':
      return op.wolves.length === 1
        ? `🐺 独狼：${op.wolves[0]}`
        : `🐺 狼人相互认识：${(op.wolves || []).join('、')}`
    case 'lone_wolf':
      return `🐺 独狼 ${op.lone_wolf || '（?）'} 窥视中央第 ${(op.center ?? -1) + 1} 张 → ${peek(op.card)}`
    case 'minion':
      return op.wolves?.length
        ? `💀 爪牙 ${op.minion} 得知了狼人是：${op.wolves.join('、')}`
        : `💀 爪牙 ${op.minion} 得知场上没有狼人。`
    case 'seer': {
      const who = op.seer || '预言家'
      if (Array.isArray(op.center_picks) && op.center_picks.length) {
        const picks = op.center_picks.map((i) => `第 ${i + 1} 张`).join('、')
        const cards = (op.peeked || []).map(peek).join('、')
        return `🔮 预言家 ${who} 窥视中央 ${picks} → ${cards}`
      }
      const card = (op.peeked || [])[0]
      return card
        ? `🔮 预言家 ${who} 窥视 ${op.target} → ${peek(card)}`
        : `🔮 预言家 ${who} 未成功窥视。`
    }
    case 'robber':
      return `🥷 强盗 ${op.robber} 偷取 ${op.target} → ${op.robber} 现持 ${peek(op.robber_new)}，${op.target} 现持 ${peek(op.target_new)}`
    case 'troublemaker':
      return `🃏 捣蛋鬼 ${op.troublemaker || '（玩家未知）'} 交换 ${op.a} 与 ${op.b} → ${op.a} 现持 ${peek(op.a_new)}，${op.b} 现持 ${peek(op.b_new)}`
    case 'insomniac':
      return `🌙 失眠者 ${op.insomniac || ''} 确认自己是 ${peek(op.card)}`
    default:
      return ''
  }
}

// Horizontal vote bars, most-voted target first. The left label column is a
// fixed width, so every track is the same length; only the fill is sized
// proportionally to the vote count (pct of the top count).
const voteChart = computed(() => {
  const entries = Object.entries(data.value?.votes || {}).map(([target, count]) => ({ target, count }))
  const max = Math.max(0, ...entries.map((e) => e.count))
  return entries
    .sort((a, b) => b.count - a.count)
    .map((e) => ({ ...e, pct: max ? Math.round((e.count / max) * 100) : 0 }))
})

</script>

<template>
  <div v-if="data">
    <section class="container result-hero">
      <span class="result-eyebrow">一夜落幕 · 真相揭晓</span>
      <div class="result-emblem" aria-hidden="true">{{ data.reason === 'no_evil_but_votes' ? '☾' : data.good_win ? '☀' : '☾' }}</div>
      <h1>{{ data.reason === 'no_evil_but_votes' ? '全员落败' : data.reason === 'no_evil_players' ? '全员获胜' : data.good_win ? '好人阵营获胜' : '狼人阵营获胜' }}</h1>
      <p class="result-reason">{{ verdictText(data.reason) }}</p>
      <div class="execution-note">
        <span>处决结果</span>
        <strong>{{ data.executed || '无人被处决' }}</strong>
      </div>
      <div v-if="me" class="personal-result">
        <img :src="avatarUrl(me.avatar)" :alt="me.userid" />
        <div class="personal-identity">
          <span>{{ me.userid }} · 最终身份</span>
          <strong>{{ roleIcon(me.final_role) }} {{ roleName(me.final_role) }}</strong>
        </div>
        <span class="personal-verdict" :class="{ won: me.won }">{{ me.won ? '胜利' : '落败' }}</span>
      </div>
    </section>

    <section class="container next-room" aria-labelledby="next-room-title">
      <div class="next-room-heading">
        <div>
          <h2 id="next-room-title">再来一局</h2>
          <p>沿用你的玩家身份，继续下一场。</p>
        </div>
        <div class="next-room-code">
          <span>下一个房间</span>
          <strong>{{ nextId }}</strong>
        </div>
      </div>
      <div class="next-room-actions">
        <button class="btn-primary" :disabled="nextBusy || autoJoin" @click="enterNext(true)">
          <span aria-hidden="true" class="next-action-icon">＋</span>
          新建下一个房间
        </button>
        <button v-if="autoJoin" class="next-cancel" @click="cancelAutoJoin">取消自动加入</button>
        <button v-else :disabled="nextBusy" @click="enterNext(false)">
          加入下一个房间
          <span aria-hidden="true" class="next-action-icon">→</span>
        </button>
      </div>
      <div v-if="nextBusy || nextMessage" class="next-room-status" :class="{ 'is-waiting': autoJoin || nextBusy }" role="status" aria-live="polite">
        <span v-if="autoJoin || nextBusy" class="next-status-dot" aria-hidden="true"></span>
        <span>{{ nextBusy ? '正在进入下一个房间…' : nextMessage }}</span>
      </div>
    </section>

    <!-- 投票柱状图：横向条，长度按得票数比例 -->
    <div class="container vote-section">
      <div class="result-section-heading"><div><span class="result-eyebrow">每一票，都有答案</span><h2>投票分布</h2></div><span class="section-count">{{ players.length }} 位玩家</span></div>
      <div v-if="voteChart.length" class="vote-chart">
        <div v-for="e in voteChart" :key="e.target" class="vote-bar-row">
          <span class="vote-target" :class="targetFaction(e.target)">
            {{ e.target }}
            <span class="vote-target-role">{{ roleIcon(finalRoleByUser[e.target]) }} {{ roleName(finalRoleByUser[e.target]) }}</span>
          </span>
          <div class="vote-bar-track" :title="`${e.target} ${e.count} 票`">
            <div
              class="vote-bar-fill"
              :class="targetFaction(e.target)"
              :style="{ width: e.pct + '%' }"
            ></div>
          </div>
          <span class="vote-count">{{ e.count }}</span>
        </div>
      </div>
      <p v-else class="muted">全部弃权，无人被投。</p>
      <details class="vote-breakdown">
        <summary>查看每位玩家的投票</summary>
        <div class="vote-details">
        <div v-for="p in players" :key="'v' + p.userid" class="vote-detail-row">
          <span class="vote-detail-bubble" :class="targetFaction(p.userid)">
            <img class="vote-detail-avatar small" :src="avatarUrl(p.avatar)" :alt="p.userid" />
            <span class="vote-detail-user">{{ p.userid }}</span>
          </span>
          <span class="vote-detail-arrow">→</span>
          <span
            v-if="p.vote_target"
            class="vote-detail-bubble"
            :class="targetFaction(p.vote_target)"
          >
            <img
              class="vote-detail-avatar small"
              :src="avatarUrl(avatarMap[p.vote_target])"
              :alt="p.vote_target"
            />
            <span class="vote-detail-user">{{ p.vote_target }}</span>
          </span>
          <span v-else class="vote-detail-abstain">弃权</span>
        </div>
        </div>
      </details>
    </div>

    <!-- 每位玩家：最初身份 → 最终身份 + 胜负 -->
    <div class="container">
      <div class="result-section-heading"><div><span class="result-eyebrow">从夜晚到天亮</span><h2>身份揭晓</h2></div><span class="section-count">初始 → 最终</span></div>
      <div class="transition-list">
        <div
          v-for="p in players"
          :key="p.userid"
          class="transition-row"
          :class="p.won ? 'win' : 'lose'"
        >
          <img class="transition-avatar" :src="avatarUrl(p.avatar)" :alt="p.userid" />
          <div class="transition-main">
            <div class="transition-top">
              <span class="transition-user">{{ p.userid }}</span>
              <span class="transition-verdict" :class="p.won ? 'win' : 'lose'">
                {{ p.won ? '胜利' : '落败' }}
              </span>
            </div>
            <div class="transition-change">
              <span class="role-chip">{{ roleIcon(p.role) }} {{ roleName(p.role) }}</span>
              <span class="transition-arrow">→</span>
              <span class="role-chip">{{ roleIcon(p.final_role) }} {{ roleName(p.final_role) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 夜晚操作回放（后端 JSON，前端渲染） -->
    <div v-if="ops.length" class="container">
      <div class="result-section-heading"><div><span class="result-eyebrow">按生效顺序，还原整夜</span><h2>夜间回放</h2></div></div>
      <div class="ops-list">
        <div v-for="(op, i) in ops" :key="i" class="ops-step">
          <span class="ops-index">{{ i + 1 }}</span>
          <span class="ops-text">{{ opSentence(op) }}</span>
        </div>
      </div>
    </div>
  </div>
  <div v-else-if="err" class="container error">{{ err }} <button :disabled="loading" @click="loadResult">重试</button></div>
  <div v-else class="status surface-panel">正在结算…</div>
</template>

<style scoped>
.result-hero {
  text-align: center;
  padding: 28px 22px 20px;
  border-color: rgba(229, 189, 84, 0.3);
  background: radial-gradient(ellipse at 50% 0, rgba(229, 189, 84, 0.13), transparent 65%), var(--surface);
}
.result-eyebrow { color: var(--accent); font-size: 0.68rem; letter-spacing: 0.1em; }
.result-emblem { display: grid; place-items: center; width: 72px; height: 72px; margin: 22px auto 18px; border-radius: 50%; border: 1px solid rgba(229, 189, 84, 0.35); outline: 5px solid rgba(229, 189, 84, 0.04); background: rgba(229, 189, 84, 0.06); color: var(--accent-hover); font-size: 2.5rem; }
.result-hero h1 { margin: 0; font-size: clamp(1.5rem, 6vw, 1.9rem); letter-spacing: 0.05em; }
.result-reason { margin: 12px auto 18px; max-width: 30em; color: var(--text-dim); font-size: 0.82rem; line-height: 1.8; }
.execution-note { display: flex; justify-content: center; align-items: center; flex-wrap: wrap; gap: 10px; font-size: 0.8rem; }
.execution-note > span { color: var(--text-dim); }
.execution-note strong { font-weight: 600; overflow-wrap: anywhere; }
.personal-result { display: flex; align-items: center; gap: 12px; margin-top: 22px; padding-top: 20px; border-top: 1px solid var(--border); text-align: left; }
.personal-result img { width: 44px; height: 44px; border-radius: 50%; }
.personal-identity { display: grid; gap: 5px; min-width: 0; }
.personal-identity > span { color: var(--text-dim); font-size: 0.7rem; overflow-wrap: anywhere; }
.personal-identity strong { font-size: 0.95rem; }
.personal-verdict { margin-left: auto; flex-shrink: 0; padding: 6px 10px; border: 1px solid var(--border); border-radius: 8px; color: var(--text-dim); font-size: 0.8rem; }
.personal-verdict.won { color: var(--accent-hover); background: rgba(229, 189, 84, 0.08); border-color: rgba(229, 189, 84, 0.3); }
.result-section-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin: 3px 0 20px; }
.result-section-heading h2 { margin: 6px 0 0; font-size: 1.15rem; }
.section-count { color: var(--text-dim); font-size: 0.7rem; white-space: nowrap; }
.vote-breakdown { border-top: 1px solid var(--border); margin-top: 18px; padding-top: 14px; }
.vote-breakdown summary { color: var(--text-dim); font-size: 0.78rem; cursor: pointer; }
.vote-breakdown summary:focus-visible { outline: 2px solid var(--accent); outline-offset: 4px; }
.vote-breakdown .vote-details { display: grid; grid-template-columns: 1fr; gap: 10px; margin-top: 16px; }
.vote-breakdown .vote-detail-row { display: grid; grid-template-columns: minmax(0, 1fr) 16px minmax(0, 1fr); }
.vote-breakdown .vote-detail-bubble { border: 0; background: transparent; padding: 4px 0; }
.vote-breakdown .vote-detail-user { white-space: normal; overflow-wrap: anywhere; font-size: 0.8rem; }
.vote-breakdown .vote-detail-abstain { border: 0; background: none; padding: 4px 0; }

.next-room {
  border-color: rgba(229, 189, 84, 0.28);
  background: linear-gradient(125deg, rgba(229, 189, 84, 0.08), transparent 65%), var(--surface);
}
.next-room-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}
.next-room h2 { margin: 0 0 6px; font-size: 1.15rem; font-weight: 750; }
.next-room-heading p { margin: 0; color: var(--text-dim); font-size: 0.78rem; line-height: 1.6; }
.next-room-code {
  flex-shrink: 0;
  padding: 8px 12px;
  border: 1px solid rgba(229, 189, 84, 0.2);
  border-radius: var(--radius-sm);
  background: rgba(0, 0, 0, 0.16);
  text-align: center;
}
.next-room-code span { display: block; color: var(--text-dim); font-size: 0.65rem; margin-bottom: 3px; }
.next-room-code strong {
  text-transform: none;
  color: var(--accent-hover);
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 1.15rem;
  letter-spacing: 1px;
}
.next-room-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.next-room-actions button {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 5px;
  min-width: 0;
  min-height: 46px;
  margin: 0;
  padding: 11px 8px;
  font-size: 0.82rem;
  line-height: 1.4;
}
.next-action-icon { color: inherit; font-size: 1.05rem; line-height: 1; }
.next-room-actions .next-cancel { color: var(--text-dim); background: transparent; }
.next-room-actions button:focus-visible { outline: 2px solid var(--accent-hover); outline-offset: 3px; }
.next-room-status {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
  font-size: 0.78rem;
  line-height: 1.6;
}
.next-room-status span { color: var(--evil); }
.next-room-status.is-waiting span { color: var(--text-dim); }
.next-status-dot {
  flex: 0 0 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 0 4px rgba(229, 189, 84, 0.1);
}
@media (max-width: 360px) {
  .next-room-heading { align-items: flex-start; }
  .next-room-code { padding: 8px; }
  .next-room-actions { grid-template-columns: 1fr; }
}

.transition-list { display: flex; flex-direction: column; gap: 8px; }
.transition-row {
  display: grid;
  grid-template-columns: 40px 1fr;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface-2);
}
.transition-row.win { border-color: rgba(229, 189, 84, 0.25); }
.transition-row.lose { border-color: var(--border); }
.transition-avatar { width: 40px; height: 40px; border-radius: 50%; }
.transition-main { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.transition-top {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
}
.transition-user { font-weight: 700; color: var(--text); }
.transition-change {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.role-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 10px;
  border-radius: 999px;
  background: rgba(229, 189, 84, 0.08);
  border: 1px solid rgba(229, 189, 84, 0.25);
  color: var(--text);
  font-size: 0.78rem;
  font-weight: 500;
  white-space: nowrap;
}
.transition-arrow { color: var(--text-dim); }
.transition-verdict {
  font-weight: 800;
  font-size: 0.75rem;
  min-width: 32px;
  text-align: right;
}
.transition-verdict.win { color: var(--accent-hover); }
.transition-verdict.lose { color: var(--text-dim); }

.ops-list { display: flex; flex-direction: column; gap: 6px; }
.ops-step {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  background: rgba(229, 189, 84, 0.06);
  border: 1px solid rgba(229, 189, 84, 0.22);
}
.ops-index {
  flex: none;
  width: 22px;
  height: 22px;
  line-height: 22px;
  text-align: center;
  border-radius: 50%;
  background: rgba(229, 189, 84, 0.18);
  color: var(--accent);
  font-weight: 800;
  font-size: 12px;
}
.ops-text { font-size: 0.92rem; color: var(--text); line-height: 1.6; }

/* 投票分布柱状图 */
.vote-section {
  max-width: 100%;
  margin-left: auto;
  margin-right: auto;
}
.vote-chart { display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px; }
.vote-bar-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.vote-target {
  /* fixed width so every bar track starts at the same x and has equal length,
     regardless of how long a username / role name happens to be */
  flex: none;
  width: 100px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 5px;
  font-weight: 700;
  color: var(--text);
  text-align: left;
  line-height: 1.4;
}
.vote-target.good { color: var(--good); }
.vote-target.evil { color: var(--evil); }
.vote-target-role {
  font-size: 0.68rem;
  font-weight: 500;
  color: var(--text-dim);
  white-space: nowrap;
}
.vote-bar-track {
  position: relative;
  flex: 1;
  height: 10px;
  border-radius: 4px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  overflow: hidden;
}
.vote-bar-fill {
  position: absolute;
  /* left-anchored; width set inline proportionally to the vote count */
  inset: 0 auto 0 0;
  height: 100%;
  border-radius: 3px;
  background: linear-gradient(90deg, var(--accent), rgba(229, 189, 84, 0.55));
  transition: width 0.4s ease;
}
.vote-bar-fill.good { background: linear-gradient(90deg, var(--good), rgba(69, 183, 245, 0.45)); }
.vote-bar-fill.evil { background: linear-gradient(90deg, var(--evil), rgba(255, 139, 69, 0.45)); }
.vote-count {
  flex: none;
  font-weight: 800;
  color: var(--accent);
  min-width: 18px;
  text-align: right;
}

/* 谁投了谁：头像行，居中排列，换行排布以利用横向空间 */
.vote-details {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 10px 20px;
}
/* 每行只是纯文本/头像排列，不套卡片框，避免视觉上太碎 */
.vote-detail-row {
  display: flex;
  align-items: center;
  gap: 6px;
}
.vote-detail-avatar {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  flex: none;
}
.vote-detail-avatar.small { width: 20px; height: 20px; }
.vote-detail-bubble {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px 3px 5px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border);
}
.vote-detail-bubble.good {
  background: rgba(69, 183, 245, 0.10);
  border-color: rgba(69, 183, 245, 0.35);
}
.vote-detail-bubble.evil {
  background: rgba(255, 139, 69, 0.12);
  border-color: rgba(255, 139, 69, 0.45);
}
.vote-detail-user { font-weight: 700; color: var(--text); white-space: nowrap; }
.vote-detail-arrow { color: var(--text-dim); }
.vote-detail-abstain {
  padding: 3px 12px;
  border-radius: 999px;
  background: var(--surface-2);
  border: 1px dashed var(--border);
  color: var(--text-dim);
  font-size: 0.85rem;
}
.ops-list { gap: 0; }
.ops-step { position: relative; border: 0; background: transparent; padding: 0 0 22px; gap: 14px; }
.ops-step:not(:last-child)::before { content: ''; position: absolute; left: 10px; top: 27px; bottom: 5px; width: 1px; background: rgba(229, 189, 84, 0.22); }
.ops-step:last-child { padding-bottom: 0; }
.ops-text { font-size: 0.85rem; line-height: 1.8; overflow-wrap: anywhere; }
.vote-target { overflow-wrap: anywhere; font-size: 0.85rem; }
.vote-chart { gap: 16px; }
@media (max-width: 360px) {
  .result-hero { padding: 24px 16px 18px; }
  .transition-row { padding: 10px; gap: 8px; }
  .role-chip { padding: 3px 6px; font-size: 0.72rem; }
  .transition-change { gap: 5px; }
  .section-count { font-size: 0.65rem; }
}
@media (prefers-reduced-motion: reduce) {
  .vote-bar-fill { transition: none; }
}
</style>
