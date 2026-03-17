import { z } from 'zod'

export const userOutSchema = z.object({
  id: z.number(),
  email: z.string(),
  first_name: z.string(),
  last_name: z.string(),
  role: z.enum(['user', 'admin']).or(z.string()),
  created_at: z.string(),
})

export type UserOut = z.infer<typeof userOutSchema>

export const tokenSchema = z.object({
  access_token: z.string(),
  token_type: z.string().default('bearer'),
})

export type TokenResponse = z.infer<typeof tokenSchema>