import { useEffect, useRef } from 'react'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'

export default function LogPanel({ lines, height = 280 }: { lines: string[]; height?: number | string }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => { ref.current?.scrollIntoView({ behavior: 'smooth' }) }, [lines])

  return (
    <Box sx={{
      bgcolor: '#111827', border: '1px solid #1f2937', borderRadius: 1,
      p: 1.5, height, overflowY: 'auto',
      fontFamily: '"Fira Code", "Courier New", monospace',
    }}>
      {lines.length === 0
        ? <Typography variant="caption" color="text.disabled">Waiting for output...</Typography>
        : lines.map((line, i) => (
            <Typography key={i} variant="caption" component="div" sx={{ lineHeight: 1.7, color: '#94a3b8', whiteSpace: 'pre-wrap' }}>
              {line}
            </Typography>
          ))
      }
      <div ref={ref} />
    </Box>
  )
}
