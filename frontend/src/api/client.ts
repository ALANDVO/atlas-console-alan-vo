import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1'

export const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
})

// Request interceptor to add auth token from cookie (handled by withCredentials)
// but also support Authorization header for programmatic access
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('access_token')
  if (token && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Clear local storage and redirect to login
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

// Auth API
export const authApi = {
  login: (email: string, password: string) =>
    api.post<TokenResponse>('/auth/login', { email, password }),

  demoToken: () =>
    api.post<TokenResponse>('/auth/demo/token'),

  refresh: (refreshToken: string) =>
    api.post<TokenResponse>('/auth/refresh', { refresh_token: refreshToken }),

  logout: () =>
    api.post('/auth/logout'),

  me: () =>
    api.get<UserResponse>('/auth/me'),

  oidcLogin: () =>
    api.get<OIDCLoginResponse>('/auth/oidc/login'),

  oidcCallback: (code: string, state: string, codeVerifier: string) =>
    api.post<TokenResponse>('/auth/oidc/callback', { code, state, code_verifier: codeVerifier }),

  oidcLogout: () =>
    api.get('/auth/oidc/logout'),
}

// Dashboard API
export const dashboardApi = {
  getDashboard: () =>
    api.get<DashboardResponse>('/dashboard'),

  getStats: () =>
    api.get<DashboardStats>('/dashboard/stats'),
}

// Types
export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface UserResponse {
  id: number
  email: string
  full_name: string | null
  role: string
  is_active: boolean
  created_at: string
}

export interface OIDCLoginResponse {
  authorization_url: string
  state: string
  nonce: string
  code_verifier: string
}

export interface DashboardStats {
  total_flows: number
  active_flows: number
  completed_flows: number
  total_findings: number
  critical_findings: number
  high_findings: number
}

export interface RecentActivity {
  id: number
  type: string
  title: string
  description: string
  timestamp: string
  status: string
}

export interface DashboardResponse {
  stats: DashboardStats
  recent_activity: RecentActivity[]
  user: {
    id: number
    email: string
    full_name: string | null
    role: string
  }
}