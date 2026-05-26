import client from './client'
import type { JobInfo, PipelineState } from '../types'

export const pipelineApi = {
  getJobs: () => client.get<JobInfo[]>('/pipeline/jobs').then(r => r.data),
  getState: (jobId: string) => client.get<PipelineState>(`/pipeline/${jobId}/state`).then(r => r.data),
  run: () => client.post<{ job_id: string; topic: string }>('/pipeline/run').then(r => r.data),
  streamUrl: (jobId: string) => `/api/v1/pipeline/${jobId}/stream`,
}
