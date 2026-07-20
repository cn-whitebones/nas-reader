<template>
  <div class="pdf-reader" :class="{ fit: scale === null }" ref="container">
    <canvas ref="canvas"></canvas>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
// pdf.js
import * as pdfjsLib from 'pdfjs-dist'
import PdfWorker from 'pdfjs-dist/build/pdf.worker.min.mjs?url'

pdfjsLib.GlobalWorkerOptions.workerSrc = PdfWorker

const props = defineProps<{ fileUrl: string; initialPage?: number }>()
const emit = defineEmits<{
  pageChange: [page: number, total: number]
  // fit=true 表示当前为整页适配态(可点击翻页);false 表示已放大(自由滚动查看)
  zoomChange: [fit: boolean]
}>()

const container = ref<HTMLElement>()
const canvas = ref<HTMLCanvasElement>()
const pageNum = ref(props.initialPage || 1)
const totalPages = ref(0)
// scale=null 表示自动适配整页到视口(点击翻页体验需要单页可见,不产生滚动);
// 用户主动放大/缩小后变为具体数值,进入手动缩放模式
const scale = ref<number | null>(null)
let pdfDoc: any = null

async function load() {
  const token = localStorage.getItem('access_token') || ''
  const loadingTask = pdfjsLib.getDocument({
    url: props.fileUrl,
    httpHeaders: { Authorization: `Bearer ${token}` },
  })
  pdfDoc = await loadingTask.promise
  totalPages.value = pdfDoc.numPages
  await render()
}

// 计算"整页可见"的缩放比:取宽/高两个方向能容纳的较小者
function fitScale(page: any): number {
  const base = page.getViewport({ scale: 1 })
  const el = container.value
  if (!el) return 1.2
  const availW = Math.max(el.clientWidth - 24, 100)
  const availH = Math.max(el.clientHeight - 24, 100)
  return Math.min(availW / base.width, availH / base.height)
}

async function render() {
  if (!pdfDoc || !canvas.value) return
  const page = await pdfDoc.getPage(pageNum.value)
  const s = scale.value ?? fitScale(page)
  const viewport = page.getViewport({ scale: s })
  const ctx = canvas.value.getContext('2d')!
  canvas.value.width = viewport.width
  canvas.value.height = viewport.height
  await page.render({ canvasContext: ctx, viewport }).promise
  emit('pageChange', pageNum.value, totalPages.value)
  emit('zoomChange', scale.value === null)
}

function go(n: number) {
  if (n < 1 || n > totalPages.value) return
  pageNum.value = n
  // 翻页时回到整页适配态,避免停留在上一页的放大区域
  scale.value = null
  if (container.value) container.value.scrollTop = 0
  render()
}
function next() { go(pageNum.value + 1) }
function prev() { go(pageNum.value - 1) }

// delta>0 放大,delta<0 缩小;delta=0 复位到整页适配
async function zoom(delta: number) {
  if (delta === 0) {
    scale.value = null
    render()
    return
  }
  // 从自动适配切到手动模式时,先取当前适配比作为基准
  if (scale.value == null && pdfDoc) {
    const page = await pdfDoc.getPage(pageNum.value)
    scale.value = fitScale(page)
  }
  const next = Math.min(Math.max((scale.value ?? 1.2) + delta, 0.5), 4)
  // 缩小回到适配比附近时自动回落到 fit 态,便于恢复点击翻页
  if (pdfDoc) {
    const page = await pdfDoc.getPage(pageNum.value)
    if (next <= fitScale(page) + 0.01) {
      scale.value = null
      render()
      return
    }
  }
  scale.value = next
  render()
}

watch(() => props.initialPage, (p) => { if (p) { pageNum.value = p; render() } })
onMounted(load)
defineExpose({ go, next, prev, zoom })
</script>

<style scoped>
.pdf-reader { height: 100%; background: #525659; box-sizing: border-box; overflow: auto; -webkit-overflow-scrolling: touch; }
/* 整页适配态:居中显示,不滚动 */
.pdf-reader.fit { display: flex; align-items: center; justify-content: center; padding: 12px; overflow: hidden; }
canvas { display: block; margin: auto; box-shadow: 0 2px 12px rgba(0, 0, 0, 0.4); }
.pdf-reader.fit canvas { max-width: 100%; max-height: 100%; }
</style>
