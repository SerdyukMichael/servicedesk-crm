import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useUnreadCount } from '../hooks/useNotifications'

const NAV_ITEMS = [
  { to: '/tickets', icon: '🔧', label: 'Заявки' },
  { to: '/clients', icon: '🏢', label: 'Клиенты' },
  { to: '/equipment', icon: '💻', label: 'Оборудование' },
  { to: '/equipment-models', icon: '📋', label: 'Модели' },
  { to: '/parts', icon: '📦', label: 'Склад' },
  { to: '/service-catalog', icon: '💼', label: 'Услуги' },
  { to: '/invoices', icon: '📄', label: 'Счета' },
  { to: '/notifications', icon: '🔔', label: 'Уведомления', badge: true },
]

const ROLE_LABELS: Record<string, string> = {
  admin: 'Администратор',
  engineer: 'Инженер',
  manager: 'Менеджер',
  svc_mgr: 'Руководитель сервиса',
  director: 'Директор',
  sales_mgr: 'Менеджер продаж',
  client_user: 'Пользователь клиента',
}

export default function Layout() {
  const { user, logout, hasRole } = useAuth()
  const { data: unreadData } = useUnreadCount()
  const unreadCount = unreadData?.count ?? 0

  const isClientUser = hasRole('client_user')
  const showUsers = hasRole('admin', 'svc_mgr', 'director', 'client_user')

  const initials = user?.full_name
    ? user.full_name
        .split(' ')
        .slice(0, 2)
        .map(w => w[0])
        .join('')
        .toUpperCase()
    : '?'

  const roleLabel =
    user?.roles && user.roles.length > 0
      ? (ROLE_LABELS[user.roles[0]] ?? user.roles[0])
      : ''

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">SD</div>
          <div className="sidebar-logo-text">
            ServiceDesk
            <span>CRM</span>
          </div>
        </div>

        <nav className="sidebar-nav">
          {NAV_ITEMS.filter(item => !(isClientUser && item.to === '/parts')).map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                'sidebar-nav-item' + (isActive ? ' active' : '')
              }
            >
              <span className="sidebar-nav-icon">{item.icon}</span>
              {item.label}
              {item.badge && unreadCount > 0 && (
                <span className="sidebar-nav-badge">{unreadCount}</span>
              )}
            </NavLink>
          ))}

          {showUsers && (
            <NavLink
              to="/users"
              className={({ isActive }) =>
                'sidebar-nav-item' + (isActive ? ' active' : '')
              }
            >
              <span className="sidebar-nav-icon">👥</span>
              Пользователи
            </NavLink>
          )}

          {hasRole('admin') && (
            <NavLink
              to="/settings"
              className={({ isActive }) =>
                'sidebar-nav-item' + (isActive ? ' active' : '')
              }
            >
              <span className="sidebar-nav-icon">⚙️</span>
              Настройки
            </NavLink>
          )}
        </nav>
      </aside>

      <div className="main-wrapper">
        <header className="topbar">
          <div className="topbar-spacer" />
          <div className="topbar-user">
            <div style={{ textAlign: 'right' }}>
              <div className="topbar-user-name">{user?.full_name ?? '—'}</div>
              <div className="topbar-user-role">{roleLabel}</div>
            </div>
            <div className="topbar-avatar">{initials}</div>
            <button className="btn btn-secondary btn-sm" onClick={logout}>
              Выйти
            </button>
          </div>
        </header>

        <main className="page-content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
