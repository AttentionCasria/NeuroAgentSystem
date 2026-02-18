<script setup>
import { onMounted, ref } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import UserDialog from '@/components/UserDialog.vue'
import { useUserStore } from '@/stores/user'
import { deleteChatAPI, getChatHistoryAPI, getChatTitlesAPI, newChatStreamAPI, sendQuestionStreamAPI } from '@/api/talk'
import LoadingModel from '@/components/LoadingModel.vue'
defineOptions({ name: 'TalkIndex' })

const message = ref('')
const isDialogShow = ref(false)
const userStore = useUserStore()
const talkTitleList = ref([])  // 默认空数组
const inputRef = ref(null)

const currentTalkId = ref(0)       // 当前对话 ID，0 表示新对话
const currentTalkList = ref([])    // 当前对话消息列表

const canSendMessage = ref(true) // 防止重复发送

const loading = ref(false)  // 控制加载中模态框是否展示


marked.setOptions({
  gfm: true,
  breaks: true,
})

const renderMarkdown = (raw = '') => {
  return DOMPurify.sanitize(
    marked.parse(raw, {
      breaks: true,
      gfm: true
    })
  )
}



// 页面挂载时拉取历史对话
onMounted(async () => {
  await fetchTalkTitle()

  if (talkTitleList.value.length > 0) {
    currentTalkId.value = talkTitleList.value[0].talkId
    fetchTalkHistory(currentTalkId.value)
  }
})

// 拉取历史标题列表
async function fetchTalkTitle() {
  const res = await getChatTitlesAPI()


  if (res.data && res.data.length > 0) {
    talkTitleList.value = res.data
  }
}

// 点击切换历史对话
function handleClickTalkTitle(talkId) {
  currentTalkId.value = talkId
  fetchTalkHistory(talkId)
}

// 获取对话历史
async function fetchTalkHistory(talkId = currentTalkId.value) {
  const res = await getChatHistoryAPI(talkId)
  currentTalkList.value = res.data
}

// 点击开始新对话
function handleNewChat() {
  currentTalkId.value = 0
  currentTalkList.value = []

  // 删除已有占位
  talkTitleList.value = talkTitleList.value.filter(t => t.talkId !== 0)

  // 插入新占位标题，确保没有重复的talkId = 0后再插入
  if (!talkTitleList.value.some(t => t.talkId === 0)) {
    talkTitleList.value.unshift({ talkId: 0, title: '新对话' })
  }

  // 自动聚焦输入框
  if (inputRef.value) inputRef.value.focus()
}

// 发送消息
async function sendMessage() {
  const text = message.value.trim()
  if (text === '') return
  message.value = ''

  canSendMessage.value = false
  loading.value = true

  // 用户消息先 push
  currentTalkList.value.push(text)

  if (currentTalkId.value === 0) {
    // 新对话
    try {
      const res = await newChatStreamAPI({ question: text })
      const { talkId, title, content } = res.data

      currentTalkId.value = talkId

      // 替换占位标题
      const index = talkTitleList.value.findIndex(t => t.talkId === 0)
      if (index !== -1) talkTitleList.value[index] = { talkId, title }
      else talkTitleList.value.unshift({ talkId, title })

      currentTalkList.value.push(content)
    } catch (err) {
      console.error('新建对话失败', err)
      currentTalkList.value.pop() // 撤回用户消息
    }
  } else {
    // 继续对话
    try {
      const res2 = await sendQuestionStreamAPI({ talkId: currentTalkId.value, question: text })
      currentTalkList.value.push(res2.data.content)
    } catch (err) {
      console.error('发送消息失败', err)
      currentTalkList.value.pop() // 撤回用户消息
    }
  }

  canSendMessage.value = true
  loading.value = false
  window.location.reload() // 刷新，从新拉取数据
}

async function handleDeleteAll() {
  if (!confirm('确定要删除所有对话吗？此操作不可撤销！')) return

  if (!talkTitleList.value || talkTitleList.value.length === 0) return

  try {
    // 循环删除每个对话
    for (const talk of talkTitleList.value) {
      // 跳过占位（新对话占位 talkId = 0）
      if (talk.talkId === 0) continue
      await deleteChatAPI(talk.talkId)
    }

    // 清空前端列表和当前对话
    talkTitleList.value = []
    currentTalkList.value = []
    currentTalkId.value = 0

  } catch (err) {
    console.error('删除所有对话失败', err)
    alert('删除失败，请重试')
  }

  // 重置所有数据
  talkTitleList.value = []
  currentTalkId.value = 0
  currentTalkList.value = []


  // 拉取空列表
  fetchTalkTitle()
}

// 弹出用户信息弹窗
function handleUserClick() {
  isDialogShow.value = true
}

// 复制回答
function handleCopy(text) {
  if (!text) return

  // 优先使用现代 API
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text)
      .then(() => {
        alert('复制成功')
      })
      .catch(() => {
        fallbackCopy(text)
      })
  } else {
    fallbackCopy(text)
  }
}

// 兼容旧浏览器
function fallbackCopy(text) {
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.style.position = 'fixed'
  textarea.style.opacity = '0'
  document.body.appendChild(textarea)

  textarea.select()

  try {
    document.execCommand('copy')
    alert('复制成功')
  } catch (err) {
    console.error('复制失败', err)
    alert('复制失败')
  }

  document.body.removeChild(textarea)
}


</script>

<template>
  <LoadingModel v-model="loading" />

  <!-- 用户信息弹窗 -->
  <UserDialog :visible="isDialogShow" @close="isDialogShow = false"></UserDialog>

  <div class="container">
    <div class="chat-history">
      <div class="new-chat" @click="handleNewChat">开始新对话</div>
      <div class="delete-chat" @click="handleDeleteAll">删除所有对话</div>
      <h3>历史记录</h3>

      <!-- 左侧展示历史对话标题列表 -->
      <div class="chat-list">
        <div
          v-for="talk in talkTitleList"
          :key="talk.talkId"
          class="chat-item"
          :class="{ active: talk.talkId === currentTalkId }"
          @click="handleClickTalkTitle(talk.talkId)">
          <span class="title">{{ talk.title }}</span>
        </div>
      </div>
    </div>

    <div class="chat-panel">
      <!-- 渲染产品名称以及用户信息 -->
      <header class="chat-header">
        <span class="title">Synapse MD</span>
        <div class="user" @click="handleUserClick">
          <img :src="userStore.image" alt="avatar" />
          <p class="username">{{ userStore.name }}</p>
        </div>
      </header>

      <!-- 对话展示区 -->
      <main class="chat-messages">
        <div class="chat-content" v-if="currentTalkList.length > 0">
          <div
            v-for="(msg, i) in currentTalkList"
            :key="i"
            class="message-wrapper"
            :class="{ user: i % 2 === 0 }">

            <div
              class="message"
              :class="{ user: i % 2 === 0 }">

              <template v-if="i % 2 === 0">
                {{ msg }}
              </template>

              <div v-else class="markdown-body" v-html="renderMarkdown(msg)">
              </div>
            </div>

            <!-- 复制按钮 -->
            <button class="copy-btn" @click="handleCopy(msg)">
              复制
            </button>

          </div>

        </div>
        <div v-else class="empty">
          我可以帮助您什么？
        </div>
      </main>

      <!-- 输入区 -->
      <div class="input-box">
        <input type="text" ref="inputRef" placeholder="请输入您的问题" v-model="message" @keyup.enter="sendMessage" />
        <button class="send-btn" :disabled="message.trim() === '' || !canSendMessage" @click="sendMessage">
          <ArrowSVG color="#fff" size="24" />
        </button>
      </div>
    </div>
  </div>
</template>



<style scoped lang="scss">
* {
  color: #333;
}

.container {
  width: 100vw;
  height: 100vh;

  display: flex;
  background-color: #f7f9fc;

  .chat-history {
    width: 260px;
    background-color: #fff;
    padding: 10px;
    color: #333;
    border-right: 1px solid #e5e7eb;

    .new-chat,
    .delete-chat {
      margin: 15px auto;
      text-align: center;
      padding: 10px;
      transition: all 0.15s ease;
      cursor: pointer;
      font-size: 14px;
      border: 1px solid #e5e7eb;
      border-radius: 8px;
    }

    .new-chat {
      background-color: #07bf9b;
      color: #fff;
      border: none;
    }

    .new-chat:hover {
      background-color: #05a583;
    }

    .delete-chat {
      color: #ff4d4f;
      background-color: #fff;
    }

    .delete-chat:hover {
      background-color: #fff1f0;
      border-color: #ffa39e;
    }

    h3 {
      font-size: 14px;
      margin: 20px 10px 10px;
      color: #666;
    }

    .chat-list {
      max-height: calc(100vh - 200px);
      overflow-y: auto;

      .chat-item {
        padding: 10px 12px;
        border-radius: 8px;
        cursor: pointer;
        font-size: 14px;
        color: #4b5563;
        transition: all 0.15s ease;

        margin-bottom: 8px;

        .title {
          display: block;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        &:hover {
          background-color: #f3f4f6;
          color: #111827;
        }

        &.active {
          background-color: #eff6ff;
          color: #3b82f6;
          font-weight: 500;
        }
      }
    }
  }

  .chat-panel {
    flex: 1;
    background-color: #f7f9fc;
    display: flex;
    flex-direction: column;

    .chat-header {
      height: 60px;
      padding: 0 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      background-color: #fff;
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
      z-index: 10;

      .title {
        font-size: 18px;
        font-weight: 600;
        color: #3b82f6;
      }

      .user {
        display: flex;
        align-items: center;
        gap: 10px;
        cursor: pointer;
        padding: 4px 8px;
        border-radius: 20px;
        transition: background-color 0.2s;

        &:hover {
          background-color: #f3f4f6;
        }

        img {
          width: 32px;
          height: 32px;
          border-radius: 50%;
          border: 2px solid #eff6ff;
        }

        .username {
          font-weight: 500;
          font-size: 14px;
          color: #4b5563;
        }
      }
    }

    .chat-messages {
      flex: 1;
      display: flex;
      justify-content: center;
      overflow-y: auto;
      padding: 20px 0;

      .chat-content {
        width: 80%;
        max-width: 900px;
        display: flex;
        flex-direction: column;
        gap: 16px;
        padding-bottom: 40px;

        scrollbar-width: thin;
        scrollbar-color: #e5e7eb transparent;

        &::-webkit-scrollbar {
          width: 6px;
        }

        &::-webkit-scrollbar-thumb {
          background-color: #e5e7eb;
          border-radius: 10px;
        }

        .message {
          padding: 12px 20px;
          align-self: flex-start;
          border-radius: 12px;
          background-color: #fff;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
          border: 1px solid #e5e7eb;
          line-height: 1.6;
          display: inline-block;
          width: auto;
          max-width: 85%;
          word-break: break-word;
          overflow-wrap: anywhere;
          color: #374151;

          .markdown-body {
            color: #374151;
            font-size: 15px;
            line-height: 1.6;
            white-space: pre-wrap;
          }

          :deep(.markdown-body pre) {
            background-color: #f8fafc;
            padding: 12px;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
            overflow-x: auto;
          }

          :deep(.markdown-body code) {
            font-family: 'Fira Code', 'Consolas', monospace;
            background-color: #f1f5f9;
            color: #ef4444;
            padding: 2px 4px;
            border-radius: 4px;
          }

          &.user {
            background-color: #3b82f6;
            border-radius: 12px 12px 0 12px;
            align-self: flex-end;
            display: inline-block;
            width: auto;
            max-width: 85%;
            color: #fff;
            border: none;
            box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.2);

            * {
              color: #fff;
            }
          }
        }

        .message-wrapper {
          display: flex;
          flex-direction: column;
          position: relative;

          &.user {
            align-items: flex-end;
          }

          &:hover .copy-btn {
            opacity: 1;
          }
        }

        .copy-btn {
          margin-top: 4px;
          font-size: 12px;
          background: transparent;
          border: none;
          color: #9ca3af;
          cursor: pointer;
          opacity: 0;
          transition: opacity 0.2s ease;

          &:hover {
            color: #3b82f6;
          }
        }
      }

      .empty {
        display: flex;
        justify-content: center;
        align-items: center;
        font-size: 32px;
        font-weight: 600;
        text-shadow: 0 1px 0 #fff;
      }
    }

    .input-box {
      width: 80%;
      max-width: 800px;
      margin: 0 auto 30px auto;
      display: flex;
      align-items: center;
      padding: 8px 16px;
      border-radius: 16px;
      background-color: #fff;
      box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
      border: 1px solid #e5e7eb;
      box-sizing: border-box;
      transition: all 0.2s ease;

      &:focus-within {
        border-color: #3b82f6;
        box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.1);
      }

      input {
        flex: 1;
        height: 44px;
        padding: 0 12px;
        border: none;
        outline: none;
        background-color: transparent;
        font-size: 16px;
        color: #1f2937;

        &::placeholder {
          color: #9ca3af;
        }
      }

      .send-btn {
        width: 36px;
        height: 36px;
        margin-left: 12px;
        border-radius: 10px;
        border: none;
        background-color: #3b82f6;
        color: #fff;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        transition: all 0.2s ease;

        &:hover:not(:disabled) {
          transform: translateY(-1px);
          box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.3);
        }

        &:active:not(:disabled) {
          transform: translateY(0);
        }

        &:disabled {
          background-color: #f3f4f6;
          cursor: not-allowed;

          :deep(svg) {
            color: #d1d5db !important;
          }
        }
      }
    }
  }
}
</style>
