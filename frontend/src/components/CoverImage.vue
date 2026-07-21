<template>
  <!-- blurFill:网格卡片用「边缘取色纯色填充 + 完整前景」,消除留白且不裁切封面 -->
  <div v-if="blurFill && src" class="cover-fill" :style="{ background: bgColor }">
    <img class="fg" :src="src" :alt="alt" loading="lazy" />
  </div>
  <!-- 默认:单图(列表小缩略图等),行为与原先一致 -->
  <img v-else-if="src" :src="src" :alt="alt" loading="lazy" />
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import http from '@/api/http'

const props = defineProps<{
  bookId: string
  alt?: string
  // 封面版本(如 metadata.scraped_at):变化时强制重载,避免文件名不变导致缓存旧封面
  version?: string | null
  // 边缘取色填充:取封面四周边缘平均色做背景,原比例前景居中,消除留白
  blurFill?: boolean
}>()

const src = ref('')
// 填充背景色:默认主题填充色,取到边缘色后替换
const bgColor = ref('var(--el-fill-color-light)')
let objectUrl: string | null = null

function revoke() {
  if (objectUrl) {
    URL.revokeObjectURL(objectUrl)
    objectUrl = null
  }
}

// 用小 canvas 采样封面四周边缘的平均色(同源 blob,不会污染画布)
function computeEdgeColor(url: string) {
  const img = new Image()
  img.onload = () => {
    try {
      const w = 24
      const h = 32
      const canvas = document.createElement('canvas')
      canvas.width = w
      canvas.height = h
      const ctx = canvas.getContext('2d')
      if (!ctx) return
      ctx.drawImage(img, 0, 0, w, h)
      const data = ctx.getImageData(0, 0, w, h).data
      let r = 0
      let g = 0
      let b = 0
      let n = 0
      const add = (x: number, y: number) => {
        const i = (y * w + x) * 4
        r += data[i]
        g += data[i + 1]
        b += data[i + 2]
        n++
      }
      // 遍历上下两行、左右两列
      for (let x = 0; x < w; x++) {
        add(x, 0)
        add(x, h - 1)
      }
      for (let y = 0; y < h; y++) {
        add(0, y)
        add(w - 1, y)
      }
      if (n > 0) bgColor.value = `rgb(${Math.round(r / n)}, ${Math.round(g / n)}, ${Math.round(b / n)})`
    } catch {
      // 跨域或读取失败:保持默认背景色
    }
  }
  img.src = url
}

async function load() {
  revoke()
  src.value = ''
  bgColor.value = 'var(--el-fill-color-light)'
  try {
    const params = props.version ? { v: props.version } : undefined
    const res = await http.get(`/books/${props.bookId}/cover`, { responseType: 'blob', params })
    objectUrl = URL.createObjectURL(res.data)
    src.value = objectUrl
    if (props.blurFill) computeEdgeColor(objectUrl)
  } catch {
    // 加载失败保持空,由父组件的 fallback 处理
  }
}

onMounted(load)
onBeforeUnmount(revoke)
watch(() => [props.bookId, props.version], load)
</script>

<style scoped>
.cover-fill {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
}
/* 前景层:完整封面居中,不裁切、不丢书名;不设 z-index,避免遮挡卡片角标 */
.cover-fill .fg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
}
</style>
