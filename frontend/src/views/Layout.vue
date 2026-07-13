<template>
  <el-container class="layout">
    <el-header class="header">
      <span class="logo">📚 NAS Reader</span>
      <el-menu mode="horizontal" :router="true" :default-active="$route.path" class="nav">
        <el-menu-item index="/library">书库</el-menu-item>
        <el-menu-item index="/shelves">书架</el-menu-item>
        <el-menu-item index="/search">搜索</el-menu-item>
        <el-menu-item v-if="auth.isAdmin" index="/admin">管理</el-menu-item>
      </el-menu>
      <el-dropdown @command="onCommand">
        <span class="user">{{ auth.user?.username }} <el-icon><arrow-down /></el-icon></span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="logout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </el-header>
    <el-main class="main" :class="{ 'reader-mode': isReader }"><router-view /></el-main>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ArrowDown } from '@element-plus/icons-vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const isReader = computed(() => route.name === 'reader')

function onCommand(cmd: string) {
  if (cmd === 'logout') {
    auth.logout()
    router.push('/login')
  }
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
.main { background: #f5f7fa; }
/* 阅读器模式:去掉 el-main 默认内边距与滚动,交给阅读器内部自行滚动 */
.reader-mode { padding: 0; overflow: hidden; }
/* 移动端:收紧导航,避免横向溢出 */
@media (max-width: 600px) {
  /* 顶部更矮;只调左右内边距,避免简写覆盖 padding-top 安全区 */
  .header { gap: 6px; padding-left: 8px; padding-right: 8px; height: calc(46px + env(safe-area-inset-top)); }
  .logo { font-size: 13px; }
  .nav { height: 46px; }
  .nav :deep(.el-menu-item) { height: 46px; line-height: 46px; padding: 0 10px; }
  .user { font-size: 13px; }
  /* 仅普通页面收紧内边距并避让 home 横条;阅读器保持全屏无边距 */
  .main:not(.reader-mode) { padding: 12px; padding-bottom: calc(12px + env(safe-area-inset-bottom)); }
}
</style>
