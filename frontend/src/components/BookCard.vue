<template>
  <div class="book-card" @click="$router.push(`/books/${book.id}`)">
    <div class="cover">
      <CoverImage v-if="book.has_cover" :book-id="book.id" :alt="displayTitle" />
      <GeneratedCover v-else :title="displayTitle" :format="book.format" />
      <span v-if="book.has_cover" class="badge">{{ book.format.toUpperCase() }}</span>
    </div>
    <div class="meta">
      <div class="line title" :title="displayTitle">{{ displayTitle }}</div>
      <div class="line author" :title="authorText">{{ authorText }}</div>
      <div class="line info">{{ chapterText }}</div>
      <div class="line info">{{ wordsText }}</div>
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
const authorText = computed(() => props.book.authors.join(', ') || '—')
const chapterText = computed(() => `${props.book.chapter_count} 章`)
// 字数缺失时用「—」占位,保证卡片始终 4 行、网格整齐
const wordsText = computed(() => formatWords(props.book.word_count) || '—')
</script>

<style scoped>
.book-card { cursor: pointer; border-radius: 8px; overflow: hidden; background: #fff; box-shadow: 0 1px 6px rgba(0, 0, 0, 0.08); transition: transform 0.15s; display: flex; flex-direction: column; }
.book-card:hover { transform: translateY(-3px); }
.cover { position: relative; aspect-ratio: 3 / 4; background: #eef1f6; display: flex; align-items: center; justify-content: center; overflow: hidden; }
/* 真实封面保持原比例、用背景色填充留白,和生成封面等高;比例不
   对的封面四周留空,居中显示,保证网格中所有卡片高度一致 */
.cover img { max-width: 100%; max-height: 100%; object-fit: contain; }
.badge { position: absolute; left: 6px; bottom: 6px; background: rgba(0, 0, 0, 0.55); color: #fff; font-size: 10px; padding: 2px 6px; border-radius: 4px; letter-spacing: 0.05em; }
/* meta 四行固定结构:书名/作者/章节/字数,每行独立单行且高度固定,
   保证网格所有卡片视觉一致(无 chip、无 wrap、无 min-height 兜底) */
.meta { padding: 8px 10px 10px; }
.line { line-height: 1.3; height: 1.3em; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.title { font-size: 14px; font-weight: 500; color: #303133; }
.author { font-size: 12px; color: #909399; margin-top: 4px; }
.info { font-size: 12px; color: #909399; margin-top: 2px; }
</style>
