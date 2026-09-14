<script setup>
defineProps({
  title: { type: String, default: '确认？' },
  message: { type: String, default: '' },
  confirmText: { type: String, default: '确认' },
  cancelText: { type: String, default: '取消' },
  confirmDisabled: { type: Boolean, default: false },
})
const emit = defineEmits(['confirm', 'cancel'])
</script>

<template>
  <div class="modal-backdrop" @click.self="emit('cancel')">
    <div class="modal" role="dialog" aria-modal="true" :aria-labelledby="title">
      <h2 class="modal-title">{{ title }}</h2>
      <div class="modal-body"><slot>{{ message }}</slot></div>
      <div class="modal-actions">
        <button type="button" @click="emit('cancel')">{{ cancelText }}</button>
        <button type="button" class="btn-primary modal-confirm" :disabled="confirmDisabled" @click="emit('confirm')">
          {{ confirmText }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background: rgba(0, 0, 0, 0.55);
}
.modal {
  width: min(380px, 92vw);
  padding: 22px 24px;
  border-radius: 16px;
  background: var(--bg-1, #10151d);
  border: 1px solid rgba(229, 189, 84, 0.25);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5);
}
.modal-title {
  margin: 0;
  font-size: 1.2rem;
  text-align: center;
  color: var(--text);
}
.modal-body {
  margin: 16px 0 22px;
  color: var(--text-dim);
  text-align: center;
  line-height: 1.6;
}
.modal-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 10px;
}
</style>