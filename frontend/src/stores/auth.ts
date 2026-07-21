import { defineStore } from 'pinia'
import { authApi, type User } from '@/api/auth'

// Storage key constants
const KEY_ACCESS_TOKEN = 'nas-reader:access-token'
const KEY_REFRESH_TOKEN = 'nas-reader:refresh-token'
// For backward compatibility: read old key if new key doesn't exist
const OLD_KEY_ACCESS_TOKEN = 'access_token'
const OLD_KEY_REFRESH_TOKEN = 'refresh_token'

interface AuthState {
  accessToken: string
  refreshToken: string
  user: User | null
}

function loadWithFallback(key: string, oldKey: string): string {
  const val = localStorage.getItem(key)
  if (val !== null) return val
  const oldVal = localStorage.getItem(oldKey)
  if (oldVal !== null) {
    // Migrate to new key
    localStorage.setItem(key, oldVal)
    localStorage.removeItem(oldKey)
    return oldVal
  }
  return ''
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    accessToken: loadWithFallback(KEY_ACCESS_TOKEN, OLD_KEY_ACCESS_TOKEN),
    refreshToken: loadWithFallback(KEY_REFRESH_TOKEN, OLD_KEY_REFRESH_TOKEN),
    user: null,
  }),
  getters: {
    isLoggedIn: (s) => !!s.accessToken,
    isAdmin: (s) => s.user?.role === 'admin',
  },
  actions: {
    _persist() {
      localStorage.setItem(KEY_ACCESS_TOKEN, this.accessToken)
      localStorage.setItem(KEY_REFRESH_TOKEN, this.refreshToken)
    },
    async login(username: string, password: string) {
      const { data } = await authApi.login(username, password)
      this.accessToken = data.access_token
      this.refreshToken = data.refresh_token
      this._persist()
      await this.fetchMe()
    },
    async refresh(): Promise<string> {
      const { data } = await authApi.refresh(this.refreshToken)
      this.accessToken = data.access_token
      this._persist()
      return data.access_token
    },
    async fetchMe() {
      const { data } = await authApi.me()
      this.user = data
    },
    logout() {
      this.accessToken = ''
      this.refreshToken = ''
      this.user = null
      localStorage.removeItem(KEY_ACCESS_TOKEN)
      localStorage.removeItem(KEY_REFRESH_TOKEN)
      // Cleanup old keys just in case
      localStorage.removeItem(OLD_KEY_ACCESS_TOKEN)
      localStorage.removeItem(OLD_KEY_REFRESH_TOKEN)
    },
  },
})
