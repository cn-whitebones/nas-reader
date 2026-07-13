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
import { ref } from 'vue'
import BookGrid from '@/components/BookGrid.vue'
import { searchApi, type BookBrief } from '@/api/books'

const keyword = ref('')
const books = ref<BookBrief[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(24)
const searched = ref(false)

async function doSearch() {
  if (!keyword.value.trim()) return
  const { data } = await searchApi.search(keyword.value.trim(), { page: page.value, size: size.value })
  books.value = data.items
  total.value = data.total
  searched.value = true
}

function onPage(p: number) {
  page.value = p
  doSearch()
}
</script>

<style scoped>
.search-page { max-width: 900px; margin: 0 auto; }
.search-bar { margin-bottom: 20px; }
.result-info { color: #909399; font-size: 13px; margin-bottom: 12px; }
.pager { margin-top: 20px; justify-content: center; }
</style>
