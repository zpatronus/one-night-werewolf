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
  show.value = true
}
function closePicker() {
  show.value = false
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
      v-if="show"
      ref="dialogEl"
      open
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
.avatar-dialog { width: 420px; }
</style>