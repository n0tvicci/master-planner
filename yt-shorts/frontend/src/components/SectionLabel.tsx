import Typography from '@mui/material/Typography'
import type { ReactNode } from 'react'

export default function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <Typography
      variant="caption"
      color="text.secondary"
      sx={{ textTransform: 'uppercase', letterSpacing: 0.5, mb: 1, display: 'block' }}
    >
      {children}
    </Typography>
  )
}
