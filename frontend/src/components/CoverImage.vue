<template>
  <img v-if="src" :src="src" :alt="alt" loading="lazy" />
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import http from '@/api/http'

const props = defineProps<{
  bookId: string
  alt?: string
}>()

const src = ref('')
let objectUrl: string | null = null

function revoke() {
  if (objectUrl) {
    URL.revokeObjectURL(objectUrl)
    objectUrl = null
  }
}

async function load() {
  revoke()
  src.value = ''
  try {
    const res = await http.get(`/books/${props.bookId}/cover`, { responseType: 'blob' })
    objectUrl = URL.createObjectURL(res.data)
    src.value = objectUrl
  } catch {
    // 加载失败保持空,由父组件的 fallback 处理
  }
}

onMounted(load)
onBeforeUnmount(revoke)
watch(() => props.bookId, load)
</script>
