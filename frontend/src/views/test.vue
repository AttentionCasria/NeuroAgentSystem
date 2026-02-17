<script setup>
import { ref } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import LoadingModel from '@/components/LoadingModel.vue'

defineOptions({
  name: 'TestIndex',
})

// 建议直接在 parse 里传参数
const renderMarkdown = (raw = '') => {
  const parsed = marked.parse(raw, {
    gfm: true,
    breaks: true
  })

  console.log('原始内容:', raw)
  console.log('marked解析后:', parsed)

  return DOMPurify.sanitize(parsed)
}

// 测试文本
const testText = ref(`
这是普通文本

这是 **加粗文本**

这是 *斜体*

这是 ***加粗斜体***

# 标题测试

- 列表1
- 列表2
`)

// 加载状态
const loading = ref(true)
</script>

<template>
  <div style="padding:40px">
    <h2>原始 Markdown</h2>
    <pre>{{ testText }}</pre>

    <h2>解析后效果</h2>
    <div class="markdown-body" v-html="renderMarkdown(testText)"></div>

    <LoadingModel v-model="loading" />
  </div>
</template>

<style scoped lang="scss">
/* 强制测试 strong 是否被覆盖 */
strong {
  color: red;
  font-weight: bold;
}
</style>
