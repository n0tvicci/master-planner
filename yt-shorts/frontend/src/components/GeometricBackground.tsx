import Box from '@mui/material/Box'

export default function GeometricBackground() {
  return (
    <Box sx={{ position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 0, overflow: 'hidden' }}>

      {/* S1 — amber rotating square */}
      <Box sx={{
        position: 'absolute', top: '12%', left: '78%',
        width: 28, height: 28,
        border: '1px solid #ff6b35',
        opacity: 0.45,
        animation: 'izk-s1 7s ease-in-out infinite',
        '@keyframes izk-s1': {
          '0%':   { transform: 'translateY(0) rotate(0deg)' },
          '50%':  { transform: 'translateY(-18px) rotate(180deg)' },
          '100%': { transform: 'translateY(0) rotate(360deg)' },
        },
      }} />

      {/* S2 — amber drifting diamond */}
      <Box sx={{
        position: 'absolute', top: '48%', left: '62%',
        width: 36, height: 36,
        border: '1px solid #ff6b35',
        opacity: 0.30,
        animation: 'izk-s2 11s ease-in-out infinite 1.2s',
        '@keyframes izk-s2': {
          '0%,100%': { transform: 'translate(0, 0) rotate(45deg)' },
          '33%':     { transform: 'translate(8px, -12px) rotate(60deg)' },
          '66%':     { transform: 'translate(-6px, 8px) rotate(30deg)' },
        },
      }} />

      {/* S3 — green reverse-rotating square */}
      <Box sx={{
        position: 'absolute', top: '72%', left: '85%',
        width: 20, height: 20,
        border: '1px solid #2d6a4f',
        opacity: 0.35,
        animation: 'izk-s3 9s ease-in-out infinite 2.1s',
        '@keyframes izk-s3': {
          '0%':   { transform: 'translateY(0) rotate(0deg)' },
          '50%':  { transform: 'translateY(-14px) rotate(-180deg)' },
          '100%': { transform: 'translateY(0) rotate(-360deg)' },
        },
      }} />

      {/* S4 — large slow green diamond */}
      <Box sx={{
        position: 'absolute', top: '30%', left: '88%',
        width: 48, height: 48,
        border: '1px solid #2d6a4f',
        opacity: 0.25,
        animation: 'izk-s4 14s ease-in-out infinite 0.7s',
        '@keyframes izk-s4': {
          '0%,100%': { transform: 'translate(0, 0) rotate(45deg)' },
          '50%':     { transform: 'translate(-10px, -16px) rotate(60deg)' },
        },
      }} />

      {/* S5 — glowing amber dot */}
      <Box sx={{
        position: 'absolute', top: '20%', left: '70%',
        width: 7, height: 7,
        borderRadius: '50%',
        bgcolor: '#ff6b35',
        opacity: 0.60,
        boxShadow: '0 0 10px #ff6b35',
        animation: 'izk-s5 5s ease-in-out infinite 3.5s',
        '@keyframes izk-s5': {
          '0%,100%': { transform: 'translateY(0) scale(1)',    opacity: 0.60 },
          '50%':     { transform: 'translateY(-8px) scale(1.3)', opacity: 0.40 },
        },
      }} />

      {/* S6 — amber line fragment */}
      <Box sx={{
        position: 'absolute', top: '62%', left: '75%',
        width: 32, height: 1,
        bgcolor: '#ff6b35',
        opacity: 0.20,
        animation: 'izk-s6 12s ease-in-out infinite 1.8s',
        '@keyframes izk-s6': {
          '0%,100%': { transform: 'rotate(45deg) translateX(0)' },
          '50%':     { transform: 'rotate(65deg) translateX(8px)' },
        },
      }} />

      {/* S7 — large faint slowly-rotating filled square */}
      <Box sx={{
        position: 'absolute', top: '55%', left: '58%',
        width: 56, height: 56,
        bgcolor: '#ff6b35',
        opacity: 0.10,
        animation: 'izk-s7 18s linear infinite 0.3s',
        '@keyframes izk-s7': {
          '0%':   { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
      }} />

    </Box>
  )
}
