<template>
  <div class="grid">
    <BookCard v-for="b in books" :key="b.id" :book="b" />
  </div>
  <el-empty v-if="!books.length" description="暂无图书" />
</template>

<script setup lang="ts">
import BookCard from './BookCard.vue'
import type { BookBrief } from '@/api/books'

defineProps<{ books: BookBrief[] }>()
</script>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 16px;
}
@media (max-width: 600px) {
  .grid { grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 10px; }
}
</style>
