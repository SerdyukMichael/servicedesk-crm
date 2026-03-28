import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { ReactNode } from 'react'

interface PrivateRouteProps {
  children: ReactNode
  roles?: string[]
}

export default function PrivateRoute({ children, roles }: PrivateRouteProps) {
  const { token, hasRole } = useAuth()
  const location = useLocation()

  if (!token) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  if (roles && roles.length > 0 && !hasRole(...roles)) {
    return (
      <div className="page-content">
        <div className="empty-state">
          <div className="empty-state-icon">🔒</div>
          <p>У вас нет доступа к этому разделу.</p>
        </div>
      </div>
    )
  }

  return <>{children}</>
}
