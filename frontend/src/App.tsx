import { useEffect, useState } from 'react'
import { Link, Navigate, Route, Routes } from 'react-router-dom'
import { Button, Layout, Menu, Space } from 'antd'
import { AgentRunPage } from './pages/AgentRunPage'
import { AgentConsolePage } from './pages/AgentConsolePage'
import { CandidateReviewPage } from './pages/CandidateReviewPage'
import { LoginPage } from './pages/LoginPage'
import { PreferencesPage } from './pages/PreferencesPage'
import { TripCreatePage } from './pages/TripCreatePage'
import { TripDetailPage } from './pages/TripDetailPage'
import { TripListPage } from './pages/TripListPage'
import { VersionsPage } from './pages/VersionsPage'
import { clearSession, getAccessToken } from './auth/session'

const { Header, Content, Sider } = Layout

export function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(Boolean(getAccessToken()))

  useEffect(() => {
    const handleAuthenticated = () => setIsAuthenticated(true)
    const handleUnauthorized = () => setIsAuthenticated(false)
    window.addEventListener('waypilot:authenticated', handleAuthenticated)
    window.addEventListener('waypilot:unauthorized', handleUnauthorized)
    return () => {
      window.removeEventListener('waypilot:authenticated', handleAuthenticated)
      window.removeEventListener('waypilot:unauthorized', handleUnauthorized)
    }
  }, [])

  const logout = () => {
    clearSession()
    setIsAuthenticated(false)
  }

  if (!isAuthenticated) {
    return (
      <Layout style={{ minHeight: '100vh', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
        <Routes>
          <Route path="/auth/login" element={<LoginPage />} />
          <Route path="*" element={<Navigate to="/auth/login" replace />} />
        </Routes>
      </Layout>
    )
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ color: '#fff', fontWeight: 600 }}>
        <Space style={{ justifyContent: 'space-between', width: '100%' }}>
          <span>WayPilot</span>
          <Button size="small" onClick={logout}>
            Sign out
          </Button>
        </Space>
      </Header>
      <Layout>
        <Sider theme="light" width={220}>
          <Menu
            mode="inline"
            items={[
              { key: 'trips', label: <Link to="/trips">Travel plans</Link> },
              { key: 'preferences', label: <Link to="/settings/preferences">Global preferences</Link> },
            ]}
          />
        </Sider>
        <Content style={{ padding: 24 }}>
          <Routes>
            <Route path="/" element={<Navigate to="/trips" replace />} />
            <Route path="/auth/login" element={<Navigate to="/trips" replace />} />
            <Route path="/trips" element={<TripListPage />} />
            <Route path="/trips/new" element={<TripCreatePage />} />
            <Route path="/trips/:tripId" element={<TripDetailPage />} />
            <Route path="/trips/:tripId/agent" element={<AgentConsolePage />} />
            <Route path="/trips/:tripId/candidates/:candidateId" element={<CandidateReviewPage />} />
            <Route path="/trips/:tripId/versions" element={<VersionsPage />} />
            <Route path="/agent-runs/:runId" element={<AgentRunPage />} />
            <Route path="/settings/preferences" element={<PreferencesPage />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  )
}
