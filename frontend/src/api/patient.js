import request from '@/utils/request'

export const getPatientsAPI = ({ page = 1, size = 10, filter = {} } = {}) =>
  request.get('/patients', {
    params: {
      page,
      size,
      name: filter.name || undefined,
      diseases: filter.diseases || undefined,
    },
  })

export const getPatientDetailAPI = (id) => request.get(`/patients/${id}`)

export const createPatientAPI = (data) => request.post('/patients', data)

export const updatePatientAPI = (id, data) => request.put(`/patients/${id}`, data)

export const deletePatientAPI = (id) => request.delete(`/patients/${id}`)
