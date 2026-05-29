import { useEffect, useRef, useState } from 'react'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Typography from '@mui/material/Typography'
import TextField from '@mui/material/TextField'
import LinearProgress from '@mui/material/LinearProgress'
import RefreshIcon from '@mui/icons-material/Refresh'
import { analyticsApi } from '../api/analytics'
import { usePipelineContext } from '../store/PipelineContext'
import ErrorAlert from '../components/ErrorAlert'
import SectionLabel from '../components/SectionLabel'
import { IZK } from '../theme'
import type { AnalyticsReport } from '../types'

const POLL_INTERVAL = 4000
const POLL_MAX = 15

export default function AnalyticsPage() {
  const { activeJobId } = usePipelineContext()
  const [jobId, setJobId] = useState(activeJobId ?? '')
  const [report, setReport] = useState<AnalyticsReport | null>(null)
  const [pulling, setPulling] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null)

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

  const flagColor = report?.flag === 'GREEN' ? '#2d6a4f' : report?.flag === 'RED' ? '#c0392b' : '#d4a017'
  const usValueColor = usPct >= 70 ? 'primary.main' : flagColor

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Topbar */}
      <Box sx={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        px: 3, py: '14px', borderBottom: '1px solid', borderColor: IZK.subtleBorder,
        bgcolor: 'background.paper', flexShrink: 0,
      }}>
        <Typography sx={{ fontSize: 13, fontWeight: 600, letterSpacing: '2px', textTransform: 'uppercase', color: 'text.secondary' }}>
          Analytics
        </Typography>
        <Box sx={{ fontSize: 9, letterSpacing: '2px', color: IZK.dim }}>72H REPORT</Box>
      </Box>

      {/* Content */}
      <Box sx={{ flex: 1, overflowY: 'auto', p: 3 }}>
        <Box sx={{ display: 'flex', gap: 1.5, mb: 2, alignItems: 'flex-end' }}>
          <TextField
            label="Job ID"
            size="small"
            value={jobId}
            placeholder="job-20260526-143021"
            onChange={e => setJobId(e.target.value)}
            sx={{ width: 280 }}
          />
          <Button variant="contained" startIcon={<RefreshIcon />} disabled={!jobId || pulling} onClick={handlePull}>
            {pulling ? 'Pulling...' : 'Pull Latest'}
          </Button>
        </Box>

        <ErrorAlert error={error} severity="info" />

        {report && (
          <Box>
            {/* Stat cards row */}
            <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
              {/* US Share card */}
              <Box sx={{
                p: 3, width: 180, flexShrink: 0, textAlign: 'center',
                bgcolor: IZK.card, border: '1px solid',
                borderColor: flagColor + '50',
                borderLeft: '2px solid', borderLeftColor: flagColor,
              }}>
                <Typography sx={{ fontSize: 8, color: IZK.dim, letterSpacing: '2px', textTransform: 'uppercase', mb: 1 }}>
                  US Audience Share
                </Typography>
                <Typography sx={{
                  fontSize: 36, fontWeight: 800, color: usValueColor,
                  textShadow: usPct >= 70 ? '0 0 16px #ff6b3560' : 'none',
                  lineHeight: 1, mb: 0.5,
                }}>
                  {usPct}%
                </Typography>
                <Box sx={{
                  display: 'inline-flex', fontSize: 8, letterSpacing: '1.5px',
                  color: flagColor, border: '1px solid', borderColor: flagColor + '50',
                  px: 1, py: 0.25, mt: 0.5,
                }}>
                  {report.flag}
                </Box>
                <Typography sx={{ fontSize: 9, color: IZK.dim, display: 'block', mt: 0.75 }}>
                  Target: 50%+
                </Typography>
              </Box>

              {/* Notes card */}
              <Box sx={{ flex: 1, bgcolor: IZK.card, border: '1px solid', borderColor: IZK.subtleBorder, p: 2 }}>
                <SectionLabel>Report Details</SectionLabel>
                {report.notes && (
                  <Typography sx={{ fontSize: 12, color: 'text.secondary', lineHeight: 1.6 }}>{report.notes}</Typography>
                )}
              </Box>
            </Box>

            {/* Country breakdown */}
            {countries.length > 0 && (
              <>
                <SectionLabel>Country Breakdown</SectionLabel>
                <Box sx={{ bgcolor: IZK.card, border: '1px solid', borderColor: IZK.subtleBorder }}>
                  {countries.map(([country, share], i) => {
                    const pct = Math.round(share * 100)
                    return (
                      <Box key={country} sx={{
                        display: 'grid', gridTemplateColumns: '140px 52px 1fr',
                        alignItems: 'center', gap: 2, p: '12px 16px',
                        borderBottom: i < countries.length - 1 ? '1px solid' : 'none',
                        borderColor: IZK.subtleBorder,
                      }}>
                        <Typography sx={{ fontSize: 12, color: country === 'US' ? 'text.primary' : 'text.secondary' }}>
                          {country}
                        </Typography>
                        <Typography sx={{ fontSize: 12, fontWeight: 600, color: country === 'US' ? 'primary.main' : 'text.secondary' }}>
                          {pct}%
                        </Typography>
                        <LinearProgress variant="determinate" value={pct} />
                      </Box>
                    )
                  })}
                </Box>
              </>
            )}
          </Box>
        )}
      </Box>
    </Box>
  )
}
