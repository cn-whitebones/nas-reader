<template>
  <div class="book-card" @click="$router.push(`/books/${book.id}`)">
    <div class="cover">
      <CoverImage v-if="book.has_cover" blur-fill :book-id="book.id" :alt="displayTitle" :version="book.cover_version" />
      <GeneratedCover v-else :title="displayTitle" :format="book.format" />
      <span class="badge">{{ book.format.toUpperCase() }}</span>
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
.book-card { cursor: pointer; border-radius: 8px; overflow: hidden; background: var(--el-bg-color-overlay); border: 1px solid var(--el-border-color-lighter); box-shadow: 0 1px 6px rgba(0, 0, 0, 0.08); transition: transform 0.15s; display: flex; flex-direction: column; }
/* 仅在支持悬停的设备(桌面鼠标)上浮起;触摸屏 tap 后 hover 会被粘住导致卡片错位 */
@media (hover: hover) {
  .book-card:hover { transform: translateY(-3px); }
}
.cover { position: relative; aspect-ratio: 3 / 4; background: var(--el-fill-color-light); display: flex; align-items: center; justify-content: center; overflow: hidden; border-bottom: 1px solid var(--el-border-color-lighter); }
/* 真实封面由 CoverImage 的 blur-fill 双层结构处理:模糊放大背景填满留白、
   原比例前景居中,网格中所有卡片等高且无生硬白边;生成封面自身即 3:4 满铺 */
.badge { position: absolute; left: 6px; bottom: 6px; background: rgba(0, 0, 0, 0.55); color: #fff; font-size: 10px; padding: 2px 6px; border-radius: 4px; letter-spacing: 0.05em; }
/* meta 四行固定结构:书名/作者/章节/字数,每行独立单行且高度固定,
   保证网格所有卡片视觉一致(无 chip、无 wrap、无 min-height 兜底) */
.meta { padding: 8px 10px 10px; }
.line { line-height: 1.3; height: 1.3em; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.title { font-size: 14px; font-weight: 500; color: var(--el-text-color-primary); }
.author { font-size: 12px; color: var(--el-text-color-secondary); margin-top: 4px; }
.info { font-size: 12px; color: var(--el-text-color-secondary); margin-top: 2px; }
</style>
