<template>
  <div v-if="book" class="detail">
    <div class="hero">
      <div class="cover">
        <CoverImage v-if="book.has_cover" :book-id="bookId" :alt="title" />
        <div v-else class="no-cover">{{ book.format.toUpperCase() }}</div>
      </div>
      <div class="info">
        <h1>{{ title }}</h1>
        <p v-if="md?.subtitle" class="subtitle">{{ md.subtitle }}</p>
        <p class="line"><b>作者:</b>{{ md?.authors?.join(', ') || '未知' }}</p>
        <p v-if="md?.publisher" class="line"><b>出版社:</b>{{ md.publisher }}</p>
        <p v-if="md?.pub_date" class="line"><b>出版:</b>{{ md.pub_date }}</p>
        <p v-if="md?.isbn" class="line"><b>ISBN:</b>{{ md.isbn }}</p>
        <p v-if="md?.rating" class="line"><b>评分:</b>{{ md.rating }}</p>
        <div v-if="md?.tags?.length" class="tags">
          <el-tag v-for="t in md.tags" :key="t" size="small" effect="plain">{{ t }}</el-tag>
        </div>
        <p class="line"><b>格式:</b>{{ book.format.toUpperCase() }} · {{ (book.file_size / 1024 / 1024).toFixed(1) }} MB · {{ book.chapter_count }} 章</p>
        <p v-if="book.progress && book.progress.percent > 0" class="line">
          <b>进度:</b>{{ book.progress.percent.toFixed(1) }}%
        </p>

        <div class="actions">
          <el-button type="primary" size="large" class="act-btn" @click="$router.push(`/read/${book.id}`)">
            {{ book.progress && book.progress.percent > 0 ? '继续阅读' : '开始阅读' }}
          </el-button>
          <el-button size="large" class="act-btn" @click="scrapeDialog = true">刮削信息</el-button>
          <el-dropdown class="shelf-dropdown" @command="addToShelf" trigger="click">
            <el-button size="large" class="act-btn">收藏到书架 <el-icon><ArrowDown /></el-icon></el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item v-for="sh in shelves" :key="sh.id" :command="sh.id">{{ sh.name }}</el-dropdown-item>
                <el-dropdown-item v-if="!shelves.length" disabled>请先在书架页创建书架</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </div>

    <div v-if="md?.description" class="description">
      <h3>简介</h3>
      <p>{{ md.description }}</p>
    </div>

    <!-- 刮削对话框 -->
    <el-dialog v-model="scrapeDialog" title="刮削元数据" :width="dialogWidth" top="6vh">
      <div class="scrape-head">
        <el-input v-model="scrapeKeyword" placeholder="搜索关键词" class="kw-input" />
        <el-select v-model="scrapeProvider" placeholder="自动(多源降级)" clearable class="provider-select">
          <el-option label="豆瓣" value="douban" />
          <el-option label="Google Books" value="google" />
          <el-option label="Open Library" value="openlibrary" />
        </el-select>
        <el-button type="primary" :loading="scraping" @click="runScrape">搜索</el-button>
      </div>
      <div class="candidates">
        <div v-for="(c, i) in candidates" :key="i" class="candidate" @click="applyCandidate(c)">
          <img v-if="c.cover_url" :src="c.cover_url" class="cand-cover" />
          <div class="cand-info">
            <div class="cand-title">{{ c.title }} <el-tag size="small">{{ c.provider }}</el-tag></div>
            <div class="cand-sub">{{ c.authors.join(', ') }} · {{ c.publisher || '' }} {{ c.pub_date || '' }}</div>
            <div class="cand-desc">{{ c.description }}</div>
          </div>
        </div>
        <el-empty v-if="scrapeSearched && !candidates.length" description="无结果,可换关键词或来源" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowDown } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { booksApi, type BookDetail } from '@/api/books'
import { shelvesApi, type Shelf } from '@/api/shelves'
import { scrapeApi, type Candidate } from '@/api/admin'
import CoverImage from '@/components/CoverImage.vue'

const route = useRoute()
const bookId = route.params.id as string

const book = ref<BookDetail | null>(null)
const md = computed(() => book.value?.metadata)
const title = computed(() => md.value?.title || book.value?.file_name || '')
const shelves = ref<Shelf[]>([])

const scrapeDialog = ref(false)
const scrapeKeyword = ref('')
const scrapeProvider = ref<string | undefined>(undefined)
const candidates = ref<Candidate[]>([])
const scraping = ref(false)
// 弹窗宽度:移动端近乎占满屏幕,桌面固定 640px
const dialogWidth = computed(() => (window.innerWidth < 600 ? '94vw' : '640px'))
const scrapeSearched = ref(false)

async function load() {
  const { data } = await booksApi.detail(bookId)
  book.value = data
  scrapeKeyword.value = data.metadata?.title || data.file_name.replace(/\.[^.]+$/, '')
}

async function runScrape() {
  scraping.value = true
  try {
    const { data } = await scrapeApi.scrapeBook(bookId, scrapeKeyword.value, scrapeProvider.value)
    candidates.value = data
    scrapeSearched.value = true
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '刮削失败')
  } finally {
    scraping.value = false
  }
}

async function applyCandidate(c: Candidate) {
  await scrapeApi.apply(bookId, c)
  ElMessage.success('已应用元数据')
  scrapeDialog.value = false
  await load()
}

async function addToShelf(shelfId: string) {
  try {
    await shelvesApi.addBook(shelfId, bookId)
    ElMessage.success('已收藏')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '收藏失败')
  }
}

onMounted(async () => {
  await load()
  const { data } = await shelvesApi.list()
  shelves.value = data
})
</script>

<style scoped>
.detail { max-width: 900px; margin: 0 auto; }
.hero { display: flex; gap: 24px; background: #fff; padding: 24px; border-radius: 8px; }
.cover { width: 180px; flex-shrink: 0; align-self: flex-start; aspect-ratio: 3/4; border-radius: 6px; overflow: hidden; background: #eef1f6; }
.cover img { width: 100%; height: 100%; object-fit: cover; }
.no-cover { display: flex; align-items: center; justify-content: center; height: 100%; color: #a0a4ac; font-size: 26px; font-weight: 600; }
.info { flex: 1; min-width: 0; }
.info h1 { margin: 0 0 8px; font-size: 22px; }
.subtitle { color: #909399; margin: 0 0 12px; }
.line { margin: 6px 0; font-size: 14px; color: #606266; }
.tags { display: flex; gap: 6px; flex-wrap: wrap; margin: 10px 0; }
.actions { margin-top: 18px; display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
.act-btn { margin: 0; }
/* dropdown 触发器本身撑满,使内部按钮与其它按钮同高同宽策略一致 */
.shelf-dropdown :deep(.el-button) { width: 100%; }
.description { background: #fff; padding: 24px; border-radius: 8px; margin-top: 16px; }
.description p { color: #606266; line-height: 1.8; white-space: pre-wrap; }
.scrape-head { display: flex; gap: 10px; margin-bottom: 16px; }
.kw-input { flex: 1; min-width: 0; }
.provider-select { width: 160px; }
.candidates { max-height: 52vh; overflow-y: auto; }
.candidate { display: flex; gap: 12px; padding: 12px; border-radius: 8px; cursor: pointer; }
.candidate:hover { background: #f5f7fa; }
.cand-cover { width: 60px; height: 84px; object-fit: cover; border-radius: 4px; flex-shrink: 0; }
.cand-info { min-width: 0; flex: 1; }
.cand-title { font-weight: 600; overflow-wrap: anywhere; }
.cand-sub { font-size: 13px; color: #909399; margin: 4px 0; overflow-wrap: anywhere; }
.cand-desc { font-size: 12px; color: #b0b3b8; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }

@media (max-width: 600px) {
  .hero { flex-direction: column; align-items: center; }
  .cover { width: 140px; align-self: center; }
  /* 搜索栏纵向堆叠,避免横向挤压 */
  .scrape-head { flex-direction: column; }
  .provider-select { width: 100%; }
  /* 操作按钮移动端各占一行,高度一致不尴尬换行 */
  .actions { flex-direction: column; align-items: stretch; }
  .shelf-dropdown { width: 100%; }
}
</style>
