<template>
  <div class="admin">
    <el-tabs v-model="tab">
      <!-- 文件源 -->
      <el-tab-pane label="文件源" name="sources">
        <div class="tab-toolbar">
          <el-button type="primary" @click="openSourceDialog()">添加文件源</el-button>
          <span class="hint">路径需为容器内挂载路径,如 /data/book1</span>
        </div>
        <!-- 扫描进度:进行中/刚完成的任务显示进度条 -->
        <div v-if="activeScans.length" class="scan-progress-list">
          <div v-for="item in activeScans" :key="item.sourceId" class="scan-progress">
            <div class="scan-progress-head">
              <span class="scan-name">{{ item.name }}</span>
              <span class="scan-stat">{{ scanStatText(item.task) }}</span>
            </div>
            <el-progress
              :percentage="scanPercent(item.task)"
              :status="item.task.status === 'failed' ? 'exception' : item.task.status === 'done' ? 'success' : undefined"
              :indeterminate="item.task.status === 'pending' || (item.task.status === 'running' && item.task.total === 0)"
              :duration="1"
            />
          </div>
        </div>
        <!-- 桌面端:表格 -->
        <el-table v-if="!isMobile" :data="sources" style="width: 100%">
          <el-table-column prop="name" label="名称" />
          <el-table-column prop="root_path" label="路径" show-overflow-tooltip />
          <el-table-column prop="type" label="类型" width="90" />
          <el-table-column label="自动扫描" width="90">
            <template #default="{ row }">{{ row.auto_scan ? `每${row.scan_interval_minutes}分` : '否' }}</template>
          </el-table-column>
          <el-table-column label="操作" width="320">
            <template #default="{ row }">
              <el-button size="small" :loading="scanning[row.id]" @click="scan(row)">扫描</el-button>
              <el-button size="small" :loading="scanning[row.id]" @click="scan(row, true)">重新解析</el-button>
              <el-button size="small" @click="openSourceDialog(row)">编辑</el-button>
              <el-button size="small" type="danger" @click="removeSource(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <!-- 移动端:卡片列表 -->
        <div v-else class="card-list">
          <div v-for="s in sources" :key="s.id" class="data-card">
            <div class="card-head">
              <span class="card-title">{{ s.name }}</span>
              <el-tag size="small" effect="plain">{{ s.type }}</el-tag>
            </div>
            <div class="card-line"><span class="k">路径</span><span class="v">{{ s.root_path }}</span></div>
            <div class="card-line"><span class="k">自动扫描</span><span class="v">{{ s.auto_scan ? `每 ${s.scan_interval_minutes} 分` : '否' }}</span></div>
            <div class="card-actions">
              <el-button size="small" :loading="scanning[s.id]" @click="scan(s)">扫描</el-button>
              <el-button size="small" :loading="scanning[s.id]" @click="scan(s, true)">重新解析</el-button>
              <el-button size="small" @click="openSourceDialog(s)">编辑</el-button>
              <el-button size="small" type="danger" @click="removeSource(s)">删除</el-button>
            </div>
          </div>
          <el-empty v-if="!sources.length" description="暂无文件源" />
        </div>
      </el-tab-pane>

      <!-- 用户 -->
      <el-tab-pane label="用户" name="users">
        <div class="tab-toolbar">
          <el-button type="primary" @click="openUserDialog()">创建用户</el-button>
        </div>
        <!-- 桌面端:表格 -->
        <el-table v-if="!isMobile" :data="users" style="width: 100%">
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
        <!-- 移动端:卡片列表 -->
        <div v-else class="card-list">
          <div v-for="u in users" :key="u.id" class="data-card">
            <div class="card-head">
              <span class="card-title">{{ u.username }}</span>
              <el-tag size="small" :type="u.is_active ? 'success' : 'info'">{{ u.is_active ? '启用' : '禁用' }}</el-tag>
            </div>
            <div class="card-line"><span class="k">角色</span><span class="v">{{ u.role === 'admin' ? '管理员' : '普通用户' }}</span></div>
            <div class="card-actions">
              <el-button size="small" @click="toggleActive(u)">{{ u.is_active ? '禁用' : '启用' }}</el-button>
              <el-button size="small" @click="openPermDialog(u)">权限</el-button>
              <el-button size="small" type="danger" @click="removeUser(u)">删除</el-button>
            </div>
          </div>
          <el-empty v-if="!users.length" description="暂无用户" />
        </div>
      </el-tab-pane>

      <!-- 刮削设置 -->
      <el-tab-pane label="刮削设置" name="scrape">
        <div class="scrape-settings">
          <h3 class="ss-title">刮削源</h3>
          <p class="ss-desc">
            控制「自动」模式下的来源顺序与启用状态。刮削时按从上到下的顺序依次尝试,命中即停止。
            关闭某个源后,自动模式将跳过它。
          </p>
          <div class="provider-list">
            <div v-for="(p, idx) in providers" :key="p.provider" class="provider-row">
              <span class="pr-order">{{ idx + 1 }}</span>
              <span class="pr-name">{{ p.label || p.provider }}</span>
              <el-switch v-model="p.enabled" />
              <div class="pr-actions">
                <el-button size="small" :disabled="idx === 0" @click="moveProvider(idx, -1)">上移</el-button>
                <el-button size="small" :disabled="idx === providers.length - 1" @click="moveProvider(idx, 1)">
                  下移
                </el-button>
              </div>
            </div>
          </div>
          <div class="ss-actions">
            <el-button type="primary" :loading="savingProviders" @click="saveProviders">保存刮削源</el-button>
          </div>

          <el-divider />

          <h3 class="ss-title">豆瓣 Cookie</h3>
          <p class="ss-desc">
            豆瓣未登录时极易被反爬拦截,导致刮削失败。配置浏览器登录豆瓣后的 Cookie 可显著提高成功率。
            <br />
            获取方式:浏览器登录 <a href="https://book.douban.com" target="_blank" rel="noopener">book.douban.com</a>,
            打开开发者工具(F12)→ Network → 刷新页面 → 任选一个请求 → 复制 Request Headers 里的 Cookie 值。
          </p>
          <div class="ss-status">
            当前状态:
            <el-tag v-if="scrapeSettings.douban_cookie_set" type="success" size="small">
              已配置({{ scrapeSettings.douban_cookie_length }} 字符)
            </el-tag>
            <el-tag v-else type="info" size="small">未配置</el-tag>
          </div>
          <el-input
            v-model="doubanCookieInput"
            type="textarea"
            :rows="4"
            placeholder="粘贴豆瓣 Cookie,留空并保存则清除(回退到环境变量)"
            class="ss-input"
          />
          <div class="ss-actions">
            <el-button type="primary" :loading="savingScrape" @click="saveScrapeSettings">保存</el-button>
            <el-button v-if="scrapeSettings.douban_cookie_set" :loading="savingScrape" @click="clearDoubanCookie">
              清除
            </el-button>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 文件源对话框 -->
    <el-dialog v-model="sourceDialog" :title="editingSource ? '编辑文件源' : '添加文件源'" :width="dialogWidth">
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
    <el-dialog v-model="userDialog" title="创建用户" :width="userDialogWidth">
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
    <el-dialog v-model="permDialog" title="文件源访问权限" :width="permDialogWidth">
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
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { sourcesApi, usersApi, scrapeApi, type ProviderItem, type ScanTask, type ScrapeSettings, type Source, type User } from '@/api/admin'

const tab = ref('sources')
const sources = ref<Source[]>([])
const users = ref<User[]>([])
const scanning = reactive<Record<string, boolean>>({})
// 扫描实时进度(sourceId → 最近任务),供进度条展示;pollTimers 保存轮询定时器
const scanProgress = reactive<Record<string, ScanTask>>({})
const pollTimers: Record<string, ReturnType<typeof setInterval>> = {}

// 响应式:移动端改用卡片列表,避免表格横向溢出
const isMobile = ref(window.innerWidth < 768)
const dialogWidth = ref(isMobile.value ? '94vw' : '460px')
const userDialogWidth = ref(isMobile.value ? '94vw' : '400px')
const permDialogWidth = ref(isMobile.value ? '94vw' : '440px')
function onResize() {
  isMobile.value = window.innerWidth < 768
  dialogWidth.value = isMobile.value ? '94vw' : '460px'
  userDialogWidth.value = isMobile.value ? '94vw' : '400px'
  permDialogWidth.value = isMobile.value ? '94vw' : '440px'
}

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

// 刮削设置
const scrapeSettings = reactive<ScrapeSettings>({ douban_cookie_set: false, douban_cookie_length: 0 })
const doubanCookieInput = ref('')
const savingScrape = ref(false)
// 刮削源顺序与启用状态
const providers = ref<ProviderItem[]>([])
const savingProviders = ref(false)

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

async function scan(row: Source, force = false) {
  scanning[row.id] = true
  try {
    const { data: task } = await sourcesApi.scan(row.id, force)
    ElMessage.success(force ? '重新解析已开始' : '扫描已开始')
    scanProgress[row.id] = task
    poll(task.id, row.id)
  } catch (e: any) {
    scanning[row.id] = false
    ElMessage.error(e.response?.data?.detail || '扫描失败')
  }
}

function poll(taskId: string, sourceId: string) {
  if (pollTimers[sourceId]) clearInterval(pollTimers[sourceId])
  pollTimers[sourceId] = setInterval(async () => {
    try {
      const { data } = await sourcesApi.scanTask(taskId)
      scanProgress[sourceId] = data
      if (data.status === 'done' || data.status === 'failed') {
        clearInterval(pollTimers[sourceId])
        delete pollTimers[sourceId]
        scanning[sourceId] = false
        ElMessage[data.status === 'done' ? 'success' : 'error'](
          data.status === 'done' ? `扫描完成:新增 ${data.added},更新 ${data.updated}` : `扫描失败:${data.error}`,
        )
        // 完成后刷新文件源列表(更新 last_scan_at),几秒后清除进度条
        loadSources()
        setTimeout(() => { delete scanProgress[sourceId] }, 5000)
      }
    } catch {
      // 单次轮询失败忽略,下次继续
    }
  }, 1500)
}

// 页面加载/刷新时恢复:查每个源最近任务,仍在跑则续上进度与轮询
async function restoreRunningScans() {
  await Promise.all(
    sources.value.map(async (s) => {
      try {
        const { data } = await sourcesApi.scanTasks(s.id)
        const latest = data[0]
        if (latest && (latest.status === 'pending' || latest.status === 'running')) {
          scanProgress[s.id] = latest
          scanning[s.id] = true
          poll(latest.id, s.id)
        }
      } catch {
        /* 忽略 */
      }
    }),
  )
}

// 当前需展示进度条的扫描(进行中或刚完成的),附上源名便于显示
const activeScans = computed(() =>
  Object.entries(scanProgress).map(([sourceId, task]) => ({
    sourceId,
    task,
    name: sources.value.find((s) => s.id === sourceId)?.name || '文件源',
  })),
)

function scanPercent(task: ScanTask): number {
  if (task.status === 'done') return 100
  if (!task.total) return 0
  return Math.min(100, Math.round((task.processed / task.total) * 100))
}

function scanStatText(task: ScanTask): string {
  if (task.status === 'pending') return '等待中…'
  if (task.status === 'failed') return `失败:${task.error || '未知错误'}`
  if (task.status === 'done') return `完成 · 新增 ${task.added} · 更新 ${task.updated}`
  // running
  const base = task.total ? `${task.processed}/${task.total}` : '扫描中…'
  return `${base} · 新增 ${task.added} · 更新 ${task.updated}`
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

async function loadScrapeSettings() {
  const { data } = await scrapeApi.getSettings()
  Object.assign(scrapeSettings, data)
}

async function saveScrapeSettings() {
  savingScrape.value = true
  try {
    const { data } = await scrapeApi.updateSettings(doubanCookieInput.value)
    Object.assign(scrapeSettings, data)
    doubanCookieInput.value = ''
    ElMessage.success('刮削设置已保存')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    savingScrape.value = false
  }
}

async function clearDoubanCookie() {
  doubanCookieInput.value = ''
  await saveScrapeSettings()
}

async function loadProviders() {
  const { data } = await scrapeApi.getProviders()
  providers.value = data
}

function moveProvider(idx: number, delta: number) {
  const to = idx + delta
  if (to < 0 || to >= providers.value.length) return
  const arr = providers.value
  ;[arr[idx], arr[to]] = [arr[to], arr[idx]]
}

async function saveProviders() {
  savingProviders.value = true
  try {
    const { data } = await scrapeApi.updateProviders(providers.value)
    providers.value = data
    ElMessage.success('刮削源已保存')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    savingProviders.value = false
  }
}

onMounted(async () => {
  window.addEventListener('resize', onResize)
  await Promise.all([loadSources(), loadUsers(), loadScrapeSettings(), loadProviders()])
  await restoreRunningScans()
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  Object.values(pollTimers).forEach(clearInterval)
})
</script>

<style scoped>
.admin { max-width: 100%; overflow-x: hidden; }
.tab-toolbar { margin-bottom: 16px; display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.hint { color: #909399; font-size: 13px; }
.perm-row { padding: 6px 0; }
.perm-row .path { color: #c0c4cc; font-size: 12px; margin-left: 6px; }
.scrape-settings { max-width: 640px; padding-bottom: 32px; }
.ss-title { font-size: 16px; margin: 0 0 8px; color: var(--el-text-color-primary); }
.ss-desc { color: var(--el-text-color-secondary); font-size: 13px; line-height: 1.7; margin: 0 0 12px; }
.ss-desc a { color: var(--el-color-primary); }
.ss-status { margin-bottom: 10px; font-size: 14px; color: var(--el-text-color-regular); }
.ss-input { margin-bottom: 12px; }
.ss-actions { display: flex; gap: 10px; }
.provider-list { margin-bottom: 12px; }
.provider-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  margin-bottom: 8px;
  background: var(--el-bg-color-overlay);
}
.pr-order {
  width: 22px;
  height: 22px;
  flex-shrink: 0;
  border-radius: 50%;
  background: var(--el-fill-color);
  color: var(--el-text-color-secondary);
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.pr-name { flex: 1; font-weight: 500; color: var(--el-text-color-primary); }
.pr-actions { display: flex; gap: 6px; }

/* 扫描进度 */
.scan-progress-list { display: flex; flex-direction: column; gap: 12px; margin-bottom: 16px; }
.scan-progress {
  background: var(--el-bg-color-overlay);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 10px;
  padding: 12px 14px;
}
.scan-progress-head {
  display: flex; align-items: center; justify-content: space-between;
  gap: 10px; margin-bottom: 8px; font-size: 13px;
}
.scan-progress-head .scan-name { font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.scan-progress-head .scan-stat { color: var(--el-text-color-secondary); flex-shrink: 0; }

/* 移动端卡片列表 */
.card-list { display: flex; flex-direction: column; gap: 12px; }
.data-card {
  background: var(--el-bg-color-overlay);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 10px;
  padding: 14px;
}
.card-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 8px; }
.card-title { font-size: 16px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.card-line { display: flex; gap: 8px; font-size: 13px; margin: 4px 0; }
.card-line .k { color: var(--el-text-color-secondary); flex-shrink: 0; min-width: 56px; }
.card-line .v { color: var(--el-text-color-regular); word-break: break-all; }
.card-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
.card-actions .el-button { margin: 0; }
</style>
