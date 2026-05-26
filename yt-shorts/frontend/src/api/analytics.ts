import client from './client'
import type { AnalyticsReport } from '../types'

export const analyticsApi = {
  getReport: (jobId: string) => client.get<AnalyticsReport>(`/analytics/${jobId}`).then(r => r.data),
  pull: (jobId: string) => client.post(`/analytics/${jobId}/pull`).then(r => r.data),
}
