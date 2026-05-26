import Chip from '@mui/material/Chip'

export default function StatusBadge({ tier, score }: { tier: number; score?: number }) {
  const color = tier === 1 ? 'success' : tier === 2 ? 'warning' : 'default'
  const label = score != null ? `Tier ${tier} · ${score}/10` : `Tier ${tier}`
  return <Chip label={label} color={color} size="small" variant="outlined" />
}
