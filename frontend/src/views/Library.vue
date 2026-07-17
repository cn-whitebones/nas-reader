<template>
  <div class="library">
    <!-- 左侧目录树 -->
    <aside class="sidebar" :class="{ open: mobileTreeOpen }">
      <div class="sidebar-head">
        <span>目录</span>
        <el-button link @click="mobileTreeOpen = false" class="close-tree">收起</el-button>
      </div>
      <el-tree
        :data="treeData"
        :props="{ label: 'name', children: 'children' }"
        node-key="key"
        @node-click="onNodeClick"
        highlight-current
      >
        <template #default="{ data }">
          <span>{{ data.name }} <span class="cnt">({{ data.book_count }})</span></span>
        </template>
      </el-tree>
    </aside>

    <!-- 右侧图书 -->
    <section class="content">
      <div class="toolbar">
        <el-button class="tree-toggle" @click="mobileTreeOpen = true">目录</el-button>
        <el-select v-model="formatFilter" placeholder="全部格式" clearable @change="reload" style="width: 140px">
          <el-option label="TXT" value="txt" />
          <el-option label="EPUB" value="epub" />
          <el-option label="PDF" value="pdf" />
          <el-option label="MOBI" value="mobi" />
          <el-option label="漫画" value="comic" />
        </el-select>
        <span class="path">{{ curDir || '全部' }}</span>
        <span class="spacer"></span>
        <el-radio-group v-model="viewMode" size="small">
          <el-radio-button value="grid">
            <el-icon><Grid /></el-icon>
          </el-radio-button>
          <el-radio-button value="list">
            <el-icon><List /></el-icon>
          </el-radio-button>
        </el-radio-group>
      </div>

      <BookGrid v-if="viewMode === 'grid'" :books="books" />
      <BookList v-else :books="books" />

      <el-pagination
        v-if="total > size"
        class="pager"
        layout="prev, pager, next"
        :total="total"
        :page-size="size"
        :current-page="page"
        @current-change="onPage"
      />
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Grid, List } from '@element-plus/icons-vue'
import BookGrid from '@/components/BookGrid.vue'
import BookList from '@/components/BookList.vue'
import { booksApi, type BookBrief, type TreeNode } from '@/api/books'

const route = useRoute()
const router = useRouter()

const treeData = ref<any[]>([])
const books = ref<BookBrief[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(24)
const curDir = ref<string | undefined>(undefined)
const curSource = ref<string | undefined>(undefined)
const formatFilter = ref<string | undefined>(undefined)
const mobileTreeOpen = ref(false)
const viewMode = ref<'grid' | 'list'>(
  (localStorage.getItem('library_view_mode') as 'grid' | 'list') || 'grid'
)
watch(viewMode, (v) => localStorage.setItem('library_view_mode', v))

// 从 URL query 恢复浏览状态:右滑返回/刷新/分享后可回到原先的翻页与筛选
function restoreFromQuery() {
  const q = route.query
  page.value = Math.max(1, Number(q.page) || 1)
  curDir.value = typeof q.dir === 'string' ? q.dir : undefined
  curSource.value = typeof q.source === 'string' ? q.source : undefined
  formatFilter.value = typeof q.format === 'string' ? q.format : undefined
}

// 把当前浏览状态写回 URL query(replace 避免污染历史栈)
function syncQuery() {
  const q: Record<string, string> = {}
  if (page.value > 1) q.page = String(page.value)
  if (curDir.value) q.dir = curDir.value
  if (curSource.value) q.source = curSource.value
  if (formatFilter.value) q.format = formatFilter.value
  router.replace({ query: q })
}

function decorate(nodes: TreeNode[]): any[] {
  return nodes.map((n) => ({
    ...n,
    key: `${n.source_id}:${n.path}`,
    children: n.children ? decorate(n.children) : [],
  }))
}

async function loadTree() {
  const { data } = await booksApi.tree()
  treeData.value = decorate(data)
}

async function reload() {
  syncQuery()
  const { data } = await booksApi.list({
    page: page.value,
    size: size.value,
    dir_path: curDir.value,
    source_id: curSource.value,
    format: formatFilter.value,
  })
  books.value = data.items
  total.value = data.total
}

function onNodeClick(node: any) {
  curSource.value = node.source_id
  curDir.value = node.path
  page.value = 1
  mobileTreeOpen.value = false
  reload()
}

function onPage(p: number) {
  page.value = p
  reload()
}

onMounted(async () => {
  restoreFromQuery()
  await Promise.all([loadTree(), reload()])
})
</script>

<style scoped>
.library { display: flex; gap: 16px; height: 100%; }
.sidebar { width: 260px; flex-shrink: 0; background: #fff; border-radius: 8px; padding: 12px; overflow-y: auto; }
.sidebar-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; font-weight: 600; }
.close-tree { display: none; }
.cnt { color: #c0c4cc; font-size: 12px; }
.content { flex: 1; min-width: 0; }
.toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.tree-toggle { display: none; }
.path { color: #909399; font-size: 13px; }
.spacer { flex: 1; }
.pager { margin-top: 20px; justify-content: center; }
/* 解决最底部卡片被切掉的问题 */
.content { overflow-y: auto; padding-bottom: 40px; }

@media (max-width: 700px) {
  .sidebar {
    position: fixed; left: 0; top: 0; bottom: 0; z-index: 100;
    transform: translateX(-100%); transition: transform 0.2s; box-shadow: 2px 0 12px rgba(0, 0, 0, 0.2);
  }
  .sidebar.open { transform: translateX(0); }
  .close-tree, .tree-toggle { display: inline-flex; }
}
</style>
