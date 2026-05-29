import Box from '@mui/material/Box'
import { IZK } from '../theme'

interface Props {
  tier: number
  score?: number
}

export default function StatusBadge({ tier, score }: Props) {
  const label = score != null ? `Tier ${tier} · ${score}/10` : `Tier ${tier}`
  const color = tier === 1 ? '#2d6a4f' : tier === 2 ? '#d4a017' : IZK.dim
  const borderColor = tier === 1 ? '#2d6a4f60' : tier === 2 ? '#d4a01750' : '#2a2040'

  return (
    <Box sx={{
      display: 'inline-flex',
      alignItems: 'center',
      fontSize: 8,
      letterSpacing: '1.5px',
      textTransform: 'uppercase',
      color,
      border: '1px solid',
      borderColor,
      px: 1,
      py: 0.25,
      lineHeight: 1.6,
      flexShrink: 0,
    }}>
      {label}
    </Box>
  )
}
