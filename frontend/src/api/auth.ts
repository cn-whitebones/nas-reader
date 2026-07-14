import http from './http'

export interface User {
  id: string
  username: string
  role: 'admin' | 'user'
  is_active: boolean
  created_at: string
}

export const authApi = {
  setupStatus: () => http.get<{ needs_setup: boolean }>('/auth/setup-status'),
  setup: (username: string, password: string) =>
    http.post<User>('/auth/setup', { username, password }),
  login: (username: string, password: string) => {
    // 后端使用 OAuth2PasswordRequestForm,需 form-urlencoded
    const form = new URLSearchParams()
    form.set('username', username)
    form.set('password', password)
    return http.post<{ access_token: string; refresh_token: string }>('/auth/login', form)
  },
  refresh: (refresh_token: string) =>
    http.post<{ access_token: string }>('/auth/refresh', { refresh_token }),
  me: () => http.get<User>('/auth/me'),
  changePassword: (old_password: string, new_password: string) =>
    http.post('/auth/change-password', { old_password, new_password }),
}
