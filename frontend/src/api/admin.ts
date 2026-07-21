import http from './http'
import type { Metadata } from './books'
import { useAuthStore } from '@/stores/auth'

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
  started_at?: string | null
  finished_at?: string | null
  created_at?: string
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
  scanTasks: (sourceId: string) => http.get<ScanTask[]>(`/sources/${sourceId}/scan-tasks`),
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

export interface ScrapeStep {
  provider: string
  level: 'info' | 'success' | 'warning' | 'error'
  message: string
  elapsed_ms?: number | null
}

export interface ScrapeResult {
  keyword: string
  candidates: Candidate[]
  steps: ScrapeStep[]
}

export interface ScrapeSettings {
  douban_cookie_set: boolean
  douban_cookie_length: number
}

export interface ProviderItem {
  provider: string
  enabled: boolean
  label?: string | null
}

export const scrapeApi = {
  search: (keyword: string, provider?: string) =>
    http.get<ScrapeResult>('/scrape/search', { params: { keyword, provider } }),
  scrapeBook: (bookId: string, keyword?: string, provider?: string) =>
    http.post<ScrapeResult>(`/books/${bookId}/scrape`, { keyword, provider }),
  apply: (bookId: string, candidate: Candidate) =>
    http.post<Metadata>(`/books/${bookId}/metadata/apply`, { candidate }),
  updateMetadata: (bookId: string, data: Partial<Metadata>) =>
    http.patch<Metadata>(`/scrape/books/${bookId}/metadata`, data),
  getSettings: () => http.get<ScrapeSettings>('/settings/scrape'),
  updateSettings: (douban_cookie: string) =>
    http.patch<ScrapeSettings>('/settings/scrape', { douban_cookie }),
  getProviders: () => http.get<ProviderItem[]>('/settings/scrape/providers'),
  updateProviders: (providers: ProviderItem[]) =>
    http.put<ProviderItem[]>('/settings/scrape/providers', { providers }),
}

/**
 * 流式刮削(SSE)。用 fetch 读取 text/event-stream(EventSource 无法带 JWT header)。
 * onStep 每步实时回调,onDone 收到候选结果,onError 出错回调。返回一个取消函数。
 */
export function scrapeStream(
  keyword: string,
  provider: string | undefined,
  handlers: {
    onStep: (step: ScrapeStep) => void
    onDone: (candidates: Candidate[]) => void
    onError: (message: string) => void
  },
  limit?: number,
): () => void {
  const auth = useAuthStore()
  const controller = new AbortController()
  const params = new URLSearchParams({ keyword })
  if (provider) params.set('provider', provider)
  if (limit) params.set('limit', String(limit))

  ;(async () => {
    try {
      const resp = await fetch(`/api/v1/scrape/stream?${params.toString()}`, {
        headers: { Authorization: `Bearer ${auth.accessToken}` },
        signal: controller.signal,
      })
      if (!resp.ok || !resp.body) {
        handlers.onError(`刮削请求失败(${resp.status})`)
        return
      }
      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      for (;;) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        // 按 SSE 事件分隔(空行)切分
        const events = buffer.split('\n\n')
        buffer = events.pop() || ''
        for (const raw of events) {
          const ev = parseSseEvent(raw)
          if (!ev) continue
          if (ev.event === 'step') handlers.onStep(ev.data as ScrapeStep)
          else if (ev.event === 'done') handlers.onDone((ev.data.candidates || []) as Candidate[])
          else if (ev.event === 'error') handlers.onError(ev.data.message || '刮削出错')
        }
      }
    } catch (e: any) {
      if (e?.name !== 'AbortError') handlers.onError(e?.message || '刮削连接中断')
    }
  })()

  return () => controller.abort()
}

function parseSseEvent(raw: string): { event: string; data: any } | null {
  let event = 'message'
  const dataLines: string[] = []
  for (const line of raw.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim()
    else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
  }
  if (!dataLines.length) return null
  try {
    return { event, data: JSON.parse(dataLines.join('\n')) }
  } catch {
    return null
  }
}

export const readingSettingsApi = {
  get: () => http.get('/reading-settings'),
  update: (data: Record<string, unknown>) => http.patch('/reading-settings', data),
}
