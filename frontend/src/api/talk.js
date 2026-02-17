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

// api/questionAPI.js
function streamRequest(params, onChunk) {
  const userStore = useUserStore()
  const token = userStore.token
  return new Promise((resolve, reject) => {
    fetch('/api/user/ques/streamingQues', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        token: token,
      },
      body: JSON.stringify(params),
    })
      .then((res) => {
        // 处理 401 错误
        // if (res.status === 401) {
        //   userStore.reset()
        //   router.push('/login')
        //   reject(new Error('Unauthorized'))
        //   return
        // }

        const reader = res.body.getReader()
        const decoder = new TextDecoder('utf-8')
        let fullAnswer = ''

        function readChunk() {
          reader
            .read()
            .then(({ value, done }) => {
              if (done) {
                // 最终包装成原来的接口格式
                resolve({
                  data: { talkId: params.talkId || Date.now(), title: '回答', content: fullAnswer },
                })
                return
              }

              const chunk = decoder.decode(value)
              chunk.split('\n\n').forEach((line) => {
                if (line.startsWith('data:')) {
                  const msg = line.replace(/^data:\s*/, '')
                  if (msg === '[完成]') {
                    // 流结束
                    resolve({
                      data: {
                        talkId: params.talkId || Date.now(),
                        title: '回答',
                        content: fullAnswer,
                      },
                    })
                  } else if (!msg.startsWith('[开始处理]') && !msg.startsWith('[错误]')) {
                    fullAnswer += msg
                    if (onChunk) onChunk(msg)
                  }
                }
              })

              readChunk()
            })
            .catch((err) => reject(err))
        }

        readChunk()
      })
      .catch((err) => reject(err))
  })
}
//    ------ 流形式 --------
// 继续对话
export const sendQuestionStreamAPI = (params, onChunk) => streamRequest(params, onChunk)

// 新建对话
export const newChatStreamAPI = (params, onChunk) => streamRequest(params, onChunk)

// 5. 删除对话
// talkId: Number
export const deleteChatAPI = (talkId) => request.delete(`/user/deleteTalk/${talkId}`)
