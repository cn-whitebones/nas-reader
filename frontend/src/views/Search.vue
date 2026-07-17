<template>
  <div class="search-page">
    <div class="search-bar">
      <el-input
        v-model="keyword"
        placeholder="搜索书名、作者、文件名、标签…"
        clearable
        size="large"
        @keyup.enter="doSearch"
      >
        <template #append>
          <el-button @click="doSearch">搜索</el-button>
        </template>
      </el-input>
    </div>

    <div v-if="searched" class="result-info">找到 {{ total }} 条结果</div>
    <BookGrid :books="books" />

    <el-pagination
      v-if="total > size"
      class="pager"
      layout="prev, pager, next"
      :total="total"
      :page-size="size"
      :current-page="page"
      @current-change="onPage"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import BookGrid from '@/components/BookGrid.vue'
import { searchApi, type BookBrief } from '@/api/books'

const route = useRoute()
const router = useRouter()

const keyword = ref('')
const books = ref<BookBrief[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(24)
const searched = ref(false)

// 把查询条件写回 URL,右滑返回/刷新后可复现搜索结果
function syncQuery() {
  const q: Record<string, string> = { q: keyword.value.trim() }
  if (page.value > 1) q.page = String(page.value)
  router.replace({ query: q })
}

async function runQuery() {
  const kw = keyword.value.trim()
  if (!kw) return
  const { data } = await searchApi.search(kw, { page: page.value, size: size.value })
  books.value = data.items
  total.value = data.total
  searched.value = true
}

// 用户点击「搜索」或回车:重置到第一页
function doSearch() {
  if (!keyword.value.trim()) return
  page.value = 1
  syncQuery()
  runQuery()
}

function onPage(p: number) {
  page.value = p
  syncQuery()
  runQuery()
}

onMounted(() => {
  const q = route.query
  if (typeof q.q === 'string' && q.q.trim()) {
    keyword.value = q.q
    page.value = Math.max(1, Number(q.page) || 1)
    runQuery()
  }
})
</script>

<style scoped>
.search-page { max-width: 900px; margin: 0 auto; }
.search-bar { margin-bottom: 20px; }
.result-info { color: #909399; font-size: 13px; margin-bottom: 12px; }
.pager { margin-top: 20px; justify-content: center; }
</style>
