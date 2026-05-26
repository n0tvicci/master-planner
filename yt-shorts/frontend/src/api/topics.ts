import client from './client'
import type { Topic } from '../types'

export const topicsApi = {
  getPending: () => client.get<Topic[]>('/topics/pending').then(r => r.data),
  getQueue: () => client.get<Topic[]>('/topics/queue').then(r => r.data),
  generate: () => client.post('/topics/generate').then(r => r.data),
  approve: (id: string) => client.post(`/topics/${id}/approve`).then(r => r.data),
  reject: (id: string) => client.post(`/topics/${id}/reject`).then(r => r.data),
}
