import { ReactNode, useEffect } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../hooks/useAuth'

interface LayoutProps {
  children?: ReactNode
}

const navigation = [
  { path: '/dashboard', label: 'Dashboard', icon: '📊' },
  { path: '/flows', label: 'Flows', icon: '🔄' },
  { path: '/scope', label: 'Scope', icon: '🎯' },
  { path: '/resources', label: 'Resources', icon: '📚' },
  { path: '/mcp', label: 'MCP Tools', icon: '🔌' },
  { path: '/providers', label: 'Providers', icon: '🤖' },
]

export function Layout({ children }: LayoutProps) {
  const { user, logout, isAuthenticated } = useAuthStore()
  const navigate = useNavigate()

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login', { replace: true })
    }
  }, [isAuthenticated, navigate])

  if (!isAuthenticated) {
    return null
  }

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="layout">
      <aside className="layout__sidebar" role="navigation" aria-label="Main navigation">
        <header className="layout__header">
          <div className="login-card__logo" style={{ width: '40px', height: '40px', fontSize: '1rem' }}>
            AC
          </div>
          <span style={{ fontWeight: 600, fontSize: '1.125rem' }}>Atlas Console</span>
        </header>
        <nav className="layout__nav">
          <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {navigation.map((item) => (
              <li key={item.path}>
                <NavLink
                  to={item.path}
                  className={({ isActive }) =>
                    `layout__nav-item ${isActive ? 'layout__nav-item--active' : ''}`
                  }
                  style={{ display: 'flex', alignItems: 'center', gap: '12px' }}
                >
                  <span style={{ fontSize: '1.125rem' }}>{item.icon}</span>
                  <span>{item.label}</span>
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
        <footer className="layout__footer">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '50%',
                background: 'var(--color-primary)',
                color: 'white',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 600,
                fontSize: '0.875rem',
              }}
            >
              {user?.full_name?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase() || 'U'}
            </div>
            <div style={{ minWidth: 0 }}>
              <div style={{ fontWeight: 500, fontSize: '0.875rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {user?.full_name || user?.email}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', textTransform: 'capitalize' }}>
                {user?.role}
              </div>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="btn btn--ghost btn--sm"
            style={{ width: '100%', justifyContent: 'flex-start' }}
          >
            🚪 Logout
          </button>
        </footer>
      </aside>
      <main className="layout__main" role="main">
        {children || <Outlet />}
      </main>
    </div>
  )
}