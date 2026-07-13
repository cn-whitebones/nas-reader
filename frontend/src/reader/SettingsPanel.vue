<template>
  <el-drawer v-model="visible" title="阅读设置" :size="drawerSize" direction="rtl">
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
import { computed } from 'vue'
import { useReaderStore, type ReaderSettings } from '@/stores/reader'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [boolean] }>()

const store = useReaderStore()
const s = computed(() => store.settings)
const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})
const drawerSize = computed(() => (window.innerWidth < 600 ? '80%' : 360))

function upd<K extends keyof ReaderSettings>(key: K, value: ReaderSettings[K]) {
  store.update({ [key]: value } as Partial<ReaderSettings>)
}
</script>

<style scoped>
.setting-group { margin-bottom: 24px; padding: 0 4px; }
.setting-group label { display: block; margin-bottom: 8px; color: #606266; font-size: 14px; }
.tip { color: #909399; font-size: 12px; padding: 0 4px; }
</style>
