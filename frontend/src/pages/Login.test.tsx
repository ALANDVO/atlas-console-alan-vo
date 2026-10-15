import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { Login } from './Login'
import { useAuthStore } from '../hooks/useAuth'
import { authApi } from '../api/client'

// Mock the auth store
vi.mock('../hooks/useAuth', () => ({
  useAuthStore: vi.fn(),
  initAuth: vi.fn(),
}))

// Mock the API client
vi.mock('../api/client', () => ({
  authApi: {
    login: vi.fn(),
    demoToken: vi.fn(),
    oidcLogin: vi.fn(),
  },
}))

const mockUseAuthStore = useAuthStore as unknown as ReturnType<typeof vi.fn>
const mockAuthApi = authApi as unknown as Record<string, ReturnType<typeof vi.fn>>

function renderLogin() {
  return render(
    <BrowserRouter>
      <Login />
    </BrowserRouter>
  )
}

describe('Login Page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseAuthStore.mockReturnValue({
      demoLogin: vi.fn().mockResolvedValue(undefined),
      isLoading: false,
      error: null,
      clearError: vi.fn(),
    })
    mockAuthApi.oidcLogin.mockResolvedValue({
      data: {
        authorization_url: 'https://keycloak.example.com/auth',
        state: 'test-state',
        nonce: 'test-nonce',
        code_verifier: 'test-verifier',
      },
    })
  })

  afterEach(() => {
    vi.resetAllMocks()
  })

  it('renders login form with email and password fields', () => {
    renderLogin()

    expect(screen.getByLabelText('Email')).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  it('shows demo credentials hint', () => {
    renderLogin()

    expect(screen.getByText(/demo@atlas\.local/i)).toBeInTheDocument()
    // "demo" appears multiple times, use getAllByText
    const demoElements = screen.getAllByText(/demo/i)
    expect(demoElements.length).toBeGreaterThanOrEqual(2)
  })

  it('calls demoLogin on form submit', async () => {
    const demoLoginMock = vi.fn().mockResolvedValue(undefined)
    mockUseAuthStore.mockReturnValue({
      demoLogin: demoLoginMock,
      isLoading: false,
      error: null,
      clearError: vi.fn(),
    })

    renderLogin()

    fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'demo@atlas.local' } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'demo' } })
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(demoLoginMock).toHaveBeenCalled()
    })
  })

  it('shows loading state during login', async () => {
    let resolveDemoLogin: (value: void) => void
    const demoLoginPromise = new Promise<void>((resolve) => {
      resolveDemoLogin = resolve
    })

    mockUseAuthStore.mockReturnValue({
      demoLogin: vi.fn().mockReturnValue(demoLoginPromise),
      isLoading: true,
      error: null,
      clearError: vi.fn(),
    })

    renderLogin()

    // Find submit button by role
    const submitButton = screen.getByRole('button')
    fireEvent.click(submitButton)

    expect(submitButton).toBeDisabled()
    // Check for loading spinner using test-id
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument()

    await act(async () => {
      resolveDemoLogin!()
      await demoLoginPromise
    })
  })

  it('displays error message when login fails', () => {
    mockUseAuthStore.mockReturnValue({
      demoLogin: vi.fn().mockRejectedValue(new Error('Invalid credentials')),
      isLoading: false,
      error: 'Invalid credentials',
      clearError: vi.fn(),
    })

    renderLogin()

    expect(screen.getByRole('alert')).toHaveTextContent('Invalid credentials')
  })

  it('shows OIDC login button when demo mode is enabled', () => {
    // Set demo mode env
    vi.stubEnv('VITE_DEMO_MODE', 'true')

    renderLogin()

    expect(screen.getByRole('button', { name: /sign in with keycloak/i })).toBeInTheDocument()

    vi.unstubAllEnvs()
  })

  it('clears error when user starts typing', () => {
    const clearErrorMock = vi.fn()
    mockUseAuthStore.mockReturnValue({
      demoLogin: vi.fn().mockRejectedValue(new Error('Invalid credentials')),
      isLoading: false,
      error: 'Invalid credentials',
      clearError: clearErrorMock,
    })

    renderLogin()

    expect(screen.getByRole('alert')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'new@email.com' } })

    expect(clearErrorMock).toHaveBeenCalled()
  })
})