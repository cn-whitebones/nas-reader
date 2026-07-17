<template>
  <div class="book-card" @click="$router.push(`/books/${book.id}`)">
    <div class="cover">
      <CoverImage v-if="book.has_cover" :book-id="book.id" :alt="displayTitle" />
      <GeneratedCover v-else :title="displayTitle" :format="book.format" />
      <span v-if="book.has_cover" class="badge">{{ book.format.toUpperCase() }}</span>
    </div>
    <div class="meta">
      <div class="title" :title="displayTitle">{{ displayTitle }}</div>
      <div class="author">{{ book.authors.join(', ') || '—' }}</div>
      <div class="sub">
        <span class="chip">{{ book.chapter_count }} 章</span>
        <span v-if="book.word_count" class="chip">{{ formatWords(book.word_count) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { type BookBrief } from '@/api/books'
import { formatWords } from '@/utils/format'
import CoverImage from './CoverImage.vue'
import GeneratedCover from './GeneratedCover.vue'

const props = defineProps<{ book: BookBrief }>()
const displayTitle = computed(() => props.book.title || props.book.file_name)
</script>

<style scoped>
.book-card { cursor: pointer; border-radius: 8px; overflow: hidden; background: #fff; box-shadow: 0 1px 6px rgba(0, 0, 0, 0.08); transition: transform 0.15s; }
.book-card:hover { transform: translateY(-3px); }
.cover { position: relative; aspect-ratio: 3 / 4; background: #eef1f6; }
.cover img { width: 100%; height: 100%; object-fit: cover; }
.badge { position: absolute; top: 6px; right: 6px; background: rgba(0, 0, 0, 0.55); color: #fff; font-size: 10px; padding: 2px 6px; border-radius: 4px; }
.meta { padding: 8px 10px; }
.title { font-size: 14px; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.author { font-size: 12px; color: #909399; margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
/* 字数/章节用可换行的 chip,避免移动端窄卡片下被截断显示不全 */
.sub { font-size: 11px; color: #909399; margin-top: 4px; display: flex; flex-wrap: wrap; gap: 4px 6px; }
.sub .chip { white-space: nowrap; }
</style>
