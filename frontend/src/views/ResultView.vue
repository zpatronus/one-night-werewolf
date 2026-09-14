<script setup>
import { computed, onMounted, ref } from 'vue'
import { post } from '../api'
import { calculateResult } from '../result'
import { creds } from '../store'
import { roleName, roleIcon, verdictText, errorText } from '../gameConfig'
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

const peek = (c) => `${roleIcon(c)} ${roleName(c)}`

// Render one night-action entry (JSON from the backend, language-free codes).
function opSentence(op) {
  switch (op.type) {
    case 'wolf':
      return `🐺 狼人相互认识：${(op.wolves || []).join('、')}`
    case 'lone_wolf':
      return `🐺 独狼窥视中央第 ${(op.center ?? -1) + 1} 张 → ${peek(op.card)}`
    case 'minion':
      return `💀 爪牙 ${op.minion} 得知了狼人是：${(op.wolves || []).join('、')}`
    case 'seer': {
      const who = op.seer || '预言家'
      if (Array.isArray(op.center_picks) && op.center_picks.length) {
        const picks = op.center_picks.map((i) => `第 ${i + 1} 张`).join('、')
        const cards = (op.peeked || []).map(peek).join('、')
        return `🔮 ${who} 窥视中央 ${picks} → ${cards}`
      }
      const card = (op.peeked || [])[0]
      return card
        ? `🔮 ${who} 窥视 ${op.target} → ${peek(card)}`
        : `🔮 ${who} 未成功窥视。`
    }
    case 'robber':
      return `🥷 强盗 ${op.robber} 偷取 ${op.target} → ${op.robber} 现持 ${peek(op.robber_new)}，${op.target} 现持 ${peek(op.target_new)}`
    case 'troublemaker':
      return `🃏 捣蛋鬼 ${op.troublemaker || '（玩家未知）'} 交换 ${op.a} 与 ${op.b} → ${op.a} 现持 ${peek(op.a_new)}，${op.b} 现持 ${peek(op.b_new)}`
    case 'insomniac':
      return `🌙 ${op.insomniac || '失眠者'} 确认自己是 ${peek(op.card)}`
    default:
      return ''
  }
}

function voters() {
  const v = data.value?.votes || {}
  const keys = Object.keys(v)
  if (!keys.length) return '全部弃权，无人被投。'
  return keys.map((u) => `${u} ${v[u]}`).join('、')
}
</script>

<template>
  <div v-if="data">
    <div class="container verdict-banner" :class="data.good_win ? 'good' : 'evil'">
      {{ verdictText(data.reason) }}
    </div>

    <div class="container">
      <div class="subtitle">被处决者</div>
      <p class="verdict-executed">
        <template v-if="data.executed">{{ data.executed }} 被处决出局</template>
        <template v-else>无人被处决（弃权或平票）</template>
      </p>
      <p class="muted" style="font-size:13px">投票分布：{{ voters() }}</p>
      <p v-for="p in players" :key="p.userid" class="muted">{{ p.userid }} → {{ p.vote_target || '弃权' }}</p>
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
          <span class="transition-user">{{ p.userid }}</span>
          <span class="transition-role">{{ roleIcon(p.role) }} {{ roleName(p.role) }}</span>
          <span class="transition-arrow">→</span>
          <span class="transition-role">{{ roleIcon(p.final_role) }} {{ roleName(p.final_role) }}</span>
          <span class="transition-verdict" :class="p.won ? 'win' : 'lose'">
            {{ p.won ? '胜' : '负' }}
          </span>
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

    <div class="container nav-actions">
      <button class="btn-primary btn-block" @click="$router.push('/')">返回主页</button>
      <button class="btn-primary btn-block" style="background:rgba(255,255,255,0.08)" @click="$router.push('/createroom')">
        创建新房间
      </button>
    </div>
  </div>
  <div v-else-if="err" class="container error">{{ err }} <button :disabled="loading" @click="loadResult">重试</button></div>
  <div v-else class="muted" style="text-align:center">正在结算…</div>
</template>

<style scoped>
.verdict-executed { font-size: 24px; font-weight: 800; color: var(--accent); margin: 4px 0; }

.transition-list { display: flex; flex-direction: column; gap: 8px; }
.transition-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface-2);
}
.transition-row.win { border-color: rgba(46, 204, 113, 0.45); }
.transition-row.lose { border-color: rgba(231, 76, 60, 0.45); }
.transition-avatar { width: 34px; height: 34px; border-radius: 50%; }
.transition-user { font-weight: 700; color: var(--text); min-width: 40px; }
.transition-arrow { color: var(--text-dim); }
.transition-role { color: var(--text); font-size: 0.92rem; white-space: nowrap; }
.transition-verdict {
  margin-left: auto;
  font-weight: 800;
  font-size: 0.95rem;
  min-width: 24px;
  text-align: center;
}
.transition-verdict.win { color: var(--good, #2ecc71); }
.transition-verdict.lose { color: var(--evil, #e74c3c); }

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

.nav-actions { padding-top: 6px; }
</style>
