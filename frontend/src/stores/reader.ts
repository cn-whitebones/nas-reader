import { defineStore } from 'pinia'
import { readingSettingsApi } from '@/api/admin'
import { applyTheme } from '@/theme'
import { DEBOUNCE_SETTINGS } from '@/constants'

export interface ReaderSettings {
  font_family: string
  font_size: number
  line_height: number
  margin: number
  theme: 'light' | 'dark' | 'sepia'
  extra: Record<string, unknown>
}

const DEFAULTS: ReaderSettings = {
  font_family: 'serif',
  font_size: 18,
  line_height: 1.6,
  margin: 16,
  theme: 'light',
  extra: {},
}

let saveTimer: ReturnType<typeof setTimeout> | null = null

export const useReaderStore = defineStore('reader', {
  state: () => ({ settings: { ...DEFAULTS } as ReaderSettings, loaded: false }),
  actions: {
    async load() {
      try {
        const { data } = await readingSettingsApi.get()
        this.settings = { ...DEFAULTS, ...data }
      } catch {
        this.settings = { ...DEFAULTS }
      }
      this.loaded = true
      applyTheme(this.settings.theme)
    },
    update(patch: Partial<ReaderSettings>) {
      this.settings = { ...this.settings, ...patch }
      // 主题变更即时应用到全局(状态栏/外壳),不等防抖
      if (patch.theme) applyTheme(patch.theme)
      // 防抖持久化
      if (saveTimer) clearTimeout(saveTimer)
      saveTimer = setTimeout(() => {
        readingSettingsApi.update(this.settings).catch(() => {})
      }, DEBOUNCE_SETTINGS)
    },
  },
})
