import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import Box from '@mui/material/Box'
import Drawer from '@mui/material/Drawer'
import List from '@mui/material/List'
import ListItemButton from '@mui/material/ListItemButton'
import ListItemText from '@mui/material/ListItemText'
import Typography from '@mui/material/Typography'
import { IZK } from '../theme'

const W = 200
const NAV = [
  { label: 'Topics', path: '/' },
  { label: 'Pipeline', path: '/pipeline' },
  { label: 'Publish', path: '/publish' },
  { label: 'Analytics', path: '/analytics' },
]

export default function AppShell() {
  const navigate = useNavigate()
  const { pathname } = useLocation()

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
      <Drawer
        variant="permanent"
        sx={{ width: W, flexShrink: 0, '& .MuiDrawer-paper': { width: W } }}
      >
        <Box sx={{ p: '20px 16px 16px', borderBottom: '1px solid', borderColor: IZK.subtleBorder }}>
          <Typography sx={{
            fontSize: 11, fontWeight: 700, letterSpacing: '5px',
            textTransform: 'uppercase', color: 'primary.main',
            textShadow: '0 0 10px #ff6b3570', mb: 0.5,
          }}>
            Shorts
          </Typography>
          <Typography sx={{ fontSize: 9, letterSpacing: '2px', textTransform: 'uppercase', color: IZK.dim }}>
            YT Automation
          </Typography>
        </Box>

        <List dense sx={{ pt: 1.5, flex: 1 }}>
          {NAV.map(({ label, path }) => {
            const active = pathname === path
            return (
              <ListItemButton
                key={path}
                selected={active}
                onClick={() => navigate(path)}
                sx={{
                  borderLeft: '2px solid',
                  borderColor: active ? 'primary.main' : 'transparent',
                  background: active ? 'linear-gradient(90deg, #ff6b3510, transparent)' : 'transparent',
                  '&.Mui-selected': { bgcolor: 'transparent' },
                  '&.Mui-selected:hover': { bgcolor: '#ff6b3508' },
                  '&:hover': { bgcolor: '#ff6b3806' },
                  py: 1.25, px: 2,
                }}
              >
                <Box sx={{
                  width: 6, height: 6, borderRadius: '50%', mr: 1.5, flexShrink: 0,
                  bgcolor: active ? 'primary.main' : IZK.dim,
                  boxShadow: active ? '0 0 6px #ff6b35' : 'none',
                  transition: 'all 0.15s',
                }} />
                <ListItemText
                  primary={label}
                  slotProps={{
                    primary: {
                      sx: {
                        fontSize: 12,
                        letterSpacing: '0.5px',
                        color: active ? 'text.primary' : IZK.muted,
                      },
                    },
                  }}
                />
              </ListItemButton>
            )
          })}
        </List>

        <Box sx={{ p: '12px 16px', borderTop: '1px solid', borderColor: IZK.subtleBorder }}>
          <Typography sx={{ fontSize: 9, color: IZK.dim, letterSpacing: '1px' }}>
            EST · UTC−5
          </Typography>
        </Box>
      </Drawer>

      <Box component="main" sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', bgcolor: 'background.default' }}>
        <Outlet />
      </Box>
    </Box>
  )
}
