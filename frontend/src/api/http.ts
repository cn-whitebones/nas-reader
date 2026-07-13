import axios, { type AxiosInstance } from 'axios'
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

http.interceptors.response.use(
  (res) => res,
  async (error) => {
    const auth = useAuthStore()
    const original = error.config
    if (error.response?.status === 401 && !original._retry && auth.refreshToken) {
      original._retry = true
      try {
        refreshing = refreshing ?? auth.refresh()
        const token = await refreshing
        refreshing = null
        original.headers.Authorization = `Bearer ${token}`
        return http(original)
      } catch {
        refreshing = null
        auth.logout()
        router.push('/login')
      }
    }
    return Promise.reject(error)
  },
)

export default http
