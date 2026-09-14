<script setup>
import { computed, ref } from 'vue'
import { avatarUrl, getMyAvatar, setMyAvatar, AVATARS, randomAvatar } from '../avatar'

const props = defineProps({ modelValue: String })
const emit = defineEmits(['update:modelValue'])
const dialogEl = ref(null)
const show = ref(false)

const value = computed({
  get: () => props.modelValue || getMyAvatar(),
  set: (v) => emit('update:modelValue', setMyAvatar(v)),
})

function openPicker() {
  if (show.value) return
  show.value = true
  // Native <dialog> modal — floats above the page in the top layer, centered,
  // with a dimming backdrop. (Bare `open` instead renders it inline in flow.)
  requestAnimationFrame(() => dialogEl.value?.showModal())
}
function closePicker() {
  if (!show.value) return
  show.value = false
  dialogEl.value?.close()
}
function chooseAvatar(file) {
  value.value = file
  closePicker()
}
function randomize() {
  value.value = randomAvatar()
}
function dismissBackdrop(event) {
  const dialog = dialogEl.value
  if (event.target !== dialog) return
  const b = dialog.getBoundingClientRect()
  if (event.clientX < b.left || event.clientX > b.right ||
      event.clientY < b.top || event.clientY > b.bottom) {
    closePicker()
  }
}
</script>

<template>
  <div>
    <div class="subtitle avatar-title">选择头像</div>
    <div class="avatar-picker-row">
      <button type="button" class="avatar-preview-wrap" title="点击选择头像" @click="openPicker">
        <img class="avatar-preview" :src="avatarUrl(value)" alt="avatar" />
      </button>
      <button type="button" @click="randomize">随机头像</button>
    </div>
    <dialog
      ref="dialogEl"
      class="avatar-dialog"
      aria-labelledby="avatar-dialog-title"
      @click="dismissBackdrop"
    >
      <div class="avatar-dialog-header">
        <h2 id="avatar-dialog-title">选择头像</h2>
        <button type="button" aria-label="关闭" @click="closePicker">×</button>
      </div>
      <div class="avatar-grid">
        <button
          v-for="file in AVATARS"
          :key="file"
          type="button"
          class="avatar-thumb"
          :class="{ 'avatar-selected': file === value }"
          :aria-pressed="file === value"
          :aria-label="file.replace(/-/g, ' ')"
          :title="file"
          @click="chooseAvatar(file)"
        >
          <img :src="avatarUrl(file)" alt="" />
        </button>
      </div>
    </dialog>
  </div>
</template>

<style scoped>
.avatar-title { margin-top: 14px; }
</style>

<style>
/* Modal look for the floating avatar picker. `::backdrop` cannot be scoped,
   and the native <dialog> sits in the browser's top layer, so these live here. */
.avatar-dialog {
  width: 420px;
  max-width: calc(100vw - 32px);
  padding: 18px;
  border-radius: 12px;
  border: 1px solid var(--border);
  background: #1a2029;           /* solid, opaque — keeps avatars easy to see */
  color: var(--text);
  margin: auto;
}
.avatar-dialog::backdrop {
  background: rgba(0, 0, 0, 0.6);
}
</style>