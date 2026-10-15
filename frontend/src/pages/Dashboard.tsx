import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { dashboardApi, type DashboardResponse } from '../api/client'
import { Layout } from '../components/Layout'

const STATUS_LABELS: Record<string, string> = {
  running: 'Running',
  critical: 'Critical',
  completed: 'Completed',
  pending: 'Pending',
}

const ACTIVITY_ICONS: Record<string, string> = {
  flow_started: '🚀',
  finding: '🔍',
  flow_completed: '✅',
}

const ACTIVITY_ICON_CLASS: Record<string, string> = {
  flow_started: 'activity-item__icon--flow_started',
  finding: 'activity-item__icon--finding',
  flow_completed: 'activity-item__icon--flow_completed',
}

const STATUS_CLASS: Record<string, string> = {
  running: 'activity-item__status--running',
  critical: 'activity-item__status--critical',
  completed: 'activity-item__status--completed',
  pending: 'activity-item__status--pending',
}

export function Dashboard() {
  const [data, setData] = useState<DashboardResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true

    async function fetchDashboard() {
      try {
        setLoading(true)
        const response = await dashboardApi.getDashboard()
        if (mounted) {
          setData(response.data)
          setError(null)
        }
      } catch (err) {
        if (mounted) {
          setError(err instanceof Error ? err.message : 'Failed to load dashboard')
        }
      } finally {
        if (mounted) {
          setLoading(false)
        }
      }
    }

    fetchDashboard()
    return () => { mounted = false }
  }, [])

  if (loading) {
    return (
      <Layout>
        <div className="loading-overlay" data-testid="loading-overlay">
          <div className="loading" style={{ width: '40px', height: '40px', borderWidth: '3px' }} />
        </div>
      </Layout>
    )
  }

  if (error || !data) {
    return (
      <Layout>
        <div className="card" style={{ maxWidth: '600px', margin: '0 auto' }}>
          <div className="card__body" style={{ textAlign: 'center', padding: '48px' }}>
            <div style={{ fontSize: '3rem', marginBottom: '16px' }}>⚠️</div>
            <h2 style={{ marginBottom: '8px' }}>Unable to load dashboard</h2>
            <p style={{ color: 'var(--color-text-muted)', marginBottom: '24px' }}>
              {error || 'Unknown error'}
            </p>
            <button className="btn btn--primary" onClick={() => window.location.reload()}>
              Retry
            </button>
          </div>
        </div>
      </Layout>
    )
  }

  const { stats, recent_activity, user } = data

  return (
    <Layout>
      <header style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: '4px' }}>
          Dashboard
        </h1>
        <p style={{ color: 'var(--color-text-muted)' }}>
          Welcome back, {user.full_name || user.email}
        </p>
      </header>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-card__label">Total Flows</div>
          <div className="stat-card__value stat-card__value--primary">{stats.total_flows}</div>
        </div>
        <div className="stat-card">
          <div className="stat-card__label">Active</div>
          <div className="stat-card__value stat-card__value--primary">{stats.active_flows}</div>
        </div>
        <div className="stat-card">
          <div className="stat-card__label">Completed</div>
          <div className="stat-card__value stat-card__value--success">{stats.completed_flows}</div>
        </div>
        <div className="stat-card">
          <div className="stat-card__label">Total Findings</div>
          <div className="stat-card__value">{stats.total_findings}</div>
        </div>
        <div className="stat-card">
          <div className="stat-card__label">Critical</div>
          <div className="stat-card__value stat-card__value--critical">{stats.critical_findings}</div>
        </div>
        <div className="stat-card">
          <div className="stat-card__label">High</div>
          <div className="stat-card__value stat-card__value--high">{stats.high_findings}</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
        <section className="card">
          <div className="card__header">
            <h2 style={{ fontSize: '1.125rem', fontWeight: 600 }}>Recent Activity</h2>
            <Link to="/flows" className="btn btn--ghost btn--sm">View All</Link>
          </div>
          <div className="card__body" style={{ padding: 0 }}>
            <div className="activity-list">
              {recent_activity.length === 0 ? (
                <div style={{ padding: '32px', textAlign: 'center', color: 'var(--color-text-muted)' }}>
                  No recent activity
                </div>
              ) : (
                recent_activity.map((activity) => (
                  <div key={activity.id} className="activity-item">
                    <div
                      className={`activity-item__icon ${ACTIVITY_ICON_CLASS[activity.type] || ''}`}
                    >
                      {ACTIVITY_ICONS[activity.type] || '📋'}
                    </div>
                    <div className="activity-item__content">
                      <div className="activity-item__title">{activity.title}</div>
                      <div className="activity-item__description">{activity.description}</div>
                      <div className="activity-item__meta">
                        <time dateTime={activity.timestamp}>
                          {new Date(activity.timestamp).toLocaleString()}
                        </time>
                        <span className={`activity-item__status ${STATUS_CLASS[activity.status] || ''}`}>
                          {STATUS_LABELS[activity.status] || activity.status}
                        </span>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </section>

        <section className="card">
          <div className="card__header">
            <h2 style={{ fontSize: '1.125rem', fontWeight: 600 }}>Quick Actions</h2>
          </div>
          <div className="card__body">
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <Link to="/flows/new" className="btn btn--primary" style={{ textAlign: 'left' }}>
                <span>➕</span>
                <span>Create New Flow</span>
              </Link>
              <Link to="/scope" className="btn btn--secondary" style={{ textAlign: 'left' }}>
                <span>🎯</span>
                <span>Manage Scope</span>
              </Link>
              <Link to="/resources" className="btn btn--secondary" style={{ textAlign: 'left' }}>
                <span>📚</span>
                <span>Browse Resources</span>
              </Link>
              <Link to="/mcp" className="btn btn--secondary" style={{ textAlign: 'left' }}>
                <span>🔌</span>
                <span>Configure MCP Tools</span>
              </Link>
              <Link to="/providers" className="btn btn--secondary" style={{ textAlign: 'left' }}>
                <span>🤖</span>
                <span>Manage LLM Providers</span>
              </Link>
            </div>
          </div>
        </section>
      </div>

      <section className="card" style={{ marginTop: '24px' }}>
        <div className="card__header">
          <h2 style={{ fontSize: '1.125rem', fontWeight: 600 }}>System Status</h2>
        </div>
        <div className="card__body">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
            <div style={{ padding: '16px', background: 'var(--color-bg)', borderRadius: '8px' }}>
              <div style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)', marginBottom: '4px' }}>API Status</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--color-success)' }} />
                <span style={{ fontWeight: 500 }}>Operational</span>
              </div>
            </div>
            <div style={{ padding: '16px', background: 'var(--color-bg)', borderRadius: '8px' }}>
              <div style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)', marginBottom: '4px' }}>Database</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--color-success)' }} />
                <span style={{ fontWeight: 500 }}>Connected</span>
              </div>
            </div>
            <div style={{ padding: '16px', background: 'var(--color-bg)', borderRadius: '8px' }}>
              <div style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)', marginBottom: '4px' }}>Keycloak</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--color-warning)' }} />
                <span style={{ fontWeight: 500 }}>Not Configured</span>
              </div>
            </div>
            <div style={{ padding: '16px', background: 'var(--color-bg)', borderRadius: '8px' }}>
              <div style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)', marginBottom: '4px' }}>LLM Providers</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--color-warning)' }} />
                <span style={{ fontWeight: 500 }}>0 Configured</span>
              </div>
            </div>
          </div>
        </div>
      </section>
    </Layout>
  )
}