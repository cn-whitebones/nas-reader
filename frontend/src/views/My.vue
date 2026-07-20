<template>
  <div class="my-page">
    <h2 class="page-title">我的</h2>

    <!-- 账户信息 -->
    <section class="card">
      <div class="card-head">账户信息</div>
      <div class="info-row">
        <span class="k">用户名</span>
        <span class="v">{{ auth.user?.username || '—' }}</span>
      </div>
      <div class="info-row">
        <span class="k">角色</span>
        <span class="v">
          <el-tag size="small" :type="auth.isAdmin ? 'warning' : 'info'">
            {{ auth.isAdmin ? '管理员' : '普通用户' }}
          </el-tag>
        </span>
      </div>
      <div class="info-row">
        <span class="k">注册时间</span>
        <span class="v">{{ registeredAt }}</span>
      </div>
    </section>

    <!-- 安全 -->
    <section class="card">
      <div class="card-head">安全</div>
      <div class="action-row">
        <div class="action-text">
          <div class="action-title">修改密码</div>
          <div class="action-desc">定期更换密码以保护账户安全</div>
        </div>
        <el-button @click="pwdVisible = true">修改</el-button>
      </div>
    </section>

    <!-- 预留:后续个性化设置(阅读偏好、界面等)可在此追加卡片 -->

    <div class="logout-wrap">
      <el-button type="danger" plain @click="onLogout">退出登录</el-button>
    </div>

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
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/api/auth'

const auth = useAuthStore()
const router = useRouter()

const dialogWidth = computed(() => (window.innerWidth < 768 ? '94vw' : '460px'))

const registeredAt = computed(() => {
  const raw = auth.user?.created_at
  if (!raw) return '—'
  const d = new Date(raw)
  if (Number.isNaN(d.getTime())) return '—'
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
})

function onLogout() {
  auth.logout()
  router.push('/login')
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
.my-page { max-width: 640px; margin: 0 auto; }
.page-title { font-size: 20px; margin: 0 0 16px; color: #303133; }
.card {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  padding: 16px 18px;
  margin-bottom: 16px;
}
.card-head {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 12px;
}
.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  font-size: 14px;
  border-top: 1px solid #f5f7fa;
}
.info-row:first-of-type { border-top: none; }
.info-row .k { color: #909399; }
.info-row .v { color: #303133; }
.action-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.action-title { font-size: 14px; color: #303133; }
.action-desc { font-size: 12px; color: #909399; margin-top: 2px; }
.logout-wrap { text-align: center; margin-top: 24px; }
</style>
