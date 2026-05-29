import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import type { ReactNode } from 'react'

export default function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1.5 }}>
      <Typography sx={{
        fontSize: 9,
        letterSpacing: '3px',
        textTransform: 'uppercase',
        color: '#ff6b3599',
        flexShrink: 0,
        lineHeight: 1,
      }}>
        {children}
      </Typography>
      <Box sx={{ flex: 1, height: '1px', background: 'linear-gradient(90deg, #ff6b3525, transparent)' }} />
    </Box>
  )
}
