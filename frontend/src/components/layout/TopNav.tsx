import { Link } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { cn } from '@/lib/utils/cn'

export function TopNav({ onLoginClick }: { onLoginClick?: () => void }) {
  const { state, logout } = useAuth()

  return (
    <header className="sticky top-0 z-20 border-b border-white/40 bg-white/30 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link to="/" className="flex items-center gap-2">
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-xl bg-ink-950 text-sm font-semibold text-white shadow-soft">
            PC
          </span>
          <span className="text-sm font-semibold tracking-tight text-ink-950">PC Build Assistant</span>
        </Link>

        <nav className="flex items-center gap-2 text-sm text-ink-900">
          <Link className="rounded-lg px-3 py-2 hover:bg-white/50" to="/app">
            Dashboard
          </Link>
          <Link className="rounded-lg px-3 py-2 hover:bg-white/50" to="/app/catalog">
            Catalog
          </Link>

          {state.status === 'authenticated' ? (
            <>
              <span className="hidden text-xs text-ink-800 sm:inline">
                {state.user.first_name} {state.user.last_name}
              </span>
              <button
                onClick={logout}
                className={cn(
                  'ml-2 inline-flex items-center justify-center rounded-xl px-4 py-2 text-xs font-semibold',
                  'bg-ink-950 text-white hover:bg-ink-900',
                )}
              >
                Log out
              </button>
            </>
          ) : (
            <button
              onClick={onLoginClick}
              className={cn(
                'ml-2 inline-flex items-center justify-center rounded-xl px-4 py-2 text-xs font-semibold',
                'bg-brand-600 text-white hover:bg-brand-500',
              )}
            >
              Log in
            </button>
          )}
        </nav>
      </div>
    </header>
  )
}