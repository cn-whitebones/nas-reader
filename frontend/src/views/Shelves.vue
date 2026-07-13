<template>
  <div class="shelves-page">
    <div class="toolbar">
      <el-radio-group v-model="activeShelf" @change="loadBooks">
        <el-radio-button v-for="sh in shelves" :key="sh.id" :value="sh.id">
          {{ sh.name }} ({{ sh.book_count }})
        </el-radio-button>
      </el-radio-group>
      <div class="spacer" />
      <el-button type="primary" @click="createDialog = true">新建书架</el-button>
      <el-button v-if="activeShelf" @click="removeShelf">删除当前</el-button>
    </div>

    <BookGrid :books="books" />
    <el-empty v-if="!shelves.length" description="还没有书架,点右上角新建" />

    <el-dialog v-model="createDialog" title="新建书架" width="360px">
      <el-input v-model="newName" placeholder="书架名称" @keyup.enter="createShelf" />
      <template #footer>
        <el-button @click="createDialog = false">取消</el-button>
        <el-button type="primary" @click="createShelf">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import BookGrid from '@/components/BookGrid.vue'
import { shelvesApi, type Shelf } from '@/api/shelves'
import type { BookBrief } from '@/api/books'

const shelves = ref<Shelf[]>([])
const activeShelf = ref<string>('')
const books = ref<BookBrief[]>([])
const createDialog = ref(false)
const newName = ref('')

async function loadShelves() {
  const { data } = await shelvesApi.list()
  shelves.value = data
  if (data.length && !activeShelf.value) {
    activeShelf.value = data[0].id
    await loadBooks()
  }
}

async function loadBooks() {
  if (!activeShelf.value) {
    books.value = []
    return
  }
  const { data } = await shelvesApi.books(activeShelf.value)
  books.value = data
}

async function createShelf() {
  if (!newName.value.trim()) return
  try {
    const { data } = await shelvesApi.create(newName.value.trim())
    shelves.value.push(data)
    activeShelf.value = data.id
    newName.value = ''
    createDialog.value = false
    await loadBooks()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  }
}

async function removeShelf() {
  await ElMessageBox.confirm('确定删除该书架?收藏关系会一并移除。', '提示', { type: 'warning' })
  await shelvesApi.remove(activeShelf.value)
  shelves.value = shelves.value.filter((s) => s.id !== activeShelf.value)
  activeShelf.value = shelves.value[0]?.id || ''
  await loadBooks()
}

onMounted(loadShelves)
</script>

<style scoped>
.toolbar { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
.spacer { flex: 1; }
</style>
