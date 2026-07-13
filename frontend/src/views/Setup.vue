<template>
  <div class="center-page">
    <el-card class="box" header="初始化管理员">
      <p class="tip">首次使用,请创建管理员账号。之后由管理员创建其他用户。</p>
      <el-form :model="form" label-width="80px" @submit.prevent>
        <el-form-item label="用户名"><el-input v-model="form.username" /></el-form-item>
        <el-form-item label="密码"><el-input v-model="form.password" type="password" show-password /></el-form-item>
        <el-button type="primary" :loading="loading" style="width: 100%" @click="submit">创建并进入</el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { authApi } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const form = reactive({ username: '', password: '' })
const loading = ref(false)
const router = useRouter()
const auth = useAuthStore()

async function submit() {
  if (!form.username || form.password.length < 6) {
    ElMessage.warning('用户名必填,密码至少 6 位')
    return
  }
  loading.value = true
  try {
    await authApi.setup(form.username, form.password)
    await auth.login(form.username, form.password)
    router.push('/library')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '初始化失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.center-page { display: flex; align-items: center; justify-content: center; height: 100%; background: #f5f7fa; }
.box { width: 360px; max-width: 90vw; }
.tip { color: #909399; font-size: 13px; margin-top: 0; }
</style>
