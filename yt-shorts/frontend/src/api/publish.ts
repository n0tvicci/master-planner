import client from './client'
import type { Metadata, UploadWindow } from '../types'

export const publishApi = {
  getWindow: () => client.get<UploadWindow>('/publish/window').then(r => r.data),
  getMetadata: (jobId: string) => client.get<Metadata>(`/publish/${jobId}/metadata`).then(r => r.data),
  upload: (jobId: string, dryRun = false) =>
    client.post(`/publish/${jobId}/upload`, null, { params: { dry_run: dryRun } }).then(r => r.data),
  streamUrl: (jobId: string) => `/api/v1/publish/${jobId}/stream`,
}
