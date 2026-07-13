<template>
  <div class="html-reader" :class="`theme-${s.theme}`" :style="pageStyle">
    <div class="content" :style="contentStyle" v-html="html"></div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useReaderStore } from '@/stores/reader'

defineProps<{ html: string }>()
const store = useReaderStore()
const s = computed(() => store.settings)

// 页面容器主题背景
const pageStyle = computed(() => ({
  padding: `24px ${s.value.margin}px`,
}))
// 文本排版:字体/字号/行距生效
const contentStyle = computed(() => ({
  fontFamily: s.value.font_family,
  fontSize: `${s.value.font_size}px`,
  lineHeight: String(s.value.line_height),
  maxWidth: '760px',
  margin: '0 auto',
}))
</script>

<style scoped>
.html-reader { min-height: 100%; box-sizing: border-box; transition: background 0.2s; }
.theme-light { background: #ffffff; color: #2c2c2c; }
.theme-sepia { background: #f5ecd9; color: #5b4636; }
.theme-dark { background: #1a1a1a; color: #c8c8c8; }
.content :deep(p) { margin: 0 0 1em; text-indent: 2em; }
.content :deep(img) { max-width: 100%; height: auto; }
.content :deep(h1),
.content :deep(h2),
.content :deep(h3) { text-indent: 0; }
</style>
