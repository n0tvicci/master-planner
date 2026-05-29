import { useState } from 'react'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Typography from '@mui/material/Typography'
import CheckIcon from '@mui/icons-material/Check'
import CloseIcon from '@mui/icons-material/Close'
import StatusBadge from './StatusBadge'
import type { Topic } from '../types'
import { IZK } from '../theme'

interface Props {
  topic: Topic
  onApprove: (id: string) => Promise<void>
  onReject: (id: string) => Promise<void>
}

export default function TopicCard({ topic, onApprove, onReject }: Props) {
  const [busy, setBusy] = useState<'approve' | 'reject' | null>(null)

  const handle = (action: 'approve' | 'reject') => async () => {
    setBusy(action)
    try { action === 'approve' ? await onApprove(topic.id) : await onReject(topic.id) }
    finally { setBusy(null) }
  }

  const isFeatured = topic.tier === 1

  return (
    <Box sx={{
      display: 'flex',
      alignItems: 'center',
      gap: 2,
      p: '14px 16px',
      mb: 0.75,
      bgcolor: isFeatured ? '#160d1e' : IZK.card,
      border: '1px solid',
      borderColor: isFeatured ? '#2a2040' : IZK.subtleBorder,
      borderLeft: '2px solid',
      borderLeftColor: isFeatured ? 'primary.main' : 'transparent',
      boxShadow: isFeatured ? '0 0 20px #ff6b3510, inset 0 0 20px #ff6b3505' : 'none',
    }}>
      <Box sx={{
        width: 32,
        height: 32,
        flexShrink: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        border: '1px solid',
        borderColor: isFeatured ? '#ff6b3550' : '#2a2040',
        color: isFeatured ? 'primary.main' : IZK.dim,
        fontSize: 11,
        fontWeight: 700,
        textShadow: isFeatured ? '0 0 8px #ff6b35' : 'none',
      }}>
        {topic.tier_score ?? topic.tier}
      </Box>

      <Box sx={{ flex: 1, minWidth: 0 }}>
        <Typography sx={{
          fontSize: 12,
          color: isFeatured ? 'text.primary' : IZK.muted,
          fontWeight: isFeatured ? 500 : 400,
          mb: 0.5,
          lineHeight: 1.4,
        }} noWrap>
          {topic.title}
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
          <StatusBadge tier={topic.tier} score={topic.tier_score} />
          {topic.hook_object && (
            <Typography sx={{ fontSize: 9, color: IZK.dim, letterSpacing: '0.5px' }}>
              Hook: {topic.hook_object}
            </Typography>
          )}
        </Box>
      </Box>

      <Box sx={{ display: 'flex', gap: 1, flexShrink: 0 }}>
        <Button
          size="small"
          variant="outlined"
          startIcon={<CheckIcon sx={{ fontSize: '12px !important' }} />}
          disabled={busy !== null}
          onClick={handle('approve')}
          sx={{ borderColor: '#2d6a4f', color: '#2d6a4f', '&:hover': { bgcolor: '#2d6a4f10', borderColor: '#2d6a4f' } }}
        >
          Approve
        </Button>
        <Button
          size="small"
          variant="outlined"
          startIcon={<CloseIcon sx={{ fontSize: '12px !important' }} />}
          disabled={busy !== null}
          onClick={handle('reject')}
          sx={{ borderColor: '#c0392b60', color: '#c0392b80', '&:hover': { bgcolor: '#c0392b08', borderColor: '#c0392b' } }}
        >
          Reject
        </Button>
      </Box>
    </Box>
  )
}
