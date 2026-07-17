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
.book-card { cursor: pointer; border-radius: 8px; overflow: hidden; background: #fff; box-shadow: 0 1px 6px rgba(0, 0, 0, 0.08); transition: transform 0.15s; display: flex; flex-direction: column; }
.book-card:hover { transform: translateY(-3px); }
.cover { position: relative; aspect-ratio: 3 / 4; background: #eef1f6; display: flex; align-items: center; justify-content: center; overflow: hidden; }
/* 真实封面保持原比例、用背景色填充留白,和生成封面等高;比例不
   对的封面四周留空,居中显示,保证网格中所有卡片高度一致 */
.cover img { max-width: 100%; max-height: 100%; object-fit: contain; }
.badge { position: absolute; top: 6px; right: 6px; background: rgba(0, 0, 0, 0.55); color: #fff; font-size: 10px; padding: 2px 6px; border-radius: 4px; }
/* meta 各行高度固定,保证网格卡片整体等高、排列整齐 */
.meta { padding: 8px 10px; }
.title { font-size: 14px; font-weight: 500; line-height: 1.3; height: 1.3em; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.author { font-size: 12px; color: #909399; line-height: 1.3; height: 1.3em; margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
/* 章节/字数 chip:预留两行高度并顶部对齐——字数少的占位到两行(整齐),
   字数多的仍可换行完整显示(不截断),从而卡片高度始终一致 */
.sub {
  font-size: 11px; color: #909399; margin-top: 5px;
  line-height: 1.4; min-height: 2.8em;
  display: flex; flex-wrap: wrap; align-content: flex-start; gap: 3px 6px;
}
.sub .chip { white-space: nowrap; }
</style>
