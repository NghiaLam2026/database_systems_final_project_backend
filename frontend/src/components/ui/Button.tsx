import React from 'react'
import { cn } from '@/lib/utils/cn'
type Variant = 'primary' | 'secondary' | 'ghost'

export function Button({
  children,
  onClick,
  type = 'button',
  disabled,
  loading,
  variant = 'primary',
  className,
}: {
  children: React.ReactNode
  onClick?: () => void
  type?: 'button' | 'submit'
  disabled?: boolean
  loading?: boolean
  variant?: Variant
  className?: string
}) {
  const isDisabled = disabled || loading

  const base =
    'inline-flex items-center justify-center rounded-xl px-4 py-3 text-sm font-semibold transition focus:outline-none focus:ring-2 focus:ring-brand-400/40'
  const variants: Record<Variant, string> = {
    primary: 'bg-brand-600 text-white hover:bg-brand-500 disabled:bg-mist-200 disabled:text-ink-800/50',
    secondary: 'bg-ink-950 text-white hover:bg-ink-900 disabled:bg-ink-950/30',
    ghost: 'bg-transparent text-ink-900 hover:bg-white/60 disabled:text-ink-800/50',
  }

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={isDisabled}
      className={cn(base, variants[variant], className)}
    >
      {loading ? 'Loading…' : children}
    </button>
  )
}