import { useMemo, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Cpu, ShieldCheck, Sparkles } from 'lucide-react'
import { TopNav } from '@/components/layout/TopNav'
import { Modal } from '@/components/ui/Modal'
import { Button } from '@/components/ui/Button'
import { TextField } from '@/components/ui/TextField'
import { register as registerApi } from '@/features/auth/auth.api'
import { useAuth } from '@/hooks/useAuth'
import { ApiError } from '@/lib/api/client'

type Mode = 'login' | 'register'

export function LandingPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const { state, login } = useAuth()

  const initialOpen = Boolean((location.state as { openAuth?: boolean } | null)?.openAuth)
  const [open, setOpen] = useState(initialOpen)
  const [mode, setMode] = useState<Mode>('login')

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const canSubmit = useMemo(() => {
    if (!email.trim() || !password.trim()) return false
    if (mode === 'register' && (!firstName.trim() || !lastName.trim())) return false
    return true
  }, [email, firstName, lastName, mode, password])

  const onClose = () => {
    setOpen(false)
    setError(null)
    navigate('/', { replace: true, state: {} })
  }

  const onSubmit = async () => {
    setError(null)
    setBusy(true)
    try {
      if (mode === 'register') {
        await registerApi({
          email,
          password,
          first_name: firstName,
          last_name: lastName,
        })
      }
      await login(email, password)
      onClose()
      navigate('/app', { replace: true })
    } catch (e) {
      if (e instanceof ApiError) setError(e.message)
      else if (e instanceof Error) setError(e.message)
      else setError('Something went wrong.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen bg-hero">
      <TopNav onLoginClick={() => setOpen(true)} />

      <main className="mx-auto max-w-6xl px-6 pb-16 pt-14">
        <div className="text-center">
          <h1 className="mx-auto max-w-2xl text-balance text-4xl font-semibold tracking-tight text-ink-950 sm:text-5xl">
            One <span className="text-brand-600">Build</span> for all your PC needs
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-pretty text-sm leading-6 text-ink-800">
            Create and manage builds, browse parts, and get compatibility-aware help. Fast, simple, and designed to feel
            premium.
          </p>

          <div className="mt-8 flex justify-center gap-3">
            {state.status === 'authenticated' ? (
              <Link to="/app">
                <Button variant="secondary">Go to dashboard</Button>
              </Link>
            ) : (
              <Button onClick={() => setOpen(true)}>Log in</Button>
            )}
            <Link to="/app/catalog">
              <Button variant="ghost" className="border border-white/70 bg-white/40 backdrop-blur hover:bg-white/60">
                Browse catalog
              </Button>
            </Link>
          </div>
        </div>

        <section className="mt-12 grid gap-4 sm:grid-cols-3">
          <FeatureCard
            icon={<Cpu className="h-5 w-5 text-brand-600" />}
            title="General"
            body="Build a workspace for your parts, budget, and upgrades."
          />
          <FeatureCard
            icon={<ShieldCheck className="h-5 w-5 text-brand-600" />}
            title="Manage"
            body="Secure accounts, role-based access, and clean audit-friendly soft deletes."
          />
          <FeatureCard
            icon={<Sparkles className="h-5 w-5 text-brand-600" />}
            title="Connect"
            body="Chat is wired end-to-end today; AI orchestration can plug in later."
          />
        </section>
      </main>

      <Modal open={open} title={mode === 'login' ? 'Account Log In' : 'Create Account'} onClose={onClose}>
        <div className="p-7">
          <button
            className="absolute right-4 top-4 rounded-lg p-2 text-ink-800/60 hover:bg-white/60 hover:text-ink-900"
            onClick={onClose}
            aria-label="Close"
          >
            ✕
          </button>

          <div className="text-center">
            <div className="mx-auto inline-flex items-center gap-2">
              <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-ink-950 text-sm font-semibold text-white">
                PC
              </span>
              <span className="text-sm font-semibold tracking-tight text-ink-950">PC Build Assistant</span>
            </div>
            <h2 className="mt-4 text-2xl font-semibold text-ink-950">
              {mode === 'login' ? 'Account Log In' : 'Create Account'}
            </h2>
          </div>

          <div className="mt-6 space-y-3">
            {mode === 'register' ? (
              <div className="grid grid-cols-2 gap-3">
                <TextField label="First name" value={firstName} onChange={setFirstName} placeholder="First name" />
                <TextField label="Last name" value={lastName} onChange={setLastName} placeholder="Last name" />
              </div>
            ) : null}

            <TextField
              label="Username/Email"
              value={email}
              onChange={setEmail}
              placeholder="Username/Email"
              autoComplete="email"
            />
            <TextField
              label="Password"
              type="password"
              value={password}
              onChange={setPassword}
              placeholder="Password"
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
            />
          </div>

          {error ? (
            <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          ) : null}

          <div className="mt-6">
            <Button
              className="w-full"
              onClick={onSubmit}
              disabled={!canSubmit}
              loading={busy}
              variant="primary"
            >
              {mode === 'login' ? 'Log In' : 'Register'}
            </Button>
          </div>

          <div className="mt-4 flex items-center justify-between text-xs">
            <button className="text-brand-600 hover:underline" type="button" onClick={() => setMode('login')}>
              Having problems?
            </button>
            <button
              className="text-brand-600 hover:underline"
              type="button"
              onClick={() => setMode(mode === 'login' ? 'register' : 'login')}
            >
              {mode === 'login' ? 'Register Now' : 'Back to Log In'}
            </button>
          </div>

          <div className="my-6 flex items-center gap-3">
            <div className="h-px flex-1 bg-mist-200" />
            <div className="text-[11px] text-ink-800/70">More Login Methods</div>
            <div className="h-px flex-1 bg-mist-200" />
          </div>

          <div className="flex justify-center gap-3">
            {['G', '', 'f', 'X', 'PS'].map((t) => (
              <button
                key={t}
                type="button"
                className="flex h-11 w-11 items-center justify-center rounded-full border border-mist-200 bg-white text-sm text-ink-900 shadow-sm hover:bg-mist-50"
                aria-label={`Login method ${t}`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>
      </Modal>
    </div>
  )
}

function FeatureCard({ icon, title, body }: { icon: React.ReactNode; title: string; body: string }) {
  return (
    <div className="rounded-xl2 border border-white/70 bg-white/55 p-6 shadow-soft backdrop-blur">
      <div className="mb-3 inline-flex h-9 w-9 items-center justify-center rounded-xl bg-white shadow-sm">{icon}</div>
      <div className="text-left">
        <div className="text-sm font-semibold text-ink-950">{title}</div>
        <div className="mt-1 text-sm leading-6 text-ink-800">{body}</div>
      </div>
    </div>
  )
}