<template>
  <!-- 使用方式：<LoadingModal v-model="loading" /> -->
  <transition name="fade">
    <div
      v-if="show"
      class="lm-overlay"
      role="dialog"
      aria-modal="true"
      aria-label="加载中对话框"
      @click.self="tryClose">
      <div class="lm-container" @click.stop>
        <div class="lm-spinner" aria-hidden="true"></div>
        <div class="lm-message">{{ message }}</div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { watch, onMounted, onBeforeUnmount, computed } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, required: true },
  message: { type: String, default: '加载中...' },
  disableClose: { type: Boolean, default: true }, // true：不允许通过点击遮罩或 ESC 关闭
})
const emit = defineEmits(['update:modelValue'])

const show = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

// 防止背景滚动
watch(
  () => show.value,
  (val) => {
    if (val) document.body.style.overflow = 'hidden'
    else document.body.style.overflow = ''
  },
  { immediate: true }
)

// ESC 键处理（只有在 disableClose=false 时允许关闭）
function onKeydown(e) {
  if (e.key === 'Escape' || e.key === 'Esc') {
    if (!props.disableClose) show.value = false
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  document.body.style.overflow = ''
})

function tryClose() {
  if (!props.disableClose) show.value = false
}
</script>

<style scoped>
/* 遮罩 */
.lm-overlay {
  position: fixed;
  inset: 0;
  /* top:0; right:0; bottom:0; left:0 */
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.5);
  z-index: 10000;
  -webkit-tap-highlight-color: transparent;
}

/* 容器 */
.lm-container {
  min-width: 220px;
  max-width: 90%;
  padding: 20px 28px;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  pointer-events: auto;
  /* 保证容器内元素可交互（虽然没有交互） */
}

/* 圆形加载器（将通过 border 创建动画） */
.lm-spinner {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  border: 6px solid rgba(0, 0, 0, 0.08);
  border-top-color: #07bf9b;
  /* accent color */
  animation: lm-spin 1s linear infinite;
}

@keyframes lm-spin {
  to {
    transform: rotate(360deg);
  }
}

.lm-message {
  font-size: 14px;
  color: #222;
  text-align: center;
}

/* 简单淡入效果 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 180ms ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
