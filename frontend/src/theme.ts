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

/** 仅更新 <meta name="theme-color">(安卓状态栏/地址栏颜色)。 */
export function setStatusBarColor(color: string): void {
  let meta = document.querySelector<HTMLMetaElement>('meta[name="theme-color"]')
  if (!meta) {
    meta = document.createElement('meta')
    meta.name = 'theme-color'
    document.head.appendChild(meta)
  }
  meta.content = color
}

export function applyTheme(theme: AppTheme): void {
  const root = document.documentElement
  const isDark = theme === 'dark'
  root.classList.toggle('dark', isDark)
  // 全局外壳只有明亮/暗黑两态(sepia 归明亮),供全局 CSS 变量取色
  root.dataset.appTheme = isDark ? 'dark' : 'light'
  // 全局状态栏只跟随明亮/暗黑(sepia 归明亮);护眼沉浸仅在阅读器内单独处理
  setStatusBarColor(isDark ? THEME_STATUS_COLOR.dark : THEME_STATUS_COLOR.light)
}
