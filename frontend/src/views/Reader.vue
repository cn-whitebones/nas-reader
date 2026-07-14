<template>
  <div class="reader-page" :class="[`theme-${settings.theme}`, { 'chrome-hidden': !showChrome }]">
    <!-- 顶栏:绝对定位浮在内容之上,不影响布局,隐藏时文字撑满全屏 -->
    <div class="topbar">
      <el-button link @click="router.back()"><el-icon><ArrowLeft /></el-icon> 返回</el-button>
      <span class="title">{{ book?.title || book?.file_name }}</span>
      <div class="actions">
        <el-button link @click="chapterDrawer = true"><el-icon><Menu /></el-icon> 目录</el-button>
        <el-button link @click="settingsOpen = true"><el-icon><Setting /></el-icon> 设置</el-button>
      </div>
    </div>

    <!-- 正文(始终占满全屏,不受顶/底栏影响) -->
    <div class="body">
      <!-- 沉浸态浮层:左下章节名 + 右下分页(仅 chrome 隐藏时显示) -->
      <div v-show="!showChrome && book" class="hud">
        <span class="hud-chapter">{{ chapterTitle }}</span>
        <span class="hud-page">{{ curPage + 1 }}/{{ totalPages }}</span>
      </div>
      <template v-if="book">
        <!-- PDF:保持原生 pdf.js 翻页 -->
        <PdfReader
          v-if="book.format === 'pdf'"
          :file-url="fileUrl"
          :initial-page="Number(initialLocation) || 1"
          @page-change="onPdfPage"
        />
        <!-- txt/epub:多列分页翻页 -->
        <template v-else>
          <HtmlReader
            ref="htmlReaderRef"
            :html="chapterHtml"
            :initial-char-offset="initialCharOffset"
            @paginated="onPaginated"
            @page-change="onHtmlPageChange"
          />
          <!-- 点击翻页区域:左/右翻页,中间切换工具栏 -->
          <div class="tap-zones" @touchstart.passive="onTouchStart" @touchend.passive="onTouchEnd" @click="onTapZoneClick">
            <div class="tap-zone left" data-zone="left"></div>
            <div class="tap-zone center" data-zone="center"></div>
            <div class="tap-zone right" data-zone="right"></div>
          </div>
        </template>
      </template>
      <el-empty v-else description="加载中..." />
    </div>

    <!-- 底栏:进度信息(非 pdf,始终占位) -->
    <div v-if="book && book.format !== 'pdf'" class="footbar">
      <el-button size="small" text :disabled="curChapter <= 0 && htmlFirstPage" @click="prevPageOrChapter">上一页</el-button>
      <span class="progress">{{ chapters[curChapter]?.title || `第 ${curChapter + 1} 章` }} · {{ curPage + 1 }}/{{ totalPages }}</span>
      <el-button size="small" text :disabled="curChapter >= chapters.length - 1 && htmlLastPage" @click="nextPageOrChapter">下一页</el-button>
    </div>

    <!-- 目录抽屉 -->
    <el-drawer v-model="chapterDrawer" title="目录" direction="ltr" :size="drawerSize" @closed="showChrome = false">
      <div class="toc">
        <div
          v-for="ch in chapters"
          :key="ch.idx"
          class="toc-item"
          :class="{ active: ch.idx === curChapter }"
          @click="jumpChapter(ch.idx)"
        >
          {{ ch.title || `第 ${ch.idx + 1} 章` }}
        </div>
      </div>
    </el-drawer>

    <SettingsPanel v-model="settingsOpen" @update:modelValue="(v) => { settingsOpen = v; if (!v) showChrome = false }" />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Menu, Setting } from '@element-plus/icons-vue'
import { booksApi, type BookDetail, type Chapter } from '@/api/books'
import { useReaderStore } from '@/stores/reader'
import HtmlReader from '@/reader/HtmlReader.vue'
import PdfReader from '@/reader/PdfReader.vue'
import SettingsPanel from '@/reader/SettingsPanel.vue'

const route = useRoute()
const router = useRouter()
const bookId = route.params.id as string

const readerStore = useReaderStore()
const settings = computed(() => readerStore.settings)

const book = ref<BookDetail | null>(null)
const chapters = ref<Chapter[]>([])
const curChapter = ref(0)
const chapterHtml = ref('')
const initialLocation = ref('') // pdf 用页码
const initialCharOffset = ref(0) // txt/epub 用字符偏移
const chapterDrawer = ref(false)
const settingsOpen = ref(false)
const showChrome = ref(false) // 默认隐藏(沉浸式);点中间切换,翻页后自动隐藏

function toggleChrome() {
  showChrome.value = !showChrome.value
}

// 分页状态(来自 HtmlReader)
const totalPages = ref(1)
const curPage = ref(0)
const htmlFirstPage = ref(true)
const htmlLastPage = ref(false)

const htmlReaderRef = ref<InstanceType<typeof HtmlReader>>()

const fileUrl = computed(() => booksApi.fileUrl(bookId))
const drawerSize = computed(() => (window.innerWidth < 600 ? '80%' : 320))
// HUD 显示:章节名(PDF 时为书名),分页(统一 1-based)
const chapterTitle = computed(() => chapters.value[curChapter.value]?.title || book.value?.title || book.value?.file_name || '')

// 跨章节翻页时,新章节分页完成后要跳到的位置:'last' = 末页
let pendingGoLast = false
let saveTimer: ReturnType<typeof setTimeout> | null = null

onMounted(async () => {
  await readerStore.load()
  const [{ data: detail }, { data: chs }] = await Promise.all([
    booksApi.detail(bookId),
    booksApi.chapters(bookId),
  ])
  book.value = detail
  chapters.value = chs
  const prog = detail.progress
  if (prog) {
    curChapter.value = prog.chapter_idx || 0
    initialLocation.value = prog.location
    // txt/epub:location 存的是字符偏移
    initialCharOffset.value = /^\d+$/.test(prog.location) ? Number(prog.location) : 0
  }
  if (detail.format !== 'pdf') {
    await loadChapter(curChapter.value)
  }
  window.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
})

async function loadChapter(idx: number, goLast = false) {
  if (idx < 0 || idx >= chapters.value.length) return
  curChapter.value = idx
  pendingGoLast = goLast
  const { data } = await booksApi.content(bookId, idx)
  chapterHtml.value = data.html
  // html 变化会触发 HtmlReader 重新分页并按 initialCharOffset 定位
}

function jumpChapter(idx: number) {
  chapterDrawer.value = false
  initialCharOffset.value = 0
  loadChapter(idx)
}

// —— 来自 HtmlReader 的事件 ——
function onPaginated(total: number, current: number) {
  totalPages.value = total
  curPage.value = current
  // 跨章节:进入下一章从第一页(默认),进入上一章跳到末页
  if (pendingGoLast) {
    pendingGoLast = false
    htmlReaderRef.value?.goToPage(total - 1)
  }
  updatePageFlags()
}

function onHtmlPageChange(page: number, charOffset: number) {
  curPage.value = page
  updatePageFlags()
  saveProgress(String(charOffset))
}

function updatePageFlags() {
  htmlFirstPage.value = htmlReaderRef.value?.isFirstPage() ?? true
  htmlLastPage.value = htmlReaderRef.value?.isLastPage() ?? false
}

// —— 翻页(含跨章节)——
function nextPageOrChapter() {
  const r = htmlReaderRef.value
  if (!r) return
  if (r.nextPage()) return
  // 已在末页 → 下一章第一页
  if (curChapter.value < chapters.value.length - 1) {
    initialCharOffset.value = 0
    loadChapter(curChapter.value + 1, false)
  }
}
function prevPageOrChapter() {
  const r = htmlReaderRef.value
  if (!r) return
  if (r.prevPage()) return
  // 已在首页 → 上一章末页
  if (curChapter.value > 0) {
    initialCharOffset.value = 0
    loadChapter(curChapter.value - 1, true)
  }
}

function onTapZoneClick(e: MouseEvent) {
  const z = (e.target as HTMLElement)?.dataset?.zone
  if (z === 'left') { prevPageOrChapter(); showChrome.value = false }
  else if (z === 'right') { nextPageOrChapter(); showChrome.value = false }
  else if (z === 'center') toggleChrome()
}

// —— 键盘(PC)——
function onKeydown(e: KeyboardEvent) {
  if (!book.value || book.value.format === 'pdf') return
  if (e.key === 'ArrowRight' || e.key === 'PageDown') nextPageOrChapter()
  else if (e.key === 'ArrowLeft' || e.key === 'PageUp') prevPageOrChapter()
}

// —— 滑动(移动端)——
let touchStartX = 0
let touchStartY = 0
function onTouchStart(e: TouchEvent) {
  touchStartX = e.touches[0].clientX
  touchStartY = e.touches[0].clientY
}
function onTouchEnd(e: TouchEvent) {
  const dx = e.changedTouches[0].clientX - touchStartX
  const dy = e.changedTouches[0].clientY - touchStartY
  if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy)) {
    if (dx < 0) nextPageOrChapter()
    else prevPageOrChapter()
  }
}

// —— PDF 进度 ——
function onPdfPage(page: number, total: number) {
  curPage.value = page - 1  // 1-based → 0-based
  totalPages.value = total
  saveProgress(String(page), total > 0 ? (page / total) * 100 : 0)
}

// —— 进度保存 ——
function saveProgress(location: string, percentOverride?: number) {
  if (!book.value) return
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = setTimeout(() => {
    let percent = percentOverride ?? 0
    if (book.value!.format !== 'pdf') {
      const total = chapters.value.length || 1
      const pageFrac = totalPages.value > 0 ? (curPage.value + 1) / totalPages.value : 0
      percent = ((curChapter.value + pageFrac) / total) * 100
    }
    booksApi
      .putProgress(bookId, {
        location,
        percent: Math.min(Math.max(percent, 0), 100),
        chapter_idx: curChapter.value,
      })
      .catch(() => {})
  }, 800)
}
</script>

<style scoped>
.reader-page { position: relative; display: block; height: 100%; overflow: hidden; transition: background 0.25s; }
.theme-light { background: #fff; }
.theme-sepia { background: #f5ecd9; }
.theme-dark { background: #1a1a1a; }

.topbar {
  position: absolute;
  top: 0; left: 0; right: 0;
  z-index: 20;
  display: flex; align-items: center; gap: 12px;
  padding: 8px 16px;
  padding-top: calc(8px + env(safe-area-inset-top));
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid rgba(128, 128, 128, 0.15);
  transition: opacity 0.2s, transform 0.2s;
}
.theme-dark .topbar { background: rgba(26, 26, 26, 0.92); color: #c8c8c8; }
.theme-sepia .topbar { background: rgba(245, 236, 217, 0.92); }
.topbar .title { flex: 1; text-align: center; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.actions { display: flex; gap: 4px; }

/* 正文始终占满全屏(顶/底栏浮在上面,不影响布局) */
.body { position: absolute; inset: 0; overflow: hidden; }

/* 沉浸态 HUD:左下章节名 + 右下分页 */
.hud {
  position: absolute;
  inset: 0;
  z-index: 5;  /* 高于正文,低于顶/底栏(20)和点击层(10)——实际在点击层之上避免被拦截 */
  pointer-events: none;
  font-size: 12px;
  color: #909399;
  transition: opacity 0.25s;
}
.hud-chapter {
  position: absolute;
  top: calc(8px + env(safe-area-inset-top));
  left: 12px;
  max-width: 60%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  background: rgba(255, 255, 255, 0.6);
  padding: 4px 10px;
  border-radius: 10px;
  backdrop-filter: blur(4px);
}
.theme-dark .hud-chapter { background: rgba(0, 0, 0, 0.5); color: #c8c8c8; }
.hud-page {
  position: absolute;
  bottom: calc(8px + env(safe-area-inset-bottom));
  right: 12px;
  background: rgba(255, 255, 255, 0.6);
  padding: 4px 10px;
  border-radius: 10px;
  backdrop-filter: blur(4px);
  font-variant-numeric: tabular-nums;
}
.theme-dark .hud-page { background: rgba(0, 0, 0, 0.5); color: #c8c8c8; }

/* 点击翻页区域覆盖层(在 HUD 之上,确保点击翻页能命中) */
.tap-zones { position: absolute; inset: 0; z-index: 10; display: flex; }
.tap-zone { height: 100%; }
.tap-zone.left { width: 30%; }
.tap-zone.center { width: 40%; }
.tap-zone.right { width: 30%; }

.footbar {
  position: absolute;
  bottom: 0; left: 0; right: 0;
  z-index: 20;
  display: flex; gap: 12px; align-items: center; justify-content: space-between;
  padding: 8px 16px;
  padding-bottom: calc(8px + env(safe-area-inset-bottom));
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(8px);
  border-top: 1px solid rgba(128, 128, 128, 0.15);
  font-size: 13px;
  transition: opacity 0.2s, transform 0.2s;
}
.theme-dark .footbar { background: rgba(26, 26, 26, 0.92); color: #c8c8c8; }
.theme-sepia .footbar { background: rgba(245, 236, 217, 0.92); }
.footbar .progress { flex: 1; text-align: center; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #909399; }

.chrome-fade-enter-active, .chrome-fade-leave-active { transition: opacity 0.2s; }
.chrome-fade-enter-from, .chrome-fade-leave-to { opacity: 0; }

/* 隐藏工具栏(点击中间):顶/底栏淡出,内容区位置和分页完全不变 */
.chrome-hidden .topbar {
  opacity: 0;
  transform: translateY(-100%);
  pointer-events: none;
}
.chrome-hidden .footbar {
  opacity: 0;
  transform: translateY(100%);
  pointer-events: none;
}

.toc-item { padding: 10px 12px; cursor: pointer; border-radius: 6px; font-size: 14px; }
.toc-item:hover { background: #f0f0f0; }
.toc-item.active { color: var(--el-color-primary); font-weight: 600; }
</style>
