<template>
  <el-container class="layout">
    <!-- 顶栏:桌面端含完整导航;移动端仅 logo + 用户名 -->
    <el-header v-if="!isReader" class="header">
      <span class="logo">📚 NAS Reader</span>
      <el-menu mode="horizontal" :router="true" :default-active="activeMenu" class="nav desktop-only">
        <el-menu-item index="/library">书库</el-menu-item>
        <el-menu-item index="/shelves">书架</el-menu-item>
        <el-menu-item v-if="auth.isAdmin" index="/admin">管理</el-menu-item>
        <el-menu-item index="/me">我的</el-menu-item>
      </el-menu>
      <span class="spacer mobile-only"></span>
      <span class="user">{{ auth.user?.username }}</span>
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
  </el-container>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { Reading, Collection, Setting, User } from '@element-plus/icons-vue'
import { useRoute, RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useReaderStore } from '@/stores/reader'

const auth = useAuthStore()
const route = useRoute()
const readerStore = useReaderStore()
const isReader = computed(() => route.name === 'reader')

// 进入 App 外壳即加载并应用全局主题(不再等进阅读器),避免换肤闪白
onMounted(() => {
  if (!readerStore.loaded) readerStore.load()
})

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
  ]
  if (auth.isAdmin) base.push({ path: '/admin', label: '管理', icon: Setting })
  base.push({ path: '/me', label: '我的', icon: User })
  return base
})

function isActiveTab(path: string) {
  if (path === '/library') return route.path.startsWith('/library') || route.path.startsWith('/books')
  return route.path.startsWith(path)
}
</script>

<style scoped>
.layout { height: 100%; overflow-x: hidden; }
.header {
  display: flex;
  align-items: center;
  gap: 16px;
  border-bottom: 1px solid var(--app-border);
  background: var(--app-surface);
  color: var(--app-text);
  overflow: hidden;
  /* 全屏 PWA:顶部避让状态栏/刘海;背景延伸进安全区实现刘海区沉浸 */
  padding-top: env(safe-area-inset-top);
  height: calc(56px + env(safe-area-inset-top));
  box-sizing: border-box;
}
.logo { font-weight: 600; white-space: nowrap; }
/* el-menu 横向默认 60px 高,强制与 header 内容区同高并去掉自带边框,避免撑出/错位 */
.nav { flex: 1; min-width: 0; height: 56px; border-bottom: none; background: transparent; }
.nav :deep(.el-menu-item) { height: 56px; line-height: 56px; }
.user { display: flex; align-items: center; gap: 4px; white-space: nowrap; color: var(--app-text); opacity: 0.75; }
.spacer { flex: 1; }
.main { background: var(--app-bg); color: var(--app-text); }
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
    background: var(--app-surface);
    border-top: 1px solid var(--app-border);
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
