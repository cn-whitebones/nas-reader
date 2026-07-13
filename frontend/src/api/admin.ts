import http from './http'
import type { Metadata } from './books'

export interface Source {
  id: string
  name: string
  root_path: string
  type: 'book' | 'comic' | 'mixed'
  auto_scan: boolean
  scan_interval_minutes: number
  enabled: boolean
  last_scan_at: string | null
  created_at: string
}

export interface ScanTask {
  id: string
  source_id: string
  status: 'pending' | 'running' | 'done' | 'failed'
  total: number
  processed: number
  added: number
  updated: number
  error: string | null
}

export interface User {
  id: string
  username: string
  role: 'admin' | 'user'
  is_active: boolean
  created_at: string
}

export interface Candidate {
  provider: string
  title: string
  subtitle?: string | null
  authors: string[]
  publisher?: string | null
  isbn?: string | null
  pub_date?: string | null
  description?: string | null
  language?: string | null
  tags: string[]
  rating?: number | null
  cover_url?: string | null
  external_id?: string | null
}

export const sourcesApi = {
  list: () => http.get<Source[]>('/sources'),
  create: (data: Partial<Source>) => http.post<Source>('/sources', data),
  update: (id: string, data: Partial<Source>) => http.patch<Source>(`/sources/${id}`, data),
  remove: (id: string) => http.delete(`/sources/${id}`),
  scan: (id: string, force = false) =>
    http.post<ScanTask>(`/sources/${id}/scan`, null, { params: { force } }),
  scanTask: (taskId: string) => http.get<ScanTask>(`/scan-tasks/${taskId}`),
}

export const usersApi = {
  list: (page = 1, size = 50) => http.get('/users', { params: { page, size } }),
  create: (username: string, password: string, role: 'admin' | 'user') =>
    http.post<User>('/users', { username, password, role }),
  update: (id: string, data: Record<string, unknown>) => http.patch<User>(`/users/${id}`, data),
  remove: (id: string) => http.delete(`/users/${id}`),
  getPermissions: (id: string) => http.get(`/users/${id}/permissions`),
  setPermissions: (id: string, permissions: unknown[]) =>
    http.put(`/users/${id}/permissions`, { permissions }),
  getDefaultPermissions: () => http.get('/settings/default-permissions'),
  setDefaultPermissions: (permissions: unknown[]) =>
    http.put('/settings/default-permissions', { permissions }),
}

export const scrapeApi = {
  search: (keyword: string, provider?: string) =>
    http.get<Candidate[]>('/scrape/search', { params: { keyword, provider } }),
  scrapeBook: (bookId: string, keyword?: string, provider?: string) =>
    http.post<Candidate[]>(`/books/${bookId}/scrape`, { keyword, provider }),
  apply: (bookId: string, candidate: Candidate) =>
    http.post<Metadata>(`/books/${bookId}/metadata/apply`, { candidate }),
  updateMetadata: (bookId: string, data: Partial<Metadata>) =>
    http.put<Metadata>(`/books/${bookId}/metadata`, data),
}

export const readingSettingsApi = {
  get: () => http.get('/reading-settings'),
  update: (data: Record<string, unknown>) => http.put('/reading-settings', data),
}
