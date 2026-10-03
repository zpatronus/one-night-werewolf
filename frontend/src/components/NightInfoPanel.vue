<script setup>
import { roleName } from '../gameConfig'
import RoleCard from './RoleCard.vue'

defineProps({
  role: String,
  description: String,
  cards: { type: Array, default: () => [] },
  roomid: String,
  userid: String,
  expanded: Boolean,
  panelId: { type: String, default: 'private-information' },
})
const emit = defineEmits(['update:expanded'])
</script>

<template>
    <section class="container discussion-private">
      <div class="section-heading">
        <div><span class="night-label">仅自己可见</span><h2>我的夜间信息</h2></div>
        <button type="button" class="toggle-role" :aria-expanded="expanded" :aria-controls="panelId" @click="emit('update:expanded', !expanded)">
          {{ expanded ? '隐藏信息' : '查看信息' }}
        </button>
      </div>
      <div v-if="expanded" :id="panelId">
        <div class="night-identity">
          <RoleCard :roomid="roomid" :userid="userid" :role="role" eager class="night-role-art" />
          <div><span class="night-label">你的初始身份</span><h2>{{ roleName(role) }}</h2></div>
        </div>
        <div class="night-observation">
          <p>{{ description }}</p>
          <div v-if="cards.length" class="revealed-cards">
          <figure v-for="(card, index) in cards" :key="index">
            <figcaption>{{ card.label }}</figcaption>
            <RoleCard :roomid="roomid" :userid="userid" :role="card.role" eager />
          </figure>
        </div>
        </div>
      </div>
      <p v-else class="private-hidden">信息已收起，需要时可随时回看。</p>
    </section>

</template>

<style scoped>

.discussion-private { padding: 22px; }
.section-heading { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.section-heading h2 { margin: 5px 0 0; font-size: 1.1rem; }
.toggle-role { flex-shrink: 0; margin: 0; padding: 8px 12px; border-radius: 999px; color: var(--accent); border-color: rgba(229, 189, 84, .25); background: rgba(229, 189, 84, .06); font-size: .75rem; }
.night-label { display: block; color: var(--text-dim); font-size: .72rem; letter-spacing: .06em; }
.night-identity { display: flex; flex-direction: column; align-items: stretch; margin: 20px 0 16px; gap: 12px; }
.night-role-art { width: 100%; }
.night-identity h2 { margin: 5px 0 0; font-size: 1.1rem; }
.night-observation { padding: 18px; border: 1px solid var(--border); border-left: 2px solid var(--accent); border-radius: 4px 12px 12px 4px; background: rgba(5, 12, 23, .35); }
.night-observation p { margin: 0; font-size: .9rem; line-height: 1.85; overflow-wrap: anywhere; }
.revealed-cards { display: grid; grid-template-columns: minmax(0, 1fr); gap: 12px; margin-top: 16px; }
.revealed-cards figure { min-width: 0; margin: 0; }
.revealed-cards figcaption { margin-bottom: 8px; font-size: .75rem; line-height: 1.6; color: var(--accent-hover); overflow-wrap: anywhere; }
.private-hidden { margin: 16px 0 0; color: var(--text-dim); font-size: .8rem; }
.toggle-role:focus-visible { outline: 2px solid var(--accent-hover); outline-offset: 3px; }
@media (max-width: 360px) { .discussion-private { padding: 18px 14px; } .night-observation { padding: 14px; } }
</style>
