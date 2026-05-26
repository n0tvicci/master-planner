import { createTheme } from '@mui/material/styles'

export const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: '#4f79ff' },
    secondary: { main: '#22c55e' },
    background: { default: '#0d1117', paper: '#1e2533' },
    warning: { main: '#f59e0b' },
    error: { main: '#ef4444' },
    success: { main: '#22c55e' },
  },
  typography: { fontFamily: 'Inter, system-ui, sans-serif' },
  components: {
    MuiPaper: { styleOverrides: { root: { backgroundImage: 'none' } } },
  },
})
