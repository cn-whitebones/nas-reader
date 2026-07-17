<template>
  <div class="shelves-page">
    <!-- 顶部标题行:书架名 + 收藏总数(shelf.book_count 是权威值,搜索时不变) -->
    <div class="header">
      <h2 class="shelf-title">{{ shelf?.name || '我的收藏' }}</h2>
      <span class="count">{{ shelf?.book_count ?? 0 }} 本</span>
    </div>

    <!-- 工具栏:搜索 + 排序;移动端把排序图标化,布局与书库一致 -->
    <div class="toolbar">
      <el-input
        v-model="keyword"
        class="search-input"
        :placeholder="isMobile ? '搜索收藏' : '搜索书名/作者/文件名'"
        clearable
        :prefix-icon="Search"
        @keyup.enter="onSearchSubmit"
        @clear="onSearchSubmit"
      />
      <el-select v-model="sort" @change="onSortChange" style="width: 130px">
        <el-option v-for="s in SORTS" :key="s.value" :label="s.label" :value="s.value" />
      </el-select>
      <el-button :icon="order === 'asc' ? SortUp : SortDown" @click="toggleOrder"
        :title="order === 'asc' ? '升序' : '降序'" />
    </div>

    <BookGrid v-if="books.length" :books="books" />
    <!-- 空态区分:书架空 vs 搜索无结果,措辞不同 -->
    <el-empty
      v-else-if="!loading"
      :description="hasQuery ? '没有匹配的收藏' : '书架还是空的,去书库收藏喜欢的书吧'"
    />

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
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { Search, SortDown, SortUp } from '@element-plus/icons-vue'
import BookGrid from '@/components/BookGrid.vue'
import { shelvesApi, type Shelf } from '@/api/shelves'
import type { BookBrief } from '@/api/books'

// 书架排序键与书库一致,再加"收藏时间"作为默认(最近收藏排前)
const SORTS = [
  { label: '收藏时间', value: 'shelf_added' },
  { label: '名称', value: 'title' },
  { label: '作者', value: 'author' },
  { label: '字数', value: 'words' },
  { label: '章节数', value: 'chapters' },
]

const shelf = ref<Shelf | null>(null)
const books = ref<BookBrief[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(24)
const keyword = ref('')
// 默认按"收藏时间倒序":最近加入的书排最前,和常规使用直觉一致
const sort = ref('shelf_added')
const order = ref<'asc' | 'desc'>('desc')
const loading = ref(true)

const hasQuery = computed(() => keyword.value.trim().length > 0)

const isMobile = ref(window.innerWidth <= 700)
function onResize() {
  isMobile.value = window.innerWidth <= 700
}

async function reload() {
  loading.value = true
  try {
    const { data } = await shelvesApi.myBooksPaged({
      page: page.value,
      size: size.value,
      q: keyword.value.trim() || undefined,
      sort: sort.value,
      order: order.value,
    })
    books.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function loadShelfMeta() {
  const { data } = await shelvesApi.my()
  shelf.value = data
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
function onPage(p: number) {
  page.value = p
  reload()
}

onMounted(async () => {
  window.addEventListener('resize', onResize)
  await Promise.all([loadShelfMeta(), reload()])
})
onBeforeUnmount(() => window.removeEventListener('resize', onResize))
</script>

<style scoped>
.shelves-page { padding-bottom: 40px; }
.header { display: flex; align-items: baseline; gap: 10px; margin-bottom: 12px; }
.shelf-title { margin: 0; font-size: 20px; }
.count { color: #909399; font-size: 14px; }
/* 工具栏:PC 内联搜索+排序;移动端搜索框 flex:1,自动收紧 */
.toolbar { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; }
.search-input { width: 260px; }
.pager { margin-top: 20px; justify-content: center; }

@media (max-width: 700px) {
  .toolbar { flex-wrap: nowrap; gap: 6px; }
  .search-input { width: auto; flex: 1; min-width: 0; }
}
</style>
