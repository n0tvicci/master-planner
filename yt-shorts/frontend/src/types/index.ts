export interface Topic {
  id: string
  title: string
  tier: number
  tier_score?: number
  hook_object?: string
  status?: string
  created_at?: string
  title_options?: string[]
}

export interface PipelineState {
  job_id: string
  completed_steps: string[]
  running?: boolean
  video_id?: string
}

export interface JobInfo {
  job_id: string
  completed_steps: string[]
  running: boolean
}

export interface Metadata {
  title: string
  description: string
  tags: string[]
  pinned_comment: string
}

export interface UploadWindow {
  in_window: boolean
  next_window: string
}

export interface AnalyticsReport {
  us_share: number
  flag: 'GREEN' | 'YELLOW' | 'RED'
  notes?: string
  country_breakdown?: Record<string, number>
}
