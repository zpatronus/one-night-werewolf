<script setup>
import { computed, ref, watch } from 'vue'
import { roleName } from '../gameConfig'
import { cachedImage, cacheImage, forgetImage } from '../imageCache'

const props = defineProps({ role: String, eager: Boolean })
const images = import.meta.glob('../assets/roles/*.webp', { eager: true, import: 'default' })
const filename = computed(() => `${props.role}.webp`)
const bundledSrc = computed(() => images[`../assets/roles/${filename.value}`])
const src = ref('')
watch(bundledSrc, url => {
  src.value = url ? cachedImage(filename.value, url) || url : ''
}, { immediate: true, flush: 'sync' })

function remember() {
  if (src.value === bundledSrc.value) cacheImage(filename.value, bundledSrc.value)
}
function recover() {
  if (src.value && src.value !== bundledSrc.value) {
    forgetImage(filename.value)
    src.value = bundledSrc.value
  }
}
</script>

<template>
  <img v-if="src" class="role-art" :src="src" :alt="roleName(role)" width="768" height="512"
    :loading="eager ? 'eager' : 'lazy'" decoding="async" @load="remember" @error="recover" />
  <span v-else class="role-art-fallback">{{ roleName(role) || '未知身份' }}</span>
</template>

<style scoped>
.role-art { display: block; width: 100%; height: auto; aspect-ratio: 3 / 2; object-fit: contain; border-radius: 7px; }
.role-art-fallback { display: block; padding: 12px; color: var(--text-dim); }
</style>
