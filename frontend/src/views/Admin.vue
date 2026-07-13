<template>
  <div class="admin">
    <el-tabs v-model="tab">
      <!-- 文件源 -->
      <el-tab-pane label="文件源" name="sources">
        <div class="tab-toolbar">
          <el-button type="primary" @click="openSourceDialog()">添加文件源</el-button>
          <span class="hint">路径需为容器内挂载路径,如 /data/book1</span>
        </div>
        <el-table :data="sources" style="width: 100%">
          <el-table-column prop="name" label="名称" />
          <el-table-column prop="root_path" label="路径" show-overflow-tooltip />
          <el-table-column prop="type" label="类型" width="90" />
          <el-table-column label="自动扫描" width="90">
            <template #default="{ row }">{{ row.auto_scan ? `每${row.scan_interval_minutes}分` : '否' }}</template>
          </el-table-column>
          <el-table-column label="操作" width="240">
            <template #default="{ row }">
              <el-button size="small" :loading="scanning[row.id]" @click="scan(row)">扫描</el-button>
              <el-button size="small" @click="openSourceDialog(row)">编辑</el-button>
              <el-button size="small" type="danger" @click="removeSource(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- 用户 -->
      <el-tab-pane label="用户" name="users">
        <div class="tab-toolbar">
          <el-button type="primary" @click="openUserDialog()">创建用户</el-button>
        </div>
        <el-table :data="users" style="width: 100%">
          <el-table-column prop="username" label="用户名" />
          <el-table-column prop="role" label="角色" width="100" />
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? '启用' : '禁用' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="260">
            <template #default="{ row }">
              <el-button size="small" @click="toggleActive(row)">{{ row.is_active ? '禁用' : '启用' }}</el-button>
              <el-button size="small" @click="openPermDialog(row)">权限</el-button>
              <el-button size="small" type="danger" @click="removeUser(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- 文件源对话框 -->
    <el-dialog v-model="sourceDialog" :title="editingSource ? '编辑文件源' : '添加文件源'" width="460px">
      <el-form :model="sourceForm" label-width="90px">
        <el-form-item label="名称"><el-input v-model="sourceForm.name" /></el-form-item>
        <el-form-item label="路径"><el-input v-model="sourceForm.root_path" placeholder="/data/book1" :disabled="!!editingSource" /></el-form-item>
        <el-form-item label="类型">
          <el-select v-model="sourceForm.type">
            <el-option label="图书" value="book" />
            <el-option label="漫画" value="comic" />
            <el-option label="混合" value="mixed" />
          </el-select>
        </el-form-item>
        <el-form-item label="自动扫描"><el-switch v-model="sourceForm.auto_scan" /></el-form-item>
        <el-form-item label="扫描间隔" v-if="sourceForm.auto_scan">
          <el-input-number v-model="sourceForm.scan_interval_minutes" :min="1" :max="1440" /> 分钟
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="sourceDialog = false">取消</el-button>
        <el-button type="primary" @click="saveSource">保存</el-button>
      </template>
    </el-dialog>

    <!-- 用户对话框 -->
    <el-dialog v-model="userDialog" title="创建用户" width="400px">
      <el-form :model="userForm" label-width="70px">
        <el-form-item label="用户名"><el-input v-model="userForm.username" /></el-form-item>
        <el-form-item label="密码"><el-input v-model="userForm.password" type="password" show-password /></el-form-item>
        <el-form-item label="角色">
          <el-select v-model="userForm.role">
            <el-option label="普通用户" value="user" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="userDialog = false">取消</el-button>
        <el-button type="primary" @click="saveUser">创建</el-button>
      </template>
    </el-dialog>

    <!-- 权限对话框 -->
    <el-dialog v-model="permDialog" title="文件源访问权限" width="440px">
      <p class="hint">勾选该用户可访问的文件源:</p>
      <el-checkbox-group v-model="checkedSources">
        <div v-for="s in sources" :key="s.id" class="perm-row">
          <el-checkbox :value="s.id">{{ s.name }} <span class="path">{{ s.root_path }}</span></el-checkbox>
        </div>
      </el-checkbox-group>
      <template #footer>
        <el-button @click="permDialog = false">取消</el-button>
        <el-button type="primary" @click="savePermissions">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { sourcesApi, usersApi, type Source, type User } from '@/api/admin'

const tab = ref('sources')
const sources = ref<Source[]>([])
const users = ref<User[]>([])
const scanning = reactive<Record<string, boolean>>({})

// 文件源
const sourceDialog = ref(false)
const editingSource = ref<Source | null>(null)
const sourceForm = reactive({
  name: '',
  root_path: '',
  type: 'book' as 'book' | 'comic' | 'mixed',
  auto_scan: false,
  scan_interval_minutes: 60,
})

// 用户
const userDialog = ref(false)
const userForm = reactive({ username: '', password: '', role: 'user' as 'user' | 'admin' })

// 权限
const permDialog = ref(false)
const permUser = ref<User | null>(null)
const checkedSources = ref<string[]>([])

async function loadSources() {
  const { data } = await sourcesApi.list()
  sources.value = data
}
async function loadUsers() {
  const { data } = await usersApi.list()
  users.value = (data as any).items
}

function openSourceDialog(row?: Source) {
  editingSource.value = row || null
  Object.assign(sourceForm, row
    ? { name: row.name, root_path: row.root_path, type: row.type, auto_scan: row.auto_scan, scan_interval_minutes: row.scan_interval_minutes }
    : { name: '', root_path: '', type: 'book', auto_scan: false, scan_interval_minutes: 60 })
  sourceDialog.value = true
}

async function saveSource() {
  try {
    if (editingSource.value) {
      await sourcesApi.update(editingSource.value.id, { ...sourceForm })
    } else {
      await sourcesApi.create({ ...sourceForm } as any)
    }
    sourceDialog.value = false
    await loadSources()
    ElMessage.success('已保存')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  }
}

async function scan(row: Source) {
  scanning[row.id] = true
  try {
    const { data: task } = await sourcesApi.scan(row.id)
    ElMessage.success('扫描已开始')
    poll(task.id, row.id)
  } catch (e: any) {
    scanning[row.id] = false
    ElMessage.error(e.response?.data?.detail || '扫描失败')
  }
}

function poll(taskId: string, sourceId: string) {
  const timer = setInterval(async () => {
    const { data } = await sourcesApi.scanTask(taskId)
    if (data.status === 'done' || data.status === 'failed') {
      clearInterval(timer)
      scanning[sourceId] = false
      ElMessage[data.status === 'done' ? 'success' : 'error'](
        data.status === 'done' ? `扫描完成:新增 ${data.added},更新 ${data.updated}` : `扫描失败:${data.error}`,
      )
    }
  }, 1500)
}

async function removeSource(row: Source) {
  await ElMessageBox.confirm(`删除文件源「${row.name}」?图书记录会一并移除。`, '提示', { type: 'warning' })
  await sourcesApi.remove(row.id)
  await loadSources()
}

function openUserDialog() {
  Object.assign(userForm, { username: '', password: '', role: 'user' })
  userDialog.value = true
}
async function saveUser() {
  try {
    await usersApi.create(userForm.username, userForm.password, userForm.role)
    userDialog.value = false
    await loadUsers()
    ElMessage.success('已创建')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  }
}
async function toggleActive(row: User) {
  await usersApi.update(row.id, { is_active: !row.is_active })
  await loadUsers()
}
async function removeUser(row: User) {
  await ElMessageBox.confirm(`删除用户「${row.username}」?`, '提示', { type: 'warning' })
  await usersApi.remove(row.id)
  await loadUsers()
}

async function openPermDialog(row: User) {
  permUser.value = row
  const { data } = await usersApi.getPermissions(row.id)
  checkedSources.value = (data as any[]).filter((p) => p.can_read).map((p) => p.source_id)
  permDialog.value = true
}
async function savePermissions() {
  if (!permUser.value) return
  const permissions = checkedSources.value.map((sid) => ({ source_id: sid, sub_path: null, can_read: true }))
  await usersApi.setPermissions(permUser.value.id, permissions)
  permDialog.value = false
  ElMessage.success('权限已更新')
}

onMounted(async () => {
  await Promise.all([loadSources(), loadUsers()])
})
</script>

<style scoped>
.admin { max-width: 100%; overflow-x: hidden; }
.tab-toolbar { margin-bottom: 16px; display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.hint { color: #909399; font-size: 13px; }
.perm-row { padding: 6px 0; }
.perm-row .path { color: #c0c4cc; font-size: 12px; margin-left: 6px; }
</style>
