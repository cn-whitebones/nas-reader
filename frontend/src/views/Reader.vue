<template>
  <div class="reader-page" :class="`theme-${settings.theme}`">
    <!-- 顶栏 -->
    <div class="topbar">
      <el-button link @click="router.back()"><el-icon><ArrowLeft /></el-icon> 返回</el-button>
      <span class="title">{{ book?.title || book?.file_name }}</span>
      <div class="actions">
        <el-button link @click="chapterDrawer = true"><el-icon><Menu /></el-icon> 目录</el-button>
        <el-button link @click="settingsOpen = true"><el-icon><Setting /></el-icon> 设置</el-button>
      </div>
    </div>

    <!-- 正文 -->
    <div class="body" ref="bodyEl" @scroll="onScroll">
      <template v-if="book">
        <PdfReader
          v-if="book.format === 'pdf'"
          :file-url="fileUrl"
          :initial-page="Number(initialLocation) || 1"
          @page-change="onPdfPage"
        />
        <HtmlReader v-else :html="chapterHtml" />
      </template>
      <el-empty v-else description="加载中..." />
    </div>

    <!-- 章节间导航(非 pdf) -->
    <div v-if="book && book.format !== 'pdf'" class="chapter-nav">
      <el-button size="small" :disabled="curChapter <= 0" @click="loadChapter(curChapter - 1)">上一章</el-button>
      <span>{{ curChapter + 1 }} / {{ chapters.length }}</span>
      <el-button size="small" :disabled="curChapter >= chapters.length - 1" @click="loadChapter(curChapter + 1)">下一章</el-button>
    </div>

    <!-- 目录抽屉 -->
    <el-drawer v-model="chapterDrawer" title="目录" direction="ltr" :size="drawerSize">
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

    <SettingsPanel v-model="settingsOpen" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
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
const initialLocation = ref('')
const chapterDrawer = ref(false)
const settingsOpen = ref(false)
const bodyEl = ref<HTMLElement>()

const fileUrl = computed(() => booksApi.fileUrl(bookId))
const drawerSize = computed(() => (window.innerWidth < 600 ? '80%' : 320))

let saveTimer: ReturnType<typeof setTimeout> | null = null

onMounted(async () => {
  await readerStore.load()
  const [{ data: detail }, { data: chs }] = await Promise.all([
    booksApi.detail(bookId),
    booksApi.chapters(bookId),
  ])
  book.value = detail
  chapters.value = chs
  // 恢复进度
  const prog = detail.progress
  if (prog) {
    curChapter.value = prog.chapter_idx || 0
    initialLocation.value = prog.location
  }
  if (detail.format !== 'pdf') {
    await loadChapter(curChapter.value)
  }
})

async function loadChapter(idx: number) {
  if (idx < 0 || idx >= chapters.value.length) return
  curChapter.value = idx
  const { data } = await booksApi.content(bookId, idx)
  chapterHtml.value = data.html
  bodyEl.value?.scrollTo({ top: 0 })
  saveProgress()
}

function jumpChapter(idx: number) {
  chapterDrawer.value = false
  loadChapter(idx)
}

function onScroll() {
  saveProgress()
}

function onPdfPage(page: number, total: number) {
  curChapter.value = 0
  initialLocation.value = String(page)
  saveProgress(String(page), total > 0 ? (page / total) * 100 : 0)
}

function saveProgress(location?: string, percentOverride?: number) {
  if (!book.value) return
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = setTimeout(() => {
    let percent = percentOverride ?? 0
    let loc = location ?? ''
    if (book.value!.format !== 'pdf') {
      // 用章节进度 + 滚动比例估算百分比
      const el = bodyEl.value
      const scrollRatio =
        el && el.scrollHeight > el.clientHeight
          ? el.scrollTop / (el.scrollHeight - el.clientHeight)
          : 0
      const total = chapters.value.length || 1
      percent = ((curChapter.value + scrollRatio) / total) * 100
      loc = String(curChapter.value)
    }
    booksApi
      .putProgress(bookId, {
        location: loc,
        percent: Math.min(Math.max(percent, 0), 100),
        chapter_idx: curChapter.value,
      })
      .catch(() => {})
  }, 1000)
}
</script>

<style scoped>
/* 用 fixed+inset 直接铺满整个视口,绕开 #app/el-main 的百分比高度传导链,
   彻底规避 iOS PWA 首帧视口高度算错导致的底部白边。盖住 Layout 顶栏,
   阅读器自带返回/目录/设置顶栏,不冗余。 */
.reader-page {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.theme-light { background: #fff; }
.theme-sepia { background: #f5ecd9; }
.theme-dark { background: #1a1a1a; }
.topbar { display: flex; align-items: center; gap: 12px; padding: 8px 16px; padding-top: calc(8px + env(safe-area-inset-top)); border-bottom: 1px solid rgba(128, 128, 128, 0.2); }
.topbar .title { flex: 1; text-align: center; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.actions { display: flex; gap: 4px; }
.body { flex: 1; overflow-y: auto; -webkit-overflow-scrolling: touch; }
.chapter-nav { display: flex; gap: 12px; align-items: center; justify-content: center; padding: 8px 10px; padding-bottom: calc(8px + env(safe-area-inset-bottom)); border-top: 1px solid rgba(128, 128, 128, 0.15); }
/* 底部工具栏按主题配色,连同安全区形成整体,不再是突兀白带 */
.theme-light .chapter-nav { background: #f7f7f7; }
.theme-sepia .chapter-nav { background: #efe4cc; }
.theme-dark .chapter-nav { background: #262626; }
.theme-dark .chapter-nav span { color: #c8c8c8; }
.toc-item { padding: 10px 12px; cursor: pointer; border-radius: 6px; font-size: 14px; }
.toc-item:hover { background: #f0f0f0; }
.toc-item.active { color: var(--el-color-primary); font-weight: 600; }
</style>
