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
          <el-button size="large" class="act-btn" @click="openScrapeDialog" v-if="isAdmin">刮削信息</el-button>
          <el-button size="large" class="act-btn" :type="inShelf ? 'success' : 'default'" @click="toggleShelf">
            {{ inShelf ? '已收藏' : '收藏到书架' }}
          </el-button>
        </div>
      </div>
    </div>

    <div v-if="md?.description" class="description">
      <h3>简介</h3>
      <p>{{ md.description }}</p>
    </div>

    <!-- 刮削对话框 -->
    <el-dialog v-model="scrapeDialog" title="元数据管理" :width="dialogWidth" top="6vh">
      <el-tabs v-model="editTab">
        <el-tab-pane label="刮削搜索" name="scrape">
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
        </el-tab-pane>
        <el-tab-pane label="手动编辑" name="manual">
          <el-form label-width="80px">
            <el-form-item label="书名"><el-input v-model="manualForm.title" /></el-form-item>
            <el-form-item label="副标题"><el-input v-model="manualForm.subtitle" /></el-form-item>
            <el-form-item label="作者"><el-input v-model="manualForm.authors" placeholder="多个作者用逗号分隔" /></el-form-item>
            <el-form-item label="出版社"><el-input v-model="manualForm.publisher" /></el-form-item>
            <el-form-item label="出版日期"><el-input v-model="manualForm.pub_date" placeholder="如: 2023-01" /></el-form-item>
            <el-form-item label="ISBN"><el-input v-model="manualForm.isbn" /></el-form-item>
            <el-form-item label="标签"><el-input v-model="manualForm.tags" placeholder="多个标签用逗号分隔" /></el-form-item>
            <el-form-item label="简介"><el-input v-model="manualForm.description" type="textarea" :rows="6" /></el-form-item>
          </el-form>
          <div style="text-align: right; margin-top: 16px;">
            <el-button type="primary" :loading="scraping" @click="saveManualEdit">保存</el-button>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { booksApi, type BookDetail } from '@/api/books'
import { shelvesApi } from '@/api/shelves'
import { scrapeApi, type Candidate } from '@/api/admin'
import { useAuthStore } from '@/stores/auth'
import CoverImage from '@/components/CoverImage.vue'

const auth = useAuthStore()
const isAdmin = computed(() => auth.isAdmin)

const route = useRoute()
const bookId = route.params.id as string

const book = ref<BookDetail | null>(null)
const md = computed(() => book.value?.metadata)
const title = computed(() => md.value?.title || book.value?.file_name || '')
const inShelf = ref(false)

const scrapeDialog = ref(false)
const scrapeKeyword = ref('')
const scrapeProvider = ref<string | undefined>(undefined)
const candidates = ref<Candidate[]>([])
const scraping = ref(false)
// 弹窗宽度:移动端近乎占满屏幕,桌面固定 640px
const dialogWidth = computed(() => (window.innerWidth < 600 ? '94vw' : '640px'))
const scrapeSearched = ref(false)

// 手动编辑 tab
const editTab = ref('scrape')  // 'scrape' | 'manual'
const manualForm = reactive({
  title: '',
  subtitle: '',
  authors: '',
  publisher: '',
  pub_date: '',
  isbn: '',
  description: '',
  tags: '',
})

function openScrapeDialog() {
  scrapeDialog.value = true
  editTab.value = 'scrape'
  // 回填当前元数据到表单
  if (md.value) {
    manualForm.title = md.value.title || ''
    manualForm.subtitle = md.value.subtitle || ''
    manualForm.authors = (md.value.authors || []).join(', ')
    manualForm.publisher = md.value.publisher || ''
    manualForm.pub_date = md.value.pub_date || ''
    manualForm.isbn = md.value.isbn || ''
    manualForm.description = md.value.description || ''
    manualForm.tags = (md.value.tags || []).join(', ')
  }
}

async function saveManualEdit() {
  scraping.value = true
  try {
    const tags = manualForm.tags
      .split(/[,，]/)
      .map((t) => t.trim())
      .filter(Boolean)
    const authors = manualForm.authors
      .split(/[,，]/)
      .map((a) => a.trim())
      .filter(Boolean)
    await scrapeApi.updateMetadata(bookId, {
      title: manualForm.title || undefined,
      subtitle: manualForm.subtitle || undefined,
      authors: authors.length ? authors : undefined,
      publisher: manualForm.publisher || undefined,
      pub_date: manualForm.pub_date || undefined,
      isbn: manualForm.isbn || undefined,
      description: manualForm.description || undefined,
      tags: tags.length ? tags : undefined,
    })
    ElMessage.success('已保存')
    scrapeDialog.value = false
    await load() // 刷新详情页
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    scraping.value = false
  }
}

async function load() {
  const { data } = await booksApi.detail(bookId)
  book.value = data
  scrapeKeyword.value = data.metadata?.title || data.file_name.replace(/\.[^.]+$/, '')
}

async function loadShelfState() {
  try {
    const { data } = await shelvesApi.myBooks()
    inShelf.value = data.some((b) => b.id === bookId)
  } catch {
    inShelf.value = false
  }
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

async function toggleShelf() {
  try {
    if (inShelf.value) {
      await shelvesApi.removeBook(bookId)
      inShelf.value = false
      ElMessage.success('已从书架移除')
    } else {
      await shelvesApi.addBook(bookId)
      inShelf.value = true
      ElMessage.success('已收藏到书架')
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

onMounted(async () => {
  await load()
  await loadShelfState()
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
}
</style>
