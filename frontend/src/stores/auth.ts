import { defineStore } from 'pinia'
import { authApi, type User } from '@/api/auth'

interface AuthState {
  accessToken: string
  refreshToken: string
  user: User | null
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    accessToken: localStorage.getItem('access_token') || '',
    refreshToken: localStorage.getItem('refresh_token') || '',
    user: null,
  }),
  getters: {
    isLoggedIn: (s) => !!s.accessToken,
    isAdmin: (s) => s.user?.role === 'admin',
  },
  actions: {
    _persist() {
      localStorage.setItem('access_token', this.accessToken)
      localStorage.setItem('refresh_token', this.refreshToken)
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
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
    },
  },
})
