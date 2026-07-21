<template>
  <div class="html-reader" :class="`theme-${s.theme}`" ref="rootEl">
    <div class="viewport" ref="viewportEl">
      <div
        class="pages"
        ref="pagesEl"
        :class="{ 'no-transition': disableTransition }"
        :style="pagesStyle"
        v-html="html"
      ></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useReaderStore } from '@/stores/reader'
import { DEBOUNCE_RESIZE } from '@/constants'

const props = defineProps<{
  html: string
  /** 恢复用:目标字符偏移(该章节纯文本中的偏移),分页后定位到对应页 */
  initialCharOffset?: number
}>()

const emit = defineEmits<{
  /** 分页完成,回传总页数与当前页(0基) */
  paginated: [totalPages: number, currentPage: number]
  /** 当前页变化,回传页码与该页首字符偏移 */
  pageChange: [page: number, charOffset: number]
}>()

const store = useReaderStore()
const s = computed(() => store.settings)

const rootEl = ref<HTMLElement>()
const viewportEl = ref<HTMLElement>()
const pagesEl = ref<HTMLElement>()

const pageWidth = ref(0) // 单页(单列)宽度,含列间距
const totalPages = ref(1)
const currentPage = ref(0)

// 跨章节进入动画偏移(单位为页宽)。正常翻页时为 0;
// 进入下一章时先被设为 currentPage+1,使内容位于右侧外,再动画回 0,实现从右往左进入。
const chapterEnterOffset = ref(0)
const disableTransition = ref(false)
const chapterEnterDirection = ref<'none' | 'next' | 'prev'>('none')
const chapterEnterTarget = ref<'first' | 'last'>('first')

// 多列布局:列宽=视口内容宽,列间距=2倍水平内边距(视觉上成为相邻页的合并留白)
const pagesStyle = computed(() => ({
  columnWidth: pageWidth.value ? `${pageWidth.value - colGap.value}px` : 'auto',
  columnGap: `${colGap.value}px`,
  columnFill: 'auto' as const,
  fontFamily: s.value.font_family,
  fontSize: `${s.value.font_size}px`,
  lineHeight: String(s.value.line_height),
  height: `${Math.max(0, viewportHeight.value - padY.value * 2 - 8)}px`,
  transform: `translateX(${-(currentPage.value - chapterEnterOffset.value) * pageWidth.value}px)`,
}))

const colGap = ref(0)
const viewportHeight = ref(0)
const padY = ref(32)

/** 重新测量并分页 */
async function paginate(preserveCharOffset?: number) {
  const vp = viewportEl.value
  const pages = pagesEl.value
  if (!vp || !pages) return

  await nextTick()

  const vpRect = vp.getBoundingClientRect()
  const vpCs = getComputedStyle(vp)
  padY.value = parseFloat(vpCs.paddingTop) || 0
  const margin = s.value.margin
  colGap.value = margin * 2
  // 页宽 = 视口宽度(每次平移一整个视口)
  pageWidth.value = vpRect.width
  viewportHeight.value = vpRect.height

  await nextTick()

  // 内容总宽 → 页数
  const scrollWidth = pages.scrollWidth
  totalPages.value = Math.max(1, Math.round(scrollWidth / pageWidth.value))

  // 恢复到指定字符偏移所在页
  let target = 0
  if (chapterEnterTarget.value === 'last') {
    target = totalPages.value - 1
  } else if (preserveCharOffset != null && preserveCharOffset > 0) {
    target = pageOfCharOffset(preserveCharOffset)
  }
  const nextPage = Math.min(target, totalPages.value - 1)

  // 跨章节进入动画:先无过渡地把内容放到进入侧外,再开启动画滑入目标页
  if (chapterEnterDirection.value !== 'none') {
    const dir = chapterEnterDirection.value
    chapterEnterDirection.value = 'none'
    chapterEnterTarget.value = 'first'
    disableTransition.value = true
    currentPage.value = nextPage
    // 下一章从右往左进入:目标页在右侧外(+1 页);上一章从左往右进入:目标页在左侧外(-1 页)
    chapterEnterOffset.value = dir === 'next' ? currentPage.value + 1 : -1
    await nextTick()
    disableTransition.value = false
    chapterEnterOffset.value = 0
  } else {
    currentPage.value = nextPage
  }

  emit('paginated', totalPages.value, currentPage.value)
  emitPageChange()
}

/** 计算某字符偏移落在第几页(基于文本节点 Range 测量) */
function pageOfCharOffset(charOffset: number): number {
  const pages = pagesEl.value
  if (!pages || pageWidth.value === 0) return 0
  const node = findTextNodeAtOffset(pages, charOffset)
  if (!node) return 0
  try {
    const range = document.createRange()
    range.setStart(node.node, node.localOffset)
    range.setEnd(node.node, Math.min(node.localOffset + 1, node.node.textContent!.length))
    const rect = range.getBoundingClientRect()
    const pagesRect = pages.getBoundingClientRect()
    // rect.left 相对当前 translate 后的位置;换算回未平移时的横向偏移
    const x = rect.left - pagesRect.left
    return Math.max(0, Math.floor(x / pageWidth.value))
  } catch {
    return 0
  }
}

/** 遍历文本节点,找到累计字符偏移所在的文本节点及局部偏移 */
function findTextNodeAtOffset(root: HTMLElement, target: number): { node: Text; localOffset: number } | null {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT)
  let acc = 0
  let n = walker.nextNode() as Text | null
  while (n) {
    const len = n.textContent?.length ?? 0
    if (acc + len >= target) {
      return { node: n, localOffset: Math.max(0, target - acc) }
    }
    acc += len
    n = walker.nextNode() as Text | null
  }
  // 超出则返回最后一个文本节点末尾
  return null
}

/** 当前页首字符在章节纯文本中的偏移 */
function charOffsetOfCurrentPage(): number {
  const pages = pagesEl.value
  if (!pages) return 0
  // 用当前页左边缘 x 找到该处的文本位置
  const pagesRect = pages.getBoundingClientRect()
  const targetX = pagesRect.left + 2 // 页左边缘稍向内
  const targetY = pagesRect.top + 4
  const pos = caretCharIndexAtPoint(pages, targetX, targetY)
  return pos
}

/** 用 caretRangeFromPoint 求某屏幕坐标处字符在纯文本里的累计偏移 */
function caretCharIndexAtPoint(root: HTMLElement, x: number, y: number): number {
  let range: Range | null = null
  const doc = document as any
  if (doc.caretRangeFromPoint) {
    range = doc.caretRangeFromPoint(x, y)
  } else if (doc.caretPositionFromPoint) {
    const p = doc.caretPositionFromPoint(x, y)
    if (p) {
      range = document.createRange()
      range.setStart(p.offsetNode, p.offset)
    }
  }
  if (!range) return 0
  // 累计该节点之前所有文本节点长度 + 局部 offset
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT)
  let acc = 0
  let n = walker.nextNode() as Text | null
  while (n) {
    if (n === range.startContainer) return acc + range.startOffset
    acc += n.textContent?.length ?? 0
    n = walker.nextNode() as Text | null
  }
  return 0
}

function emitPageChange() {
  emit('pageChange', currentPage.value, charOffsetOfCurrentPage())
}

/** 供父组件调用的翻页接口 */
function goToPage(p: number): boolean {
  if (p < 0 || p >= totalPages.value) return false
  chapterEnterOffset.value = 0
  currentPage.value = p
  emitPageChange()
  return true
}
function nextPage(): boolean {
  if (currentPage.value >= totalPages.value - 1) return false
  chapterEnterOffset.value = 0
  currentPage.value++
  emitPageChange()
  return true
}
function prevPage(): boolean {
  if (currentPage.value <= 0) return false
  chapterEnterOffset.value = 0
  currentPage.value--
  emitPageChange()
  return true
}
function isFirstPage() { return currentPage.value <= 0 }
function isLastPage() { return currentPage.value >= totalPages.value - 1 }

/** 父组件在切换章节前调用,让新章节按方向做进入动画 */
function prepareChapterTransition(direction: 'next' | 'prev', target: 'first' | 'last' = 'first') {
  chapterEnterDirection.value = direction
  chapterEnterTarget.value = target
}

defineExpose({ goToPage, nextPage, prevPage, isFirstPage, isLastPage, paginate, prepareChapterTransition })

// 内容(章节)变化 → 重新分页,定位到 initialCharOffset
watch(
  () => props.html,
  () => paginate(props.initialCharOffset),
)
// 字体/字号/行距/边距变化 → 保持当前字符位置重新分页
watch(
  () => [s.value.font_family, s.value.font_size, s.value.line_height, s.value.margin],
  () => {
    const off = charOffsetOfCurrentPage()
    paginate(off)
  },
)

let resizeTimer: ReturnType<typeof setTimeout> | null = null
function onResize() {
  if (resizeTimer) clearTimeout(resizeTimer)
  resizeTimer = setTimeout(() => {
    const off = charOffsetOfCurrentPage()
    paginate(off)
  }, DEBOUNCE_RESIZE)
}

onMounted(() => {
  window.addEventListener('resize', onResize)
  paginate(props.initialCharOffset)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
})
</script>

<style scoped>
.html-reader { height: 100%; box-sizing: border-box; overflow: hidden; transition: background 0.2s; }
.theme-light { background: #ffffff; color: #2c2c2c; }
.theme-sepia { background: #f5ecd9; color: #5b4636; }
.theme-dark { background: #1a1a1a; color: #c8c8c8; }

.viewport {
  height: 100%;
  /* 顶部 padding 避开绝对定位顶栏;底部 padding 留出 HUD(章节名/分页浮层)位置 */
  padding: 48px v-bind('s.margin + "px"') 64px v-bind('s.margin + "px"');
  box-sizing: border-box;
  overflow: hidden;
}
/* 多列容器:横向排列成多页,transform 平移翻页 */
.pages {
  transition: transform 0.28s ease;
  will-change: transform;
}
.pages.no-transition {
  transition: none !important;
}
.pages :deep(p) { margin: 0 0 1em; text-indent: 2em; }
.pages :deep(img) { max-width: 100%; max-height: 90%; height: auto; break-inside: avoid; }
.pages :deep(h1),
.pages :deep(h2),
.pages :deep(h3) { text-indent: 0; break-inside: avoid; }
</style>
