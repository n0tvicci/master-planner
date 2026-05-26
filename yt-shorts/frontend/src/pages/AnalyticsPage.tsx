import { useEffect, useRef, useState } from 'react'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Typography from '@mui/material/Typography'
import Paper from '@mui/material/Paper'
import TextField from '@mui/material/TextField'
import LinearProgress from '@mui/material/LinearProgress'
import RefreshIcon from '@mui/icons-material/Refresh'
import { analyticsApi } from '../api/analytics'
import { usePipelineContext } from '../store/PipelineContext'
import ErrorAlert from '../components/ErrorAlert'
import SectionLabel from '../components/SectionLabel'
import type { AnalyticsReport } from '../types'

const FLAG_COLOR = { GREEN: 'success', YELLOW: 'warning', RED: 'error' } as const
const FLAG_LABEL = { GREEN: 'GREEN', YELLOW: 'YELLOW', RED: 'RED' } as const
const POLL_INTERVAL = 4000
const POLL_MAX = 15

export default function AnalyticsPage() {
  const { activeJobId } = usePipelineContext()
  const [jobId, setJobId] = useState(activeJobId ?? '')
  const [report, setReport] = useState<AnalyticsReport | null>(null)
  const [pulling, setPulling] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Auto-fill from pipeline when the user hasn't typed anything
  useEffect(() => {
    setJobId(prev => prev || activeJobId || '')
  }, [activeJobId])

  useEffect(() => () => { if (pollRef.current) clearTimeout(pollRef.current) }, [])

  const load = async (id: string) => {
    setError(null)
    try { setReport(await analyticsApi.getReport(id)) }
    catch { setReport(null); setError('No report found. Click Pull Latest to fetch.') }
  }

  useEffect(() => { if (jobId) load(jobId) }, [jobId])

  const handlePull = async () => {
    if (!jobId) return
    setPulling(true); setError(null)
    try {
      await analyticsApi.pull(jobId)
      let attempts = 0
      const poll = () => {
        if (attempts >= POLL_MAX) {
          setPulling(false)
          setError('Analytics pull timed out — try again in a minute.')
          return
        }
        attempts++
        analyticsApi.getReport(jobId)
          .then(r => { setReport(r); setError(null); setPulling(false) })
          .catch(() => { pollRef.current = setTimeout(poll, POLL_INTERVAL) })
      }
      pollRef.current = setTimeout(poll, POLL_INTERVAL)
    } catch { setError('Failed to pull analytics'); setPulling(false) }
  }

  const usPct = report ? Math.round(report.us_share * 100) : 0
  const countries = report?.country_breakdown
    ? Object.entries(report.country_breakdown).sort((a, b) => b[1] - a[1]).slice(0, 6)
    : []

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h6" fontWeight={700}>Analytics</Typography>
        <Button variant="contained" startIcon={<RefreshIcon />} disabled={!jobId || pulling} onClick={handlePull}>
          {pulling ? 'Pulling...' : 'Pull Latest'}
        </Button>
      </Box>

      <TextField label="Job ID" size="small" value={jobId} placeholder="job-20260526-143021"
        onChange={e => setJobId(e.target.value)} sx={{ mb: 2, width: 300 }} />

      <ErrorAlert error={error} severity="info" />

      {report && (
        <Box>
          <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
            <Paper variant="outlined" sx={{
              p: 3, width: 180, textAlign: 'center', flexShrink: 0,
              borderColor: `${FLAG_COLOR[report.flag]}.main`,
              bgcolor: `${FLAG_COLOR[report.flag]}.main` + '08',
            }}>
              <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 0.5 }}>
                US Audience Share
              </Typography>
              <Typography variant="h3" fontWeight={800} color={`${FLAG_COLOR[report.flag]}.main`} sx={{ my: 1 }}>
                {usPct}%
              </Typography>
              <Typography variant="caption" color={`${FLAG_COLOR[report.flag]}.main`} fontWeight={700}>
                {FLAG_LABEL[report.flag]}
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>Target: 50%+</Typography>
            </Paper>

            <Paper variant="outlined" sx={{ flex: 1, p: 2 }}>
              <SectionLabel>Report Details</SectionLabel>
              {report.notes && <Typography variant="body2" color="text.secondary">{report.notes}</Typography>}
            </Paper>
          </Box>

          {countries.length > 0 && (
            <>
              <SectionLabel>Country Breakdown</SectionLabel>
              <Paper variant="outlined">
                {countries.map(([country, share], i) => {
                  const pct = Math.round(share * 100)
                  return (
                    <Box key={country} sx={{
                      display: 'grid', gridTemplateColumns: '140px 60px 1fr',
                      alignItems: 'center', gap: 2, p: 1.5,
                      borderBottom: i < countries.length - 1 ? '1px solid' : 'none', borderColor: 'divider',
                    }}>
                      <Typography variant="body2">{country}</Typography>
                      <Typography variant="body2" fontWeight={600} color={country === 'US' ? 'success.main' : 'text.primary'}>
                        {pct}%
                      </Typography>
                      <LinearProgress variant="determinate" value={pct}
                        color={country === 'US' ? 'success' : 'primary'}
                        sx={{ height: 4, borderRadius: 2 }} />
                    </Box>
                  )
                })}
              </Paper>
            </>
          )}
        </Box>
      )}
    </Box>
  )
}
