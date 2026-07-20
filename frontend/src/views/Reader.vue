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
        <span class="hud-page">
          <template v-if="book?.format === 'comic'">
            第 {{ curChapter + 1 }} 页
            <template v-if="comicIsDoublePage">{{ comicSubPage === 0 ? '· 左' : '· 右' }}</template>
          </template>
          <template v-else>{{ curPage + 1 }}/{{ totalPages }}</template>
        </span>
      </div>
      <template v-if="book">
        <!-- PDF:保持原生 pdf.js 翻页 -->
        <template v-if="book?.format === 'pdf'">
          <PdfReader
            ref="pdfReaderRef"
            :file-url="fileUrl"
            :initial-page="Number(initialLocation) || 1"
            @page-change="onPdfPage"
          />
          <!-- 点击翻页区域:左/右翻页,中间切换工具栏(与文本/漫画一致) -->
          <div class="tap-zones" @touchstart.passive="onTouchStart" @touchend.passive="onTouchEnd" @click="onTapZoneClick">
            <div class="tap-zone left" data-zone="left"></div>
            <div class="tap-zone center" data-zone="center"></div>
            <div class="tap-zone right" data-zone="right"></div>
          </div>
        </template>
        <!-- 漫画:单图显示,自动检测横图旋转90度;移动端双页横图自动切分为左右两页 -->
        <template v-else-if="book?.format === 'comic'">
          <div class="comic-page" ref="comicPageRef">
            <template v-if="comicIsDoublePage">
              <!-- 双页漫画:分别显示左/右半页 -->
              <img
                :src="comicSubPage === 0 ? comicLeftImage : comicRightImage"
                class="loaded"
                style="max-width: 100%; width: 100%; height: auto;"
              />
            </template>
            <template v-else>
              <!-- 普通单页漫画 -->
              <img
                ref="comicImgRef"
                :src="comicImgSrc"
                :class="{ 'rotate-90': comicRotate90, loaded: comicImgLoaded }"
                @load="onComicImgLoad"
                @error="onComicImgError"
              />
            </template>
            <div v-if="comicImgLoaded && !comicIsDoublePage" class="comic-rotate-btn" @click.stop="toggleComicRotate">
              <el-icon :size="18"><Refresh /></el-icon>
            </div>
          </div>
          <!-- 点击翻页区域:旋转时整个层跟着旋转,左右点击逻辑自然对齐视觉,无需改 JS -->
          <div class="tap-zones" :class="{ 'rotate-90': comicRotate90 && !comicIsDoublePage }" @touchstart.passive="onTouchStart" @touchend.passive="onTouchEnd" @click="onTapZoneClick">
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

    <SettingsPanel
      v-model="settingsOpen"
      @update:modelValue="(v) => { settingsOpen = v; if (!v) showChrome = false }"
      :is-comic="isComic"
      :is-mobile="isMobile"
      :book-id="bookId"
      :book-double-page="book?.double_page"
      :book-start-right="book?.start_right"
      @comic-prefs-changed="reloadCurrentPage"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
import { ArrowLeft, Menu, Setting, Refresh } from '@element-plus/icons-vue'
import { booksApi, type BookDetail, type Chapter } from '@/api/books'
import { useReaderStore } from '@/stores/reader'
import { applyTheme, setStatusBarColor, THEME_STATUS_COLOR, type AppTheme } from '@/theme'
import HtmlReader from '@/reader/HtmlReader.vue'
import PdfReader from '@/reader/PdfReader.vue'
import SettingsPanel from '@/reader/SettingsPanel.vue'

const route = useRoute()
const router = useRouter()
const bookId = route.params.id as string

const readerStore = useReaderStore()
const settings = computed(() => readerStore.settings)

// 阅读器内让状态栏/刘海跟随当前阅读主题(含护眼)沉浸;离开时由 onBeforeUnmount 恢复全局
watch(
  () => settings.value.theme,
  (t) => setStatusBarColor(THEME_STATUS_COLOR[t as AppTheme] || THEME_STATUS_COLOR.light),
)

const book = ref<BookDetail | null>(null)
const chapters = ref<Chapter[]>([])
const curChapter = ref(0)
const chapterHtml = ref('')
const initialLocation = ref('') // pdf 用页码
const initialCharOffset = ref(0) // txt/epub 用字符偏移
const chapterDrawer = ref(false)
const settingsOpen = ref(false)
const showChrome = ref(false) // 默认隐藏(沉浸式);点中间切换,翻页后自动隐藏
const goLastOnLoad = ref(false) // 标记下一章加载完成后是否显示末页(右半页)

function toggleChrome() {
  showChrome.value = !showChrome.value
}

// 分页状态(来自 HtmlReader)
const totalPages = ref(1)
const curPage = ref(0)
const htmlFirstPage = ref(true)
const htmlLastPage = ref(false)

const htmlReaderRef = ref<InstanceType<typeof HtmlReader>>()
const pdfReaderRef = ref<InstanceType<typeof PdfReader>>()

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
const isMobile = ref(window.innerWidth < 700) // 移动端阈值
// 双页漫画相关
const comicIsDoublePage = ref(false) // 当前页是否是双页横向
const comicSubPage = ref(0) // 子页:0=左半页,1=右半页
const comicLeftImage = ref('') // 左半页图片
const comicRightImage = ref('') // 右半页图片
const comicOriginalImage = ref('') // 原图src
const comicRotateHeightVh = ref(0) // 旋转后图片高度（vh 单位）,由 JS 精确计算
const STORAGE_KEY_PREFIX = 'nas-reader:comic-pref:'

// 读取漫画设置:localStorage 用户覆盖值 > 书籍默认值
function getComicPrefs() {
  // 先试读本地
  try {
    const raw = localStorage.getItem(`${STORAGE_KEY_PREFIX}${bookId}`)
    if (raw) {
      const local = JSON.parse(raw)
      return {
        doublePage: !!local.doublePage,
        startRight: !!local.startRight,
      }
    }
  } catch { /* ignore */ }
  return {
    doublePage: !!book.value?.double_page,
    startRight: !!book.value?.start_right,
  }
}

// 漫画设置改变时:重切当前页
async function reloadCurrentPage() {
  if (!isComic.value) return
  // 先清空旧状态,触发重新加载
  const wasDouble = comicIsDoublePage.value
  chapterHtml.value = ''
  comicIsDoublePage.value = false
  comicImgLoaded.value = false
  comicLeftImage.value = ''
  comicRightImage.value = ''
  await new Promise(r => setTimeout(r, 50))
  // 重新拉取当前章
  const { data } = await booksApi.content(bookId, curChapter.value)
  chapterHtml.value = data.html
  goLastOnLoad.value = wasDouble && comicSubPage.value === 1
}

// 从后端返回的 HTML 中提取 base64 img src
const comicImgSrc = computed(() => {
  if (!isComic.value || !chapterHtml.value) return ''
  const match = chapterHtml.value.match(/src="([^"]+)"/)
  return match ? match[1] : ''
})

function onComicImgLoad(e: Event) {
  const img = e.target as HTMLImageElement
  // 用户手动旋转过就不做任何处理
  if (userManualRotated.value) {
    comicIsDoublePage.value = false
    comicImgLoaded.value = true
    return
  }
  const prefs = getComicPrefs()
  // 是否走双页模式，由本地覆盖或后端设置决定；不再基于宽高比自动触发。
  // PC 端不做双页切割。
  if (prefs.doublePage && isMobile.value) {
    comicIsDoublePage.value = true
    comicOriginalImage.value = comicImgSrc.value
    comicRotate90.value = false
    splitDoublePage(img)
    // 一张原图对应“一整章”，进入这章时从阅读方向的第一半开始（跨章向前翻页时定位到末半）
    const startRight = prefs.startRight
    const firstSub = startRight ? 1 : 0
    const lastSub = startRight ? 0 : 1
    comicSubPage.value = goLastOnLoad.value ? lastSub : firstSub
    goLastOnLoad.value = false
  } else if (isMobile.value) {
    // 未开启双页模式：仅在图片明显是横图时做一次旋转，以便竖屏阅读
    comicIsDoublePage.value = false
    comicRotate90.value = img.naturalWidth > img.naturalHeight
    if (comicRotate90.value) {
      // 旋转后精确计算最大尺寸，确保两个方向都不溢出屏幕:
      // 旋转后:视觉高度方向 = 原始宽度，视觉宽度方向 = 原始高度
      // CSS width 控制视觉高度方向，CSS height 自动按比例对应视觉宽度方向
      // scale = min( 0.97*screenHeight / w, screenWidth / h )
      // width_vh = scale * w / screenHeight * 100
      const screenH = window.innerHeight
      const screenW = window.innerWidth
      const w = img.naturalWidth
      const h = img.naturalHeight
      const scaleByH = 0.97 * screenH / w
      const scaleByW = screenW / h
      const scale = Math.min(scaleByH, scaleByW)
      const widthVh = (scale * w / screenH) * 100
      const visualWVh = (scale * h / screenH) * 100
      comicRotateHeightVh.value = widthVh
      // 直接设置内联样式（旋转后 width/height 对调控制方向）
      img.style.width = `${widthVh}vh`
      img.style.height = 'auto'
      img.style.maxWidth = 'none'
      // margin 居中:基于视觉宽度（scale*h）计算
      img.style.margin = `calc((100vw - ${visualWVh}vh) / 2) 0`
    }
  } else {
    comicIsDoublePage.value = false
  }
  comicImgLoaded.value = true
}

function splitDoublePage(img: HTMLImageElement) {
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  const halfWidth = Math.floor(img.naturalWidth / 2)
  // 切左半页
  canvas.width = halfWidth
  canvas.height = img.naturalHeight
  ctx.drawImage(img, 0, 0, halfWidth, img.naturalHeight, 0, 0, halfWidth, img.naturalHeight)
  comicLeftImage.value = canvas.toDataURL('image/jpeg', 0.95)
  // 切右半页
  ctx.drawImage(img, halfWidth, 0, halfWidth, img.naturalHeight, 0, 0, halfWidth, img.naturalHeight)
  comicRightImage.value = canvas.toDataURL('image/jpeg', 0.95)
  // 重置到左半页
  comicSubPage.value = 0
}

function onComicImgError() {
  comicImgLoaded.value = true
  comicIsDoublePage.value = false
}

function toggleComicRotate() {
  userManualRotated.value = true
  comicRotate90.value = !comicRotate90.value
  // 手动旋转也需要重新计算尺寸
  if (comicRotate90.value && comicImgRef.value) {
    const img = comicImgRef.value
    const screenH = window.innerHeight
    const screenW = window.innerWidth
    const w = img.naturalWidth
    const h = img.naturalHeight
    const scaleByH = 0.97 * screenH / w
    const scaleByW = screenW / h
    const scale = Math.min(scaleByH, scaleByW)
    const widthVh = (scale * w / screenH) * 100
    const visualWVh = (scale * h / screenH) * 100
    comicRotateHeightVh.value = widthVh
    img.style.width = `${widthVh}vh`
    img.style.height = 'auto'
    img.style.maxWidth = 'none'
    img.style.margin = `calc((100vw - ${visualWVh}vh) / 2) 0`
  } else if (comicImgRef.value) {
    // 关闭旋转，清除内联样式
    comicImgRef.value.style.width = ''
    comicImgRef.value.style.height = ''
    comicImgRef.value.style.maxWidth = ''
    comicImgRef.value.style.margin = ''
  }
}

// 切换章节时重置加载状态,不清空旋转方向
watch(curChapter, () => {
  if (isComic.value) {
    comicImgLoaded.value = false
    comicIsDoublePage.value = false
    comicSubPage.value = 0
    comicLeftImage.value = ''
    comicRightImage.value = ''
  }
})

const isFirstPage = computed(() => {
  if (isComic.value) {
    if (comicIsDoublePage.value) return curChapter.value <= 0 && comicSubPage.value <= 0
    return curChapter.value <= 0
  }
  return curChapter.value <= 0 && htmlFirstPage.value
})
const isLastPage = computed(() => {
  if (isComic.value) {
    if (comicIsDoublePage.value) return curChapter.value >= chapters.value.length - 1 && comicSubPage.value >= 1
    return curChapter.value >= chapters.value.length - 1
  }
  return curChapter.value >= chapters.value.length - 1 && htmlLastPage.value
})
const footbarText = computed(() => {
  if (isComic.value) {
    let pageInfo = `${curChapter.value + 1}/${chapters.value.length}`
    if (comicIsDoublePage.value) {
      pageInfo = `${curChapter.value + 1}${comicSubPage.value === 0 ? '左' : '右'}/${chapters.value.length}`
    }
    return `${chapters.value[curChapter.value]?.title || `第 ${curChapter.value + 1} 页`} · ${pageInfo}`
  }
  return `${chapters.value[curChapter.value]?.title || `第 ${curChapter.value + 1} 章`} · ${curPage.value + 1}/${totalPages.value}`
})

let saveTimer: ReturnType<typeof setTimeout> | null = null

onMounted(async () => {
  await readerStore.load()
  // 进入阅读器:状态栏跟随阅读主题(护眼也沉浸)
  setStatusBarColor(THEME_STATUS_COLOR[settings.value.theme as AppTheme] || THEME_STATUS_COLOR.light)
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
  window.addEventListener('resize', onWindowResize)
  // 兜底保存:切后台/锁屏用 visibilitychange,关闭/刷新用 pagehide
  document.addEventListener('visibilitychange', onVisibilityChange)
  window.addEventListener('pagehide', commitProgress)
})

function onWindowResize() {
  isMobile.value = window.innerWidth < 700
}

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  window.removeEventListener('resize', onWindowResize)
  document.removeEventListener('visibilitychange', onVisibilityChange)
  window.removeEventListener('pagehide', commitProgress)
  // 离开阅读器:恢复全局状态栏颜色(护眼在全局归明亮)
  applyTheme(settings.value.theme)
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
  // 漫画:先清空 html + 重置双页状态,防止 v-if 切换到单页 <img> 时,
  // 旧章 html 触发一次 @load 提前消费掉 goLastOnLoad,导致跨章向前翻页落错半页
  if (isComic.value) {
    chapterHtml.value = ''
    comicIsDoublePage.value = false
    comicImgLoaded.value = false
    comicLeftImage.value = ''
    comicRightImage.value = ''
  }
  curChapter.value = idx
  const { data } = await booksApi.content(bookId, idx)
  // 标记:翻到上一章时是否要显示末半页(在 onComicImgLoad 中根据阅读方向落点)
  goLastOnLoad.value = goLast
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
  // PDF:交给 pdf.js 翻到下一页(到末页自动无效)
  if (book.value?.format === 'pdf') {
    pdfReaderRef.value?.next()
    return
  }
  // 漫画:一页一章;双页则先翻到跨页的另一半(按阅读方向)
  if (isComic.value) {
    if (comicIsDoublePage.value) {
      const startRight = getComicPrefs().startRight
      const firstSub = startRight ? 1 : 0
      // 当前还在跨页的第一半 → 翻到第二半,不跳章
      if (comicSubPage.value === firstSub) {
        comicSubPage.value = startRight ? 0 : 1
        return
      }
    }
    // 单页,或已在双页的第二半 → 下一章
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
  // PDF:交给 pdf.js 翻到上一页
  if (book.value?.format === 'pdf') {
    pdfReaderRef.value?.prev()
    return
  }
  // 漫画:双页则先翻回跨页的第一半;否则上一章
  if (isComic.value) {
    if (comicIsDoublePage.value) {
      const startRight = getComicPrefs().startRight
      const firstSub = startRight ? 1 : 0
      // 当前在跨页的第二半 → 翻回第一半,不跳章
      if (comicSubPage.value !== firstSub) {
        comicSubPage.value = firstSub
        return
      }
    }
    // 单页,或已在双页第一半 → 上一章(定位到末半页,由 onComicImgLoad 处理)
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
  if (!book.value) return
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
  width: auto;
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

/* PC端(≥700px):尽可能放大图片,充分利用屏幕空间,保持原始比例,同时避免图片失真 */
@media (min-width: 700px) {
  .comic-page img:not(.rotate-90) {
    /* 非旋转时优先占满高度(不旋转的漫画通常是竖图),同时限制最大宽度避免太宽 */
    max-height: 95vh;
    max-width: 95vw;
    width: auto;
    height: auto;
  }
  /* 旋转的图片(横变竖)单独调整 */
  .comic-page img.rotate-90 {
    max-width: none;
    max-height: 100vw;
  }
}

/* 移动端(<700px):保持更适度的大小,避免边缘留白太少 */
@media (max-width: 700px) {
  .comic-page img {
    max-width: 100%;
    max-height: none;
    width: 100%;
    height: auto;
  }
  /* 双页图片确保足够大,竖屏显示完整 */
  .comic-page img.loaded:not(.rotate-90) {
    max-height: 90vh;
    width: auto;
  }
}

/* 横图旋转90度，尺寸和边距由 JS 精确计算并设置内联样式 */
.comic-page img.rotate-90 {
  transform: rotate(90deg);
}

/* PC 端：不做额外调整，按常规显示 */
@media (min-width: 700px) {
  .comic-page img.rotate-90 {
    max-width: 95vmin;
    height: auto;
  }
}

/* 移动端横屏：保守值兜底 */
@media (max-width: 700px) and (orientation: landscape) {
  .comic-page img.rotate-90 {
    max-width: 90vh;
    height: auto;
    width: auto;
    margin: calc((100vw - 90vh) / 2) 0;
  }
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
