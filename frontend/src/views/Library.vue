<template>
  <div class="library">
    <!-- 移动端侧栏遮罩:点击外部区域收起 -->
    <div v-if="mobileTreeOpen && isMobile" class="sidebar-mask" @click="mobileTreeOpen = false"></div>

    <!-- 左侧目录树 -->
    <aside class="sidebar" :class="{ open: mobileTreeOpen }">
      <div class="sidebar-head">
        <span>目录</span>
        <el-button link @click="mobileTreeOpen = false" class="close-tree">收起</el-button>
      </div>
      <!-- 全部图书入口:清空目录/源筛选,回到全部 -->
      <div
        class="all-books"
        :class="{ active: !curDir && !curSource }"
        @click="onSelectAll"
      >
        <el-icon><Files /></el-icon>
        <span>全部图书</span>
        <span class="cnt">({{ allBooksCount }})</span>
      </div>
      <el-tree
        ref="treeRef"
        :data="treeData"
        :props="{ label: 'name', children: 'children' }"
        node-key="key"
        @node-click="onNodeClick"
        highlight-current
      >
        <template #default="{ data }">
          <span>{{ data.name }} <span class="cnt">({{ data.book_count }})</span></span>
        </template>
      </el-tree>
    </aside>

    <!-- 右侧图书 -->
    <section class="content">
      <!-- 工具栏 -->
      <div class="toolbar">
        <!-- 目录:PC 隐藏(左侧固定树),移动端图标按钮 -->
        <el-button class="tree-toggle" :icon="Menu" @click="mobileTreeOpen = true" circle title="目录" />

        <!-- PC:内联筛选与排序 -->
        <template v-if="!isMobile">
          <el-input
            v-model="keyword"
            class="search-input"
            placeholder="搜索书名/作者/文件名/标签"
            clearable
            :prefix-icon="Search"
            @keyup.enter="onSearchSubmit"
            @clear="onSearchSubmit"
          />
          <el-select v-model="formatFilter" placeholder="全部格式" clearable @change="onFilterChange" style="width: 130px">
            <el-option v-for="f in FORMATS" :key="f.value" :label="f.label" :value="f.value" />
          </el-select>
          <el-select v-model="sort" @change="onSortChange" style="width: 130px">
            <el-option v-for="s in SORTS" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
          <el-button :icon="order === 'asc' ? SortUp : SortDown" @click="toggleOrder" :title="order === 'asc' ? '升序' : '降序'" />
          <el-badge :is-dot="hasAdvancedFilter" class="filter-badge">
            <el-button :icon="Filter" @click="filterPanel = true">筛选</el-button>
          </el-badge>
          <span class="path">{{ curDir || '全部' }} · {{ total }} 本</span>
        </template>

        <!-- 移动端:强制单行,搜索框 flex:1,其它全部图标化 -->
        <template v-else>
          <el-input
            v-model="keyword"
            class="search-input-m"
            placeholder="搜索"
            clearable
            :prefix-icon="Search"
            @keyup.enter="onSearchSubmit"
            @clear="onSearchSubmit"
          />
          <el-badge :is-dot="hasAdvancedFilter || !!formatFilter" class="filter-badge">
            <el-button :icon="Operation" @click="filterPanel = true" circle title="筛选/排序" />
          </el-badge>
        </template>

        <span class="spacer"></span>
        <el-radio-group v-model="viewMode" size="small">
          <el-radio-button value="grid"><el-icon><Grid /></el-icon></el-radio-button>
          <el-radio-button value="list"><el-icon><List /></el-icon></el-radio-button>
        </el-radio-group>
      </div>

      <!-- 移动端状态行:上工具栏留给操作,总数/当前目录单独一行,避免挤 -->
      <div v-if="isMobile" class="status-m">{{ curDir || '全部' }} · {{ total }} 本</div>

      <BookGrid v-if="viewMode === 'grid'" :books="books" />
      <BookList v-else :books="books" />

      <el-pagination
        v-if="total > size"
        class="pager"
        :layout="isMobile ? 'prev, pager, next' : 'prev, pager, next, jumper'"
        :pager-count="isMobile ? 5 : 7"
        :total="total"
        :page-size="size"
        :current-page="page"
        @current-change="onPage"
      />
    </section>

    <!-- 筛选/排序面板:PC 为 Drawer(右侧),移动端为底部 Drawer -->
    <el-drawer
      v-model="filterPanel"
      :title="isMobile ? '筛选与排序' : '高级筛选'"
      :direction="isMobile ? 'btt' : 'rtl'"
      :size="isMobile ? '75%' : 340"
    >
      <div class="filter-body">
        <!-- 移动端把格式/排序也放进来 -->
        <template v-if="isMobile">
          <div class="fld">
            <label>格式</label>
            <el-select v-model="formatFilter" placeholder="全部格式" clearable style="width: 100%" @change="onFilterChange">
              <el-option v-for="f in FORMATS" :key="f.value" :label="f.label" :value="f.value" />
            </el-select>
          </div>
          <div class="fld">
            <label>排序方式</label>
            <div class="sort-row">
              <el-select v-model="sort" style="flex: 1" @change="onSortChange">
                <el-option v-for="s in SORTS" :key="s.value" :label="s.label" :value="s.value" />
              </el-select>
              <el-button :icon="order === 'asc' ? SortUp : SortDown" @click="toggleOrder">
                {{ order === 'asc' ? '升序' : '降序' }}
              </el-button>
            </div>
          </div>
        </template>

        <div class="fld">
          <label>章节数</label>
          <el-radio-group v-model="chapterRange" class="range-tags" @change="onFilterChange">
            <el-radio-button v-for="r in CHAPTER_RANGES" :key="r.value" :value="r.value">{{ r.label }}</el-radio-button>
          </el-radio-group>
        </div>

        <div class="fld">
          <label>字数</label>
          <el-radio-group v-model="wordRange" class="range-tags" @change="onFilterChange">
            <el-radio-button v-for="r in WORD_RANGES" :key="r.value" :value="r.value">{{ r.label }}</el-radio-button>
          </el-radio-group>
          <div class="hint">PDF / 漫画无字数统计,设置字数范围会将其排除</div>
        </div>

        <div class="fld">
          <label>封面</label>
          <el-radio-group v-model="coverFilter" @change="onFilterChange">
            <el-radio-button :value="undefined">全部</el-radio-button>
            <el-radio-button :value="true">有封面</el-radio-button>
            <el-radio-button :value="false">无封面</el-radio-button>
          </el-radio-group>
        </div>
      </div>

      <template #footer>
        <el-button @click="resetFilters">重置</el-button>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { Grid, List, Filter, Operation, SortUp, SortDown, Files, Search, Menu } from '@element-plus/icons-vue'
import BookGrid from '@/components/BookGrid.vue'
import BookList from '@/components/BookList.vue'
import { booksApi, type BookBrief, type TreeNode } from '@/api/books'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const FORMATS = [
  { label: 'TXT', value: 'txt' },
  { label: 'EPUB', value: 'epub' },
  { label: 'PDF', value: 'pdf' },
  { label: 'MOBI', value: 'mobi' },
  { label: '漫画', value: 'comic' },
]
const SORTS = [
  { label: '名称', value: 'title' },
  { label: '作者', value: 'author' },
  { label: '字数', value: 'words' },
  { label: '章节数', value: 'chapters' },
  { label: '添加时间', value: 'added' },
  { label: '文件大小', value: 'size' },
]

// 章节数/字数常用区间快选:value 作标识,min/max 为查询边界(null=开区间)
// 字数单位为「万字」,传后端时再 ×10000;控制在 4 档,抽屉内一行等宽平铺不换行
const CHAPTER_RANGES: { label: string; value: string; min: number | null; max: number | null }[] = [
  { label: '不限', value: '', min: null, max: null },
  { label: '<100', value: '0-100', min: null, max: 100 },
  { label: '100-1000', value: '100-1000', min: 100, max: 1000 },
  { label: '>1000', value: '1000-', min: 1000, max: null },
]
const WORD_RANGES: { label: string; value: string; min: number | null; max: number | null }[] = [
  { label: '不限', value: '', min: null, max: null },
  { label: '<10万', value: '0-10', min: null, max: 10 },
  { label: '10-100万', value: '10-100', min: 10, max: 100 },
  { label: '>100万', value: '100-', min: 100, max: null },
]

const treeData = ref<any[]>([])
const treeRef = ref<any>(null)
const books = ref<BookBrief[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(24)
const curDir = ref<string | undefined>(undefined)
const curSource = ref<string | undefined>(undefined)
const formatFilter = ref<string | undefined>(undefined)
const keyword = ref('')
const sort = ref('title')
const order = ref<'asc' | 'desc'>('asc')
const chapterRange = ref('') // 选中的章节区间 value
const wordRange = ref('') // 选中的字数区间 value(单位:万字)
const coverFilter = ref<boolean | undefined>(undefined)
const mobileTreeOpen = ref(false)
const filterPanel = ref(false)

const viewMode = ref<'grid' | 'list'>(
  (localStorage.getItem('library_view_mode') as 'grid' | 'list') || 'grid'
)

// 响应式判断移动端
const isMobile = ref(window.innerWidth <= 700)
function onResize() {
  isMobile.value = window.innerWidth <= 700
  // 桌面态强制关闭移动端抽屉,避免残留 mask
  if (!isMobile.value) mobileTreeOpen.value = false
}

const hasAdvancedFilter = computed(
  () => chapterRange.value !== '' || wordRange.value !== '' || coverFilter.value !== undefined
)

// 由区间 value 取 min/max 边界
function chapterBounds() {
  return CHAPTER_RANGES.find((r) => r.value === chapterRange.value) ?? CHAPTER_RANGES[0]
}
function wordBounds() {
  return WORD_RANGES.find((r) => r.value === wordRange.value) ?? WORD_RANGES[0]
}
// 由 min/max 反查区间 value(URL 恢复用)
function matchRange(
  ranges: { value: string; min: number | null; max: number | null }[],
  min: number | null,
  max: number | null
) {
  return ranges.find((r) => r.min === min && r.max === max)?.value ?? ''
}

// 顶层节点 book_count 求和 = 全部图书数(和后端 tree 一致)
const allBooksCount = computed(() =>
  treeData.value.reduce((s, n: any) => s + (n.book_count || 0), 0)
)

function decorate(nodes: TreeNode[]): any[] {
  return nodes.map((n) => ({
    ...n,
    key: `${n.source_id}:${n.path}`,
    children: n.children ? decorate(n.children) : [],
  }))
}

async function loadTree() {
  const { data } = await booksApi.tree()
  treeData.value = decorate(data)
}

// URL query 恢复:右滑返回/刷新/分享后保留浏览状态
function restoreFromQuery() {
  const q = route.query
  page.value = Math.max(1, Number(q.page) || 1)
  curDir.value = typeof q.dir === 'string' ? q.dir : undefined
  curSource.value = typeof q.source === 'string' ? q.source : undefined
  formatFilter.value = typeof q.format === 'string' ? q.format : undefined
  keyword.value = typeof q.q === 'string' ? q.q : ''
  if (typeof q.sort === 'string') sort.value = q.sort
  if (q.order === 'asc' || q.order === 'desc') order.value = q.order
  const cmin = q.cmin != null ? Number(q.cmin) : null
  const cmax = q.cmax != null ? Number(q.cmax) : null
  chapterRange.value = matchRange(CHAPTER_RANGES, cmin, cmax)
  const wmin = q.wmin != null ? Number(q.wmin) : null
  const wmax = q.wmax != null ? Number(q.wmax) : null
  wordRange.value = matchRange(WORD_RANGES, wmin, wmax)
  if (q.cover === 'true') coverFilter.value = true
  else if (q.cover === 'false') coverFilter.value = false
}

function syncQuery() {
  const q: Record<string, string> = {}
  if (page.value > 1) q.page = String(page.value)
  if (curDir.value) q.dir = curDir.value
  if (curSource.value) q.source = curSource.value
  if (formatFilter.value) q.format = formatFilter.value
  if (keyword.value.trim()) q.q = keyword.value.trim()
  if (sort.value !== 'title') q.sort = sort.value
  if (order.value !== 'asc') q.order = order.value
  const cb = chapterBounds()
  if (cb.min != null) q.cmin = String(cb.min)
  if (cb.max != null) q.cmax = String(cb.max)
  const wb = wordBounds()
  if (wb.min != null) q.wmin = String(wb.min)
  if (wb.max != null) q.wmax = String(wb.max)
  if (coverFilter.value !== undefined) q.cover = String(coverFilter.value)
  router.replace({ query: q })
}

async function reload() {
  syncQuery()
  const wan = 10000
  const cb = chapterBounds()
  const wb = wordBounds()
  const { data } = await booksApi.list({
    page: page.value,
    size: size.value,
    dir_path: curDir.value,
    source_id: curSource.value,
    format: formatFilter.value,
    q: keyword.value.trim() || undefined,
    sort: sort.value,
    order: order.value,
    chapter_min: cb.min ?? undefined,
    chapter_max: cb.max ?? undefined,
    word_min: wb.min != null ? wb.min * wan : undefined,
    word_max: wb.max != null ? wb.max * wan : undefined,
    has_cover: coverFilter.value,
  })
  books.value = data.items
  total.value = data.total
}

function onNodeClick(node: any) {
  curSource.value = node.source_id
  curDir.value = node.path
  page.value = 1
  mobileTreeOpen.value = false
  reload()
}

// 点击"全部图书":清空目录/源筛选,清除 el-tree 当前高亮
function onSelectAll() {
  curSource.value = undefined
  curDir.value = undefined
  page.value = 1
  mobileTreeOpen.value = false
  nextTick(() => treeRef.value?.setCurrentKey?.(null))
  reload()
}

function onPage(p: number) {
  page.value = p
  reload()
}

function onFilterChange() {
  page.value = 1
  reload()
}

function onSearchSubmit() {
  page.value = 1
  reload()
}

function onSortChange() {
  page.value = 1
  reload()
}

function toggleOrder() {
  order.value = order.value === 'asc' ? 'desc' : 'asc'
  page.value = 1
  reload()
}

function resetFilters() {
  chapterRange.value = ''
  wordRange.value = ''
  coverFilter.value = undefined
  if (isMobile.value) {
    formatFilter.value = undefined
    sort.value = 'title'
    order.value = 'asc'
  }
  page.value = 1
  reload()
}

onMounted(async () => {
  window.addEventListener('resize', onResize)
  restoreFromQuery()
  await Promise.all([loadTree(), reload()])
})
onBeforeUnmount(() => window.removeEventListener('resize', onResize))
</script>

<style scoped>
.library { display: flex; gap: 16px; height: 100%; }
.sidebar-mask {
  display: none; position: fixed; inset: 0; background: rgba(0, 0, 0, 0.4);
  z-index: 99;
}
.sidebar { width: 260px; flex-shrink: 0; background: var(--el-bg-color-overlay); border: 1px solid var(--el-border-color-lighter); border-radius: 8px; padding: 12px; overflow-y: auto; }
.sidebar-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; font-weight: 600; }
.close-tree { display: none; }
/* 全部图书入口:替代过去无法退出目录筛选的问题 */
.all-books {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 8px; margin-bottom: 6px;
  cursor: pointer; border-radius: 4px; font-size: 14px; color: var(--el-text-color-primary);
  transition: background 0.15s;
}
.all-books:hover { background: var(--el-fill-color-light); }
.all-books.active { background: var(--el-color-primary-light-9); color: var(--el-color-primary); }
.all-books .cnt { margin-left: auto; }
.cnt { color: #c0c4cc; font-size: 12px; }
.content { flex: 1; min-width: 0; overflow-y: auto; padding-bottom: 40px; }
.toolbar { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; }
.tree-toggle { display: none; }
/* PC 搜索框:占据工具栏左侧,给筛选/排序留位置 */
.search-input { width: 260px; }
/* 移动端搜索框:紧凑,让筛选按钮同排显示 */
.search-input-m { flex: 1; min-width: 0; }
/* 移动端状态行:目录路径 + 总数,和工具栏分行,与工具栏留白避免紧贴 */
.status-m { display: none; color: #909399; font-size: 12px; margin: 4px 0 14px; }
.path { color: #909399; font-size: 13px; }
.spacer { flex: 1; }
.pager { margin-top: 20px; justify-content: center; }
.filter-badge :deep(.el-badge__content.is-dot) { top: 4px; right: 8px; }

/* 筛选面板内部 */
.filter-body { display: flex; flex-direction: column; gap: 20px; }
.fld { display: flex; flex-direction: column; gap: 8px; }
.fld > label { font-size: 13px; font-weight: 600; color: #303133; }
/* 区间快选:4 档等宽平铺占满一行,不换行;按钮圆角、文字居中 */
.range-tags { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; width: 100%; }
.range-tags :deep(.el-radio-button) { margin: 0; }
.range-tags :deep(.el-radio-button__inner) {
  width: 100%;
  border-radius: 4px;
  border-left: 1px solid var(--el-border-color);
  padding-left: 0;
  padding-right: 0;
  text-align: center;
}
.sort-row { display: flex; gap: 8px; }
.hint { font-size: 12px; color: #a0a4ac; }

@media (max-width: 700px) {
  /* sidebar 和 mask 从 header 下方开始:不覆盖 iOS 状态栏(safe-area-inset-top),
     避免 PWA 状态栏被 mask 染灰后无法即时复位、看起来"关闭后颜色不一致" */
  .sidebar-mask { display: block; top: calc(56px + env(safe-area-inset-top)); }
  .sidebar {
    position: fixed; left: 0; top: calc(56px + env(safe-area-inset-top)); bottom: 0; z-index: 100;
    transform: translateX(-100%); transition: transform 0.2s; box-shadow: 2px 0 12px rgba(0, 0, 0, 0.2);
  }
  .sidebar.open { transform: translateX(0); }
  .close-tree, .tree-toggle { display: inline-flex; }
  /* 工具栏强制单行:目录/筛选/视图切换全用图标,搜索框 flex 占中间;
     禁用 wrap,gap 收紧,让 320px 窄屏也不会挤到换行 */
  .toolbar { flex-wrap: nowrap; gap: 6px; margin-bottom: 8px; }
  .status-m { display: block; }
}
/* Layout header 在 @media (max-width:600px) 里从 56 变 44,同步调整 */
@media (max-width: 600px) {
  .sidebar-mask { top: calc(44px + env(safe-area-inset-top)); }
  .sidebar { top: calc(44px + env(safe-area-inset-top)); }
}
</style>
