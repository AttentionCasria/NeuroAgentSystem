import request from '@/utils/request'

export const getLearningMaterialsAPI = ({ category = '', page = 1, size = 10 } = {}) =>
  request.get('/learning-materials', {
    params: {
      category: category || undefined,
      page,
      size,
    },
  })

export const getLearningMaterialDetailAPI = (id) => request.get(`/learning-materials/${id}`)
