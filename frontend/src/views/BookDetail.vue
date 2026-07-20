<template>
  <div v-if="book" class="detail">
    <!-- 顶部主区:封面 + 标题 + 作者 + CTA -->
    <div class="hero">
      <div class="cover">
        <CoverImage v-if="book.has_cover" :book-id="bookId" :alt="title" />
        <GeneratedCover v-else :title="title || book.file_name" :format="book.format" />
      </div>
      <div class="info">
        <h1 class="book-title">{{ title }}</h1>
        <p v-if="md?.subtitle" class="subtitle">{{ md.subtitle }}</p>
        <p class="author">{{ md?.authors?.join(', ') || '未知作者' }}</p>
        <div v-if="md?.tags?.length" class="tags">
          <el-tag v-for="t in md.tags" :key="t" size="small" effect="plain" round>{{ t }}</el-tag>
        </div>
        <!-- 阅读进度徽章:始终占位,避免按钮抖动 -->
        <div class="progress">
          <el-progress v-if="progressPct > 0" :percentage="progressPct" :stroke-width="6" :show-text="false" />
          <div v-else class="placeholder-progress" />
          <span class="progress-text" :class="{ 'text-muted': progressPct <= 0 }">
            {{ progressPct > 0 ? `已读 ${progressPct.toFixed(1)}%` : '未开始' }}
          </span>
        </div>

        <!-- 主 CTA 独占一行,次按钮 grid 均分下一行(1个占满,2个平分),
             无论宽窄屏都对齐,避免 flex-wrap 后主/次按钮宽度不一致 -->
        <div class="actions">
          <el-button
            type="primary"
            size="large"
            class="cta-primary"
            @click="$router.push(`/read/${book.id}`)"
          >
            <el-icon><Reading /></el-icon>
            {{ progressPct > 0 ? '继续阅读' : '开始阅读' }}
          </el-button>
          <div class="secondary-actions">
            <el-button
              size="large"
              class="cta-icon"
              :type="inShelf ? 'success' : 'default'"
              @click="toggleShelf"
            >
              {{ inShelf ? '已收藏' : '收藏' }}
            </el-button>
            <el-button
              v-if="isAdmin"
              size="large"
              class="cta-icon"
              @click="openScrapeDialog"
            >
              刮削
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 指标卡片:字数 / 章节 / 大小 / 格式 · 4 格网格,替代原来一行文本 -->
    <div class="stats">
      <div class="stat">
        <div class="stat-value">{{ wordsMain }}</div>
        <div class="stat-label">{{ wordsLabel }}</div>
      </div>
      <div class="stat">
        <div class="stat-value">{{ book.chapter_count || '—' }}</div>
        <div class="stat-label">章节</div>
      </div>
      <div class="stat">
        <div class="stat-value">{{ sizeMain }}</div>
        <div class="stat-label">{{ sizeLabel }}</div>
      </div>
      <div class="stat">
        <div class="stat-value">{{ book.format.toUpperCase() }}</div>
        <div class="stat-label">格式</div>
      </div>
    </div>

    <!-- 漫画设置:仅移动端显示，PC端不需要双页切割;仅管理员可编辑 -->
    <div class="section" v-if="book.format === 'comic' && isMobile">
      <h3 class="section-title">漫画阅读设置</h3>
      <div class="comic-settings">
        <div class="setting-item">
          <span class="setting-label">
            双页横图模式
            <span v-if="!isAdmin" class="admin-hint">（管理员设定）</span>
          </span>
          <el-switch
            v-model="doublePage"
            :disabled="!isAdmin"
            @change="saveComicSettings"
          />
        </div>
        <div v-if="doublePage" class="setting-item">
          <span class="setting-label">
            从右页开始
            <span v-if="!isAdmin" class="admin-hint">（管理员设定）</span>
          </span>
          <el-switch
            v-model="startRight"
            :disabled="!isAdmin"
            @change="saveComicSettings"
          />
        </div>
      </div>
      <p v-if="!isAdmin" class="comic-tip">如需调整阅读方式，请在阅读器右上角「设置」中本地覆盖，仅影响您自己。</p>
    </div>

    <!-- 出版信息 · 用 label/value 键值列表,取代原一堆"作者:xxx" -->
    <div class="section" v-if="hasPubInfo">
      <h3 class="section-title">出版信息</h3>
      <dl class="kv">
        <template v-if="md?.publisher">
          <dt>出版社</dt><dd>{{ md.publisher }}</dd>
        </template>
        <template v-if="md?.pub_date">
          <dt>出版日期</dt><dd>{{ md.pub_date }}</dd>
        </template>
        <template v-if="md?.isbn">
          <dt>ISBN</dt><dd class="mono">{{ md.isbn }}</dd>
        </template>
        <template v-if="md?.rating">
          <dt>评分</dt><dd>{{ md.rating }}</dd>
        </template>
        <template v-if="md?.language">
          <dt>语言</dt><dd>{{ md.language }}</dd>
        </template>
      </dl>
    </div>

    <!-- 简介 -->
    <div v-if="md?.description" class="section">
      <h3 class="section-title">简介</h3>
      <p class="description" :class="{ collapsed: !descExpanded && descOverflowable }">{{ md.description }}</p>
      <button v-if="descOverflowable" class="expand-btn" @click="descExpanded = !descExpanded">
        {{ descExpanded ? '收起' : '展开全部' }}
      </button>
    </div>

    <!-- 文件信息 · 极简放最后,给需要的人用 -->
    <div class="section file-info">
      <h3 class="section-title">文件</h3>
      <div class="file-row">
        <span class="file-name">{{ book.file_name }}</span>
      </div>
      <div v-if="book.dir_path" class="file-path">{{ book.dir_path }}</div>
    </div>

    <!-- 刮削对话框 -->
    <el-dialog v-model="scrapeDialog" title="元数据管理" :width="dialogWidth" top="6vh" @close="onScrapeDialogClose">
      <el-tabs v-model="editTab">
        <el-tab-pane label="刮削搜索" name="scrape">
          <div class="scrape-head">
            <el-input v-model="scrapeKeyword" placeholder="搜索关键词" class="kw-input" />
            <el-select v-model="scrapeProvider" placeholder="自动(多源降级)" clearable class="provider-select">
              <el-option label="豆瓣" value="douban" />
              <el-option label="Google Books" value="google" />
              <el-option label="Open Library" value="openlibrary" />
            </el-select>
            <el-button type="primary" :loading="scraping" @click="runScrape">搜索</el-button>
          </div>

          <!-- 刮削过程日志:实时展示每一步;命中候选后自动折叠,可点击展开 -->
          <div v-if="scrapeSteps.length" class="scrape-trace" :class="{ collapsed: traceCollapsed }">
            <div class="trace-head" @click="traceCollapsed = !traceCollapsed">
              <span>
                <span class="trace-toggle">{{ traceCollapsed ? '▸' : '▾' }}</span>
                刮削过程
                <span v-if="scraping" class="trace-running">进行中…</span>
              </span>
              <span class="trace-summary">
                <template v-if="scrapeSearched">共 {{ candidates.length }} 个候选</template>
                <template v-else>{{ scrapeSteps.length }} 步</template>
              </span>
            </div>
            <div v-show="!traceCollapsed" class="trace-body">
              <div v-for="(s, i) in scrapeSteps" :key="i" class="trace-step" :class="`lv-${s.level}`">
                <span class="trace-icon">{{ stepIcon(s.level) }}</span>
                <span v-if="s.provider" class="trace-provider">{{ providerLabel(s.provider) }}</span>
                <span class="trace-msg">{{ s.message }}</span>
                <span v-if="s.elapsed_ms != null" class="trace-time">{{ s.elapsed_ms }}ms</span>
              </div>
            </div>
          </div>

          <div class="candidates">
            <div v-for="(c, i) in candidates" :key="i" class="candidate" @click="applyCandidate(c)">
              <CandidateCover :url="c.cover_url" />
              <div class="cand-info">
                <div class="cand-title">{{ c.title }} <el-tag size="small">{{ providerLabel(c.provider) }}</el-tag></div>
                <div class="cand-sub">{{ c.authors.join(', ') }} · {{ c.publisher || '' }} {{ c.pub_date || '' }}</div>
                <div class="cand-desc">{{ c.description }}</div>
              </div>
            </div>
            <el-empty v-if="scrapeSearched && !candidates.length" :description="emptyHint" />
          </div>
        </el-tab-pane>
        <el-tab-pane label="手动编辑" name="manual">
          <el-form label-width="80px">
            <el-form-item label="书名"><el-input v-model="manualForm.title" /></el-form-item>
            <el-form-item label="副标题"><el-input v-model="manualForm.subtitle" /></el-form-item>
            <el-form-item label="作者"><el-input v-model="manualForm.authors" placeholder="多个作者用逗号分隔" /></el-form-item>
            <el-form-item label="出版社"><el-input v-model="manualForm.publisher" /></el-form-item>
            <el-form-item label="出版日期"><el-input v-model="manualForm.pub_date" placeholder="如: 2023-01" /></el-form-item>
            <el-form-item label="ISBN"><el-input v-model="manualForm.isbn" /></el-form-item>
            <el-form-item label="标签"><el-input v-model="manualForm.tags" placeholder="多个标签用逗号分隔" /></el-form-item>
            <el-form-item label="简介"><el-input v-model="manualForm.description" type="textarea" :rows="6" /></el-form-item>
          </el-form>
          <div style="text-align: right; margin-top: 16px;">
            <el-button type="primary" :loading="scraping" @click="saveManualEdit">保存</el-button>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Reading } from '@element-plus/icons-vue'
import { booksApi, type BookDetail } from '@/api/books'
import { shelvesApi } from '@/api/shelves'
import { scrapeApi, scrapeStream, type Candidate, type ScrapeStep } from '@/api/admin'
import { useAuthStore } from '@/stores/auth'
import CoverImage from '@/components/CoverImage.vue'
import GeneratedCover from '@/components/GeneratedCover.vue'
import CandidateCover from '@/components/CandidateCover.vue'

const auth = useAuthStore()
const isAdmin = computed(() => auth.isAdmin)
const isMobile = ref(window.innerWidth < 700)

const route = useRoute()
const bookId = route.params.id as string

const book = ref<BookDetail | null>(null)
const md = computed(() => book.value?.metadata)
const title = computed(() => md.value?.title || book.value?.file_name || '')
const inShelf = ref(false)
const descExpanded = ref(false)
// 简介长度>240 才需要展开按钮;短简介直接完整显示,避免误增交互
const descOverflowable = computed(() => (md.value?.description || '').length > 240)
const progressPct = computed(() => book.value?.progress?.percent ?? 0)
const hasPubInfo = computed(
  () => !!(md.value?.publisher || md.value?.pub_date || md.value?.isbn || md.value?.rating || md.value?.language)
)
const doublePage = computed({
  get: () => book.value?.double_page ?? false,
  set: (v: boolean) => {
    if (book.value) book.value.double_page = v
  }
})
const startRight = computed({
  get: () => book.value?.start_right ?? false,
  set: (v: boolean) => {
    if (book.value) book.value.start_right = v
  }
})
async function saveComicSettings() {
  if (!book.value) return
  try {
    const { data } = await booksApi.updateComicSettings(bookId, {
      double_page: doublePage.value,
      start_right: startRight.value,
    })
    book.value = data
    ElMessage.success('漫画设置已保存')
  } catch (e) {
    ElMessage.error('保存失败')
  }
}

// 字数展示:万字级用"12.3"+"万字"标签,千级用整数+"字",无数据显示 —
const wordsMain = computed(() => {
  const n = book.value?.word_count
  if (!n) return '—'
  if (n >= 10000) return (n / 10000).toFixed(1)
  return String(n)
})
const wordsLabel = computed(() => {
  const n = book.value?.word_count
  if (!n) return '字数'
  return n >= 10000 ? '万字' : '字'
})

// 文件大小:MB 主体,KB 也自适应,不再把单位塞进"值"里
const sizeMain = computed(() => {
  const s = book.value?.file_size || 0
  if (s >= 1024 * 1024) return (s / 1024 / 1024).toFixed(1)
  return (s / 1024).toFixed(0)
})
const sizeLabel = computed(() => ((book.value?.file_size || 0) >= 1024 * 1024 ? 'MB' : 'KB'))

const scrapeDialog = ref(false)
const scrapeKeyword = ref('')
const scrapeProvider = ref<string | undefined>(undefined)
const candidates = ref<Candidate[]>([])
const scraping = ref(false)
const applying = ref(false)
const scrapeSteps = ref<ScrapeStep[]>([])
const traceCollapsed = ref(false)
// 流式刮削的取消函数(切换关键词/关闭弹窗时中断)
let cancelStream: (() => void) | null = null
// 弹窗宽度:移动端近乎占满屏幕,桌面固定 640px
const dialogWidth = computed(() => (window.innerWidth < 600 ? '94vw' : '640px'))
const scrapeSearched = ref(false)

// 手动编辑 tab
const editTab = ref('scrape')  // 'scrape' | 'manual'
const manualForm = reactive({
  title: '',
  subtitle: '',
  authors: '',
  publisher: '',
  pub_date: '',
  isbn: '',
  description: '',
  tags: '',
})

function openScrapeDialog() {
  scrapeDialog.value = true
  editTab.value = 'scrape'
  scrapeSteps.value = []
  candidates.value = []
  scrapeSearched.value = false
  traceCollapsed.value = false
  if (md.value) {
    manualForm.title = md.value.title || ''
    manualForm.subtitle = md.value.subtitle || ''
    manualForm.authors = (md.value.authors || []).join(', ')
    manualForm.publisher = md.value.publisher || ''
    manualForm.pub_date = md.value.pub_date || ''
    manualForm.isbn = md.value.isbn || ''
    manualForm.description = md.value.description || ''
    manualForm.tags = (md.value.tags || []).join(', ')
  }
}

async function saveManualEdit() {
  scraping.value = true
  try {
    const tags = manualForm.tags.split(/[,,]/).map((t) => t.trim()).filter(Boolean)
    const authors = manualForm.authors.split(/[,,]/).map((a) => a.trim()).filter(Boolean)
    await scrapeApi.updateMetadata(bookId, {
      title: manualForm.title || undefined,
      subtitle: manualForm.subtitle || undefined,
      authors: authors.length ? authors : undefined,
      publisher: manualForm.publisher || undefined,
      pub_date: manualForm.pub_date || undefined,
      isbn: manualForm.isbn || undefined,
      description: manualForm.description || undefined,
      tags: tags.length ? tags : undefined,
    })
    ElMessage.success('已保存')
    scrapeDialog.value = false
    await load()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    scraping.value = false
  }
}

async function load() {
  const { data } = await booksApi.detail(bookId)
  book.value = data
  scrapeKeyword.value = data.metadata?.title || data.file_name.replace(/\.[^.]+$/, '')
}

async function loadShelfState() {
  try {
    const { data } = await shelvesApi.myBooks()
    inShelf.value = data.some((b) => b.id === bookId)
  } catch {
    inShelf.value = false
  }
}

const PROVIDER_LABELS: Record<string, string> = {
  douban: '豆瓣读书',
  google: 'Google Books',
  openlibrary: 'Open Library',
  manual: '手动录入',
}
function providerLabel(p: string): string {
  return PROVIDER_LABELS[p] || p
}
function stepIcon(level: string): string {
  return { info: '·', success: '✓', warning: '!', error: '✕' }[level] || '·'
}
// 无结果时,依据过程日志给出更有针对性的提示
const emptyHint = computed(() => {
  const steps = scrapeSteps.value
  if (steps.some((s) => s.message.includes('反爬'))) {
    return '豆瓣疑似反爬拦截,建议配置 DOUBAN_COOKIE 或改用其他来源'
  }
  if (steps.some((s) => s.level === 'error' && s.message.includes('超时'))) {
    return '请求超时,可能网络无法访问该来源(如 Google 需外网)'
  }
  if (steps.some((s) => s.level === 'error')) {
    return '刮削过程出错,详见上方过程日志'
  }
  return '无匹配结果,可换关键词或来源重试'
})

function onScrapeDialogClose() {
  // 关闭弹窗时中断未结束的流式刮削
  if (cancelStream) {
    cancelStream()
    cancelStream = null
  }
  scraping.value = false
}

function runScrape() {
  // 取消上一次未结束的流
  if (cancelStream) cancelStream()
  scraping.value = true
  scrapeSteps.value = []
  candidates.value = []
  scrapeSearched.value = false
  traceCollapsed.value = false

  cancelStream = scrapeStream(scrapeKeyword.value, scrapeProvider.value, {
    onStep: (step) => {
      scrapeSteps.value.push(step)
    },
    onDone: (cands) => {
      candidates.value = cands
      scrapeSearched.value = true
      scraping.value = false
      cancelStream = null
      // 命中候选后自动折叠过程区,只突出结果;无结果则保留过程便于排查
      traceCollapsed.value = cands.length > 0
    },
    onError: (msg) => {
      scrapeSteps.value.push({ provider: '', level: 'error', message: msg })
      scrapeSearched.value = true
      scraping.value = false
      cancelStream = null
      ElMessage.error(msg)
    },
  })
}

async function applyCandidate(c: Candidate) {
  try {
    applying.value = true
    await scrapeApi.apply(bookId, c)
    ElMessage.success('已应用元数据')
    scrapeDialog.value = false
    await load()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '应用失败')
  } finally {
    applying.value = false
  }
}

async function toggleShelf() {
  try {
    if (inShelf.value) {
      await shelvesApi.removeBook(bookId)
      inShelf.value = false
      ElMessage.success('已从书架移除')
    } else {
      await shelvesApi.addBook(bookId)
      inShelf.value = true
      ElMessage.success('已收藏到书架')
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

onMounted(async () => {
  await load()
  await loadShelfState()
})
</script>

<style scoped>
.detail { max-width: 900px; margin: 0 auto; }

/* ---------- Hero:PC 横排,移动端纵向 ---------- */
.hero {
  display: flex;
  gap: 24px;
  background: var(--el-bg-color-overlay);
  border: 1px solid var(--el-border-color-lighter);
  padding: 24px;
  border-radius: 8px;
  /* stretch:让封面和信息列同高,视觉更整齐 */
  align-items: stretch;
}
.cover {
  width: 180px;
  flex-shrink: 0;
  aspect-ratio: 3/4;
  border-radius: 6px;
  overflow: hidden;
  background: #eef1f6;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  align-self: flex-start;
}
.cover :deep(img) { width: 100%; height: 100%; object-fit: cover; }
/* info 与 cover 等高对齐:min-height = width(180) * 4/3 = 240px,
   内容用 space-between 自然分布(标题在顶,CTA 在底),观感齐整 */
.info {
  flex: 1;
  min-width: 0;
  min-height: 240px;
  display: flex;
  flex-direction: column;
}
/* 内容与 CTA 之间用 margin-top:auto 弹性推 CTA 到底部 */
.info > .actions { margin-top: auto; }
.book-title {
  margin: 0 0 6px;
  font-size: 22px;
  line-height: 1.35;
  color: #1f2329;
  overflow-wrap: anywhere;
}
.subtitle { color: var(--el-text-color-secondary); margin: 0 0 8px; font-size: 14px; }
.author { color: var(--el-text-color-regular); margin: 0 0 12px; font-size: 14px; }
.tags { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 12px; }

/* 阅读进度:进度条 + 文字紧凑组合,始终占位避免抖动 */
.progress { display: flex; align-items: center; gap: 10px; margin: 6px 0 14px; }
.progress :deep(.el-progress) { flex: 1; }
.placeholder-progress {
  flex: 1;
  height: 6px;
  background: var(--el-fill-color);
  border-radius: 3px;
}
.progress-text { color: #67c23a; font-size: 12px; white-space: nowrap; }
.progress-text.text-muted { color: var(--el-text-color-secondary); }

/* CTA 两行结构:主按钮独占,次按钮 grid 均分,避免 flex-wrap 后不对齐;
   info 用 flex 列布局,.actions 由 .info > .actions { margin-top:auto } 推到底 */
.actions { display: flex; flex-direction: column; gap: 10px; }
.cta-primary { width: 100%; font-weight: 600; margin: 0; }
.cta-primary :deep(.el-icon) { margin-right: 4px; }
/* 次按钮 grid 均分,只有 1 个时也占满(1fr),2 个时平分 —— 天然对齐 */
.secondary-actions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(0, 1fr));
  gap: 10px;
}
.cta-icon { margin: 0; }
.cta-icon :deep(.el-icon) { margin-right: 4px; }

/* ---------- 指标卡片:4 格网格 ---------- */
.stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  background: var(--el-bg-color-overlay);
  border: 1px solid var(--el-border-color-lighter);
  padding: 16px;
  border-radius: 8px;
  margin-top: 12px;
}
.stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 12px 4px;
  border-radius: 6px;
  background: var(--el-fill-color-light);
  min-height: 68px;
}
.stat-value {
  font-size: 20px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  line-height: 1.2;
  overflow-wrap: anywhere;
  text-align: center;
}
.stat-label { font-size: 12px; color: var(--el-text-color-secondary); margin-top: 4px; }

/* ---------- 通用 section ---------- */
.section {
  background: var(--el-bg-color-overlay);
  border: 1px solid var(--el-border-color-lighter);
  padding: 20px 24px;
  border-radius: 8px;
  margin-top: 12px;
}
.section-title {
  margin: 0 0 12px;
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

/* 键值对列表:PC 双列,移动端单列;label 灰色右对齐(单列时左对齐) */
.kv {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 8px 20px;
  margin: 0;
  font-size: 14px;
}
.kv dt { color: var(--el-text-color-secondary); }
.kv dd { margin: 0; color: var(--el-text-color-primary); overflow-wrap: anywhere; }
.kv .mono { font-family: 'SF Mono', Menlo, Consolas, monospace; font-size: 13px; }

/* 简介:折叠状态最多 5 行,展开去限制 */
.description {
  color: var(--el-text-color-regular);
  line-height: 1.8;
  white-space: pre-wrap;
  margin: 0;
  overflow-wrap: anywhere;
}
.description.collapsed {
  display: -webkit-box;
  -webkit-line-clamp: 5;
  line-clamp: 5;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.expand-btn {
  background: none;
  border: none;
  padding: 8px 0 0;
  color: var(--el-color-primary);
  font-size: 13px;
  cursor: pointer;
}

/* 文件信息:轻量单元 */
.file-info .file-name { font-size: 14px; color: var(--el-text-color-primary); overflow-wrap: anywhere; }
.file-info .file-path { color: var(--el-text-color-secondary); font-size: 12px; margin-top: 4px; overflow-wrap: anywhere; }

/* 漫画设置 */
.comic-settings {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.setting-label {
  font-size: 14px;
  color: var(--el-text-color-primary);
}
.admin-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-left: 8px;
}
.comic-tip {
  margin-top: 12px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

/* ---------- 刮削对话框(基本沿用原样) ---------- */
.scrape-head { display: flex; gap: 10px; margin-bottom: 16px; }
.kw-input { flex: 1; min-width: 0; }
.provider-select { width: 160px; }
.scrape-trace {
  background: #f8f9fb;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 14px;
  max-height: 26vh;
  overflow-y: auto;
  font-size: 13px;
  line-height: 1.7;
}
.scrape-trace.collapsed { max-height: none; padding: 8px 12px; }
.trace-head {
  display: flex;
  justify-content: space-between;
  font-weight: 600;
  color: var(--el-text-color-regular);
  margin-bottom: 6px;
  cursor: pointer;
  user-select: none;
}
.scrape-trace.collapsed .trace-head { margin-bottom: 0; }
.trace-toggle { display: inline-block; width: 14px; color: var(--el-text-color-secondary); }
.trace-running { font-weight: 400; color: #409eff; margin-left: 6px; }
.trace-summary { font-weight: 400; color: var(--el-text-color-secondary); }
.trace-step {
  display: flex;
  align-items: baseline;
  gap: 6px;
  color: var(--el-text-color-regular);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
.trace-icon { width: 14px; text-align: center; flex-shrink: 0; }
.trace-provider {
  flex-shrink: 0;
  color: var(--el-text-color-secondary);
  background: #eef0f3;
  border-radius: 4px;
  padding: 0 5px;
  font-size: 12px;
}
.trace-msg { flex: 1; word-break: break-all; }
.trace-time { flex-shrink: 0; color: var(--el-text-color-placeholder); font-size: 12px; }
.lv-success { color: #67c23a; }
.lv-success .trace-icon { color: #67c23a; }
.lv-warning { color: #e6a23c; }
.lv-warning .trace-icon { color: #e6a23c; }
.lv-error { color: #f56c6c; }
.lv-error .trace-icon { color: #f56c6c; }
.candidates { max-height: 52vh; overflow-y: auto; }
.candidate { display: flex; gap: 12px; padding: 12px; border-radius: 8px; cursor: pointer; }
.candidate:hover { background: var(--el-fill-color-light); }
.cand-info { min-width: 0; flex: 1; }
.cand-title { font-weight: 600; overflow-wrap: anywhere; }
.cand-sub { font-size: 13px; color: var(--el-text-color-secondary); margin: 4px 0; overflow-wrap: anywhere; }
.cand-desc { font-size: 12px; color: #b0b3b8; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }

/* ---------- 移动端 ---------- */
@media (max-width: 700px) {
  .hero {
    padding: 16px;
    gap: 14px;
    /* 恢复 flex-start:移动端封面保持 3:4 原始比例,信息列自然向下延伸 */
    align-items: flex-start;
  }
  .cover {
    width: 96px;
    border-radius: 4px;
    /* 恢复 3:4 比例(96*4/3=128px),不再随 info 拉伸,避免视觉难看 */
    aspect-ratio: 3/4;
    min-height: auto;
    align-self: flex-start;
  }
  /* 移动端 info 不再强撑,由内容决定高度 */
  .info { min-height: 0; }
  .book-title { font-size: 17px; margin-bottom: 4px; }
  .subtitle { font-size: 12px; margin-bottom: 4px; }
  .author { font-size: 13px; margin-bottom: 8px; }
  .tags { margin-bottom: 8px; }
  .progress { margin: 4px 0 10px; }
  /* 移动端 CTA 改横向一排:主按钮 + 2 个次按钮平铺
     .secondary-actions display:contents 让子按钮成为 .actions 的直接 flex 项,天然对齐 */
  .info > .actions { margin-top: 4px; }
  .actions {
    flex-direction: row;
    gap: 8px;
  }
  .cta-primary {
    flex: 1.6;
    min-width: 0;
    padding: 0 8px;
  }
  .secondary-actions {
    display: contents;
  }
  .cta-icon {
    flex: 1;
    min-width: 0;
    padding: 0 6px;
  }
  .cta-primary :deep(span),
  .cta-icon :deep(span) { font-size: 13px; }

  /* 指标卡:小屏收紧 padding,数字略缩;仍保持 4 格 */
  .stats { padding: 12px; gap: 6px; }
  .stat { padding: 10px 2px; min-height: 62px; }
  .stat-value { font-size: 17px; }
  .stat-label { font-size: 11px; }

  .section { padding: 16px; }
  .section-title { font-size: 15px; margin-bottom: 10px; }

  /* 键值对:移动端切单列,dt/dd 上下堆叠观感清爽 */
  .kv { grid-template-columns: 1fr; gap: 4px 0; }
  .kv dt { margin-top: 8px; font-size: 12px; }
  .kv dt:first-child { margin-top: 0; }

  .scrape-head { flex-direction: column; }
  .provider-select { width: 100%; }
}

/* 极窄屏(<360px):指标卡改 2×2 */
@media (max-width: 360px) {
  .stats { grid-template-columns: repeat(2, 1fr); }
}
</style>
