<script setup>
import { ref } from 'vue'

defineOptions({ name: 'TestIndex' })

const text = ref('这是一段用于测试复制功能的文本')

// 复制方法
function handleCopy() {
  navigator.clipboard.writeText(text.value)
    .then(() => {
      alert('复制成功')
    })
    .catch(() => {
      alert('复制失败')
    })
}
</script>

<template>
  <div class="container">
    <p class="content">{{ text }}</p>
    <button @click="handleCopy">复制</button>
  </div>
</template>

<style scoped>
.container {
  padding: 40px;
  font-size: 18px;
}

button {
  margin-top: 20px;
  padding: 8px 16px;
  cursor: pointer;
}
</style>
