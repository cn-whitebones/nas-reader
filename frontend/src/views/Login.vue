<template>
  <div class="center-page">
    <el-card class="box" header="NAS Reader 登录">
      <el-form :model="form" label-width="80px" @submit.prevent>
        <el-form-item label="用户名"><el-input v-model="form.username" @keyup.enter="submit" /></el-form-item>
        <el-form-item label="密码"><el-input v-model="form.password" type="password" show-password @keyup.enter="submit" /></el-form-item>
        <el-button type="primary" :loading="loading" style="width: 100%" @click="submit">登录</el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const form = reactive({ username: '', password: '' })
const loading = ref(false)
const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

async function submit() {
  loading.value = true
  try {
    await auth.login(form.username, form.password)
    router.push((route.query.redirect as string) || '/library')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.center-page { display: flex; align-items: center; justify-content: center; height: 100%; background: #f5f7fa; }
.box { width: 360px; max-width: 90vw; }
</style>
