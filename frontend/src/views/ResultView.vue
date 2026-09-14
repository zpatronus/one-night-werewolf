<script setup>
import { computed, onMounted, ref } from 'vue'
import { post } from '../api'
import { calculateResult } from '../result'
import { creds } from '../store'
import { roleName, roleIcon, errorText, ROLE_DISPLAY } from '../gameConfig'
import { avatarUrl } from '../avatar'
import { sortPlayers } from '../playerOrder'

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
      return `💀 爪牙 ${op.minion} 得知了狼人是：${(op.wolves || []).join('、')}`
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
    <div class="container">
      <div class="subtitle">结算</div>
      <div class="result-summary">
        <div class="summary-tile">
          <div class="summary-label">被处决者</div>
          <div class="summary-value">
            <template v-if="data.executed">🔨 {{ data.executed }} 被处决出局</template>
            <template v-else>弃权或平票，无人被处决</template>
          </div>
        </div>
        <div class="summary-tile" :class="data.good_win ? 'good' : 'evil'">
          <div class="summary-label">获胜阵营</div>
          <div class="summary-value">{{ data.good_win ? '🎉 好人阵营获胜' : '🎉 狼人阵营获胜' }}</div>
        </div>
        <div class="summary-tile" :class="me ? roleFaction(me.final_role) : ''">
          <div class="summary-label">你的最终身份</div>
          <div class="summary-value">
            <template v-if="me">{{ roleIcon(me.final_role) }} {{ roleName(me.final_role) }}</template>
            <template v-else>—</template>
          </div>
        </div>
        <div class="summary-tile" :class="me ? (me.won ? 'win' : 'lose') : ''">
          <div class="summary-label">你的结果</div>
          <div class="summary-value">{{ me ? (me.won ? '你胜利了 ✔' : '你失败了 ✘') : '—' }}</div>
        </div>
      </div>
    </div>

    <!-- 投票柱状图：横向条，长度按得票数比例 -->
    <div class="container vote-section">
      <div class="subtitle">投票分布</div>
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
    </div>

    <!-- 每位玩家：最初身份 → 最终身份 + 胜负 -->
    <div class="container">
      <div class="subtitle">角色变化</div>
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
                {{ p.won ? '胜' : '负' }}
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
      <div class="subtitle">夜晚行动</div>
      <div class="ops-list">
        <div v-for="(op, i) in ops" :key="i" class="ops-step">
          <span class="ops-index">{{ i + 1 }}</span>
          <span class="ops-text">{{ opSentence(op) }}</span>
        </div>
      </div>
    </div>
  </div>
  <div v-else-if="err" class="container error">{{ err }} <button :disabled="loading" @click="loadResult">重试</button></div>
  <div v-else class="muted" style="text-align:center">正在结算…</div>
</template>

<style scoped>
/* 顶部结算：被处决者 / 获胜阵营 / 你的最终身份 / 你的结果，网格排布 */
.result-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 8px;
}
.summary-tile {
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  background: var(--surface-2);
  border: 1px solid var(--border);
  min-width: 0;
}
.summary-tile.good { border-color: rgba(69, 183, 245, 0.4); }
.summary-tile.evil { border-color: rgba(255, 139, 69, 0.4); }
.summary-tile.win { border-color: rgba(46, 204, 113, 0.45); }
.summary-tile.lose { border-color: rgba(231, 76, 60, 0.45); }
.summary-label {
  font-size: 0.72rem;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--text-dim);
  margin-bottom: 4px;
}
.summary-value {
  font-size: 1rem;
  font-weight: 700;
  color: var(--text);
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
}
.summary-tile.good .summary-value { color: var(--good); }
.summary-tile.evil .summary-value { color: var(--evil); }
.summary-tile.win .summary-value { color: #2ecc71; }
.summary-tile.lose .summary-value { color: #e74c3c; }

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
.transition-row.win { border-color: rgba(46, 204, 113, 0.45); }
.transition-row.lose { border-color: rgba(231, 76, 60, 0.45); }
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
  font-size: 0.9rem;
  font-weight: 600;
  white-space: nowrap;
}
.transition-arrow { color: var(--text-dim); }
.transition-verdict {
  font-weight: 800;
  font-size: 1rem;
  min-width: 24px;
  text-align: right;
}
.transition-verdict.win { color: #2ecc71; }
.transition-verdict.lose { color: #e74c3c; }

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
  max-width: 400px;
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
  width: 130px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
  font-weight: 700;
  color: var(--text);
  text-align: center;
  line-height: 1.15;
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
  height: 20px;
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
</style>
