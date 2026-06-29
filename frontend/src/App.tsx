import { Link, Navigate, Route, Routes } from 'react-router-dom'
import { Layout, Menu } from 'antd'
import { AgentRunPage } from './pages/AgentRunPage'
import { CandidateReviewPage } from './pages/CandidateReviewPage'
import { PreferencesPage } from './pages/PreferencesPage'
import { TripCreatePage } from './pages/TripCreatePage'
import { TripDetailPage } from './pages/TripDetailPage'
import { TripListPage } from './pages/TripListPage'
import { VersionsPage } from './pages/VersionsPage'

const { Header, Content, Sider } = Layout

export function App() {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ color: '#fff', fontWeight: 600 }}>WayPilot</Header>
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
            <Route path="/trips" element={<TripListPage />} />
            <Route path="/trips/new" element={<TripCreatePage />} />
            <Route path="/trips/:tripId" element={<TripDetailPage />} />
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
