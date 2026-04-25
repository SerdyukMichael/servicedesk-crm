import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { CurrencyProvider } from './context/CurrencyContext'
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
import InvoiceDetailPage from './pages/InvoiceDetailPage'
import NotificationsPage from './pages/NotificationsPage'
import EquipmentModelsPage from './pages/EquipmentModelsPage'
import ServiceCatalogPage from './pages/ServiceCatalogPage'
import SettingsPage from './pages/SettingsPage'
import AuditLogPage from './pages/AuditLogPage'
import ReportsPage from './pages/ReportsPage'

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
      <CurrencyProvider>
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
          <Route
            path="equipment-models"
            element={
              <PrivateRoute roles={['admin', 'svc_mgr', 'engineer', 'director', 'sales_mgr', 'manager', 'client_user']}>
                <EquipmentModelsPage />
              </PrivateRoute>
            }
          />

          {/* Users (restricted) */}
          <Route
            path="users"
            element={
              <PrivateRoute roles={['admin', 'svc_mgr', 'director', 'client_user']}>
                <UsersPage />
              </PrivateRoute>
            }
          />

          {/* Parts */}
          <Route path="parts" element={<PartsPage />} />

          {/* Service Catalog */}
          <Route path="service-catalog" element={<ServiceCatalogPage />} />

          {/* Invoices */}
          <Route path="invoices" element={<InvoicesPage />} />
          <Route path="invoices/:id" element={<InvoiceDetailPage />} />

          {/* Notifications */}
          <Route path="notifications" element={<NotificationsPage />} />

          {/* Reports */}
          <Route
            path="reports"
            element={
              <PrivateRoute roles={['director', 'svc_mgr', 'admin']}>
                <ReportsPage />
              </PrivateRoute>
            }
          />

          {/* Audit Log */}
          <Route
            path="audit-log"
            element={
              <PrivateRoute roles={['admin', 'director']}>
                <AuditLogPage />
              </PrivateRoute>
            }
          />

          {/* Settings (admin only) */}
          <Route
            path="settings"
            element={
              <PrivateRoute roles={['admin']}>
                <SettingsPage />
              </PrivateRoute>
            }
          />

          {/* 404 */}
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
      </CurrencyProvider>
    </AuthProvider>
  )
}
