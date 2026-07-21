/**
 * 视口检测 composable: 提供移动端检测和自适应
 * 统一抽离避免每个组件重复实现 resize 监听
 */
import { ref, onMounted, onUnmounted } from 'vue'

// 移动端断点阈值 (Bootstrap 标准: < 768px 视为移动端)
const MOBILE_BREAKPOINT = 768

export function useViewport() {
  const isMobile = ref(window.innerWidth < MOBILE_BREAKPOINT)

  const handleResize = () => {
    isMobile.value = window.innerWidth < MOBILE_BREAKPOINT
  }

  onMounted(() => {
    window.addEventListener('resize', handleResize)
  })

  onUnmounted(() => {
    window.removeEventListener('resize', handleResize)
  })

  return {
    isMobile,
  }
}
