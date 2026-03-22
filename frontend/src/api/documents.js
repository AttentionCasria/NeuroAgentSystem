import request from '@/utils/request'

/** GET /api/documents — 按分类分组的文档列表 */
export const getDocumentsAPI = () => request.get('/documents')

/** GET /api/documents/{id}/url — 获取预览 + 下载签名 URL */
export const getDocumentUrlAPI = (id) => request.get(`/documents/${id}/url`)

/** GET /api/documents/match?name=xxx — AI 文献名模糊匹配 */
export const matchDocumentAPI = (name) => request.get('/documents/match', { params: { name } })
