import { useState } from 'react'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Paper from '@mui/material/Paper'
import Typography from '@mui/material/Typography'
import BoltIcon from '@mui/icons-material/Bolt'
import { pipelineApi } from '../api/pipeline'
import { usePipelineContext } from '../store/PipelineContext'
import { useJobState } from '../hooks/useJobState'
import { useSSE } from '../hooks/useSSE'
import StepTracker from '../components/StepTracker'
import LogPanel from '../components/LogPanel'
import ErrorAlert from '../components/ErrorAlert'
import SectionLabel from '../components/SectionLabel'
import { getAxiosErrorMessage } from '../utils/errors'

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
      setError(getAxiosErrorMessage(e, 'Failed to start pipeline'))
    }
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h6" fontWeight={700}>Pipeline</Typography>
      </Box>

      <ErrorAlert error={error} onClose={() => setError(null)} />

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
          <SectionLabel>Steps</SectionLabel>
          <StepTracker completedSteps={jobState?.completed_steps ?? []} isRunning={isRunning} />
        </Box>
        <Box>
          <SectionLabel>Live Log {isRunning && <span style={{ color: '#4f79ff' }}>● LIVE</span>}</SectionLabel>
          <LogPanel lines={logLines} height={340} />
        </Box>
      </Box>
    </Box>
  )
}
