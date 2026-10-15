import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { authApi, type UserResponse, type TokenResponse } from '../api/client'

interface AuthState {
  user: UserResponse | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null

  login: (email: string, password: string) => Promise<void>
  demoLogin: () => Promise<void>
  logout: () => Promise<void>
  refreshAccessToken: () => Promise<void>
  fetchUser: () => Promise<void>
  clearError: () => void
  setTokens: (tokens: TokenResponse) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      setTokens: (tokens: TokenResponse) => {
        set({
          accessToken: tokens.access_token,
          refreshToken: tokens.refresh_token,
          isAuthenticated: true,
        })
        // Also store in localStorage for axios interceptor
        localStorage.setItem('access_token', tokens.access_token)
        localStorage.setItem('refresh_token', tokens.refresh_token)
      },

      login: async (email: string, password: string) => {
        set({ isLoading: true, error: null })
        try {
          const response = await authApi.login(email, password)
          get().setTokens(response.data)
          await get().fetchUser()
        } catch (error: unknown) {
          const message = error instanceof Error ? error.message : 'Login failed'
          set({ error: message, isAuthenticated: false })
          throw error
        } finally {
          set({ isLoading: false })
        }
      },

      demoLogin: async () => {
        set({ isLoading: true, error: null })
        try {
          const response = await authApi.demoToken()
          get().setTokens(response.data)
          await get().fetchUser()
        } catch (error: unknown) {
          const message = error instanceof Error ? error.message : 'Demo login failed'
          set({ error: message, isAuthenticated: false })
          throw error
        } finally {
          set({ isLoading: false })
        }
      },

      logout: async () => {
        set({ isLoading: true })
        try {
          await authApi.logout()
        } catch {
          // Ignore logout errors
        } finally {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          set({
            user: null,
            accessToken: null,
            refreshToken: null,
            isAuthenticated: false,
            isLoading: false,
          })
        }
      },

      refreshAccessToken: async () => {
        const refreshToken = get().refreshToken
        if (!refreshToken) return

        try {
          const response = await authApi.refresh(refreshToken)
          get().setTokens(response.data)
        } catch {
          // Refresh failed, logout
          get().logout()
        }
      },

      fetchUser: async () => {
        try {
          const response = await authApi.me()
          set({ user: response.data, isAuthenticated: true })
        } catch {
          set({ user: null, isAuthenticated: false })
        }
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: 'atlas-auth',
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)

// Initialize auth on app start
export const initAuth = async () => {
  const store = useAuthStore.getState()
  if (store.isAuthenticated && store.accessToken) {
    localStorage.setItem('access_token', store.accessToken)
    if (store.refreshToken) {
      localStorage.setItem('refresh_token', store.refreshToken)
    }
    await store.fetchUser()
  }
}