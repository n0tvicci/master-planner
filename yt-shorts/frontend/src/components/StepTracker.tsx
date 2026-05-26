import Box from '@mui/material/Box'
import Paper from '@mui/material/Paper'
import Typography from '@mui/material/Typography'
import CircularProgress from '@mui/material/CircularProgress'
import CheckIcon from '@mui/icons-material/Check'

const STEPS = [
  { key: 'generate_script', label: 'Generate Script' },
  { key: 'generate_voiceover', label: 'Generate Voiceover' },
  { key: 'search_footage', label: 'Search Footage' },
  { key: 'generate_ai_footage', label: 'Generate AI Footage' },
  { key: 'check_footage_gaps', label: 'Check Footage Gaps' },
  { key: 'package_assets', label: 'Package Assets' },
]

export default function StepTracker({ completedSteps, isRunning }: { completedSteps: string[]; isRunning: boolean }) {
  const done = new Set(completedSteps)
  const nextIdx = STEPS.findIndex(s => !done.has(s.key))

  return (
    <Box>
      {STEPS.map((step, i) => {
        const isDone = done.has(step.key)
        const isActive = isRunning && i === nextIdx
        return (
          <Paper key={step.key} variant="outlined" sx={{
            display: 'flex', alignItems: 'center', gap: 1.5, p: 1.25, mb: 0.5,
            borderColor: isActive ? 'primary.main' : 'divider',
          }}>
            <Box sx={{
              width: 24, height: 24, borderRadius: '50%', flexShrink: 0,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              border: '1.5px solid',
              borderColor: isDone ? 'success.main' : isActive ? 'primary.main' : 'divider',
              bgcolor: isDone ? 'success.main' + '20' : isActive ? 'primary.main' + '20' : 'transparent',
            }}>
              {isDone ? <CheckIcon sx={{ fontSize: 12, color: 'success.main' }} />
                : isActive ? <CircularProgress size={10} thickness={5} />
                : <Typography variant="caption" color="text.disabled">{i + 1}</Typography>}
            </Box>
            <Typography variant="body2" color={isDone ? 'text.secondary' : isActive ? 'text.primary' : 'text.disabled'}
              fontWeight={isActive ? 600 : 400}>
              {step.label}
            </Typography>
          </Paper>
        )
      })}
    </Box>
  )
}
