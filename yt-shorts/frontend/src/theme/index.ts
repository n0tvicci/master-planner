import { createTheme } from '@mui/material/styles'

export const IZK = {
  card: '#130f1e',
  terminal: '#080610',
  muted: '#4a3f5a',
  dim: '#3a3050',
  subtleBorder: '#1a1428',
} as const

export const theme = createTheme({
  shape: { borderRadius: 0 },
  palette: {
    mode: 'dark',
    primary: { main: '#ff6b35' },
    secondary: { main: '#2d6a4f' },
    background: { default: '#0e0b14', paper: '#0b0910' },
    text: { primary: '#e8ddd0', secondary: '#c4b4a4' },
    divider: '#2a2040',
    error: { main: '#c0392b' },
    warning: { main: '#d4a017' },
    success: { main: '#2d6a4f' },
  },
  typography: {
    fontFamily: 'system-ui, -apple-system, sans-serif',
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: { backgroundImage: 'none' },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 0,
          textTransform: 'uppercase' as const,
          letterSpacing: '2px',
          fontSize: '10px',
          fontWeight: 600,
          boxShadow: 'none',
          '&:hover': { boxShadow: 'none' },
        },
        contained: {
          backgroundColor: '#ff6b35',
          color: '#0e0b14',
          '&:hover': { backgroundColor: '#ff8550', boxShadow: '0 0 12px #ff6b3540' },
          '&.Mui-disabled': { backgroundColor: '#2a2040', color: '#3a3050' },
        },
        outlined: {
          borderColor: '#ff6b35',
          color: '#ff6b35',
          '&:hover': { backgroundColor: '#ff6b3510', borderColor: '#ff6b35' },
          '&.Mui-disabled': { borderColor: '#2a2040', color: '#3a3050' },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 0,
          fontSize: '9px',
          letterSpacing: '1px',
          height: '22px',
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 0,
            fontSize: '12px',
            backgroundColor: '#130f1e',
            '& fieldset': { borderColor: '#2a2040' },
            '&:hover fieldset': { borderColor: '#4a3f5a' },
            '&.Mui-focused fieldset': { borderColor: '#ff6b35' },
          },
          '& .MuiInputLabel-root.Mui-focused': { color: '#ff6b35' },
        },
      },
    },
    MuiCheckbox: {
      styleOverrides: {
        root: {
          color: '#2a2040',
          '&.Mui-checked': { color: '#ff6b35' },
        },
      },
    },
    MuiLinearProgress: {
      styleOverrides: {
        root: { borderRadius: 0, backgroundColor: '#130f1e', height: 4 },
        bar: { backgroundColor: '#ff6b35', borderRadius: 0 },
      },
    },
    MuiDivider: {
      styleOverrides: {
        root: { borderColor: '#1a1428' },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: { backgroundColor: '#0b0910', borderRight: '1px solid #1a1428' },
      },
    },
    MuiCircularProgress: {
      styleOverrides: {
        root: { color: '#ff6b35' },
      },
    },
  },
})
