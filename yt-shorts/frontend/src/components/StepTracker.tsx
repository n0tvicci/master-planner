import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import { IZK } from '../theme'

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
          <Box
            key={step.key}
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 1.5,
              p: '10px 12px',
              mb: 0.5,
              bgcolor: isActive ? '#ff6b3508' : IZK.card,
              border: '1px solid',
              borderColor: isActive ? '#ff6b3540' : IZK.subtleBorder,
              borderLeft: '2px solid',
              borderLeftColor: isDone ? '#2d6a4f60' : isActive ? 'primary.main' : 'transparent',
              transition: 'all 0.15s',
            }}
          >
            <Box sx={{
              width: 24,
              height: 24,
              flexShrink: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: '1px solid',
              borderColor: isDone ? '#2d6a4f60' : isActive ? 'primary.main' : '#2a2040',
              bgcolor: isDone ? '#2d6a4f10' : isActive ? '#ff6b3510' : 'transparent',
              boxShadow: isActive ? '0 0 8px #ff6b3540' : 'none',
              color: isDone ? '#2d6a4f' : isActive ? 'primary.main' : IZK.dim,
              fontSize: 10,
              fontWeight: 700,
            }}>
              {isDone ? '✓' : i + 1}
            </Box>
            <Typography sx={{
              fontSize: 12,
              color: isDone ? 'text.secondary' : isActive ? 'text.primary' : IZK.dim,
              fontWeight: isActive ? 600 : 400,
              flex: 1,
            }}>
              {step.label}
            </Typography>
            {isActive && (
              <Box sx={{
                fontSize: 8,
                letterSpacing: '1.5px',
                color: 'primary.main',
                textTransform: 'uppercase',
                animation: 'pulse 1.5s ease-in-out infinite',
                '@keyframes pulse': { '0%, 100%': { opacity: 1 }, '50%': { opacity: 0.4 } },
              }}>
                Running
              </Box>
            )}
          </Box>
        )
      })}
    </Box>
  )
}
