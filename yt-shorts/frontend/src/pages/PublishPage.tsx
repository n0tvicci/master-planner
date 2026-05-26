import { useCallback, useEffect, useState } from 'react'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Typography from '@mui/material/Typography'
import Paper from '@mui/material/Paper'
import FormControlLabel from '@mui/material/FormControlLabel'
import Checkbox from '@mui/material/Checkbox'
import Alert from '@mui/material/Alert'
import Chip from '@mui/material/Chip'
import TextField from '@mui/material/TextField'
import RocketLaunchIcon from '@mui/icons-material/RocketLaunch'
import { usePublishContext } from '../store/PublishContext'
import { publishApi } from '../api/publish'
import { useSSE } from '../hooks/useSSE'
import LogPanel from '../components/LogPanel'
import type { Metadata, UploadWindow } from '../types'

export default function PublishPage() {
  const { jobId, setJobId, checks, toggleCheck, allChecked, gateItems, resetChecks } = usePublishContext()
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
      const axiosMsg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(axiosMsg ?? 'Upload failed')
      setUploading(false)
    }
  }

  const nextWindowStr = window_?.next_window
    ? new Date(window_.next_window).toLocaleString('en-US', { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', timeZoneName: 'short' })
    : '...'

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h6" fontWeight={700}>Publish</Typography>
        <Button variant="outlined" size="small" disabled={!jobId || uploading}
          onClick={() => jobId && publishApi.upload(jobId, true).catch(() => {})}>Dry Run</Button>
      </Box>

      <TextField label="Job ID" size="small" value={jobId ?? ''} placeholder="job-20260526-143021"
        onChange={e => handleJobChange(e.target.value)} sx={{ mb: 2, width: 300 }} />

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}

      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 3 }}>
        <Box>
          <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 0.5, mb: 1, display: 'block' }}>
            Pre-Upload Checklist
          </Typography>
          <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
            {gateItems.map((item, i) => (
              <Box key={i} sx={{ borderBottom: i < gateItems.length - 1 ? '1px solid' : 'none', borderColor: 'divider', py: 0.5 }}>
                <FormControlLabel control={<Checkbox size="small" checked={checks[i]} onChange={() => toggleCheck(i)} />}
                  label={<Typography variant="body2">{item}</Typography>} />
              </Box>
            ))}
          </Paper>

          {window_ && (
            <Alert severity={window_.in_window ? 'success' : 'warning'} sx={{ mb: 2 }}>
              {window_.in_window ? 'In optimal upload window now' : `Next window: ${nextWindowStr}`}
            </Alert>
          )}

          <Button variant="contained" size="large" startIcon={<RocketLaunchIcon />}
            disabled={!allChecked || uploading || !jobId} onClick={handleUpload}
            sx={{ background: 'linear-gradient(135deg, #4f79ff, #7c3aed)' }}>
            {uploading ? 'Uploading...' : 'Upload to YouTube'}
          </Button>
          {!allChecked && <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
            Complete checklist to enable upload
          </Typography>}
        </Box>

        <Box>
          <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 0.5, mb: 1, display: 'block' }}>
            Metadata Preview
          </Typography>
          {metadata ? (
            <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
              <Typography variant="caption" color="text.secondary">Title</Typography>
              <Typography variant="body2" fontWeight={600} sx={{ mb: 1.5 }}>{metadata.title}</Typography>
              <Typography variant="caption" color="text.secondary">Description</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5, fontSize: 11 }}>{metadata.description}</Typography>
              <Typography variant="caption" color="text.secondary">Tags</Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 0.5, mb: 1.5 }}>
                {metadata.tags.map(tag => <Chip key={tag} label={tag} size="small" />)}
              </Box>
              <Typography variant="caption" color="text.secondary">Pinned Comment</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ fontSize: 11 }}>{metadata.pinned_comment}</Typography>
            </Paper>
          ) : (
            <Typography variant="body2" color="text.secondary">Enter a job ID to preview metadata.</Typography>
          )}
          {logLines.length > 0 && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 0.5, mb: 1, display: 'block' }}>Upload Log</Typography>
              <LogPanel lines={logLines} height={180} />
            </Box>
          )}
        </Box>
      </Box>
    </Box>
  )
}
