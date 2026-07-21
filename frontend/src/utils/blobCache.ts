/**
 * Blob URL 统一缓存管理
 * - LRU 缓存策略，限制最大缓存数量
 * - 自动淘汰最久未使用的条目
 * - 自动 revoke 不再使用的 URL
 * - 解决内存泄漏风险
 */

interface CacheEntry {
  url: string
  lastAccessed: number
}

export class BlobCache {
  private cache = new Map<string, CacheEntry>()
  private maxSize: number

  constructor(maxSize: number = 12) {
    this.maxSize = maxSize
  }

  /**
   * 获取或创建 blob URL
   * 如果已经缓存，更新访问时间并返回
   * 如果未缓存，创建新 URL 并缓存，淘汰最少使用的如果超限
   */
  getOrCreate(blob: Blob, key: string): string {
    // Check cache
    if (this.cache.has(key)) {
      const entry = this.cache.get(key)!
      // 更新访问时间
      entry.lastAccessed = Date.now()
      // LRU: 移到末尾表示最近使用
      this.cache.delete(key)
      this.cache.set(key, entry)
      return entry.url
    }

    // Create new URL
    const url = URL.createObjectURL(blob)

    // Add to cache
    this.cache.set(key, { url, lastAccessed: Date.now() })

    // Evict if over capacity
    this.evictIfNeeded()

    return url
  }

  /**
   * 删除指定 key 并 revoke URL
   */
  delete(key: string): void {
    const entry = this.cache.get(key)
    if (entry) {
      URL.revokeObjectURL(entry.url)
      this.cache.delete(key)
    }
  }

  /**
   * 清空整个缓存，revoke 所有 URL
   */
  clear(): void {
    for (const [_key, entry] of this.cache) {
      URL.revokeObjectURL(entry.url)
    }
    this.cache.clear()
  }

  /**
   * 淘汰最久未使用的条目直到容量足够
   */
  private evictIfNeeded(): void {
    while (this.cache.size > this.maxSize) {
      // Find the oldest entry (first in iteration order is oldest)
      const oldestKey = this.cache.keys().next().value
      if (oldestKey) {
        this.delete(oldestKey)
      } else {
        break
      }
    }
  }
}

// 全局单例 - 漫画阅读用: 最近 12 章足够, 漫画一般一页一章
export const globalComicBlobCache = new BlobCache(12)
