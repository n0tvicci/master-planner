import { createBrowserRouter } from 'react-router-dom'
import AppShell from '../layouts/AppShell'
import TopicsPage from '../pages/TopicsPage'
import PipelinePage from '../pages/PipelinePage'
import PublishPage from '../pages/PublishPage'
import AnalyticsPage from '../pages/AnalyticsPage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <TopicsPage /> },
      { path: 'pipeline', element: <PipelinePage /> },
      { path: 'publish', element: <PublishPage /> },
      { path: 'analytics', element: <AnalyticsPage /> },
    ],
  },
])
