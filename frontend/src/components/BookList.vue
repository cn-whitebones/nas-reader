<template>
  <div class="book-list">
    <div v-for="b in books" :key="b.id" class="book-item" @click="$router.push(`/books/${b.id}`)">
      <div class="cover-wrap">
        <CoverImage v-if="b.has_cover" :book-id="b.id" :alt="b.file_name" />
        <div v-else class="no-cover">{{ b.format.toUpperCase() }}</div>
      </div>
      <div class="book-info">
        <div class="book-title">{{ b.title || b.file_name }}</div>
        <div class="book-meta">
          <span v-if="b.authors?.length">{{ b.authors.join(', ') }}</span>
          <span>{{ b.format.toUpperCase() }}</span>
        </div>
        <div class="book-meta secondary">
          <span>{{ b.chapter_count }} 章</span>
          <span v-if="b.status === 'missing'" class="missing">文件缺失</span>
        </div>
      </div>
    </div>
  </div>
  <el-empty v-if="!books.length" description="暂无图书" />
</template>

<script setup lang="ts">
import CoverImage from './CoverImage.vue'
import type { BookBrief } from '@/api/books'

defineProps<{ books: BookBrief[] }>()
</script>

<style scoped>
.book-list {
  display: flex;
  flex-direction: column;
  gap: 1px;
  background: #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
}
.book-item {
  display: flex;
  gap: 12px;
  padding: 12px;
  background: #fff;
  cursor: pointer;
  transition: background 0.2s;
}
.book-item:hover {
  background: #f5f7fa;
}
.cover-wrap {
  width: 50px;
  height: 70px;
  flex-shrink: 0;
  border-radius: 4px;
  overflow: hidden;
  background: #e4e7ed;
}
.cover-wrap img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.no-cover {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #909399;
  font-size: 12px;
  font-weight: 600;
}
.book-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-evenly;
}
.book-title {
  font-weight: 600;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.book-meta {
  font-size: 12px;
  color: #606266;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}
.book-meta.secondary {
  color: #909399;
}
.book-meta .missing {
  color: #f56c6c;
}

@media (max-width: 600px) {
  .book-meta { gap: 8px; }
}
</style>
