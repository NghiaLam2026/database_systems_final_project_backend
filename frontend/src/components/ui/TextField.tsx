import React from 'react'
import { cn } from '@/lib/utils/cn'

export function TextField({
  label,
  type = 'text',
  placeholder,
  value,
  onChange,
  autoComplete,
  error,
  rightSlot,
}: {
  label?: string
  type?: React.HTMLInputTypeAttribute
  placeholder?: string
  value: string
  onChange: (v: string) => void
  autoComplete?: string
  error?: string
  rightSlot?: React.ReactNode
}) {
  return (
    <div className="w-full">
      {label ? <div className="mb-1 text-xs font-medium text-ink-800">{label}</div> : null}
      <div
        className={cn(
          'flex items-center gap-2 rounded-xl border bg-white px-4 py-3 shadow-sm',
          error ? 'border-red-300' : 'border-mist-200',
          'focus-within:border-brand-400 focus-within:ring-2 focus-within:ring-brand-400/30',
        )}
      >
        <input
          className="w-full bg-transparent text-sm text-ink-950 placeholder:text-ink-800/40 focus:outline-none"
          type={type}
          value={value}
          placeholder={placeholder}
          onChange={(e) => onChange(e.target.value)}
          autoComplete={autoComplete}
        />
        {rightSlot}
      </div>
      {error ? <div className="mt-1 text-xs text-red-600">{error}</div> : null}
    </div>
  )
}