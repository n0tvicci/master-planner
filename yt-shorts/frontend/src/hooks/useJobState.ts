import { useEffect, useState } from 'react'
import { pipelineApi } from '../api/pipeline'
import type { PipelineState } from '../types'

export function useJobState(jobId: string | null, ms = 3000) {
  const [state, setState] = useState<PipelineState | null>(null)
  useEffect(() => {
    if (!jobId) return
    const fetch = () => pipelineApi.getState(jobId).then(setState).catch(() => {})
    fetch()
    const id = setInterval(fetch, ms)
    return () => clearInterval(id)
  }, [jobId, ms])
  return state
}
