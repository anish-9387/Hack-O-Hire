import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User } from '@/lib/api-client'

interface AuthState {
  token: string | null
  user: User | null
  role: string | null
  setAuth: (token: string, user: User, role: string) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      role: null,
      setAuth: (token, user, role) => set({ token, user, role }),
      logout: () => set({ token: null, user: null, role: null }),
    }),
    {
      name: 'finhealth-auth',
    }
  )
)
