<template>
  <div class="book-card" @click="$router.push(`/books/${book.id}`)">
    <div class="cover">
      <CoverImage v-if="book.has_cover" :book-id="book.id" :alt="displayTitle" />
      <div v-else class="no-cover">{{ formatLabel }}</div>
      <span class="badge">{{ book.format.toUpperCase() }}</span>
    </div>
    <div class="meta">
      <div class="title" :title="displayTitle">{{ displayTitle }}</div>
      <div class="author">{{ book.authors.join(', ') || '—' }}</div>
      <div class="sub">
        <span>{{ book.chapter_count }} 章</span>
        <span v-if="book.word_count">· {{ formatWords(book.word_count) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { type BookBrief } from '@/api/books'
import { formatWords } from '@/utils/format'
import CoverImage from './CoverImage.vue'

const props = defineProps<{ book: BookBrief }>()
const displayTitle = computed(() => props.book.title || props.book.file_name)
const formatLabel = computed(() => props.book.format.toUpperCase())
</script>

<style scoped>
.book-card { cursor: pointer; border-radius: 8px; overflow: hidden; background: #fff; box-shadow: 0 1px 6px rgba(0, 0, 0, 0.08); transition: transform 0.15s; }
.book-card:hover { transform: translateY(-3px); }
.cover { position: relative; aspect-ratio: 3 / 4; background: #eef1f6; }
.cover img { width: 100%; height: 100%; object-fit: cover; }
.no-cover { display: flex; align-items: center; justify-content: center; height: 100%; color: #a0a4ac; font-size: 22px; font-weight: 600; }
.badge { position: absolute; top: 6px; right: 6px; background: rgba(0, 0, 0, 0.55); color: #fff; font-size: 10px; padding: 2px 6px; border-radius: 4px; }
.meta { padding: 8px 10px; }
.title { font-size: 14px; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.author { font-size: 12px; color: #909399; margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sub { font-size: 11px; color: #b0b3b8; margin-top: 3px; display: flex; gap: 4px; overflow: hidden; white-space: nowrap; }
</style>
