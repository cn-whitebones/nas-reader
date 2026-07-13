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
const scale = ref(1.2)
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

async function render() {
  if (!pdfDoc || !canvas.value) return
  const page = await pdfDoc.getPage(pageNum.value)
  const viewport = page.getViewport({ scale: scale.value })
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
function zoom(delta: number) {
  scale.value = Math.min(Math.max(scale.value + delta, 0.5), 3)
  render()
}

watch(() => props.initialPage, (p) => { if (p) { pageNum.value = p; render() } })
onMounted(load)
defineExpose({ go })
</script>

<style scoped>
.pdf-reader { display: flex; flex-direction: column; align-items: center; padding: 16px; background: #525659; min-height: 100%; }
canvas { max-width: 100%; box-shadow: 0 2px 12px rgba(0, 0, 0, 0.4); }
.pdf-nav { position: sticky; bottom: 0; display: flex; gap: 8px; align-items: center; padding: 10px; background: rgba(0,0,0,0.6); color: #fff; border-radius: 8px; margin-top: 12px; }
</style>
