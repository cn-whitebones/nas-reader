<template>
  <img v-if="src" :src="src" :alt="alt" loading="lazy" />
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import http from '@/api/http'

const props = defineProps<{
  bookId: string
  alt?: string
  // 封面版本(如 metadata.scraped_at):变化时强制重载,避免文件名不变导致缓存旧封面
  version?: string | null
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
    const params = props.version ? { v: props.version } : undefined
    const res = await http.get(`/books/${props.bookId}/cover`, { responseType: 'blob', params })
    objectUrl = URL.createObjectURL(res.data)
    src.value = objectUrl
  } catch {
    // 加载失败保持空,由父组件的 fallback 处理
  }
}

onMounted(load)
onBeforeUnmount(revoke)
watch(() => [props.bookId, props.version], load)
</script>
