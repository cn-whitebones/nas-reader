/** 展示格式化工具 */

/** 字数 → 「约 N 万字 / N 字」。空值返回空串。 */
export function formatWords(n: number | null | undefined): string {
  if (!n) return ''
  if (n >= 10000) return `约 ${(n / 10000).toFixed(1)} 万字`
  return `${n} 字`
}

/** 文件字节数 → 人类可读(KB/MB)。 */
export function formatSize(bytes: number | null | undefined): string {
  if (!bytes) return ''
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  return `${(bytes / 1024).toFixed(0)} KB`
}
