import Alert from '@mui/material/Alert'

interface Props {
  error: string | null
  onClose?: () => void
  severity?: 'error' | 'warning' | 'info'
}

export default function ErrorAlert({ error, onClose, severity = 'error' }: Props) {
  if (!error) return null
  return (
    <Alert severity={severity} sx={{ mb: 2 }} onClose={onClose}>
      {error}
    </Alert>
  )
}
