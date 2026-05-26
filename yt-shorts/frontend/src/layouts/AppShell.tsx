import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import Box from '@mui/material/Box'
import Drawer from '@mui/material/Drawer'
import List from '@mui/material/List'
import ListItemButton from '@mui/material/ListItemButton'
import ListItemIcon from '@mui/material/ListItemIcon'
import ListItemText from '@mui/material/ListItemText'
import Typography from '@mui/material/Typography'
import Divider from '@mui/material/Divider'
import ListAltIcon from '@mui/icons-material/ListAlt'
import BoltIcon from '@mui/icons-material/Bolt'
import RocketLaunchIcon from '@mui/icons-material/RocketLaunch'
import BarChartIcon from '@mui/icons-material/BarChart'

const W = 192
const NAV = [
  { label: 'Topics', path: '/', Icon: ListAltIcon },
  { label: 'Pipeline', path: '/pipeline', Icon: BoltIcon },
  { label: 'Publish', path: '/publish', Icon: RocketLaunchIcon },
  { label: 'Analytics', path: '/analytics', Icon: BarChartIcon },
]

export default function AppShell() {
  const navigate = useNavigate()
  const { pathname } = useLocation()

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
      <Drawer
        variant="permanent"
        sx={{
          width: W, flexShrink: 0,
          '& .MuiDrawer-paper': { width: W, bgcolor: '#1a1f2e', borderRight: '1px solid', borderColor: 'divider' },
        }}
      >
        <Box sx={{ p: 2, pb: 1.5 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 800, color: 'primary.main', letterSpacing: 1 }}>SHORTS</Typography>
          <Typography variant="caption" color="text.secondary">YT Automation</Typography>
        </Box>
        <Divider />
        <List dense sx={{ pt: 1 }}>
          {NAV.map(({ label, path, Icon }) => {
            const active = pathname === path
            return (
              <ListItemButton
                key={path}
                selected={active}
                onClick={() => navigate(path)}
                sx={{
                  borderLeft: '2px solid',
                  borderColor: active ? 'primary.main' : 'transparent',
                  '&.Mui-selected': { bgcolor: 'primary.main' + '15' },
                }}
              >
                <ListItemIcon sx={{ minWidth: 32, color: active ? 'text.primary' : 'text.secondary' }}>
                  <Icon fontSize="small" />
                </ListItemIcon>
                <ListItemText
                  primary={label}
                  primaryTypographyProps={{ fontSize: 13, color: active ? 'text.primary' : 'text.secondary' }}
                />
              </ListItemButton>
            )
          })}
        </List>
      </Drawer>
      <Box component="main" sx={{ flex: 1, p: 3, overflow: 'auto' }}>
        <Outlet />
      </Box>
    </Box>
  )
}
