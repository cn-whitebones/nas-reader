<template>
  <el-container class="layout">
    <!-- 顶栏:桌面端含完整导航;移动端仅 logo + 用户信息 -->
    <el-header v-if="!isReader" class="header">
      <span class="logo">📚 NAS Reader</span>
      <el-menu mode="horizontal" :router="true" :default-active="activeMenu" class="nav desktop-only">
        <el-menu-item index="/library">书库</el-menu-item>
        <el-menu-item index="/shelves">书架</el-menu-item>
        <el-menu-item index="/search">搜索</el-menu-item>
        <el-menu-item v-if="auth.isAdmin" index="/admin">管理</el-menu-item>
      </el-menu>
      <span class="spacer mobile-only"></span>
      <el-dropdown @command="onCommand">
        <span class="user">{{ auth.user?.username }} <el-icon><arrow-down /></el-icon></span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="password">修改密码</el-dropdown-item>
            <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </el-header>

    <el-main class="main" :class="{ 'reader-mode': isReader, 'has-tabbar': !isReader }">
      <router-view />
    </el-main>

    <!-- 移动端底部导航栏(原生 App 风格),阅读器模式下隐藏 -->
    <nav v-if="!isReader" class="tabbar mobile-only">
      <RouterLink
        v-for="item in tabs"
        :key="item.path"
        :to="item.path"
        class="tab-item"
        :class="{ active: isActiveTab(item.path) }"
      >
        <el-icon class="tab-icon"><component :is="item.icon" /></el-icon>
        <span class="tab-label">{{ item.label }}</span>
      </RouterLink>
    </nav>

    <!-- 修改密码 -->
    <el-dialog v-model="pwdVisible" title="修改密码" :width="dialogWidth" @closed="resetPwdForm">
      <el-form ref="pwdFormRef" :model="pwdForm" :rules="pwdRules" label-width="94px">
        <el-form-item label="原密码" prop="oldPassword">
          <el-input v-model="pwdForm.oldPassword" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码" prop="newPassword">
          <el-input v-model="pwdForm.newPassword" type="password" show-password />
        </el-form-item>
        <el-form-item label="确认新密码" prop="confirmPassword">
          <el-input v-model="pwdForm.confirmPassword" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pwdVisible = false">取消</el-button>
        <el-button type="primary" :loading="pwdSubmitting" @click="submitPassword">确定</el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ArrowDown, Reading, Collection, Search, Setting } from '@element-plus/icons-vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/api/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const isReader = computed(() => route.name === 'reader')

// 弹窗宽度:移动端窄屏用近似全宽
const dialogWidth = computed(() => (window.innerWidth < 768 ? '94vw' : '460px'))

// 顶部菜单高亮:详情/阅读页归属书库
const activeMenu = computed(() => {
  const p = route.path
  if (p.startsWith('/books') || p.startsWith('/read')) return '/library'
  return p
})

const tabs = computed(() => {
  const base = [
    { path: '/library', label: '书库', icon: Reading },
    { path: '/shelves', label: '书架', icon: Collection },
    { path: '/search', label: '搜索', icon: Search },
  ]
  if (auth.isAdmin) base.push({ path: '/admin', label: '管理', icon: Setting })
  return base
})

function isActiveTab(path: string) {
  if (path === '/library') return route.path.startsWith('/library') || route.path.startsWith('/books')
  return route.path.startsWith(path)
}

function onCommand(cmd: string) {
  if (cmd === 'logout') {
    auth.logout()
    router.push('/login')
  } else if (cmd === 'password') {
    pwdVisible.value = true
  }
}

// ---- 修改密码 ----
const pwdVisible = ref(false)
const pwdSubmitting = ref(false)
const pwdFormRef = ref<FormInstance>()
const pwdForm = reactive({ oldPassword: '', newPassword: '', confirmPassword: '' })
const pwdRules: FormRules = {
  oldPassword: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, max: 128, message: '密码长度 6-128 位', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (_r, value, cb) =>
        value === pwdForm.newPassword ? cb() : cb(new Error('两次输入的密码不一致')),
      trigger: 'blur',
    },
  ],
}

function resetPwdForm() {
  pwdForm.oldPassword = ''
  pwdForm.newPassword = ''
  pwdForm.confirmPassword = ''
  pwdFormRef.value?.clearValidate()
}

async function submitPassword() {
  if (!pwdFormRef.value) return
  await pwdFormRef.value.validate(async (valid) => {
    if (!valid) return
    pwdSubmitting.value = true
    try {
      await authApi.changePassword(pwdForm.oldPassword, pwdForm.newPassword)
      ElMessage.success('密码已修改')
      pwdVisible.value = false
    } catch (e: any) {
      ElMessage.error(e?.response?.data?.detail || '修改失败')
    } finally {
      pwdSubmitting.value = false
    }
  })
}
</script>

<style scoped>
.layout { height: 100%; overflow-x: hidden; }
.header {
  display: flex;
  align-items: center;
  gap: 16px;
  border-bottom: 1px solid #eee;
  background: #fff;
  overflow: hidden;
  /* 全屏 PWA:顶部避让状态栏/刘海 */
  padding-top: env(safe-area-inset-top);
  height: calc(56px + env(safe-area-inset-top));
  box-sizing: border-box;
}
.logo { font-weight: 600; white-space: nowrap; }
/* el-menu 横向默认 60px 高,强制与 header 内容区同高并去掉自带边框,避免撑出/错位 */
.nav { flex: 1; min-width: 0; height: 56px; border-bottom: none; }
.nav :deep(.el-menu-item) { height: 56px; line-height: 56px; }
.user { cursor: pointer; display: flex; align-items: center; gap: 4px; white-space: nowrap; }
.spacer { flex: 1; }
.main { background: #f5f7fa; }
/* 阅读器模式:去掉 el-main 默认内边距与滚动,交给阅读器内部自行滚动 */
.reader-mode { padding: 0; overflow: hidden; }

/* 底部导航栏默认(桌面)隐藏 */
.tabbar { display: none; }
.mobile-only { display: none; }
.desktop-only { display: flex; }

/* 移动端:顶栏精简,导航移到底部 tabbar */
@media (max-width: 600px) {
  .desktop-only { display: none; }
  .mobile-only { display: block; }

  .header { gap: 6px; padding-left: 12px; padding-right: 12px; height: calc(44px + env(safe-area-inset-top)); }
  .logo { font-size: 14px; }
  .user { font-size: 13px; }
  .main:not(.reader-mode) { padding: 12px; }
  /* 内容区为底部 tabbar 预留空间(tabbar 图标区 50px + 减半安全区 + 间距) */
  .main.has-tabbar { padding-bottom: calc(12px + 50px + env(safe-area-inset-bottom) * 0.55); }

  .tabbar {
    display: flex;
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 1000;
    background: #fff;
    border-top: 1px solid #ebeef5;
    box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.04);
    /* 底部避让 home 横条,但只留约 60% 安全区,让图标更贴近底部;
       左右加内边距,使首末图标避开屏幕底部圆角 */
    padding-bottom: calc(env(safe-area-inset-bottom) * 0.55);
    padding-left: max(env(safe-area-inset-left), 8px);
    padding-right: max(env(safe-area-inset-right), 8px);
  }
  .tab-item {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
    height: 50px;
    text-decoration: none;
    color: #909399;
    font-size: 11px;
    border-radius: 8px;
  }
  .tab-icon { font-size: 20px; }
  .tab-label { line-height: 1; white-space: nowrap; }
  .tab-item.active { color: var(--el-color-primary); }
}
</style>
