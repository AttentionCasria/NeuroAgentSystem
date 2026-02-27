import { useUserStore } from '@/stores/user'
import request from '@/utils/request'

// 1. 获取历史对话标题
export const getChatTitlesAPI = () => request.get('/user/title')

// 2. 查询历史对话内容
// talkId: Number
export const getChatHistoryAPI = (talkId) => request.get(`/user/ques/getQues/${talkId}`)

// 3. 继续对话（发送问题）
// params = { talkId: Number, question: String }
export const sendQuestionAPI = (params) => request.post('/user/ques/getQues', params)

// 4. 新建对话
// params = { question: String }
export const newChatAPI = (params) => request.post('/user/ques/newGetQues', params)

// api/talk.js
// api/talk.js

function streamRequest(params, onChunk) {
  const userStore = useUserStore()
  const token = userStore.token

  return new Promise((resolve, reject) => {
    fetch('/api/user/ques/streamingQues', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        token,
      },
      body: JSON.stringify(params),
    })
      .then((res) => {
        if (!res.body) {
          reject(new Error('ReadableStream 不存在'))
          return
        }

        const reader = res.body.getReader()
        const decoder = new TextDecoder('utf-8')

        let fullAnswer = ''
        let realTalkId = null
        let title = '回答'
        let finished = false

        function safeResolve(payload) {
          if (finished) return
          finished = true
          resolve(payload)
        }

        function readChunk() {
          reader
            .read()
            .then(({ value, done }) => {
              if (done) {
                // ⚠️ 不在这里 resolve
                return
              }

              const chunk = decoder.decode(value, { stream: true })

              chunk.split('\n\n').forEach((block) => {
                if (!block.startsWith('data:')) return

                const jsonStr = block.replace(/^data:\s*/, '').trim()
                if (!jsonStr) return

                try {
                  const data = JSON.parse(jsonStr)

                  if (data.type === 'init') {
                    realTalkId = data.talkId
                  } else if (data.type === 'chunk') {
                    const text = data.content || ''
                    fullAnswer += text
                    if (onChunk) onChunk(text)
                  } else if (data.type === 'done') {
                    title = data.title || title

                    safeResolve({
                      data: {
                        talkId: realTalkId,
                        title,
                        content: fullAnswer,
                      },
                    })
                  }
                } catch (e) {
                  console.error('解析流失败', e)
                }
              })

              readChunk()
            })
            .catch(reject)
        }

        readChunk()
      })
      .catch(reject)
  })
}

export const sendQuestionStreamAPI = (params, onChunk) => streamRequest(params, onChunk)

export const newChatStreamAPI = (params, onChunk) => streamRequest(params, onChunk)

// 5. 删除对话
// talkId: Number
export const deleteChatAPI = (talkId) => request.delete(`/user/deleteTalk/${talkId}`)
