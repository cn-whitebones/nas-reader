// 极简 Service Worker:满足 PWA 可安装条件(安卓 Chrome 需 fetch 处理器),
// 并对应用外壳做基础缓存。不缓存 API 请求与带 hash 的资源交给 HTTP 缓存策略。
const CACHE = 'nas-reader-v1'
const SHELL = ['/', '/index.html', '/manifest.webmanifest', '/icon-192.png']

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).catch(() => {}))
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))),
    ),
  )
  self.clients.claim()
})

self.addEventListener('fetch', (event) => {
  const { request } = event
  // 只处理 GET;API 请求直连网络不缓存
  if (request.method !== 'GET' || new URL(request.url).pathname.startsWith('/api/')) {
    return
  }
  // 导航请求(HTML):网络优先,离线回退到缓存的外壳,保证断网也能打开
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() => caches.match('/index.html')),
    )
    return
  }
  // 其他 GET 资源:缓存优先,回源后写入缓存
  event.respondWith(
    caches.match(request).then(
      (cached) =>
        cached ||
        fetch(request).then((resp) => {
          const copy = resp.clone()
          caches.open(CACHE).then((c) => c.put(request, copy)).catch(() => {})
          return resp
        }),
    ),
  )
})
