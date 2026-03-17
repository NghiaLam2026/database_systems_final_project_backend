import { apiRequest } from '@/lib/api/client'
import { tokenSchema, userOutSchema } from './auth.types'

export function register(payload: {
  email: string
  password: string
  first_name: string
  last_name: string
}) {
  return apiRequest('/api/v1/auth/register', {
    method: 'POST',
    body: payload,
    schema: userOutSchema,
  })
}

export function login(payload: { email: string; password: string }) {
  return apiRequest('/api/v1/auth/login', {
    method: 'POST',
    body: payload,
    schema: tokenSchema,
  })
}

export function me(token: string) {
  return apiRequest('/api/v1/auth/me', {
    method: 'GET',
    token,
    schema: userOutSchema,
  })
}