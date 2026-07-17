import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/api/auth'

const routes: RouteRecordRaw[] = [
  { path: '/setup', name: 'setup', component: () => import('@/views/Setup.vue'), meta: { public: true } },
  { path: '/login', name: 'login', component: () => import('@/views/Login.vue'), meta: { public: true } },
  {
    path: '/',
    component: () => import('@/views/Layout.vue'),
    children: [
      { path: '', redirect: '/library' },
      { path: 'library', name: 'library', component: () => import('@/views/Library.vue') },
      { path: 'shelves', name: 'shelves', component: () => import('@/views/Shelves.vue') },
      // 搜索合并入书库,旧收藏链接 /search?q=xxx 重定向到 /library?q=xxx
      { path: 'search', redirect: (to) => ({ path: '/library', query: to.query }) },
      { path: 'books/:id', name: 'book-detail', component: () => import('@/views/BookDetail.vue') },
      { path: 'read/:id', name: 'reader', component: () => import('@/views/Reader.vue') },
      { path: 'admin', name: 'admin', component: () => import('@/views/Admin.vue'), meta: { admin: true } },
      { path: ':pathMatch(.*)*', name: 'not-found', component: () => import('@/views/NotFound.vue') },
    ],
  },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach(async (to) => {
  // 首次启动:无用户则强制进引导页
  if (to.name !== 'setup') {
    try {
      const { data } = await authApi.setupStatus()
      if (data.needs_setup) return { name: 'setup' }
    } catch {
      /* 后端不可用时放行到目标页,由页面自行处理错误 */
    }
  }

  const auth = useAuthStore()
  if (to.meta.public) return true
  if (!auth.isLoggedIn) return { name: 'login', query: { redirect: to.fullPath } }
  if (!auth.user) {
    try {
      await auth.fetchMe()
    } catch {
      auth.logout()
      return { name: 'login' }
    }
  }
  if (to.meta.admin && !auth.isAdmin) return { name: 'library' }
  return true
})

export default router
