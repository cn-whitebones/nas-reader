<template>
  <div class="gen-cover" :class="{ compact }" :style="bgStyle">
    <div v-if="compact" class="gc-initial">{{ initial }}</div>
    <template v-else>
      <div class="gc-title" :class="{ small: longTitle }">{{ title }}</div>
      <span class="gc-format">{{ format.toUpperCase() }}</span>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  title: string
  format: string
  compact?: boolean
}>()

// 标题较长时缩小字号(竖排换列后仍尽量可读)
const longTitle = computed(() => props.title.length > 8)

// compact(列表小图)模式:取首个有意义字符
const initial = computed(() => {
  const t = (props.title || '').trim().replace(/^[《「【\[(（]+/, '')
  return t ? t[0] : '?'
})

// 用标题生成稳定的柔和背景色:同名书封面一致,不同书有区分度
const bgStyle = computed(() => {
  let hash = 0
  for (let i = 0; i < props.title.length; i++) {
    hash = (hash * 31 + props.title.charCodeAt(i)) & 0xffffffff
  }
  const hue = Math.abs(hash) % 360
  // 低饱和、较亮的双色渐变,配深色文字,保证雅致且文字清晰
  const c1 = `hsl(${hue}, 42%, 62%)`
  const c2 = `hsl(${(hue + 28) % 360}, 46%, 48%)`
  return { background: `linear-gradient(145deg, ${c1}, ${c2})` }
})
</script>

<style scoped>
.gen-cover {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: flex-start;
  justify-content: flex-end;
  padding: 10% 8%;
  box-sizing: border-box;
  overflow: hidden;
}
/* 竖排书名:右起竖排,符合中文书脊阅读习惯;超出高度自动换到左侧新列 */
.gc-title {
  writing-mode: vertical-rl;
  text-orientation: upright;
  max-height: 100%;
  font-weight: 700;
  font-size: clamp(13px, 15%, 22px);
  line-height: 1.25;
  letter-spacing: 0.08em;
  color: #fff;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.28);
  overflow: hidden;
  /* 允许多列:换列由 max-height 触发自然折行 */
  white-space: normal;
  word-break: break-all;
}
.gc-title.small {
  font-size: clamp(11px, 12%, 18px);
  letter-spacing: 0.04em;
}
.gc-format {
  position: absolute;
  left: 6px;
  bottom: 6px;
  font-size: 10px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.82);
  letter-spacing: 0.05em;
}
/* compact:列表视图小图,只显示首字,居中 */
.gen-cover.compact {
  align-items: center;
  justify-content: center;
  padding: 0;
}
.gc-initial {
  font-size: clamp(18px, 42%, 30px);
  font-weight: 700;
  color: #fff;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.28);
}
</style>
