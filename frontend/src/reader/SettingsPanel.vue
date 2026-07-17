<template>
  <el-drawer v-model="visible" title="阅读设置" :size="drawerSize" direction="rtl">
    <!-- 漫画设置:仅漫画格式显示 -->
    <div v-if="isComic && isMobile" class="setting-group">
      <label>
        漫画双页
        <span v-if="hasOverride" class="override-hint">（已本地覆盖）</span>
      </label>
      <div class="comic-setting-row">
        <span>双页横图切割</span>
        <el-switch :model-value="doublePage" @update:model-value="setComicPref('doublePage', $event)" />
      </div>
      <div class="comic-setting-row" v-if="doublePage">
        <span>从右页开始阅读（日漫）</span>
        <el-switch :model-value="startRight" @update:model-value="setComicPref('startRight', $event)" />
      </div>
      <el-button
        v-if="hasOverride"
        size="small"
        type="primary"
        text
        @click="resetToDefault"
        style="margin-top: 4px; padding: 0 4px;"
      >
        恢复管理员默认设置
      </el-button>
    </div>

    <div class="setting-group">
      <label>主题</label>
      <el-radio-group :model-value="s.theme" @update:model-value="upd('theme', $event)">
        <el-radio-button value="light">明亮</el-radio-button>
        <el-radio-button value="sepia">护眼</el-radio-button>
        <el-radio-button value="dark">暗黑</el-radio-button>
      </el-radio-group>
    </div>

    <div class="setting-group">
      <label>字体</label>
      <el-select :model-value="s.font_family" @update:model-value="upd('font_family', $event)">
        <el-option label="宋体 / Serif" value="serif" />
        <el-option label="黑体 / Sans" value="sans-serif" />
        <el-option label="楷体" value="KaiTi, STKaiti, serif" />
      </el-select>
    </div>

    <div class="setting-group">
      <label>字号 {{ s.font_size }}px</label>
      <el-slider :model-value="s.font_size" :min="12" :max="40" @input="upd('font_size', $event)" />
    </div>

    <div class="setting-group">
      <label>行间距 {{ s.line_height }}</label>
      <el-slider :model-value="s.line_height" :min="1" :max="3" :step="0.1" @input="upd('line_height', $event)" />
    </div>

    <div class="setting-group">
      <label>页边距 {{ s.margin }}px</label>
      <el-slider :model-value="s.margin" :min="0" :max="80" @input="upd('margin', $event)" />
    </div>

    <p class="tip">PDF 采用原生渲染,字体/行距设置仅对 TXT/EPUB 生效。</p>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useReaderStore, type ReaderSettings } from '@/stores/reader'

const props = defineProps<{
  modelValue: boolean
  isComic?: boolean
  isMobile?: boolean
  bookId?: string
  bookDoublePage?: boolean
  bookStartRight?: boolean
}>()
const emit = defineEmits<{
  'update:modelValue': [boolean]
  'comicPrefsChanged': []
}>()

const store = useReaderStore()
const s = computed(() => store.settings)
const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})
const drawerSize = computed(() => (window.innerWidth < 600 ? '80%' : 360))

const STORAGE_KEY_PREFIX = 'nas-reader:comic-pref:'
const _prefsTick = ref(0) // localStorage 不是响应式,用 tick 触发刷新

function getStorageKey() {
  return `${STORAGE_KEY_PREFIX}${props.bookId || 'default'}`
}

function getLocalPrefs() {
  // 读之前先 touch 一下 tick 让 computed 依赖它
  void _prefsTick.value
  if (!props.bookId) return null
  try {
    const raw = localStorage.getItem(getStorageKey())
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

const hasOverride = computed(() => !!getLocalPrefs())

const doublePage = computed({
  get: () => {
    const local = getLocalPrefs()
    return local?.doublePage ?? props.bookDoublePage ?? false
  },
  set: () => {},
})
const startRight = computed({
  get: () => {
    const local = getLocalPrefs()
    return local?.startRight ?? props.bookStartRight ?? false
  },
  set: () => {},
})

function setComicPref(key: 'doublePage' | 'startRight', value: boolean) {
  const prefs = getLocalPrefs() || { doublePage: props.bookDoublePage ?? false, startRight: props.bookStartRight ?? false }
  prefs[key] = value
  localStorage.setItem(getStorageKey(), JSON.stringify(prefs))
  _prefsTick.value++ // 触发 computed 刷新
  emit('comicPrefsChanged')
}

function resetToDefault() {
  if (props.bookId) {
    localStorage.removeItem(getStorageKey())
    _prefsTick.value++
    emit('comicPrefsChanged')
  }
}

function upd<K extends keyof ReaderSettings>(key: K, value: ReaderSettings[K]) {
  store.update({ [key]: value } as Partial<ReaderSettings>)
}
</script>

<style scoped>
.setting-group { margin-bottom: 24px; padding: 0 4px; }
.setting-group label { display: block; margin-bottom: 8px; color: #606266; font-size: 14px; }
.comic-setting-row { display: flex; justify-content: space-between; align-items: center; margin: 8px 0; }
.override-hint { color: #409eff; font-size: 12px; }
.tip { color: #909399; font-size: 12px; padding: 0 4px; }
</style>
