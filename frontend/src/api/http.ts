import axios, { type AxiosInstance } from 'axios'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import router from '@/router'

const http: AxiosInstance = axios.create({ baseURL: '/api/v1', timeout: 30000 })

// 请求拦截:附加 access token
http.interceptors.request.use((config) => {
  const auth = useAuthStore()
  if (auth.accessToken) {
    config.headers.Authorization = `Bearer ${auth.accessToken}`
  }
  return config
})

// 响应拦截:401 时尝试用 refresh token 续期一次,失败则登出
let refreshing: Promise<string> | null = null
let sessionExpiredNotified = false

// 统一处理"登录失效":登出、跳登录页并提示(去重,避免并发请求弹多条)
function handleSessionExpired() {
  const auth = useAuthStore()
  auth.logout()
  if (router.currentRoute.value.name !== 'login') {
    if (!sessionExpiredNotified) {
      sessionExpiredNotified = true
      ElMessage.warning('登录已过期,请重新登录')
      setTimeout(() => (sessionExpiredNotified = false), 3000)
    }
    router.push({ name: 'login', query: { redirect: router.currentRoute.value.fullPath } })
  }
}

http.interceptors.response.use(
  (res) => res,
  async (error) => {
    const auth = useAuthStore()
    const original = error.config
    const url: string = original?.url || ''
    // 登录/续期接口自身的 401 交给调用方处理,不触发"登录过期"逻辑
    const isAuthEndpoint = url.includes('/auth/login') || url.includes('/auth/refresh')
    if (error.response?.status === 401 && !isAuthEndpoint) {
      if (!original._retry && auth.refreshToken) {
        original._retry = true
        try {
          refreshing = refreshing ?? auth.refresh()
          const token = await refreshing
          refreshing = null
          original.headers.Authorization = `Bearer ${token}`
          return http(original)
        } catch {
          refreshing = null
          handleSessionExpired()
        }
      } else {
        // 无 refresh token 或续期后仍 401:直接判定登录失效
        handleSessionExpired()
      }
    }
    return Promise.reject(error)
  },
)

export default http
