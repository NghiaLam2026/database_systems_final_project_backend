import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'

export function RequireAdmin() {
  const { state } = useAuth()

  if (state.status === 'loading') return <Outlet />
  if (state.status !== 'authenticated') return <Navigate to="/" replace />
  if (state.user.role !== 'admin') return <Navigate to="/app" replace />

  return <Outlet />
}