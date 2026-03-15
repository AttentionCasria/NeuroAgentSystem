<script setup>
import { nextTick, ref, watch } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import DeleteSVG from '@/components/svg/DeleteSVG.vue'
import DeleteAllSVG from '@/components/svg/DeleteAllSVG.vue'

defineOptions({ name: 'ChatWorkspace' })

marked.setOptions({ gfm: true, breaks: true })

const props = defineProps({
  talkTitleList: {
    type: Array,
    default: () => [],
  },
  currentTalkId: {
    type: Number,
    default: 0,
  },
  currentTalkList: {
    type: Array,
    default: () => [],
  },
  isStreaming: {
    type: Boolean,
    default: false,
  },
  chatLoading: {
    type: Boolean,
    default: false,
  },
  patients: {
    type: Array,
    default: () => [],
  },
  syncPatientId: {
    type: [Number, null],
    default: null,
  },
  syncPatient: {
    type: Object,
    default: null,
  },
  conversationPreview: {
    type: Array,
    default: () => [],
  },
  canSyncConversation: {
    type: Boolean,
    default: false,
  },
  syncResult: {
    type: Object,
    default: null,
  },
})

const syncPatientModel = defineModel('syncPatientId', { default: null })

const emit = defineEmits([
  'select-talk',
  'new-chat',
  'delete-chat',
  'delete-all',
  'send-message',
  'sync-conversation',
  'open-patient-workspace',
])

const draftMessage = ref('')
const inputRef = ref(null)
const chatContainerRef = ref(null)

watch(
  () => props.currentTalkList.length,
  () => {
    nextTick(scrollToBottom)
  },
)

watch(
  () => props.currentTalkId,
  () => {
    draftMessage.value = ''
    nextTick(() => {
      autoResize()
      scrollToBottom()
    })
  },
)

watch(draftMessage, () => {
  nextTick(autoResize)
})

const renderMarkdown = (raw = '') => {
  if (!raw) return ''

  return DOMPurify.sanitize(
    marked.parse(String(raw), {
      breaks: true,
      gfm: true,
    }),
  )
}

function autoResize() {
  const element = inputRef.value
  if (!element) return
  element.style.height = 'auto'
  element.style.height = `${Math.min(element.scrollHeight, 220)}px`
}

function scrollToBottom() {
  const element = chatContainerRef.value
  if (!element) return
  element.scrollTop = element.scrollHeight
}

function handleSendMessage() {
  const text = draftMessage.value.trim()
  if (!text || props.isStreaming) return
  emit('send-message', text)
  draftMessage.value = ''
  nextTick(autoResize)
}

function handleCopy(text) {
  if (!text) return

  if (navigator.clipboard?.writeText) {
    navigator.clipboard.writeText(text).then(() => alert('复制成功')).catch(() => fallbackCopy(text))
    return
  }

  fallbackCopy(text)
}

function fallbackCopy(text) {
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.style.position = 'fixed'
  textarea.style.opacity = '0'
  document.body.appendChild(textarea)
  textarea.select()
  document.execCommand('copy')
  document.body.removeChild(textarea)
  alert('复制成功')
}

function formatDateTime(value) {
  if (!value) return '暂无时间'

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value

  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function shortText(value, fallback = '暂无内容') {
  const text = String(value || '').trim()
  return text || fallback
}
</script>

<template>
  <section class="chat-workspace">
    <aside class="history-card section-card">
      <div class="section-head">
        <div>
          <h3>对话历史</h3>
        </div>
        <button type="button" class="ghost-icon danger" @click="emit('delete-all')">
          <DeleteAllSVG size="20" color="currentColor" />
        </button>
      </div>

      <button type="button" class="primary-action" @click="emit('new-chat')">开始新对话</button>

      <div class="history-list">
        <div v-for="talk in talkTitleList" :key="talk.talkId" class="history-item"
          :class="{ active: talk.talkId === currentTalkId }" @click="emit('select-talk', talk.talkId)">
          <div>
            <p class="history-title">{{ talk.title }}</p>
            <small>{{ talk.talkId === 0 ? '待发送问题' : `会话 #${talk.talkId}` }}</small>
          </div>
          <button type="button" class="ghost-icon" @click.stop="emit('delete-chat', talk.talkId)">
            <DeleteSVG size="16" color="currentColor" />
          </button>
        </div>

        <div v-if="!talkTitleList.length" class="empty-card compact">还没有历史对话，开始一轮新的问诊即可生成记录。</div>
      </div>
    </aside>

    <div class="chat-card section-card">
      <div class="section-head">
        <h3>实时问诊</h3>
        <span class="state-pill" :class="{ live: isStreaming }">{{ isStreaming ? '生成中' : '待输入' }}</span>
      </div>

      <main ref="chatContainerRef" class="chat-messages">
        <div v-if="chatLoading" class="empty-card">正在加载历史对话...</div>

        <div v-else-if="currentTalkList.length" class="message-stack">
          <article v-for="(msg, index) in currentTalkList" :key="`${index}-${msg}`" class="message-wrapper"
            :class="{ user: index % 2 === 0 }">
            <div class="message-meta">
              <span>{{ index % 2 === 0 ? '医生输入' : 'AI回复' }}</span>
              <button type="button" class="copy-btn" @click="handleCopy(msg)">复制</button>
            </div>

            <div class="message" :class="{ user: index % 2 === 0 }">
              <template v-if="index % 2 === 0">{{ msg }}</template>
              <div v-else class="markdown-body" v-html="renderMarkdown(msg)"></div>
            </div>
          </article>
        </div>

        <div v-else class="empty-card">输入症状、病史或问题后，AI会在这里持续生成回复。</div>
      </main>

      <div class="input-box">
        <textarea ref="inputRef" v-model="draftMessage" rows="1" placeholder="请输入症状、病史或希望AI分析的问题" @input="autoResize"
          @keydown.enter.exact.prevent="handleSendMessage" />
        <button type="button" class="send-btn" :disabled="!draftMessage.trim() || isStreaming"
          @click="handleSendMessage">
          <ArrowSVG color="#ffffff" size="20" />
        </button>
      </div>
    </div>

    <aside class="sync-card section-card">
      <div class="section-head compact">
        <div>
          <h3>同步到患者AI意见</h3>
          <p>将当前对话内容合并到指定患者的健康建议。</p>
        </div>
      </div>

      <label class="field-label">
        关联患者
        <select v-model="syncPatientModel">
          <option :value="null">请选择患者</option>
          <option v-for="patient in patients" :key="patient.id" :value="patient.id">{{ patient.name }}</option>
        </select>
      </label>

      <div v-if="syncPatient" class="summary-card">
        <p class="summary-label">当前同步目标</p>
        <h4>{{ syncPatient.name }}</h4>
        <p>{{ shortText(syncPatient.history) }}</p>
        <button type="button" class="link-btn" @click="emit('open-patient-workspace', syncPatient.id)">查看患者详情</button>
      </div>

      <div class="preview-box">
        <div class="preview-head">
          <span>待同步片段</span>
          <small>{{ currentTalkId ? `对话 #${currentTalkId}` : '新对话未落库' }}</small>
        </div>
        <div v-if="conversationPreview.length" class="preview-list">
          <article v-for="(item, index) in conversationPreview" :key="`${item.role}-${index}`" class="preview-item">
            <strong>{{ item.role === 'user' ? '问' : '答' }}</strong>
            <p>{{ item.content }}</p>
          </article>
        </div>
        <div v-else class="empty-card compact">至少完成一轮问答后，才可以执行同步。</div>
      </div>

      <button type="button" class="primary-action" :disabled="!canSyncConversation" @click="emit('sync-conversation')">
        同步当前对话
      </button>

      <div v-if="syncResult?.aiOpinion" class="result-card">
        <p class="summary-label">最近同步结果</p>
        <h4>{{ syncResult.aiOpinion.riskLevel || '已更新' }}</h4>
        <p>{{ syncResult.aiOpinion.suggestion }}</p>
        <small>{{ formatDateTime(syncResult.aiOpinion.lastUpdatedAt) }}</small>
      </div>
    </aside>
  </section>
</template>

<style scoped lang="scss">
.chat-workspace {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr) 360px;
  gap: 18px;
  min-height: 0;
}

.section-card {
  border: 1px solid rgba(217, 230, 226, 0.95);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 20px 45px rgba(15, 65, 79, 0.12);
  padding: 20px;
}

.section-head,
.preview-head,
.message-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.preview-head {
  margin-bottom: 12px;
}

.section-head.compact {
  align-items: flex-start;
}

.section-head h3,
.summary-card h4,
.result-card h4 {
  margin: 0;
}

.section-head p,
.history-item small,
.empty-card,
.message-meta,
.preview-item p,
.summary-card p,
.result-card p,
.result-card small {
  color: #5e7379;
}

.primary-action,
.send-btn,
.ghost-icon {
  border: none;
  cursor: pointer;
  transition: all 0.18s ease;
}

.primary-action,
.send-btn {
  background: linear-gradient(135deg, #11967f 0%, #0f7666 100%);
  color: #ffffff;
}

.primary-action {
  padding: 11px 16px;
  border-radius: 14px;
  font-weight: 700;
}

.ghost-icon {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: rgba(236, 245, 243, 0.82);
  color: #5e7379;
}

.ghost-icon:hover,
.primary-action:hover,
.send-btn:hover {
  transform: translateY(-1px);
}

.ghost-icon.danger:hover {
  color: #dc2626;
  background: rgba(239, 68, 68, 0.1);
}

.history-card,
.sync-card {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
}

.history-list,
.message-stack,
.preview-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.history-list {
  min-height: 0;
  overflow-y: auto;
}

.history-item,
.preview-box,
.summary-card,
.result-card {
  border: 1px solid rgba(217, 230, 226, 0.95);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.86);
}

.history-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 15px 16px;
  cursor: pointer;
  transition: all 0.18s ease;
}

.history-item:hover,
.history-item.active {
  border-color: rgba(17, 150, 127, 0.28);
  background: rgba(240, 249, 247, 0.96);
}

.history-title,
.preview-item p {
  margin: 0;
}

.chat-card {
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 245px);
}

.state-pill {
  padding: 7px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  background: rgba(148, 163, 184, 0.14);
  color: #475569;
}

.state-pill.live {
  background: rgba(17, 150, 127, 0.14);
  color: #0f7666;
}

.chat-messages {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 18px 4px 8px 0;
}

.message-wrapper {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-start;
}

.message-wrapper.user {
  align-items: flex-end;
}

.copy-btn,
.link-btn {
  border: none;
  background: transparent;
  padding: 0;
  color: #0f7666;
  cursor: pointer;
}

.message {
  max-width: min(84%, 880px);
  padding: 16px 18px;
  border-radius: 22px 22px 22px 8px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(217, 230, 226, 0.95);
  line-height: 1.72;
  color: #17313a;
}

.message.user {
  background: linear-gradient(135deg, rgba(17, 150, 127, 0.14), rgba(17, 118, 102, 0.08));
  border-radius: 22px 22px 8px 22px;
}

.input-box {
  margin-top: 16px;
  padding: 14px;
  border: 1px solid rgba(217, 230, 226, 0.95);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.92);
  display: grid;
  grid-template-columns: minmax(0, 1fr) 52px;
  gap: 12px;
}

.input-box textarea,
.field-label select {
  width: 100%;
  box-sizing: border-box;
  font: inherit;
  color: #17313a;
}

.input-box textarea {
  border: none;
  outline: none;
  resize: none;
  min-height: 42px;
  max-height: 220px;
  background: transparent;
  line-height: 1.6;
}

.send-btn {
  width: 52px;
  height: 52px;
  border-radius: 16px;
}

.send-btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
  transform: none;
}

.field-label {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-weight: 700;
  color: #17313a;
}

.field-label select {
  border: 1px solid rgba(191, 213, 207, 0.95);
  background: rgba(249, 252, 252, 0.96);
  border-radius: 14px;
  padding: 12px 14px;
}

.preview-box,
.summary-card,
.result-card {
  padding: 16px;
}

.summary-label {
  margin: 0;
  font-size: 12px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #2c7c6e;
}

.preview-item {
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr);
  gap: 10px;
}

.preview-item strong {
  color: #0f7666;
}

.empty-card {
  padding: 24px;
  border-radius: 18px;
  background: rgba(248, 251, 251, 0.88);
  border: 1px dashed rgba(169, 195, 190, 0.9);
  line-height: 1.7;
}

.empty-card.compact {
  padding: 16px;
}

.markdown-body :deep(p:first-child) {
  margin-top: 0;
}

.markdown-body :deep(p:last-child) {
  margin-bottom: 0;
}

.markdown-body :deep(pre) {
  overflow-x: auto;
  border-radius: 14px;
  padding: 12px;
  background: #0f172a;
}

@media (max-width: 1400px) {
  .chat-workspace {
    grid-template-columns: 280px minmax(0, 1fr);
  }

  .sync-card {
    grid-column: 1 / -1;
  }
}

@media (max-width: 960px) {
  .chat-workspace {
    grid-template-columns: 1fr;
  }

  .chat-card {
    min-height: 560px;
  }
}

@media (max-width: 640px) {

  .input-box,
  .section-head,
  .preview-head,
  .message-meta {
    flex-direction: column;
    align-items: stretch;
  }

  .message {
    max-width: 100%;
  }
}
</style>
