<script setup>
import { AVATARS, avatarUrl } from '../avatar'

defineProps({ modelValue: String })
defineEmits(['update:modelValue'])
</script>

<template>
  <div class="avatar-picker">
    <img
      v-for="name in AVATARS"
      :key="name"
      :src="avatarUrl(name)"
      :class="{ selected: name === modelValue }"
      :title="name"
      @click="$emit('update:modelValue', name)"
    />
  </div>
</template>