import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'

export function RequireAuth() {
  const { state } = useAuth()
  const location = useLocation()

  if (state.status === 'loading') {
    return (
      <div className="min-h-screen bg-hero">
        <div className="mx-auto max-w-6xl px-6 py-16">
          <div className="rounded-xl2 bg-white/70 p-8 shadow-card backdrop-blur">
            <div className="h-6 w-40 animate-pulse rounded bg-mist-200" />
            <div className="mt-4 h-4 w-64 animate-pulse rounded bg-mist-200" />
          </div>
        </div>
      </div>
    )
  }

  if (state.status !== 'authenticated') {
    return <Navigate to="/" replace state={{ from: location.pathname }} />
  }

  return <Outlet />
}