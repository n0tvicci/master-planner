import { useCallback, useEffect, useRef, useState } from 'react'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Typography from '@mui/material/Typography'
import FormControlLabel from '@mui/material/FormControlLabel'
import Checkbox from '@mui/material/Checkbox'
import TextField from '@mui/material/TextField'
import RocketLaunchIcon from '@mui/icons-material/RocketLaunch'
import { usePublishContext } from '../store/PublishContext'
import { usePipelineContext } from '../store/PipelineContext'
import { publishApi } from '../api/publish'
import { useSSE } from '../hooks/useSSE'
import LogPanel from '../components/LogPanel'
import ErrorAlert from '../components/ErrorAlert'
import SectionLabel from '../components/SectionLabel'
import { getAxiosErrorMessage } from '../utils/errors'
import { IZK } from '../theme'
import type { Metadata, UploadWindow } from '../types'

export default function PublishPage() {
  const { jobId, setJobId, checks, toggleCheck, allChecked, gateItems, resetChecks } = usePublishContext()
  const { activeJobId } = usePipelineContext()
  const [window_, setWindow_] = useState<UploadWindow | null>(null)
  const [metadata, setMetadata] = useState<Metadata | null>(null)
  const [uploading, setUploading] = useState(false)
  const [streamJobId, setStreamJobId] = useState<string | null>(null)
  const [logLines, setLogLines] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    publishApi.getWindow().then(setWindow_).catch(() => {})
    const id = setInterval(() => publishApi.getWindow().then(setWindow_).catch(() => {}), 60000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    if (activeJobId && !jobId) setJobId(activeJobId)
  }, [activeJobId])

  const loadMeta = useCallback(async (id: string) => {
    try { setMetadata(await publishApi.getMetadata(id)) }
    catch { setMetadata(null) }
  }, [])

  useEffect(() => { if (jobId) loadMeta(jobId); else setMetadata(null) }, [jobId, loadMeta])

  useSSE(streamJobId ? publishApi.streamUrl(streamJobId) : null,
    (line) => setLogLines(p => [...p, line]),
    () => setUploading(false))

  const handleJobChange = (val: string) => {
    setJobId(val || null); resetChecks(); setLogLines([]); setError(null)
  }

  const handleUpload = async () => {
    if (!jobId || !allChecked) return
    setError(null); setLogLines([]); setUploading(true)
    try { await publishApi.upload(jobId); setStreamJobId(jobId) }
    catch (e: unknown) {
      setError(getAxiosErrorMessage(e, 'Upload failed'))
      setUploading(false)
    }
  }

  const nextWindowStr = window_?.next_window
    ? new Date(window_.next_window).toLocaleString('en-US', { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', timeZoneName: 'short' })
    : '...'

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Topbar */}
      <Box sx={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        px: 3, py: '14px', borderBottom: '1px solid', borderColor: IZK.subtleBorder,
        bgcolor: 'background.paper', flexShrink: 0,
      }}>
        <Typography sx={{ fontSize: 13, fontWeight: 600, letterSpacing: '2px', textTransform: 'uppercase', color: 'text.secondary' }}>
          Publish
        </Typography>
        <Button
          variant="outlined"
          size="small"
          disabled={!jobId || uploading}
          onClick={() => jobId && publishApi.upload(jobId, true).catch(() => {})}
        >
          Dry Run
        </Button>
      </Box>

      {/* Content */}
      <Box sx={{ flex: 1, overflowY: 'auto', p: 3 }}>
        <TextField
          label="Job ID"
          size="small"
          value={jobId ?? ''}
          placeholder="job-20260526-143021"
          onChange={e => handleJobChange(e.target.value)}
          sx={{ mb: 2, width: 300 }}
        />

        <ErrorAlert error={error} onClose={() => setError(null)} />

        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 3 }}>
          <Box>
            <SectionLabel>Pre-Upload Checklist</SectionLabel>
            <Box sx={{ bgcolor: IZK.card, border: '1px solid', borderColor: IZK.subtleBorder, p: 1.5, mb: 2 }}>
              {gateItems.map((item, i) => (
                <Box key={i} sx={{
                  borderBottom: i < gateItems.length - 1 ? '1px solid' : 'none',
                  borderColor: IZK.subtleBorder, py: 0.5,
                }}>
                  <FormControlLabel
                    control={<Checkbox size="small" checked={checks[i]} onChange={() => toggleCheck(i)} />}
                    label={<Typography sx={{ fontSize: 12, color: checks[i] ? 'text.primary' : IZK.muted }}>{item}</Typography>}
                  />
                </Box>
              ))}
            </Box>

            {window_ && (
              <Box sx={{
                p: '10px 14px', mb: 2,
                bgcolor: IZK.card,
                border: '1px solid',
                borderColor: window_.in_window ? '#2d6a4f40' : '#d4a01740',
                borderLeft: '2px solid',
                borderLeftColor: window_.in_window ? '#2d6a4f' : '#d4a017',
              }}>
                <Typography sx={{ fontSize: 12, color: window_.in_window ? '#2d6a4f' : '#d4a017' }}>
                  {window_.in_window ? '● In optimal upload window now' : `Next window: ${nextWindowStr}`}
                </Typography>
              </Box>
            )}

            <Button
              variant="contained"
              size="large"
              startIcon={<RocketLaunchIcon />}
              disabled={!allChecked || uploading || !jobId}
              onClick={handleUpload}
            >
              {uploading ? 'Uploading...' : 'Upload to YouTube'}
            </Button>
            {!allChecked && (
              <Typography sx={{ fontSize: 11, color: IZK.dim, display: 'block', mt: 1 }}>
                Complete checklist to enable upload
              </Typography>
            )}
          </Box>

          <Box>
            <SectionLabel>Metadata Preview</SectionLabel>
            {metadata ? (
              <Box sx={{ bgcolor: IZK.card, border: '1px solid', borderColor: IZK.subtleBorder, p: 2, mb: 2 }}>
                <Typography sx={{ fontSize: 9, color: IZK.dim, letterSpacing: '2px', textTransform: 'uppercase', mb: 0.5 }}>Title</Typography>
                <Typography sx={{ fontSize: 12, fontWeight: 600, color: 'text.primary', mb: 2 }}>{metadata.title}</Typography>

                <Typography sx={{ fontSize: 9, color: IZK.dim, letterSpacing: '2px', textTransform: 'uppercase', mb: 0.5 }}>Description</Typography>
                <Typography sx={{ fontSize: 11, color: 'text.secondary', mb: 2, lineHeight: 1.6 }}>{metadata.description}</Typography>

                <Typography sx={{ fontSize: 9, color: IZK.dim, letterSpacing: '2px', textTransform: 'uppercase', mb: 0.75 }}>Tags</Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 2 }}>
                  {metadata.tags.map(tag => (
                    <Box key={tag} sx={{ fontSize: 9, letterSpacing: '1px', color: IZK.muted, border: '1px solid #2a2040', px: 1, py: 0.25 }}>
                      {tag}
                    </Box>
                  ))}
                </Box>

                <Typography sx={{ fontSize: 9, color: IZK.dim, letterSpacing: '2px', textTransform: 'uppercase', mb: 0.5 }}>Pinned Comment</Typography>
                <Typography sx={{ fontSize: 11, color: 'text.secondary', lineHeight: 1.6 }}>{metadata.pinned_comment}</Typography>
              </Box>
            ) : (
              <Typography sx={{ fontSize: 12, color: IZK.muted }}>Enter a job ID to preview metadata.</Typography>
            )}
            {logLines.length > 0 && (
              <Box sx={{ mt: 2 }}>
                <SectionLabel>Upload Log</SectionLabel>
                <LogPanel lines={logLines} height={180} />
              </Box>
            )}
          </Box>
        </Box>
      </Box>
    </Box>
  )
}
