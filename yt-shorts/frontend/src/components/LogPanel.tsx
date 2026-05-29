import { useEffect, useRef } from 'react'
import Box from '@mui/material/Box'
import { IZK } from '../theme'

function lineColor(line: string): string {
  const t = line.trimStart()
  if (t.startsWith('✓') || t.startsWith('OK')) return '#2d6a4f'
  if (t.startsWith('✗') || t.startsWith('ERROR')) return '#c0392b'
  if (t.startsWith('→') || t.startsWith('INFO')) return '#ff6b3599'
  return IZK.dim
}

export default function LogPanel({ lines, height = 280 }: { lines: string[]; height?: number | string }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => { ref.current?.scrollIntoView({ behavior: 'smooth' }) }, [lines])

  return (
    <Box sx={{
      bgcolor: IZK.terminal,
      border: '1px solid',
      borderColor: IZK.subtleBorder,
      p: 1.5,
      height,
      overflowY: 'auto',
      fontFamily: '"Courier New", monospace',
    }}>
      {lines.length === 0
        ? <Box component="span" sx={{ fontSize: 11, color: IZK.dim }}>Waiting for output...</Box>
        : lines.map((line, i) => (
            <Box key={i} component="div" sx={{ fontSize: 11, lineHeight: 1.7, color: lineColor(line), whiteSpace: 'pre-wrap' }}>
              {line}
            </Box>
          ))
      }
      <div ref={ref} />
    </Box>
  )
}
