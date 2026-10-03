<script setup>
import { computed, ref } from 'vue'
import { useRoomState } from '../useRoomState'
import { creds } from '../store'
import { post } from '../api'
import { errorText } from '../gameConfig'
import { avatarUrl } from '../avatar'
import { sortPlayers } from '../playerOrder'
import ConfirmDialog from '../components/ConfirmDialog.vue'

const { state, error, applyState } = useRoomState()
const target = ref('')
const busy = ref(false)
const err = ref('')
const confirmOpen = ref(false)
const users = computed(() => sortPlayers(creds().roomid, (state.value?.users || []).filter(p => p.userid !== creds().userid)))
const done = computed(() => state.value?.shot_target !== null && state.value?.shot_target !== undefined)
async function shoot() {
  if (busy.value || done.value || !state.value?.can_shoot) return
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
  <section v-if="state" class="container">
    <h1>猎人开枪</h1>
    <p>投票处决：{{ state.executed.join('、') }}</p>
    <p class="muted">被投票处决的最终猎人可开枪带走一人。枪击猎人不会触发再次开枪。</p>
    <template v-if="state.can_shoot && !done">
      <h2>选择开枪目标</h2>
      <div class="shot-grid">
        <button v-for="u in users" :key="u.userid" :class="{ selected: target === u.userid }"
          :aria-pressed="target === u.userid" :disabled="busy" @click="target = u.userid">
          <img :src="avatarUrl(u.avatar)" alt="" />{{ u.userid }}
        </button>
      </div>
      <button :class="{ selected: target === '' }" :aria-pressed="target === ''" :disabled="busy" @click="target = ''">放弃开枪</button>
      <p>{{ target ? `将开枪带走 ${target}` : '选择放弃开枪' }}</p>
      <button class="btn-primary btn-block" :disabled="busy" @click="confirmOpen = true">{{ busy ? '提交中…' : '确认选择' }}</button>
    </template>
    <p v-else-if="state.can_shoot">{{ state.shot_target ? `已开枪：${state.shot_target}` : '已放弃开枪' }}。等待其他猎人完成选择。</p>
    <p v-else>等待被投票处决的猎人完成开枪选择。</p>
    <p v-if="err || error" class="error">{{ err || errorText(error) }}</p>
    <ConfirmDialog v-if="confirmOpen" :confirm-disabled="busy" title="确认猎人行动" :message="target ? `开枪带走 ${target}？提交后不能修改。` : '确认放弃开枪？提交后不能修改。'" @confirm="shoot" @cancel="confirmOpen = false" />
  </section>
</template>

<style scoped>
.shot-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.shot-grid button { display: flex; align-items: center; gap: 10px; }
.shot-grid img { width: 40px; height: 40px; border-radius: 50%; }
.selected { border-color: var(--accent); background: rgba(229, 189, 84, .1); }
p { line-height: 1.75; }
</style>
