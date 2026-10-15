import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { Dashboard } from './Dashboard'
import { useAuthStore } from '../hooks/useAuth'
import { dashboardApi } from '../api/client'

// Mock the auth store
vi.mock('../hooks/useAuth', () => ({
  useAuthStore: vi.fn(),
  initAuth: vi.fn(),
}))

// Mock the API client
vi.mock('../api/client', () => ({
  dashboardApi: {
    getDashboard: vi.fn(),
  },
}))

const mockUseAuthStore = useAuthStore as unknown as ReturnType<typeof vi.fn>
const mockDashboardApi = dashboardApi as unknown as Record<string, ReturnType<typeof vi.fn>>

function renderDashboard() {
  return render(
    <BrowserRouter>
      <Dashboard />
    </BrowserRouter>
  )
}

describe('Dashboard Page', () => {
  const mockDashboardData = {
    stats: {
      total_flows: 12,
      active_flows: 3,
      completed_flows: 8,
      total_findings: 47,
      critical_findings: 2,
      high_findings: 8,
    },
    recent_activity: [
      {
        id: 1,
        type: 'flow_started',
        title: 'Penetration Test - Web App',
        description: 'Started automated penetration test on target web application',
        timestamp: '2024-01-15T10:30:00Z',
        status: 'running',
      },
      {
        id: 2,
        type: 'finding',
        title: 'SQL Injection Found',
        description: 'Critical SQL injection in login form',
        timestamp: '2024-01-15T09:15:00Z',
        status: 'critical',
      },
    ],
    user: {
      id: 1,
      email: 'demo@atlas.local',
      full_name: 'Demo User',
      role: 'operator',
    },
  }

  beforeEach(() => {
    vi.clearAllMocks()
    mockUseAuthStore.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: mockDashboardData.user,
    })
    mockDashboardApi.getDashboard.mockResolvedValue({ data: mockDashboardData })
  })

  afterEach(() => {
    vi.resetAllMocks()
  })

  it('shows loading state initially', () => {
    mockUseAuthStore.mockReturnValue({
      isAuthenticated: true,
      isLoading: true,
      user: null,
    })

    renderDashboard()

    expect(screen.getByTestId('loading-overlay')).toBeInTheDocument()
  })

  it('renders dashboard stats correctly', async () => {
    renderDashboard()

    await waitFor(() => {
      expect(screen.getByText('12')).toBeInTheDocument() // total_flows
      expect(screen.getByText('3')).toBeInTheDocument() // active_flows
      expect(screen.getByText('47')).toBeInTheDocument() // total_findings
      expect(screen.getByText('2')).toBeInTheDocument() // critical_findings
      // Use more specific queries for duplicate values
      const completedFlows = screen.getAllByText('8')
      expect(completedFlows.length).toBeGreaterThanOrEqual(2) // completed_flows and high_findings both 8
    })
  })

  it('displays welcome message with user name', async () => {
    renderDashboard()

    await waitFor(() => {
      expect(screen.getByText(/welcome back, demo user/i)).toBeInTheDocument()
    })
  })

  it('renders recent activity items', async () => {
    renderDashboard()

    await waitFor(() => {
      expect(screen.getByText('Penetration Test - Web App')).toBeInTheDocument()
      expect(screen.getByText('SQL Injection Found')).toBeInTheDocument()
    })
  })

  it('shows activity status badges', async () => {
    renderDashboard()

    await waitFor(() => {
      expect(screen.getByText('Running')).toBeInTheDocument()
      // Critical appears twice (stat label and badge), use more specific query
      const criticalElements = screen.getAllByText('Critical')
      expect(criticalElements.length).toBeGreaterThanOrEqual(2)
    })
  })

  it('displays quick action buttons', async () => {
    renderDashboard()

    await waitFor(() => {
      expect(screen.getByRole('link', { name: /create new flow/i })).toBeInTheDocument()
      expect(screen.getByRole('link', { name: /manage scope/i })).toBeInTheDocument()
      expect(screen.getByRole('link', { name: /browse resources/i })).toBeInTheDocument()
      expect(screen.getByRole('link', { name: /configure mcp tools/i })).toBeInTheDocument()
      expect(screen.getByRole('link', { name: /manage llm providers/i })).toBeInTheDocument()
    })
  })

  it('shows system status indicators', async () => {
    renderDashboard()

    await waitFor(() => {
      expect(screen.getByText('API Status')).toBeInTheDocument()
      expect(screen.getByText('Database')).toBeInTheDocument()
      expect(screen.getByText('Keycloak')).toBeInTheDocument()
      expect(screen.getByText('LLM Providers')).toBeInTheDocument()
    })
  })

  it('handles API error gracefully', async () => {
    mockDashboardApi.getDashboard.mockRejectedValue(new Error('Network error'))

    renderDashboard()

    await waitFor(() => {
      expect(screen.getByText(/unable to load dashboard/i)).toBeInTheDocument()
      expect(screen.getByText(/network error/i)).toBeInTheDocument()
    })
  })

  it('redirects to login when not authenticated', () => {
    mockUseAuthStore.mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
      user: null,
    })

    renderDashboard()

    // Should redirect - the ProtectedRoute handles this
    expect(screen.queryByText(/welcome back/i)).not.toBeInTheDocument()
  })
})