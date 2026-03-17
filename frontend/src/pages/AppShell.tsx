import { NavLink, Outlet } from 'react-router-dom'
import { TopNav } from '@/components/layout/TopNav'
import { useAuth } from '@/hooks/useAuth'
import { cn } from '@/lib/utils/cn'

export function AppShell() {
  const { state } = useAuth()

  return (
    <div className="min-h-screen bg-hero">
      <TopNav />
      <div className="mx-auto grid max-w-6xl gap-6 px-6 py-8 md:grid-cols-[220px_1fr]">
        <aside className="rounded-xl2 border border-white/70 bg-white/55 p-3 shadow-soft backdrop-blur">
          <div className="px-3 pb-3 text-xs font-semibold text-ink-800">Workspace</div>
          <nav className="space-y-1 text-sm">
            <SideLink to="/app" end>
              Builds
            </SideLink>
            <SideLink to="/app/catalog">Catalog</SideLink>
            <SideLink to="/app/chat">Chat</SideLink>
            {state.status === 'authenticated' && state.user.role === 'admin' ? (
              <>
                <div className="px-3 pt-4 text-xs font-semibold text-ink-800">Admin</div>
                <SideLink to="/app/admin/users">Users</SideLink>
              </>
            ) : null}
          </nav>
        </aside>

        <main className="rounded-xl2 border border-white/70 bg-white/55 p-6 shadow-soft backdrop-blur">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

function SideLink({ to, end, children }: { to: string; end?: boolean; children: React.ReactNode }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        cn(
          'flex rounded-lg px-3 py-2 text-ink-900 hover:bg-white/60',
          isActive && 'bg-white/80 font-semibold',
        )
      }
    >
      {children}
    </NavLink>
  )
}