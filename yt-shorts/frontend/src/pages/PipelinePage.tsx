import { useState } from 'react'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Paper from '@mui/material/Paper'
import Typography from '@mui/material/Typography'
import Alert from '@mui/material/Alert'
import BoltIcon from '@mui/icons-material/Bolt'
import { pipelineApi } from '../api/pipeline'
import { usePipelineContext } from '../store/PipelineContext'
import { useJobState } from '../hooks/useJobState'
import { useSSE } from '../hooks/useSSE'
import StepTracker from '../components/StepTracker'
import LogPanel from '../components/LogPanel'

export default function PipelinePage() {
  const { activeJobId, isRunning, setActiveJob, setRunning } = usePipelineContext()
  const [logLines, setLogLines] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const jobState = useJobState(activeJobId)

  useSSE(
    activeJobId && isRunning ? pipelineApi.streamUrl(activeJobId) : null,
    (line) => setLogLines(prev => [...prev, line]),
    () => setRunning(false),
  )

  const handleRun = async () => {
    setError(null); setLogLines([])
    try {
      const { job_id } = await pipelineApi.run()
      setActiveJob(job_id); setRunning(true)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Failed to start pipeline'
      const axiosMsg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(axiosMsg ?? msg)
    }
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h6" fontWeight={700}>Pipeline</Typography>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}

      <Paper variant="outlined" sx={{ p: 2, mb: 2, display: 'flex', alignItems: 'center', gap: 2, borderColor: 'primary.main' + '40', bgcolor: 'primary.main' + '08' }}>
        <Box sx={{ flex: 1 }}>
          <Typography variant="body2" fontWeight={700}>{activeJobId ?? 'Ready to run'}</Typography>
          <Typography variant="caption" color="text.secondary">
            {isRunning ? 'Pipeline running...' : activeJobId ? 'Completed' : 'Runs the next topic in the approved queue (~5–8 min)'}
          </Typography>
        </Box>
        <Button variant="contained" startIcon={<BoltIcon />} disabled={isRunning} onClick={handleRun}>
          {isRunning ? 'Running...' : 'Run Pipeline'}
        </Button>
      </Paper>

      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
        <Box>
          <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 0.5, mb: 1, display: 'block' }}>Steps</Typography>
          <StepTracker completedSteps={jobState?.completed_steps ?? []} isRunning={isRunning} />
        </Box>
        <Box>
          <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 0.5, mb: 1, display: 'block' }}>
            Live Log {isRunning && <span style={{ color: '#4f79ff' }}>● LIVE</span>}
          </Typography>
          <LogPanel lines={logLines} height={340} />
        </Box>
      </Box>
    </Box>
  )
}
