<template>
  <div class="shelves-page">
    <div class="toolbar">
      <h2 class="shelf-title">{{ shelf?.name || '我的收藏' }}</h2>
      <span class="count">{{ books.length }} 本</span>
    </div>

    <BookGrid :books="books" />
    <el-empty v-if="!books.length" description="书架还是空的,去书库收藏喜欢的书吧" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import BookGrid from '@/components/BookGrid.vue'
import { shelvesApi, type Shelf } from '@/api/shelves'
import type { BookBrief } from '@/api/books'

const shelf = ref<Shelf | null>(null)
const books = ref<BookBrief[]>([])

async function load() {
  const [{ data: sh }, { data: bs }] = await Promise.all([shelvesApi.my(), shelvesApi.myBooks()])
  shelf.value = sh
  books.value = bs
}

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; align-items: baseline; gap: 10px; margin-bottom: 16px; }
.shelf-title { margin: 0; font-size: 20px; }
.count { color: #909399; font-size: 14px; }
</style>
