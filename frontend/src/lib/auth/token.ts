import { jwtDecode } from 'jwt-decode'
import { z } from 'zod'

const tokenPayloadSchema = z.object({
  sub: z.coerce.number(),
  role: z.string(),
  exp: z.coerce.number(),
})

export type TokenPayload = z.infer<typeof tokenPayloadSchema>

const storageKey = 'pcbuild_access_token'

export function getToken(): string | null {
  return localStorage.getItem(storageKey)
}

export function setToken(token: string): void {
  localStorage.setItem(storageKey, token)
}

export function clearToken(): void {
  localStorage.removeItem(storageKey)
}

export function decodeToken(token: string): TokenPayload | null {
  try {
    const raw = jwtDecode(token)
    return tokenPayloadSchema.parse(raw)
  } catch {
    return null
  }
}

export function isTokenExpired(token: string): boolean {
  const payload = decodeToken(token)
  if (!payload) return true
  const now = Math.floor(Date.now() / 1000)
  return payload.exp <= now
}