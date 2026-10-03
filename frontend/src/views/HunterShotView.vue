<script setup>
import { computed, ref } from 'vue'
import { useRoomState } from '../useRoomState'
import { creds } from '../store'
import { post } from '../api'
import { errorText, roleName, roleIcon } from '../gameConfig'
import { avatarUrl } from '../avatar'
import { sortPlayers } from '../playerOrder'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import RoleCard from '../components/RoleCard.vue'
import NightInfoPanel from '../components/NightInfoPanel.vue'

const { state, error, applyState } = useRoomState()
const target = ref(null)
const busy = ref(false)
const err = ref('')
const confirmOpen = ref(false)
const users = computed(() => sortPlayers(creds().roomid, (state.value?.users || []).filter(p => p.userid !== creds().userid)))
const showNight = ref(true)
const voteTotals = computed(() => {
  const tally = new Map((state.value?.users || []).map(p => [p.userid, 0]))
  for (const vote of state.value?.votes || []) {
    if (vote.target) tally.set(vote.target, (tally.get(vote.target) || 0) + 1)
  }
  return [...tally].map(([userid, count]) => ({ userid, count }))
    .sort((a, b) => b.count - a.count || a.userid.localeCompare(b.userid))
})
const avatarByUser = computed(() => Object.fromEntries((state.value?.users || []).map(p => [p.userid, p.avatar])))
const orderedVotes = computed(() => sortPlayers(creds().roomid, state.value?.votes || []))
const abstentions = computed(() => (state.value?.votes || []).filter(v => !v.target).length)
const knownCards = computed(() => {
  const { role, info = {} } = state.value?.night || {}
  if (role === 'werewolf' && info.peek) return [{ role: info.peek, label: '查验的中央牌' }]
  if (role === 'seer') return (info.peeked || []).map((card, i) => ({ role: card, label: info.center_picks ? `中央第 ${info.center_picks[i] + 1} 张` : `${info.target} 的初始身份` }))
  if (role === 'robber' && info.new_role) return [{ role: info.new_role, label: '交换当时获得' }]
  if (role === 'insomniac' && info.final_role) return [{ role: info.final_role, label: '你的最终身份' }]
  return []
})
const highestVotes = computed(() => voteTotals.value[0]?.count || 0)
const nightText = computed(() => {
  const night = state.value?.night
  const info = night?.info || {}
  const centerNumber = Number(String(info.target || '').split('_')[1]) + 1
  switch (night?.role) {
    case 'werewolf': return info.peek ? `你是独狼，查看了中央第 ${centerNumber} 张牌：${roleName(info.peek)}。` : `夜晚开始时，你的狼人同伴：${(info.teammates || []).join('、')}。`
    case 'minion': return info.teammates?.length ? `夜晚开始时，狼人玩家：${info.teammates.join('、')}。` : '夜晚开始时，场上没有狼人玩家。'
    case 'seer': return info.center_picks ? `你查看了${info.center_picks.map((i, k) => `中央第 ${i + 1} 张：${roleName(info.peeked[k])}`).join('；')}。` : `你查看了 ${info.target} 的初始身份：${roleName(info.peeked?.[0])}。`
    case 'robber': return `你与 ${info.target} 交换了身份，交换当时获得的是${roleName(info.new_role)}。`
    case 'troublemaker': return `你交换了 ${info.target} 与 ${info.target2} 的身份，没有查看牌面。`
    case 'drunk': return `你与中央第 ${centerNumber} 张牌交换了身份，没有查看新身份。`
    case 'insomniac': return `夜间行动结束后，你确认自己的最终身份是${roleName(info.final_role)}。`
    default: return '你没有夜间行动。'
  }
})
const done = computed(() => state.value?.shot_target !== null && state.value?.shot_target !== undefined)
async function shoot() {
  if (busy.value || done.value || !state.value?.can_shoot || !target.value) return
  err.value = ''
  confirmOpen.value = false
  busy.value = true
  const res = await post('hunter_shot', { ...creds(), target: target.value })
  busy.value = false
  if (!res.ok) { err.value = errorText(res.error); return }
  applyState(res)
}
</script>

<template>
  <div v-if="state" class="hunter-view">
    <section class="container hunter-hero">
      <span class="hunter-eyebrow">投票已结束 · 猎人行动</span>
      <template v-if="state.can_shoot">
        <RoleCard role="hunter" :roomid="creds().roomid" :userid="creds().userid" eager class="hunter-art" />
        <h1>你的最终身份是猎人</h1>
        <p class="hero-copy">你被投票处决了，现在必须开枪带走一名玩家。<br>这是你的最后一次行动。</p>
      </template>
      <template v-else>
        <div class="hunter-emblem" aria-hidden="true">⌖</div>
        <h1>等待猎人最后一枪</h1>
        <p class="hero-copy">投票已结束，被处决的猎人正在选择目标。<br>行动完成后，将揭晓所有身份与本局结果。</p>
      </template>
      <div class="execution-summary">
        <span>投票处决</span>
        <div class="execution-chips"><span v-for="uid in state.executed" :key="uid">{{ uid }}</span></div>
      </div>
    </section>

    <NightInfoPanel v-model:expanded="showNight" :role="state.night?.role" :description="nightText"
      :cards="knownCards" :roomid="creds().roomid" :userid="creds().userid" panel-id="shoot-night-info" />

    <section class="container hunter-information">
      <div class="action-heading"><h2>投票结果</h2><span>全部投票已锁定</span></div>
      <div class="vote-outcome">
        <div class="outcome-heading"><span>{{ state.executed.length > 1 ? '最高票平票 · 共同处决' : '最高票 · 投票处决' }}</span><strong>{{ highestVotes }}<small>票</small></strong></div>
        <div class="outcome-players"><span v-for="uid in state.executed" :key="uid"><img :src="avatarUrl(avatarByUser[uid])" alt="" />{{ uid }}</span></div>
      </div>
      <div class="vote-subheading"><h3>得票分布</h3><span>{{ state.votes?.length || 0 }} 人已投票 · {{ abstentions }} 人弃权</span></div>
      <div class="tally-list">
        <div v-for="row in voteTotals" :key="row.userid" class="tally-row" :class="{ leading: state.executed.includes(row.userid) }">
          <span class="tally-player"><img :src="avatarUrl(avatarByUser[row.userid])" alt="" /><span>{{ row.userid }}</span></span>
          <div class="tally-track"><span :style="{ width: `${highestVotes ? row.count / highestVotes * 100 : 0}%` }"></span></div>
          <strong>{{ row.count }} 票</strong>
          <small>{{ state.executed.includes(row.userid) ? '最高票' : '' }}</small>
        </div>
      </div>
      <h3 class="vote-detail-title">谁投了谁</h3>
      <div class="vote-records">
        <div v-for="vote in orderedVotes" :key="vote.userid" class="vote-record" :class="{ 'my-vote': vote.userid === creds().userid }">
          <span class="record-player"><img :src="avatarUrl(avatarByUser[vote.userid])" alt="" /><strong>{{ vote.userid }}</strong><small v-if="vote.userid === creds().userid">你</small></span>
          <span class="vote-arrow" aria-label="投票给">→</span>
          <span class="record-player record-target" :class="{ muted: !vote.target }"><img v-if="vote.target" :src="avatarUrl(avatarByUser[vote.target])" alt="" /><strong>{{ vote.target || '弃权' }}</strong></span>
        </div>
      </div>
    </section>

    <section v-if="state.can_shoot && !done" class="container hunter-action">
      <div class="action-heading"><h2>选择开枪目标</h2><span>必须选择一人</span></div>
      <p class="action-copy">被选中的玩家将加入处决名单。请根据讨论与线索作出选择。</p>
      <div class="shot-grid">
        <button v-for="u in users" :key="u.userid" type="button" class="shot-player"
          :class="{ selected: target === u.userid }" :aria-pressed="target === u.userid"
          :disabled="busy" @click="target = u.userid">
          <img :src="avatarUrl(u.avatar)" alt="" />
          <span class="player-copy"><strong>{{ u.userid }}</strong><span>{{ state.executed.includes(u.userid) ? '已被投票处决' : '可选择为目标' }}</span></span>
          <span class="pick-mark" aria-hidden="true">{{ target === u.userid ? '✓' : '○' }}</span>
        </button>
      </div>
      <div class="selection-summary" role="status" aria-live="polite">
        <span>{{ target === null ? '尚未选择' : '开枪目标' }}</span>
        <strong>{{ target === null ? '请选择一名玩家作为开枪目标' : target }}</strong>
      </div>
      <button type="button" class="btn-primary btn-block" :disabled="busy || target === null" @click="confirmOpen = true">
        {{ busy ? '提交中…' : target ? '确认开枪' : '请先选择' }}
      </button>
      <p class="action-footnote">提交后无法修改。枪击猎人不会触发再次开枪。</p>
    </section>

    <section v-else class="container hunter-wait" role="status" aria-live="polite">
      <span class="wait-mark" aria-hidden="true">{{ state.can_shoot ? '✓' : '☾' }}</span>
      <div>
        <h2>{{ state.can_shoot ? '你的行动已完成' : '等待猎人完成行动' }}</h2>
        <p v-if="state.can_shoot">你已开枪带走 {{ state.shot_target }}。等待其他猎人完成选择后，自动进入结算。</p>
        <p v-else>无需操作，行动完成后自动进入结算。</p>
      </div>
    </section>
    <p v-if="err || error" class="container error" role="alert">{{ err || errorText(error) }}</p>
    <ConfirmDialog v-if="confirmOpen" :confirm-disabled="busy" title="确认最后一枪"
      confirm-text="开枪"
      :message="`你将开枪带走 ${target}，将其加入处决名单。提交后无法修改。`"
      @confirm="shoot" @cancel="confirmOpen = false" />
  </div>
  <section v-else class="container hunter-wait" role="status"><p>{{ error ? errorText(error) : '正在加载投票结果…' }}</p></section>
</template>

<style scoped>
.hunter-information { padding: 22px; }
.vote-outcome { margin: 18px 0 20px; padding: 15px; border: 1px solid rgba(229, 189, 84, .25); border-radius: 12px; background: linear-gradient(135deg, rgba(229, 189, 84, .08), transparent); }
.outcome-heading { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.outcome-heading > span { color: var(--accent-hover); font-size: .72rem; }
.outcome-heading > strong { color: var(--accent-hover); font-size: 1.4rem; font-variant-numeric: tabular-nums; }
.outcome-heading small { margin-left: 5px; color: var(--text-dim); font-size: .65rem; font-weight: 400; }
.outcome-players { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
.outcome-players > span { display: flex; align-items: center; gap: 7px; padding: 6px 9px 6px 6px; border-radius: 8px; background: var(--surface-2); font-size: .8rem; font-weight: 600; }
.outcome-players img { width: 26px; height: 26px; border-radius: 50%; }
.vote-subheading { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 14px; }
.vote-subheading h3 { margin: 0; font-size: .8rem; }
.vote-subheading > span { color: var(--text-faint); font-size: .65rem; }
.tally-list { display: grid; gap: 13px; }
.tally-row { display: grid; grid-template-columns: minmax(90px, 1fr) minmax(45px, 1fr) 3.5ch 3ch; align-items: center; gap: 8px; font-size: .75rem; }
.tally-player { display: flex; align-items: center; gap: 7px; min-width: 0; }
.tally-player img { width: 25px; height: 25px; border-radius: 50%; flex-shrink: 0; }
.tally-player > span { overflow-wrap: anywhere; }
.tally-row strong { white-space: nowrap; font-size: .7rem; }
.tally-row small { color: var(--accent); font-size: .6rem; }
.tally-track { height: 7px; border-radius: 8px; background: var(--surface-2); overflow: hidden; }
.tally-track span { display: block; height: 100%; border-radius: inherit; background: var(--text-faint); }
.leading .tally-track span { background: var(--accent); }
.vote-detail-title { margin: 22px 0 12px; padding-top: 18px; border-top: 1px solid var(--border); font-size: .8rem; }
.vote-records { display: grid; gap: 7px; }
.vote-record { display: grid; grid-template-columns: minmax(0, 1fr) 24px minmax(0, 1fr); align-items: center; gap: 10px; padding: 10px 12px; border: 1px solid transparent; border-radius: 10px; background: var(--surface-2); font-size: .75rem; }
.my-vote { border-color: rgba(229, 189, 84, .2); }
.record-player { display: flex; align-items: center; gap: 8px; min-width: 0; }
.record-player img { width: 26px; height: 26px; border-radius: 50%; flex-shrink: 0; }
.record-player strong { overflow-wrap: anywhere; font-weight: 500; }
.record-player small { color: var(--accent); font-size: .6rem; }
.record-target { justify-content: flex-end; }
.record-target.muted strong, .vote-arrow { color: var(--text-faint); }
.vote-arrow { text-align: center; }

.hunter-hero { padding: 22px; text-align: center; border-color: rgba(229, 189, 84, .28); background: radial-gradient(ellipse at top, rgba(229, 189, 84, .09), transparent 65%), var(--surface); }
.hunter-eyebrow { color: var(--accent); font-size: .7rem; letter-spacing: .1em; }
.hunter-art { margin: 18px 0 22px; box-shadow: var(--shadow-sm); }
.hunter-hero h1 { margin: 0; font-size: clamp(1.25rem, 5.5vw, 1.6rem); letter-spacing: .03em; }
.hero-copy { margin: 12px 0 20px; color: var(--text-dim); font-size: .8rem; line-height: 1.9; }
.hunter-emblem { display: grid; place-items: center; width: 66px; height: 66px; margin: 22px auto; border: 1px solid rgba(229, 189, 84, .35); border-radius: 50%; color: var(--accent); background: rgba(229, 189, 84, .06); font-size: 2.4rem; }
.execution-summary { display: flex; align-items: center; justify-content: space-between; gap: 14px; padding-top: 16px; border-top: 1px solid var(--border); text-align: left; }
.execution-summary > span { color: var(--text-dim); font-size: .72rem; white-space: nowrap; }
.execution-chips { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 6px; }
.execution-chips span { padding: 5px 9px; border: 1px solid var(--border-strong); border-radius: 6px; background: var(--surface-2); font-size: .75rem; overflow-wrap: anywhere; }
.hunter-action { padding: 22px; }
.action-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.action-heading h2, .hunter-wait h2 { margin: 0; font-size: 1rem; }
.action-heading > span { color: var(--text-faint); font-size: .7rem; }
.action-copy { margin: 10px 0 18px; color: var(--text-dim); font-size: .78rem; line-height: 1.8; }
.shot-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 9px; }
.shot-player { position: relative; display: flex; align-items: center; gap: 8px; min-width: 0; margin: 0; padding: 16px 10px; border: 1px solid var(--border); border-radius: 12px; background: var(--surface-2); text-align: left; }
.shot-player img { width: 36px; height: 36px; flex-shrink: 0; border-radius: 50%; object-fit: cover; }
.player-copy { display: flex; flex-direction: column; gap: 5px; min-width: 0; }
.player-copy strong { font-size: .8rem; overflow-wrap: anywhere; }
.player-copy > span { color: var(--text-faint); font-size: .6rem; }
.pick-mark { color: var(--text-faint); font-size: .8rem; }
.shot-player .pick-mark { position: absolute; top: 4px; right: 6px; }
.selected { border-color: var(--accent); background: rgba(229, 189, 84, .09); }
.selected .pick-mark, .selected strong { color: var(--accent-hover); }
.selection-summary { margin: 20px 0 16px; padding-top: 16px; border-top: 1px solid var(--border); }
.selection-summary > span { display: block; color: var(--text-faint); font-size: .68rem; margin-bottom: 6px; }
.selection-summary strong { font-size: .85rem; overflow-wrap: anywhere; }
.action-footnote { margin: 12px 0 0; color: var(--text-faint); font-size: .68rem; line-height: 1.8; text-align: center; }
.hunter-wait { display: flex; align-items: flex-start; gap: 14px; padding: 22px; }
.wait-mark { display: grid; place-items: center; width: 38px; height: 38px; flex-shrink: 0; border: 1px solid rgba(229, 189, 84, .25); border-radius: 50%; color: var(--accent); background: rgba(229, 189, 84, .06); }
.hunter-wait p { margin: 9px 0 0; color: var(--text-dim); font-size: .78rem; line-height: 1.8; }
button:focus-visible { outline: 2px solid var(--accent-hover); outline-offset: 3px; }
@media (max-width: 360px) { .hunter-hero, .hunter-action, .hunter-wait, .hunter-information { padding: 18px 14px; } .shot-player { padding: 16px 8px; gap: 6px; } .shot-player img { width: 30px; height: 30px; } .player-copy strong { font-size: .74rem; } .player-copy > span { font-size: .56rem; } }
</style>
