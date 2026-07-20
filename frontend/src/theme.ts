/**
 * 全局主题应用:把阅读设置里的 theme 同步到整个 App 与系统状态栏。
 *
 * 全局层面只区分 明亮 / 暗黑(护眼仅在阅读器正文体现,全局按明亮处理):
 * - dark:给 <html> 加 .dark 接入 Element Plus 内置暗色,外壳/状态栏转暗;
 * - light / sepia:全局外壳与状态栏均按明亮呈现。
 * 同步更新 <meta name="theme-color">,让安卓状态栏/地址栏跟随;iOS 靠顶栏背景
 * 延伸进安全区实现刘海区沉浸(见 Layout 样式)。
 */
export type AppTheme = 'light' | 'sepia' | 'dark'

export function applyTheme(theme: AppTheme): void {
  const root = document.documentElement
  const isDark = theme === 'dark'
  root.classList.toggle('dark', isDark)
  // 全局外壳只有明亮/暗黑两态(sepia 归明亮),供全局 CSS 变量取色
  root.dataset.appTheme = isDark ? 'dark' : 'light'

  const color = isDark ? '#1a1a1a' : '#ffffff'
  let meta = document.querySelector<HTMLMetaElement>('meta[name="theme-color"]')
  if (!meta) {
    meta = document.createElement('meta')
    meta.name = 'theme-color'
    document.head.appendChild(meta)
  }
  meta.content = color
}
