<template>
  <div class="login-page" :class="{ 'dark-theme': isDark }">
    <div class="login-container">
      <div class="login-header">
        <div class="logo">
          <svg width="80" height="80" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
            <!-- 书本底座 -->
            <rect x="10" y="15" width="80" height="70" rx="8" fill="white" opacity="0.95" />
            <!-- 书脊蓝色 -->
            <rect x="10" y="15" width="12" height="70" fill="#409eff" />
            <!-- 多层书页 -->
            <path d="M28 25 L40 20 L80 20 L80 80 L28 80 Z" fill="#f8f9fa" stroke="#dee2e6" stroke-width="1" />
            <path d="M28 35 L45 30 L80 30 L80 80 L28 80 Z" fill="#e9ecef" stroke="#dee2e6" stroke-width="1" />
            <path d="M28 45 L50 40 L80 40 L80 80 L28 80 Z" fill="#dee2e6" stroke="#dee2e6" stroke-width="1" />
            <!-- 红色书签 -->
            <circle cx="70" cy="30" r="8" fill="#f56565" />
            <path d="M70 36 L70 48 L64 42 L76 42 Z" fill="#c53030" />
          </svg>
        </div>
        <h1>NAS Reader</h1>
        <p class="subtitle">面向 NAS 场景的自托管电子书管理与在线阅读</p>
      </div>

      <el-card class="login-box" shadow="hover">
        <el-form :model="form" label-width="70px" @submit.prevent class="login-form">
          <el-form-item label="用户名" required>
            <el-input
              v-model="form.username"
              placeholder="请输入用户名"
              @keyup.enter="submit"
              autocomplete="username"
            />
          </el-form-item>
          <el-form-item label="密码" required>
            <el-input
              v-model="form.password"
              type="password"
              show-password
              placeholder="请输入密码"
              @keyup.enter="submit"
              autocomplete="current-password"
            />
          </el-form-item>
          <el-button type="primary" :loading="loading" size="large" style="width: 100%" @click="submit">
            登录
          </el-button>
        </el-form>
      </el-card>

      <div class="login-footer">
        <span>单机部署 · 数据自留</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useReaderStore } from '@/stores/reader'
import { THEME_STATUS_COLOR, setStatusBarColor } from '@/theme'

// 登录页强制使用浅色主题，不受用户设置影响
// 保存原始主题，离开后恢复
const readerStore = useReaderStore()
const originalTheme = ref<'light' | 'dark' | 'sepia'>('light')
const isDark = ref(false)

onMounted(() => {
  // 保存用户当前主题设置，登录页强制浅色
  originalTheme.value = readerStore.settings.theme
  isDark.value = originalTheme.value === 'dark'
  document.documentElement.classList.toggle('dark', false)
  // 状态栏颜色匹配浅色主题，让刘海区域背景正确
  setStatusBarColor(THEME_STATUS_COLOR.light)
})

const form = reactive({ username: '', password: '' })
const loading = ref(false)
const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

async function submit() {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    await auth.login(form.username, form.password)
    // 加载用户阅读设置后会自动应用主题
    router.push((route.query.redirect as string) || '/library')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  /* PWA 沉浸:让背景渐变延伸到刘海区域 */
  padding-top: env(safe-area-inset-top);
  padding-bottom: env(safe-area-inset-bottom);
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  background-attachment: fixed;
}

.login-page.dark-theme {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  background-attachment: fixed;
}

.login-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  max-width: 420px;
  padding: calc(20px + env(safe-area-inset-top)) 20px calc(20px + env(safe-area-inset-bottom));
}

.login-header {
  text-align: center;
  color: white;
  margin-bottom: 24px;
}

.login-header .logo {
  margin-bottom: 12px;
}

.login-header h1 {
  margin: 0 0 6px 0;
  font-size: 28px;
  font-weight: 600;
}

.login-header .subtitle {
  margin: 0;
  font-size: 14px;
  opacity: 0.9;
}

.login-box {
  width: 100%;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
}

.login-box :deep(.el-card__body) {
  padding: 28px 24px;
}

.login-form {
  margin-top: 0;
}

.login-footer {
  margin-top: 24px;
  color: rgba(255, 255, 255, 0.8);
  font-size: 13px;
}
</style>

