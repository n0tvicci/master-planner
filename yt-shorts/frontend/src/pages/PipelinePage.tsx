import { useState } from 'react'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
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
import { IZK } from '../theme'

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
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Topbar */}
      <Box sx={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        px: 3, py: '14px', borderBottom: '1px solid', borderColor: IZK.subtleBorder,
        bgcolor: 'background.paper', flexShrink: 0,
      }}>
        <Typography sx={{ fontSize: 13, fontWeight: 600, letterSpacing: '2px', textTransform: 'uppercase', color: 'text.secondary' }}>
          Pipeline
        </Typography>
        {isRunning && (
          <Box sx={{
            fontSize: 9, letterSpacing: '1.5px', color: 'primary.main',
            animation: 'pulse 1.5s ease-in-out infinite',
            '@keyframes pulse': { '0%, 100%': { opacity: 1 }, '50%': { opacity: 0.4 } },
          }}>
            ● RUNNING
          </Box>
        )}
      </Box>

      {/* Content */}
      <Box sx={{ flex: 1, overflowY: 'auto', p: 3 }}>
        <ErrorAlert error={error} onClose={() => setError(null)} />

        {/* Job card */}
        <Box sx={{
          display: 'flex', alignItems: 'center', gap: 2,
          p: '14px 16px', mb: 2,
          bgcolor: IZK.card,
          border: '1px solid', borderColor: '#ff6b3530',
          borderLeft: '2px solid', borderLeftColor: 'primary.main',
        }}>
          <Box sx={{ flex: 1 }}>
            <Typography sx={{ fontSize: 12, fontWeight: 600, color: 'text.primary', fontFamily: 'monospace' }}>
              {activeJobId ?? 'Ready to run'}
            </Typography>
            <Typography sx={{ fontSize: 11, color: IZK.muted, mt: 0.25 }}>
              {isRunning ? 'Pipeline running...' : activeJobId ? 'Completed' : 'Runs the next topic in the approved queue (~5–8 min)'}
            </Typography>
          </Box>
          <Button variant="contained" startIcon={<BoltIcon />} disabled={isRunning} onClick={handleRun}>
            {isRunning ? 'Running...' : 'Run Pipeline'}
          </Button>
        </Box>

        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
          <Box>
            <SectionLabel>Steps</SectionLabel>
            <StepTracker completedSteps={jobState?.completed_steps ?? []} isRunning={isRunning} />
          </Box>
          <Box>
            <SectionLabel>
              Live Log{isRunning && <span style={{ color: '#ff6b35', marginLeft: 6 }}>● LIVE</span>}
            </SectionLabel>
            <LogPanel lines={logLines} height={340} />
          </Box>
        </Box>
      </Box>
    </Box>
  )
}
