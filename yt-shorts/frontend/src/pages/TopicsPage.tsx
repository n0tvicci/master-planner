import { useCallback, useEffect, useState } from 'react'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import CircularProgress from '@mui/material/CircularProgress'
import Paper from '@mui/material/Paper'
import Typography from '@mui/material/Typography'
import AddIcon from '@mui/icons-material/Add'
import TopicCard from '../components/TopicCard'
import { topicsApi } from '../api/topics'
import type { Topic } from '../types'

export default function TopicsPage() {
  const [pending, setPending] = useState<Topic[]>([])
  const [queue, setQueue] = useState<Topic[]>([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)

  const refresh = useCallback(async () => {
    const [p, q] = await Promise.all([topicsApi.getPending(), topicsApi.getQueue()])
    setPending(p)
    setQueue(q)
  }, [])

  useEffect(() => { refresh().finally(() => setLoading(false)) }, [refresh])

  const handleGenerate = async () => {
    setGenerating(true)
    await topicsApi.generate()
    const before = pending.length
    const poll = setInterval(async () => {
      const p = await topicsApi.getPending()
      if (p.length > before) { setPending(p); clearInterval(poll); setGenerating(false) }
    }, 2000)
    setTimeout(() => { clearInterval(poll); setGenerating(false) }, 90000)
  }

  const handleApprove = async (id: string) => { await topicsApi.approve(id); await refresh() }
  const handleReject = async (id: string) => { await topicsApi.reject(id); await refresh() }

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', pt: 8 }}><CircularProgress /></Box>

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h6" fontWeight={700}>Topics</Typography>
        <Button variant="contained" startIcon={generating ? <CircularProgress size={14} color="inherit" /> : <AddIcon />}
          disabled={generating} onClick={handleGenerate}>
          {generating ? 'Generating...' : 'Generate Topics'}
        </Button>
      </Box>

      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: 3 }}>
        <Box>
          <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 0.5, mb: 1, display: 'block' }}>
            Pending Approval ({pending.length})
          </Typography>
          {pending.length === 0
            ? <Typography variant="body2" color="text.secondary">No pending topics. Click Generate to create new ones.</Typography>
            : pending.map(t => <TopicCard key={t.id} topic={t} onApprove={handleApprove} onReject={handleReject} />)
          }
        </Box>
        <Box>
          <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 0.5, mb: 1, display: 'block' }}>
            Approved Queue ({queue.length})
          </Typography>
          {queue.map((t, i) => (
            <Paper key={t.id ?? i} variant="outlined" sx={{ p: 1.5, mb: 1, display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <Typography variant="caption" color="primary.main" fontWeight={700} sx={{ minWidth: 16 }}>{i + 1}</Typography>
              <Typography variant="body2" noWrap sx={{ flex: 1 }}>{t.title}</Typography>
              {t.tier_score && <Typography variant="caption" color="text.secondary">Score {t.tier_score}</Typography>}
            </Paper>
          ))}
          {queue.length === 0 && <Typography variant="body2" color="text.secondary">No approved topics yet.</Typography>}
        </Box>
      </Box>
    </Box>
  )
}
