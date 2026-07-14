<template>
  <div class="not-found">
    <div class="code">404</div>
    <p class="msg">页面不存在或已被移动</p>
    <el-button type="primary" @click="goHome">返回书库</el-button>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
const router = useRouter()
function goHome() {
  router.replace('/library')
}
</script>

<style scoped>
.not-found {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 64px 16px;
  text-align: center;
}
.code { font-size: 64px; font-weight: 700; color: var(--el-color-primary); line-height: 1; }
.msg { color: #909399; margin: 0; }
</style>
