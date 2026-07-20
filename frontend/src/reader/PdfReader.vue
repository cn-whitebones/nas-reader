<template>
  <div class="pdf-reader" ref="container">
    <canvas ref="canvas"></canvas>
    <div class="pdf-nav">
      <el-button size="small" :disabled="pageNum <= 1" @click="go(pageNum - 1)">上一页</el-button>
      <span>{{ pageNum }} / {{ totalPages }}</span>
      <el-button size="small" :disabled="pageNum >= totalPages" @click="go(pageNum + 1)">下一页</el-button>
      <el-button size="small" @click="zoom(0.2)">放大</el-button>
      <el-button size="small" @click="zoom(-0.2)">缩小</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
// pdf.js
import * as pdfjsLib from 'pdfjs-dist'
import PdfWorker from 'pdfjs-dist/build/pdf.worker.min.mjs?url'

pdfjsLib.GlobalWorkerOptions.workerSrc = PdfWorker

const props = defineProps<{ fileUrl: string; initialPage?: number }>()
const emit = defineEmits<{ pageChange: [page: number, total: number] }>()

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
}

function go(n: number) {
  if (n < 1 || n > totalPages.value) return
  pageNum.value = n
  render()
}
function next() { go(pageNum.value + 1) }
function prev() { go(pageNum.value - 1) }
async function zoom(delta: number) {
  // 从自动适配切到手动模式时,先取当前适配比作为基准
  if (scale.value == null && pdfDoc) {
    const page = await pdfDoc.getPage(pageNum.value)
    scale.value = fitScale(page)
  }
  scale.value = Math.min(Math.max((scale.value ?? 1.2) + delta, 0.5), 3)
  render()
}

watch(() => props.initialPage, (p) => { if (p) { pageNum.value = p; render() } })
onMounted(load)
defineExpose({ go, next, prev })
</script>

<style scoped>
.pdf-reader { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; padding: 12px; background: #525659; box-sizing: border-box; overflow: hidden; }
canvas { max-width: 100%; max-height: 100%; box-shadow: 0 2px 12px rgba(0, 0, 0, 0.4); }
/* 缩放/翻页条:固定在底部并置于点击翻页层(z-index:10)之上,保证可点击 */
.pdf-nav { position: fixed; left: 50%; transform: translateX(-50%); bottom: calc(12px + env(safe-area-inset-bottom)); z-index: 30; display: flex; gap: 8px; align-items: center; padding: 10px; background: rgba(0,0,0,0.6); color: #fff; border-radius: 8px; }
</style>
