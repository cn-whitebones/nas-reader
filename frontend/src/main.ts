import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import './styles/global.css'
import App from './App.vue'
import router from './router'

// iOS 全屏 PWA 首帧视口高度不准的可靠解法:用 visualViewport 的真实高度写入
// CSS 变量 --app-height,并监听 resize/scroll/orientation 持续校正(不锁死,任何
// 视口变化都会自动更新)。多次延迟兜底 standalone 启动首帧偏差。
function setAppHeight() {
  const h = window.visualViewport?.height ?? window.innerHeight
  document.documentElement.style.setProperty('--app-height', `${h}px`)
}
setAppHeight()
window.visualViewport?.addEventListener('resize', setAppHeight)
window.visualViewport?.addEventListener('scroll', setAppHeight)
window.addEventListener('resize', setAppHeight)
window.addEventListener('orientationchange', () => setTimeout(setAppHeight, 300))
window.addEventListener('pageshow', setAppHeight)
// 启动首帧校正:多帧/多时点补测,覆盖 standalone 首次进入的高度抖动
requestAnimationFrame(setAppHeight)
;[100, 300, 600, 1000].forEach((t) => setTimeout(setAppHeight, t))

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(ElementPlus)
app.mount('#app')

// 注册 Service Worker(启用 PWA 安装能力,提供基础离线外壳)
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {})
  })
}
