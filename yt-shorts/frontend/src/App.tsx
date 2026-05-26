import { RouterProvider } from 'react-router-dom'
import { ThemeProvider, CssBaseline } from '@mui/material'
import { theme } from './theme'
import { router } from './router'
import { PipelineProvider } from './store/PipelineContext'
import { PublishProvider } from './store/PublishContext'

export default function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <PipelineProvider>
        <PublishProvider>
          <RouterProvider router={router} />
        </PublishProvider>
      </PipelineProvider>
    </ThemeProvider>
  )
}
