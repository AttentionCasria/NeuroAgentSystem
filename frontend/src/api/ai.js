import request from '@/utils/request'

export const analyzePatientAPI = (data) => request.post('/ai/analyze', data)

export const syncTalkToPatientAPI = (data) => request.post('/ai/sync-talk', data)
