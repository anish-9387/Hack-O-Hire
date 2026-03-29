import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User } from '@/lib/api-client'

interface AuthState {
  token: string | null
  refreshToken: string | null
  expiresAt: number | null
  user: User | null
  role: string | null
  setAuth: (token: string, user: User, role: string, refreshToken?: string, expiresIn?: number) => void
  setToken: (token: string, expiresIn?: number) => void
  logout: () => void
  isTokenExpired: () => boolean
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      refreshToken: null,
      expiresAt: null,
      user: null,
      role: null,
      setAuth: (token, user, role, refreshToken, expiresIn) => set({
        token,
        user,
        role,
        refreshToken: refreshToken ?? null,
        expiresAt: expiresIn ? Date.now() + expiresIn * 1000 : null,
      }),
      setToken: (token, expiresIn) => set({
        token,
        expiresAt: expiresIn ? Date.now() + expiresIn * 1000 : null,
      }),
      logout: () => set({
        token: null, refreshToken: null, expiresAt: null, user: null, role: null,
      }),
      isTokenExpired: () => {
        const { expiresAt } = get()
        if (!expiresAt) return false
        // Consider expired 60s before actual expiry to allow refresh
        return Date.now() > expiresAt - 60_000
      },
    }),
    {
      name: 'finhealth-auth',
    }
  )
)
