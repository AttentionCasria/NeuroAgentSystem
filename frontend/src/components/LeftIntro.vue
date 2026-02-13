<script setup>
import { ref, onMounted } from 'vue'
import pause from '@/utils/pause'

const typedText = ref('')
const cursorShow = ref(true)
const introductions = [
  '脑卒中深度检索健康Agent助手——以循证医学为引擎的智能临床辅助平台。',
  '融合现代医学最新指南与权威文献，提供基于证据的深度思考与分析。',
  '专注脑卒中全周期管理，从风险预警、急性识别到康复导航。',
  '以可靠信息降低认知负荷，为诊疗决策提供清晰、更新的知识支持。'
]


const introShow = ref(true)

defineOptions({
  name: 'LoginView',
})

onMounted(async () => {
  // 开启打字机
  startTyping()
})

// 开始打字，循环遍历每一条介绍语
async function startTyping() {
  let index = 0
  while (true) {
    await pause(1000)
    introShow.value = true
    await typing(introductions[index])
    await pause(1000)
    introShow.value = false

    index = (index + 1) % introductions.length
  }
}

// 打字机效果，第一个参数是要呈现的文字，第二个参数是打字延迟时间
function typing(text, delay = 100) {
  return new Promise((resolve) => {
    let index = 0
    typedText.value = ''
    cursorShow.value = true

    const interval = setInterval(() => {
      typedText.value += text[index]
      index++
      if (index === text.length) {
        clearInterval(interval)
        cursorShow.value = false
        resolve()
      }
    }, delay)
  })
}
</script>

<template>
  <div class="title">Synapse MD</div>
  <transition>
    <div class="intro" v-show="introShow">
      <span class="typing-text">{{ typedText }}</span>
      <span class="cursor" v-show="cursorShow">●</span>
    </div>
  </transition>
</template>

<style scoped lang="scss">
.v-enter-active,
.v-leave-active {
  transition: all 0.15s ease;
}

.v-enter-from {
  opacity: 0;
}

.v-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}

.title {
  font-size: 2rem;
  margin-bottom: 2rem;
}

.intro {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  text-align: center;

  .typing-text {
    white-space: pre-wrap;
    word-break: break-word;
  }

  // 打字机前面的圈圈以及其动画
  .cursor {
    margin-left: 0.3rem;
    color: #d292ff;
    animation: blink 1s infinite;
    font-size: 2rem;
  }

  @keyframes blink {

    0%,
    100% {
      opacity: 1;
    }

    50% {
      opacity: 0;
    }
  }
}
</style>
