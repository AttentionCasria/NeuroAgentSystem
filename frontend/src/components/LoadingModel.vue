<template>
  <transition name="fade">
    <div v-if="show" class="lm-overlay" role="dialog" aria-modal="true" aria-label="加载中对话框">
      <div class="lm-container">
        <div class="lm-spinner"></div>

        <div class="lm-message">
          <div class="lm-main">医疗助手正在认真思考中 ⏳</div>
          <div class="lm-sub">模型回答大约需要 3 分钟，请耐心等待</div>
          <div class="lm-tip">{{ currentTip }}</div>
        </div>

      </div>
    </div>
  </transition>
</template>


<script setup>
import { watch, onMounted, onBeforeUnmount, computed, ref } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, required: true },
  disableClose: { type: Boolean, default: true },
})

const emit = defineEmits(['update:modelValue'])

const show = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

// 🧠 脑卒中医学常识
const tips = [
  '脑卒中（中风）发作后越早送医，恢复可能性越大。',
  '出现口角歪斜、言语不清、肢体无力应立即就医。',
  '高血压是脑卒中的重要危险因素，要定期监测。',
  '突然单侧肢体麻木或无力是危险信号。',
  '中风抢救有“黄金4.5小时”原则。',
  '长期吸烟和饮酒会增加脑卒中风险。',
  '糖尿病患者更容易发生脑血管意外。',
  '发现异常症状，千万不要等待自行恢复。',
]

const currentTip = ref('')
let timer = null

function changeTip() {
  const index = Math.floor(Math.random() * tips.length)
  currentTip.value = tips[index]
}

// 防止背景滚动
watch(
  () => show.value,
  (val) => {
    if (val) {
      document.body.style.overflow = 'hidden'
      changeTip()
      timer = setInterval(changeTip, 7000)
    } else {
      document.body.style.overflow = ''
      clearInterval(timer)
    }
  },
  { immediate: true }
)

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
  clearInterval(timer)
})

// function tryClose() {
//   if (!props.disableClose) show.value = false
// }
</script>


<style scoped>
/* 遮罩 */
.lm-overlay {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-overlay-bg);
  z-index: 10000;
  -webkit-tap-highlight-color: transparent;
}

/* 容器 */
.lm-container {
  min-width: 220px;
  max-width: 90%;
  padding: 20px 28px;
  border-radius: var(--radius-md);
  background: var(--color-bg-base);
  box-shadow: var(--shadow-card);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  pointer-events: auto;
}

/* 圆形加载器 */
.lm-spinner {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  border: 6px solid var(--color-border-light);
  border-top-color: var(--color-primary-light);
  animation: lm-spin 1s linear infinite;
}

@keyframes lm-spin {
  to {
    transform: rotate(360deg);
  }
}

.lm-message {
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.lm-main {
  font-size: 15px;
  font-weight: 600;
}

.lm-sub {
  font-size: 13px;
  color: var(--color-text-medium);
}

.lm-tip {
  margin-top: 6px;
  font-size: 12px;
  color: var(--color-primary-light);
  opacity: 0.9;
}
</style>
