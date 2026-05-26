import { RouterProvider } from 'react-router-dom'
import { ThemeProvider, CssBaseline } from '@mui/material'
import { theme } from './theme'
import { router } from './router'
import { PipelineProvider } from './store/PipelineContext'

export default function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <PipelineProvider>
        <RouterProvider router={router} />
      </PipelineProvider>
    </ThemeProvider>
  )
}
