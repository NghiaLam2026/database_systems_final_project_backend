import { z } from 'zod'

export class ApiError extends Error {
  status: number
  body?: unknown

  constructor(message: string, status: number, body?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL as string | undefined

if (!apiBaseUrl) {
  // Fail fast in dev to avoid silent calls to wrong origin.
  // In production builds, this should be configured via Vite env.
  console.warn('VITE_API_BASE_URL is not set. API calls will fail.')
}

export type HttpMethod = 'GET' | 'POST' | 'PATCH' | 'DELETE'

export async function apiRequest<T>(
  path: string,
  opts: {
    method?: HttpMethod
    token?: string | null
    body?: unknown
    schema?: z.ZodType<T>
    signal?: AbortSignal
  } = {},
): Promise<T> {
  const url = `${apiBaseUrl ?? ''}${path}`
  const method = opts.method ?? 'GET'

  const headers: Record<string, string> = {
    Accept: 'application/json',
  }
  let body: BodyInit | undefined

  if (opts.token) {
    headers.Authorization = `Bearer ${opts.token}`
  }

  if (opts.body !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(opts.body)
  }

  const res = await fetch(url, { method, headers, body, signal: opts.signal })

  const isJson = res.headers.get('content-type')?.includes('application/json')
  const parsed = isJson ? await res.json().catch(() => undefined) : await res.text().catch(() => undefined)

  if (!res.ok) {
    const message =
      typeof parsed === 'object' && parsed && 'detail' in parsed
        ? String((parsed as { detail?: unknown }).detail)
        : `Request failed (${res.status})`
    throw new ApiError(message, res.status, parsed)
  }

  if (!opts.schema) return parsed as T
  return opts.schema.parse(parsed)
}