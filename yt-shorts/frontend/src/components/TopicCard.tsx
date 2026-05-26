import { useState } from 'react'
import Box from '@mui/material/Box'
import Paper from '@mui/material/Paper'
import Typography from '@mui/material/Typography'
import Button from '@mui/material/Button'
import CheckIcon from '@mui/icons-material/Check'
import CloseIcon from '@mui/icons-material/Close'
import StatusBadge from './StatusBadge'
import type { Topic } from '../types'

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

  return (
    <Paper variant="outlined" sx={{ p: 2, mb: 1, display: 'flex', alignItems: 'center', gap: 2 }}>
      <Box sx={{
        width: 40, height: 40, borderRadius: '50%', flexShrink: 0,
        border: '2px solid', borderColor: topic.tier === 1 ? 'success.main' : 'warning.main',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <Typography variant="subtitle2" color={topic.tier === 1 ? 'success.main' : 'warning.main'}>
          {topic.tier_score ?? topic.tier}
        </Typography>
      </Box>
      <Box sx={{ flex: 1, minWidth: 0 }}>
        <Typography variant="body2" fontWeight={600} noWrap>{topic.title}</Typography>
        <Box sx={{ display: 'flex', gap: 1, mt: 0.5, alignItems: 'center' }}>
          <StatusBadge tier={topic.tier} score={topic.tier_score} />
          {topic.hook_object && (
            <Typography variant="caption" color="text.secondary">Hook: {topic.hook_object}</Typography>
          )}
        </Box>
      </Box>
      <Box sx={{ display: 'flex', gap: 1, flexShrink: 0 }}>
        <Button size="small" variant="outlined" color="success" startIcon={<CheckIcon />}
          disabled={busy !== null} onClick={handle('approve')}>Approve</Button>
        <Button size="small" variant="outlined" color="error" startIcon={<CloseIcon />}
          disabled={busy !== null} onClick={handle('reject')}>Reject</Button>
      </Box>
    </Paper>
  )
}
