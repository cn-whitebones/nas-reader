<template>
  <img v-if="src" :src="src" class="cand-cover" alt="封面" />
  <div v-else class="cand-cover cand-cover-empty">
    <span v-if="loading">…</span>
    <span v-else>无图</span>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import http from '@/api/http'
import { globalComicBlobCache } from '@/utils/blobCache'

// 候选封面走后端代理加载:豆瓣图床有 Referer 防盗链,浏览器直接 <img src>
// 会 403,故用带 JWT 的 blob 请求经后端代理拉取(见 /scrape/cover-proxy)。
const props = defineProps<{ url?: string | null }>()

const src = ref('')
const loading = ref(false)
const cacheKey = () => `cover-${btoa(props.url || '')}`

async function load() {
  // revoke old if any
  if (props.url) {
    globalComicBlobCache.delete(cacheKey())
  }
  src.value = ''
  if (!props.url) return
  loading.value = true
  try {
    const res = await http.get('/scrape/cover-proxy', {
      params: { url: props.url },
      responseType: 'blob',
    })
    src.value = globalComicBlobCache.getOrCreate(res.data, cacheKey())
  } catch {
    // 加载失败保持空,显示"无图"占位
  } finally {
    loading.value = false
  }
}

onMounted(load)
onBeforeUnmount(() => {
  if (props.url) {
    globalComicBlobCache.delete(cacheKey())
  }
})
watch(() => props.url, load)
</script>

<style scoped>
.cand-cover {
  width: 60px;
  height: 84px;
  object-fit: cover;
  border-radius: 4px;
  flex-shrink: 0;
}
.cand-cover-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f2f5;
  color: #c0c4cc;
  font-size: 12px;
}
</style>
