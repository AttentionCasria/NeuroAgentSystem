<script setup>
import { ref, onMounted } from 'vue'
import pause from '@/utils/pause'

const typedText = ref('')
const cursorShow = ref(true)
const introductions = [
  '智联诊链——多智能体深度检索神经医疗机器人。',
  '融合医学文献与临床数据，助力智能诊疗。',
  '专注神经系统疾病，精准匹配症状与诊断。',
  '深度检索与分析，为患者提供科学建议。',
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
    white-space: pre;
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
