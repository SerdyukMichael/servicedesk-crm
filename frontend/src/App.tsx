import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import PrivateRoute from './components/PrivateRoute'
import Layout from './components/Layout'

import LoginPage from './pages/LoginPage'
import TicketsPage from './pages/TicketsPage'
import TicketDetailPage from './pages/TicketDetailPage'
import TicketFormPage from './pages/TicketFormPage'
import ClientsPage from './pages/ClientsPage'
import ClientDetailPage from './pages/ClientDetailPage'
import EquipmentPage from './pages/EquipmentPage'
import EquipmentDetailPage from './pages/EquipmentDetailPage'
import UsersPage from './pages/UsersPage'
import PartsPage from './pages/PartsPage'
import InvoicesPage from './pages/InvoicesPage'
import NotificationsPage from './pages/NotificationsPage'

function NotFoundPage() {
  return (
    <div className="empty-state" style={{ paddingTop: 80 }}>
      <div className="empty-state-icon">404</div>
      <p>Страница не найдена</p>
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        <Route
          element={
            <PrivateRoute>
              <Layout />
            </PrivateRoute>
          }
        >
          {/* Default redirect */}
          <Route index element={<Navigate to="/tickets" replace />} />

          {/* Tickets */}
          <Route path="tickets" element={<TicketsPage />} />
          <Route path="tickets/new" element={<TicketFormPage />} />
          <Route path="tickets/:id" element={<TicketDetailPage />} />

          {/* Clients */}
          <Route path="clients" element={<ClientsPage />} />
          <Route path="clients/:id" element={<ClientDetailPage />} />

          {/* Equipment */}
          <Route path="equipment" element={<EquipmentPage />} />
          <Route path="equipment/:id" element={<EquipmentDetailPage />} />

          {/* Users (restricted) */}
          <Route
            path="users"
            element={
              <PrivateRoute roles={['admin', 'svc_mgr', 'director']}>
                <UsersPage />
              </PrivateRoute>
            }
          />

          {/* Parts */}
          <Route path="parts" element={<PartsPage />} />

          {/* Invoices */}
          <Route path="invoices" element={<InvoicesPage />} />

          {/* Notifications */}
          <Route path="notifications" element={<NotificationsPage />} />

          {/* 404 */}
          <Route path="*" element={<NotFoundPage />} />
        </Route>

        {/* Root 404 */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  )
}
