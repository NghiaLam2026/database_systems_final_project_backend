import { createContext } from 'react'
import type { UserOut } from '@/features/auth/auth.types'

export type AuthState =
  | { status: 'anonymous'; token: null; user: null }
  | { status: 'authenticated'; token: string; user: UserOut }
  | { status: 'loading'; token: string | null; user: null }

export type AuthContextValue = {
  state: AuthState
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

export const AuthContext = createContext<AuthContextValue | null>(null)