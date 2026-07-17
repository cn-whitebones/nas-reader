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
        <span class="hud-page">{{ book?.format === 'comic' ? `第 ${curChapter + 1} 页` : `${curPage + 1}/${totalPages}` }}</span>
      </div>
      <template v-if="book">
        <!-- PDF:保持原生 pdf.js 翻页 -->
        <PdfReader
          v-if="book?.format === 'pdf'"
          :file-url="fileUrl"
          :initial-page="Number(initialLocation) || 1"
          @page-change="onPdfPage"
        />
        <!-- 漫画:单图显示,自动检测横图旋转90度 -->
        <template v-else-if="book?.format === 'comic'">
          <div class="comic-page" ref="comicPageRef">
            <img
              ref="comicImgRef"
              :src="comicImgSrc"
              :class="{ 'rotate-90': comicRotate90, loaded: comicImgLoaded }"
              @load="onComicImgLoad"
              @error="onComicImgError"
            />
            <div v-if="comicImgLoaded" class="comic-rotate-btn" @click.stop="toggleComicRotate">
              <el-icon :size="18"><Refresh /></el-icon>
            </div>
          </div>
          <!-- 点击翻页区域:旋转时整个层跟着旋转,左右点击逻辑自然对齐视觉,无需改 JS -->
          <div class="tap-zones" :class="{ 'rotate-90': comicRotate90 }" @touchstart.passive="onTouchStart" @touchend.passive="onTouchEnd" @click="onTapZoneClick">
            <div class="tap-zone left" data-zone="left"></div>
            <div class="tap-zone center" data-zone="center"></div>
            <div class="tap-zone right" data-zone="right"></div>
          </div>
        </template>
        <!-- txt/epub/mobi:多列分页翻页 -->
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
    <div v-if="book && book?.format !== 'pdf'" class="footbar">
      <el-button size="small" text :disabled="isFirstPage" @click="prevPageOrChapter">上一页</el-button>
      <span class="progress">{{ footbarText }}</span>
      <el-button size="small" text :disabled="isLastPage" @click="nextPageOrChapter">下一页</el-button>
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
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
import { ArrowLeft, Menu, Setting, Refresh } from '@element-plus/icons-vue'
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

// 漫画:一页一章,不需要 HtmlReader 内分页;横图自动旋转90度
const isComic = computed(() => (book.value?.format ?? '') === 'comic')
const comicPageRef = ref<HTMLDivElement>()
const comicImgRef = ref<HTMLImageElement>()
const comicRotate90 = ref(false)
const comicImgLoaded = ref(false)
const userManualRotated = ref(false) // 用户是否手动点过旋转按钮
// 从后端返回的 HTML 中提取 base64 img src
const comicImgSrc = computed(() => {
  if (!isComic.value || !chapterHtml.value) return ''
  const match = chapterHtml.value.match(/src="([^"]+)"/)
  return match ? match[1] : ''
})

function onComicImgLoad(e: Event) {
  const img = e.target as HTMLImageElement
  const shouldRotate = img.naturalWidth > img.naturalHeight
  // 用户没手动改过方向时,每页自动判断(不同页可能横竖混杂)
  // 用户一旦手动点过旋转按钮,就完全尊重用户选择,不再自动变
  if (!userManualRotated.value) {
    comicRotate90.value = shouldRotate
  }
  comicImgLoaded.value = true
}
function onComicImgError() {
  comicImgLoaded.value = true
}
function toggleComicRotate() {
  userManualRotated.value = true
  comicRotate90.value = !comicRotate90.value
}

// 切换章节时重置加载状态,不清空旋转方向
watch(curChapter, () => {
  if (isComic.value) {
    comicImgLoaded.value = false
  }
})

const isFirstPage = computed(() => {
  if (isComic.value) return curChapter.value <= 0
  return curChapter.value <= 0 && htmlFirstPage.value
})
const isLastPage = computed(() => {
  if (isComic.value) return curChapter.value >= chapters.value.length - 1
  return curChapter.value >= chapters.value.length - 1 && htmlLastPage.value
})
const footbarText = computed(() => {
  if (isComic.value) return `${chapters.value[curChapter.value]?.title || `第 ${curChapter.value + 1} 页`} · ${curChapter.value + 1}/${chapters.value.length}`
  return `${chapters.value[curChapter.value]?.title || `第 ${curChapter.value + 1} 章`} · ${curPage.value + 1}/${totalPages.value}`
})

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
  // 兜底保存:切后台/锁屏用 visibilitychange,关闭/刷新用 pagehide
  document.addEventListener('visibilitychange', onVisibilityChange)
  window.addEventListener('pagehide', commitProgress)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  document.removeEventListener('visibilitychange', onVisibilityChange)
  window.removeEventListener('pagehide', commitProgress)
  // 离开阅读页(关闭/刷新)时立即写入最新进度
  commitProgress()
})

// 离开路由前(返回/跳转)先完成进度保存,确保 BookDetail 刷新能拿到新进度
onBeforeRouteLeave(async () => {
  await commitProgress()
})

async function loadChapter(idx: number, goLast = false) {
  if (idx < 0 || idx >= chapters.value.length) return
  // 通知阅读器切换方向与目标页,让新章节按翻页方向做进入动画(漫画不需要)
  if (!isComic.value) {
    if (idx > curChapter.value) {
      htmlReaderRef.value?.prepareChapterTransition('next', 'first')
    } else if (idx < curChapter.value) {
      htmlReaderRef.value?.prepareChapterTransition('prev', goLast ? 'last' : 'first')
    }
  }
  curChapter.value = idx
  const { data } = await booksApi.content(bookId, idx)
  chapterHtml.value = data.html
  // 漫画:一页一章,手动保存进度;文本/PDF 靠 HtmlReader 事件触发
  if (isComic.value) {
    saveProgress(chapters.value[idx]?.location || String(idx))
  }
  // html 变化会触发 HtmlReader 重新分页并按目标页/initialCharOffset 定位
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
  // 漫画:一页一章,直接切下一章
  if (isComic.value) {
    if (curChapter.value < chapters.value.length - 1) {
      loadChapter(curChapter.value + 1, false)
    }
    return
  }
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
  // 漫画:一页一章,直接切上一章
  if (isComic.value) {
    if (curChapter.value > 0) {
      loadChapter(curChapter.value - 1, true)
    }
    return
  }
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
// 防抖提交,并记录"最近待保存进度",便于切后台/离开页面时立即兜底提交
let pendingLocation: string | null = null
let pendingPercentOverride: number | undefined

function saveProgress(location: string, percentOverride?: number) {
  if (!book.value) return
  pendingLocation = location
  pendingPercentOverride = percentOverride
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = setTimeout(commitProgress, 800)
}

// 立即把待保存进度写入后端(无防抖);无待存内容则跳过
async function commitProgress() {
  if (saveTimer) {
    clearTimeout(saveTimer)
    saveTimer = null
  }
  if (!book.value || pendingLocation === null) return
  const location = pendingLocation
  let percent = pendingPercentOverride ?? 0
  pendingLocation = null
  pendingPercentOverride = undefined
  if (book.value.format === 'comic') {
    // 漫画:一页一章,进度 = (当前章节+1)/总章节
    const total = chapters.value.length || 1
    percent = ((curChapter.value + 1) / total) * 100
  } else if (book.value.format !== 'pdf') {
    const total = chapters.value.length || 1
    const pageFrac = totalPages.value > 0 ? (curPage.value + 1) / totalPages.value : 0
    percent = ((curChapter.value + pageFrac) / total) * 100
  }
  try {
    await booksApi.putProgress(bookId, {
      location,
      percent: Math.min(Math.max(percent, 0), 100),
      chapter_idx: curChapter.value,
    })
  } catch {}
}

// 切后台/锁屏/切标签时立即兜底保存(移动端 beforeunload 不可靠,visibilitychange 才是关键)
function onVisibilityChange() {
  if (document.visibilityState === 'hidden') commitProgress()
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

/* 漫画页面:垂直滚动,横图自动旋转90度后宽度变为高度,需适配 */
.comic-page {
  width: 100%;
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px 0;
  padding-top: calc(20px + env(safe-area-inset-top));
  padding-bottom: calc(20px + env(safe-area-inset-bottom));
  box-sizing: border-box;
  position: relative;
}
.comic-page img {
  max-width: 100%;
  max-width: min(100%, 1000px);  /* 桌面端不过宽 */
  height: auto;
  display: block;
  opacity: 0;
  transition: opacity 0.15s ease-out, transform 0.15s ease-out;
}
.comic-page img[src] {
  /* 有 src 且加载完成时显示 */
}
.comic-page img[src].loaded {
  opacity: 1;
}
.theme-dark .comic-page { background: #1a1a1a; }
.theme-sepia .comic-page { background: #f5ecd9; }

/* 横图旋转90度后,宽高互换:max-width 变成 max-height,占满屏幕高度 */
.comic-page img.rotate-90 {
  transform: rotate(90deg);
  max-width: none;
  max-height: 100vw;
  /* 旋转后会偏移,需要用 margin 拉回视口中心 */
  margin: calc((100vw - 100vh) / 2) 0;
}

/* 旋转切换按钮:右下角悬浮,半透明 */
.comic-rotate-btn {
  position: absolute;
  right: 12px;
  bottom: 100px;
  z-index: 20;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.35);
  border-radius: 50%;
  color: #fff;
  cursor: pointer;
  backdrop-filter: blur(4px);
  transition: opacity 0.2s, background 0.2s;
}
.comic-rotate-btn:hover {
  background: rgba(0, 0, 0, 0.55);
}
/* 工具栏隐藏时,按钮也一起隐藏 */
.chrome-hidden .comic-rotate-btn {
  opacity: 0;
  pointer-events: none;
}

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
.tap-zones {
  position: absolute;
  inset: 0;
  z-index: 10;
  display: flex;
  transition: transform 0.15s ease-out;
}
/* 旋转后点击区从"左右竖条"变成"上下横条":横拿手机时上半屏点上一页,下半屏下一页
   不用旋转整个层,直接改 flex 方向 + 宽高互换,简单可靠 */
.tap-zones.rotate-90 {
  flex-direction: column;
}
.tap-zone { height: 100%; }
.tap-zone.left { width: 30%; }
.tap-zone.center { width: 40%; }
.tap-zone.right { width: 30%; }
/* 旋转后左右变成上下:原来的 left → 顶部 30%,原来的 right → 底部 30% */
.tap-zones.rotate-90 .tap-zone { width: 100%; }
.tap-zones.rotate-90 .tap-zone.left { height: 30%; }
.tap-zones.rotate-90 .tap-zone.center { height: 40%; }
.tap-zones.rotate-90 .tap-zone.right { height: 30%; }

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
