import { useState, FormEvent, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../hooks/useAuth'
import { authApi } from '../api/client'

export function Login() {
  const navigate = useNavigate()
  const { demoLogin, isLoading, error, clearError } = useAuthStore()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [oidcLoading, setOidcLoading] = useState(false)

  // Check for OIDC callback params
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const code = params.get('code')
    const state = params.get('state')
    const storedState = sessionStorage.getItem('oidc_state')
    const codeVerifier = sessionStorage.getItem('oidc_code_verifier')

    if (code && state && storedState && codeVerifier && state === storedState) {
      handleOidcCallback(code, codeVerifier)
    }
  }, [])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    clearError()
    try {
      await demoLogin()
      navigate('/dashboard', { replace: true })
    } catch {
      // Error handled by store
    }
  }

  const handleOidcLogin = async () => {
    setOidcLoading(true)
    clearError()
    try {
      const response = await authApi.oidcLogin()
      const { authorization_url, state, nonce, code_verifier } = response.data

      // Store PKCE params in sessionStorage
      sessionStorage.setItem('oidc_state', state)
      sessionStorage.setItem('oidc_nonce', nonce)
      sessionStorage.setItem('oidc_code_verifier', code_verifier)

      // Redirect to Keycloak
      window.location.href = authorization_url
    } catch (err) {
      const message = err instanceof Error ? err.message : 'OIDC login failed'
      useAuthStore.getState().error = message
      setOidcLoading(false)
    }
  }

  const handleOidcCallback = async (code: string, codeVerifier: string) => {
    const state = sessionStorage.getItem('oidc_state')
    if (!state) return

    setOidcLoading(true)
    try {
      const response = await authApi.oidcCallback(code, state, codeVerifier)
      const { access_token, refresh_token, expires_in, token_type } = response.data

      useAuthStore.getState().setTokens({
        access_token,
        refresh_token,
        token_type,
        expires_in,
      })

      // Clear sessionStorage
      sessionStorage.removeItem('oidc_state')
      sessionStorage.removeItem('oidc_nonce')
      sessionStorage.removeItem('oidc_code_verifier')

      await useAuthStore.getState().fetchUser()
      navigate('/dashboard', { replace: true })
    } catch (err) {
      const message = err instanceof Error ? err.message : 'OIDC callback failed'
      useAuthStore.getState().error = message
      setOidcLoading(false)
    }
  }

  const isDemoMode = import.meta.env.VITE_DEMO_MODE === 'true'

  return (
    <div className="login-page">
      <div className="card login-card">
        <div className="login-card__header">
          <div className="login-card__logo">AC</div>
          <h1 className="login-card__title">Atlas Console</h1>
          <p className="login-card__subtitle">
            Autonomous AI Penetration Testing Platform
          </p>
        </div>

        {error && (
          <div className="alert alert--error" role="alert">
            <span>⚠</span>
            <span>{error}</span>
          </div>
        )}

        <form className="login-form" onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="email" className="form-label">Email</label>
            <input
              id="email"
              type="email"
              className="form-input"
              placeholder="demo@atlas.local"
              value={email}
              onChange={(e) => { setEmail(e.target.value); clearError(); }}
              required
              disabled={isLoading}
              autoComplete="email"
            />
          </div>

          <div className="form-group">
            <label htmlFor="password" className="form-label">Password</label>
            <input
              id="password"
              type="password"
              className="form-input"
              placeholder="••••••••"
              value={password}
              onChange={(e) => { setPassword(e.target.value); clearError(); }}
              required
              disabled={isLoading}
              autoComplete="current-password"
            />
          </div>

          <button
            type="submit"
            className="btn btn--primary"
            disabled={isLoading}
            style={{ width: '100%' }}
          >
            {isLoading ? <span className="loading" data-testid="loading-spinner" /> : 'Sign In'}
          </button>
        </form>

        {isDemoMode && (
          <>
            <div className="login-form__divider">or</div>
            <button
              type="button"
              className="btn btn--secondary"
              style={{ width: '100%' }}
              onClick={handleOidcLogin}
              disabled={oidcLoading || isLoading}
            >
              {oidcLoading ? <span className="loading" /> : '🔐 Sign in with Keycloak (OIDC)'}
            </button>
          </>
        )}

        <div className="login-footer">
          <p>Demo credentials: <code>demo@atlas.local</code> / <code>demo</code></p>
          <p style={{ marginTop: '8px' }}>v1.0.0 &bull; Alan Vo {'alanvo@gmail.com'}</p>
        </div>
      </div>
    </div>
  )
}