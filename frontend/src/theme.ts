/**
 * 全局主题应用:把阅读设置里的 theme 同步到整个 App 与系统状态栏。
 *
 * 全局层面只区分 明亮 / 暗黑(护眼仅在阅读器正文体现,全局按明亮处理):
 * - dark:给 <html> 加 .dark 接入 Element Plus 内置暗色,外壳/状态栏转暗;
 * - light / sepia:全局外壳与状态栏均按明亮呈现。
 * 同步更新 <meta name="theme-color">,让安卓状态栏/地址栏跟随;iOS 靠顶栏背景
 * 延伸进安全区实现刘海区沉浸(见 Layout 样式)。
 * 阅读器内会用 setStatusBarColor 让状态栏跟随当前阅读主题(含护眼),离开时恢复。
 */
export type AppTheme = 'light' | 'sepia' | 'dark'

// 各主题对应的状态栏/刘海区颜色(与阅读器背景一致)
export const THEME_STATUS_COLOR: Record<AppTheme, string> = {
  light: '#ffffff',
  sepia: '#f5ecd9',
  dark: '#1a1a1a',
}

/**
 * 设置"沉浸色":同时更新
 *  - <meta name="theme-color">(安卓 Chrome 状态栏/地址栏)
 *  - document.body 背景色(iOS PWA 在 status-bar-style=default 下,刘海/状态栏
 *    区域的颜色取自 body 背景;theme-color 对 iOS 无效,故必须直接染 body)
 * color 传 null 时清除 body 行内背景,回落到 CSS 的 --app-bg。
 */
export function setStatusBarColor(color: string | null): void {
  let meta = document.querySelector<HTMLMetaElement>('meta[name="theme-color"]')
  if (!meta) {
    meta = document.createElement('meta')
    meta.name = 'theme-color'
    document.head.appendChild(meta)
  }
  meta.content = color || THEME_STATUS_COLOR.light
  // iOS 刘海沉浸:直接给 body 上背景色(default 模式下状态栏取 body 底色)
  document.body.style.background = color || ''
}

export function applyTheme(theme: AppTheme): void {
  const root = document.documentElement
  const isDark = theme === 'dark'
  root.classList.toggle('dark', isDark)
  // 全局外壳只有明亮/暗黑两态(sepia 归明亮),供全局 CSS 变量取色
  root.dataset.appTheme = isDark ? 'dark' : 'light'
  // 全局:清除阅读器可能残留的 body 行内背景,回落到 CSS 变量;状态栏跟随明亮/暗黑
  document.body.style.background = ''
  const meta = document.querySelector<HTMLMetaElement>('meta[name="theme-color"]')
  if (meta) meta.content = isDark ? THEME_STATUS_COLOR.dark : THEME_STATUS_COLOR.light
}
