import { useCallback, useEffect, useRef, useState } from 'react'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import CircularProgress from '@mui/material/CircularProgress'
import Typography from '@mui/material/Typography'
import AddIcon from '@mui/icons-material/Add'
import TopicCard from '../components/TopicCard'
import ErrorAlert from '../components/ErrorAlert'
import SectionLabel from '../components/SectionLabel'
import { topicsApi } from '../api/topics'
import { IZK } from '../theme'
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
      } catch { /* ignore poll errors */ }
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

  if (loading) return (
    <Box sx={{ display: 'flex', justifyContent: 'center', pt: 8 }}>
      <CircularProgress size={24} />
    </Box>
  )

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Topbar */}
      <Box sx={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        px: 3, py: '14px', borderBottom: '1px solid', borderColor: IZK.subtleBorder,
        bgcolor: 'background.paper', flexShrink: 0,
      }}>
        <Typography sx={{ fontSize: 13, fontWeight: 600, letterSpacing: '2px', textTransform: 'uppercase', color: 'text.secondary' }}>
          Topics
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          {pending.length > 0 && (
            <Box sx={{ fontSize: 9, letterSpacing: '1px', color: '#ff6b3560', bgcolor: '#ff6b3510', border: '1px solid #ff6b3520', px: 1, py: 0.25 }}>
              {pending.length} PENDING
            </Box>
          )}
          <Button
            variant="contained"
            startIcon={generating ? <CircularProgress size={12} sx={{ color: '#0e0b14' }} /> : <AddIcon />}
            disabled={generating}
            onClick={handleGenerate}
          >
            {generating ? 'Generating...' : 'Generate Topics'}
          </Button>
        </Box>
      </Box>

      {/* Content */}
      <Box sx={{ flex: 1, overflowY: 'auto', p: 3 }}>
        <ErrorAlert error={error} onClose={() => setError(null)} />

        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: 3 }}>
          <Box>
            <SectionLabel>Pending Approval ({pending.length})</SectionLabel>
            {pending.length === 0
              ? <Typography sx={{ fontSize: 12, color: IZK.muted }}>No pending topics. Click Generate to create new ones.</Typography>
              : pending.map(t => <TopicCard key={t.id} topic={t} onApprove={handleApprove} onReject={handleReject} />)
            }
          </Box>

          <Box>
            <SectionLabel>Approved Queue ({queue.length})</SectionLabel>
            {queue.map((t, i) => (
              <Box key={t.id ?? i} sx={{
                display: 'flex', alignItems: 'center', gap: 1.5,
                p: '10px 12px', mb: 0.5,
                bgcolor: IZK.card, border: '1px solid', borderColor: IZK.subtleBorder,
              }}>
                <Typography sx={{ fontSize: 10, color: 'primary.main', fontWeight: 700, minWidth: 16 }}>{i + 1}</Typography>
                <Typography sx={{ fontSize: 12, color: 'text.secondary', flex: 1 }} noWrap>{t.title}</Typography>
                {t.tier_score && (
                  <Typography sx={{ fontSize: 9, color: IZK.dim, letterSpacing: '1px' }}>
                    {t.tier_score}/10
                  </Typography>
                )}
              </Box>
            ))}
            {queue.length === 0 && (
              <Typography sx={{ fontSize: 12, color: IZK.muted }}>No approved topics yet.</Typography>
            )}
          </Box>
        </Box>
      </Box>
    </Box>
  )
}
