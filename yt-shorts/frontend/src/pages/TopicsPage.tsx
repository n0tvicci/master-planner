import { useCallback, useEffect, useRef, useState } from 'react'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import CircularProgress from '@mui/material/CircularProgress'
import Paper from '@mui/material/Paper'
import Typography from '@mui/material/Typography'
import AddIcon from '@mui/icons-material/Add'
import TopicCard from '../components/TopicCard'
import ErrorAlert from '../components/ErrorAlert'
import SectionLabel from '../components/SectionLabel'
import { topicsApi } from '../api/topics'
import type { Topic } from '../types'

export default function TopicsPage() {
  const [pending, setPending] = useState<Topic[]>([])
  const [queue, setQueue] = useState<Topic[]>([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const refresh = useCallback(async () => {
    const [p, q] = await Promise.all([topicsApi.getPending(), topicsApi.getQueue()])
    setPending(p)
    setQueue(q)
  }, [])

  useEffect(() => {
    refresh().finally(() => setLoading(false))
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
      if (timeoutRef.current) clearTimeout(timeoutRef.current)
    }
  }, [refresh])

  const handleGenerate = async () => {
    setError(null)
    setGenerating(true)
    try {
      await topicsApi.generate()
    } catch {
      setError('Failed to start topic generation')
      setGenerating(false)
      return
    }
    const before = pending.length
    pollRef.current = setInterval(async () => {
      try {
        const p = await topicsApi.getPending()
        if (p.length > before) {
          setPending(p)
          if (pollRef.current) clearInterval(pollRef.current)
          if (timeoutRef.current) clearTimeout(timeoutRef.current)
          setGenerating(false)
        }
      } catch {
        // ignore poll errors, timeout will clean up
      }
    }, 2000)
    timeoutRef.current = setTimeout(() => {
      if (pollRef.current) clearInterval(pollRef.current)
      setGenerating(false)
    }, 90000)
  }

  const handleApprove = async (id: string) => {
    try { await topicsApi.approve(id); await refresh() }
    catch { setError('Failed to approve topic') }
  }

  const handleReject = async (id: string) => {
    try { await topicsApi.reject(id); await refresh() }
    catch { setError('Failed to reject topic') }
  }

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

      <ErrorAlert error={error} onClose={() => setError(null)} />

      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: 3 }}>
        <Box>
          <SectionLabel>Pending Approval ({pending.length})</SectionLabel>
          {pending.length === 0
            ? <Typography variant="body2" color="text.secondary">No pending topics. Click Generate to create new ones.</Typography>
            : pending.map(t => <TopicCard key={t.id} topic={t} onApprove={handleApprove} onReject={handleReject} />)
          }
        </Box>
        <Box>
          <SectionLabel>Approved Queue ({queue.length})</SectionLabel>
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
