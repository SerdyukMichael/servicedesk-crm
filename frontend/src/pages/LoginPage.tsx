import { useState } from 'react'
import { useNavigate, useLocation, Navigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useAuth } from '../context/AuthContext'
import * as api from '../api/endpoints'
import type { AxiosError } from 'axios'

const schema = z.object({
  email: z.string().email('Введите корректный email'),
  password: z.string().min(1, 'Введите пароль'),
})

type FormData = z.infer<typeof schema>

export default function LoginPage() {
  const { login, token } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  // Sanitise `from` — never redirect back to /login (infinite loop)
  const rawFrom = (location.state as { from?: { pathname?: string } })?.from?.pathname
  const from = rawFrom && rawFrom !== '/login' ? rawFrom : '/tickets'

  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  // Already authenticated: skip the form entirely.
  // This prevents LoginPage from rendering on top of the authenticated layout
  // during React 18 concurrent transitions after a successful login.
  if (token) {
    return <Navigate to={from} replace />
  }

  const onSubmit = async (data: FormData) => {
    setError(null)
    setLoading(true)
    try {
      const resp = await api.login(data.email, data.password)
      const rawRoles = resp.user.roles
      const roles: string[] = Array.isArray(rawRoles)
        ? rawRoles
        : typeof rawRoles === 'string'
          ? (() => { try { return JSON.parse(rawRoles) } catch { return [rawRoles] } })()
          : []
      login(resp.access_token, {
        id: resp.user.id,
        email: resp.user.email,
        full_name: resp.user.full_name,
        roles,
      })
      setLoading(false)
      navigate(from, { replace: true })
    } catch (err) {
      const axiosErr = err as AxiosError<{ detail: unknown }>
      const detail = axiosErr.response?.data?.detail
      if (axiosErr.response?.status === 401) {
        setError(typeof detail === 'string' ? detail : 'Неверный email или пароль')
      } else if (Array.isArray(detail)) {
        // Pydantic validation error array
        const msgs = (detail as { msg: string }[]).map(e => e.msg).join('; ')
        setError(msgs || 'Ошибка валидации')
      } else if (typeof detail === 'string') {
        setError(detail)
      } else {
        setError('Ошибка соединения с сервером')
      }
    } finally {
      // setLoading(false) is also called on success before navigate(),
      // so this only fires on error paths.
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-logo">
          <div className="login-logo-icon">SD</div>
          <h1>ServiceDesk CRM</h1>
          <p>Система управления сервисными заявками</p>
        </div>

        {error && (
          <div className="alert alert-error" style={{ marginBottom: '16px' }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} noValidate>
          <div className="form-group">
            <label className="form-label" htmlFor="email">
              Email
            </label>
            <input
              id="email"
              type="email"
              className={`form-input${errors.email ? ' error' : ''}`}
              placeholder="user@example.com"
              autoComplete="username"
              {...register('email')}
            />
            {errors.email && (
              <span className="form-error">{errors.email.message}</span>
            )}
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="password">
              Пароль
            </label>
            <input
              id="password"
              type="password"
              className={`form-input${errors.password ? ' error' : ''}`}
              placeholder="••••••••"
              autoComplete="current-password"
              {...register('password')}
            />
            {errors.password && (
              <span className="form-error">{errors.password.message}</span>
            )}
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading}
            style={{ width: '100%', marginTop: '8px' }}
          >
            {loading ? (
              <>
                <span className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />
                Вход...
              </>
            ) : (
              'Войти'
            )}
          </button>
        </form>
      </div>
    </div>
  )
}
