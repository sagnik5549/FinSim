import { Loader2 } from 'lucide-react'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { AuthProvider, useAuth } from './auth/AuthContext'
import { GameProvider } from './game/GameContext'
import { applyTheme } from './game/theme'
import Login from './pages/Login'
import './index.css'

applyTheme()

function AuthGate() {
  const { user, checking } = useAuth()
  if (checking) return <div className="flex h-full items-center justify-center text-txt-mute"><Loader2 className="animate-spin" /></div>
  if (!user) return <Login />
  // Keyed by account so switching users starts from a clean game context.
  return (
    <GameProvider key={user.id}>
      <App />
    </GameProvider>
  )
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AuthProvider>
      <AuthGate />
    </AuthProvider>
  </StrictMode>,
)
