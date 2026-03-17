import React, { useCallback, useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiError } from '@/lib/api/client'
import { clearToken, getToken, isTokenExpired, setToken } from '@/lib/auth/token'
import { login as loginApi, me as meApi } from '@/features/auth/auth.api'
import { AuthContext, type AuthContextValue, type AuthState } from './AuthContext'

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const qc = useQueryClient()
  const [token, setTokenState] = useState<string | null>(() => getToken())

  const shouldFetchMe = token != null && !isTokenExpired(token)

  const meQuery = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: async () => {
      if (!token) throw new Error('Missing token')
      return await meApi(token)
    },
    enabled: shouldFetchMe,
    retry: (count, err) => {
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) return false
      return count < 1
    },
  })

  const logout = useCallback(() => {
    clearToken()
    setTokenState(null)
    qc.removeQueries({ queryKey: ['auth', 'me'] })
  }, [qc])

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await loginApi({ email, password })
      setToken(res.access_token)
      setTokenState(res.access_token)
      await qc.invalidateQueries({ queryKey: ['auth', 'me'] })
    },
    [qc],
  )

  const state: AuthState = useMemo(() => {
    if (!token) return { status: 'anonymous', token: null, user: null }
    if (isTokenExpired(token)) return { status: 'anonymous', token: null, user: null }
    if (meQuery.isLoading) return { status: 'loading', token, user: null }
    if (meQuery.data) return { status: 'authenticated', token, user: meQuery.data }

    // If token exists but /me fails with 401/403, treat as logged out.
    if (meQuery.error instanceof ApiError && (meQuery.error.status === 401 || meQuery.error.status === 403)) {
      return { status: 'anonymous', token: null, user: null }
    }
    // Otherwise allow UI to show error state while keeping token.
    return { status: 'loading', token, user: null }
  }, [meQuery.data, meQuery.error, meQuery.isLoading, token])

  const value = useMemo<AuthContextValue>(() => ({ state, login, logout }), [state, login, logout])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}