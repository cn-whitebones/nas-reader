<template>
  <div class="book-list">
    <div v-for="b in books" :key="b.id" class="book-item" @click="$router.push(`/books/${b.id}`)">
      <div class="cover-wrap">
        <CoverImage v-if="b.has_cover" :book-id="b.id" :alt="b.file_name" :version="b.cover_version" />
        <GeneratedCover v-else :title="b.title || b.file_name" :format="b.format" compact />
      </div>
      <div class="book-info">
        <div class="book-title">{{ b.title || b.file_name }}</div>
        <div class="book-meta">
          <span v-if="b.authors?.length">{{ b.authors.join(', ') }}</span>
          <span>{{ b.format.toUpperCase() }}</span>
        </div>
        <div class="book-meta secondary">
          <span>{{ b.chapter_count }} 章</span>
          <span v-if="b.word_count">{{ formatWords(b.word_count) }}</span>
          <span v-if="b.status === 'missing'" class="missing">文件缺失</span>
        </div>
      </div>
    </div>
  </div>
  <el-empty v-if="!books.length" description="暂无图书" />
</template>

<script setup lang="ts">
import CoverImage from './CoverImage.vue'
import GeneratedCover from './GeneratedCover.vue'
import type { BookBrief } from '@/api/books'
import { formatWords } from '@/utils/format'

defineProps<{ books: BookBrief[] }>()
</script>

<style scoped>
.book-list {
  display: flex;
  flex-direction: column;
  gap: 1px;
  background: var(--el-border-color-lighter);
  border-radius: 8px;
  overflow: hidden;
}
.book-item {
  display: flex;
  gap: 12px;
  padding: 12px;
  background: var(--el-bg-color-overlay);
  cursor: pointer;
  transition: background 0.2s;
}
/* 仅桌面鼠标悬停高亮;触摸屏 tap 后 hover 会被粘住 */
@media (hover: hover) {
  .book-item:hover {
    background: var(--el-fill-color-light);
  }
}
.cover-wrap {
  width: 50px;
  height: 70px;
  flex-shrink: 0;
  border-radius: 4px;
  overflow: hidden;
  background: var(--el-fill-color);
}
.cover-wrap img {
  width: 100%;
  height: 100%;
  object-fit: cover;
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
  color: var(--el-text-color-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.book-meta {
  font-size: 12px;
  color: var(--el-text-color-regular);
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}
.book-meta.secondary {
  color: var(--el-text-color-secondary);
}
.book-meta .missing {
  color: #f56c6c;
}

@media (max-width: 600px) {
  .book-meta { gap: 8px; }
}
</style>
