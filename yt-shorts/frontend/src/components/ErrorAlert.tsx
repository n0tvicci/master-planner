import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import IconButton from '@mui/material/IconButton'
import CloseIcon from '@mui/icons-material/Close'

const SEVERITY_COLORS = {
  error: { border: '#c0392b60', left: '#c0392b', bg: '#1a0a0a', text: '#e8c4c4' },
  warning: { border: '#d4a01760', left: '#d4a017', bg: '#1a1500', text: '#e8ddb0' },
  info: { border: '#ff6b3540', left: '#ff6b35', bg: '#130f1e', text: '#e8ddd0' },
} as const

interface Props {
  error: string | null
  onClose?: () => void
  severity?: 'error' | 'warning' | 'info'
}

export default function ErrorAlert({ error, onClose, severity = 'error' }: Props) {
  if (!error) return null
  const c = SEVERITY_COLORS[severity]
  return (
    <Box sx={{
      display: 'flex',
      alignItems: 'center',
      gap: 1.5,
      p: '10px 14px',
      mb: 2,
      bgcolor: c.bg,
      border: '1px solid',
      borderColor: c.border,
      borderLeft: '2px solid',
      borderLeftColor: c.left,
    }}>
      <Typography sx={{ flex: 1, fontSize: 12, color: c.text }}>{error}</Typography>
      {onClose && (
        <IconButton size="small" onClick={onClose} sx={{ color: c.left, p: 0.25 }}>
          <CloseIcon sx={{ fontSize: 14 }} />
        </IconButton>
      )}
    </Box>
  )
}
