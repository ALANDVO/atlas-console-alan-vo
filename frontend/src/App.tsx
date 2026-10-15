import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore, initAuth } from './hooks/useAuth'
import { Login } from './pages/Login'
import { Dashboard } from './pages/Dashboard'
import { Layout } from './components/Layout'
import { useEffect } from 'react'

// Placeholder pages for future features
function PlaceholderPage({ title, description, icon }: { title: string; description: string; icon: string }) {
  return (
    <Layout>
      <div className="card" style={{ maxWidth: '800px' }}>
        <div className="card__body" style={{ textAlign: 'center', padding: '64px 32px' }}>
          <div style={{ fontSize: '4rem', marginBottom: '24px' }}>{icon}</div>
          <h1 style={{ fontSize: '2rem', fontWeight: 700, marginBottom: '12px' }}>{title}</h1>
          <p style={{ color: 'var(--color-text-muted)', fontSize: '1.125rem', marginBottom: '24px' }}>
            {description}
          </p>
          <p style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
            This feature is planned for a future release.
          </p>
        </div>
      </div>
    </Layout>
  )
}

const FlowsPage = () => (
  <PlaceholderPage
    title="Penetration Flows"
    description="Manage and execute autonomous penetration testing flows"
    icon="🔄"
  />
)

const FlowDetailPage = () => (
  <PlaceholderPage
    title="Flow Details"
    description="View detailed execution progress and findings"
    icon="📋"
  />
)

const ScopePage = () => (
  <PlaceholderPage
    title="Scope Management"
    description="Define IP ranges, ports, and services for testing"
    icon="🎯"
  />
)

const ResourcesPage = () => (
  <PlaceholderPage
    title="Resource Library"
    description="Browse and manage collected resources and artifacts"
    icon="📚"
  />
)

const MCPPage = () => (
  <PlaceholderPage
    title="MCP Tools"
    description="Connect and configure external security tools via MCP"
    icon="🔌"
  />
)

const ProvidersPage = () => (
  <PlaceholderPage
    title="LLM Providers"
    description="Configure and test custom LLM provider endpoints"
    icon="🤖"
  />
)

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuthStore()

  if (isLoading) {
    return (
      <div className="loading-overlay">
        <div className="loading" style={{ width: '40px', height: '40px', borderWidth: '3px' }} />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

function App() {
  useEffect(() => {
    initAuth()
  }, [])

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="flows" element={<FlowsPage />} />
        <Route path="flows/new" element={<PlaceholderPage title="New Flow" description="Create a new penetration testing flow" icon="➕" />} />
        <Route path="flows/:id" element={<FlowDetailPage />} />
        <Route path="scope" element={<ScopePage />} />
        <Route path="resources" element={<ResourcesPage />} />
        <Route path="mcp" element={<MCPPage />} />
        <Route path="providers" element={<ProvidersPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}

export default App