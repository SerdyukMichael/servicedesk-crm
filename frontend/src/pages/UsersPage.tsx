import { useState } from 'react'
import { format, parseISO } from 'date-fns'
import { ru } from 'date-fns/locale'
import { useUsers, useCreateUser } from '../hooks/useUsers'
import { useAuth } from '../context/AuthContext'
import Pagination from '../components/Pagination'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import type { UserRole } from '../api/types'

const ROLE_LABELS: Record<string, string> = {
  admin: 'Администратор',
  engineer: 'Инженер',
  manager: 'Менеджер',
  svc_mgr: 'Руководитель сервиса',
  director: 'Директор',
  sales_mgr: 'Менеджер продаж',
}

const createSchema = z.object({
  full_name: z.string().min(2, 'Введите ФИО'),
  email: z.string().email('Введите корректный email'),
  password: z.string().min(8, 'Пароль минимум 8 символов'),
  roles: z.string().min(1, 'Выберите роль'),
  phone: z.string().optional(),
})

type CreateFormData = z.infer<typeof createSchema>

export default function UsersPage() {
  const { hasRole } = useAuth()
  const [page, setPage] = useState(1)
  const [showModal, setShowModal] = useState(false)

  const { data, isLoading, isError } = useUsers({ page, size: 20 })
  const createUser = useCreateUser()

  const canCreate = hasRole('admin')

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CreateFormData>({ resolver: zodResolver(createSchema) })

  const onSubmit = async (data: CreateFormData) => {
    await createUser.mutateAsync({
      ...data,
      roles: [data.roles as UserRole],
    })
    reset()
    setShowModal(false)
  }

  return (
    <>
      <div className="page-header">
        <h1>Пользователи</h1>
        {canCreate && (
          <button className="btn btn-primary" onClick={() => setShowModal(true)}>
            + Добавить пользователя
          </button>
        )}
      </div>

      {isLoading && (
        <div className="loading-center">
          <span className="spinner spinner-lg" />
        </div>
      )}
      {isError && (
        <div className="alert alert-error">Ошибка загрузки пользователей</div>
      )}

      {data && (
        <>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>ФИО</th>
                  <th>Email</th>
                  <th>Роль</th>
                  <th>Статус</th>
                  <th>Последний вход</th>
                  <th>Добавлен</th>
                </tr>
              </thead>
              <tbody>
                {data.items.length === 0 && (
                  <tr>
                    <td colSpan={6} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                      Пользователи не найдены
                    </td>
                  </tr>
                )}
                {data.items.map(user => (
                  <tr key={user.id}>
                    <td style={{ fontWeight: 500 }}>{user.full_name}</td>
                    <td style={{ color: 'var(--text-muted)' }}>{user.email}</td>
                    <td>
                      {user.roles.map(r => (
                        <span
                          key={r}
                          className="badge badge-assigned"
                          style={{ marginRight: 4 }}
                        >
                          {ROLE_LABELS[r] ?? r}
                        </span>
                      ))}
                    </td>
                    <td>
                      <span
                        className="badge"
                        style={{
                          background: user.is_active ? '#dcfce7' : '#f1f5f9',
                          color: user.is_active ? '#166534' : '#475569',
                        }}
                      >
                        {user.is_active ? 'Активен' : 'Заблокирован'}
                      </span>
                    </td>
                    <td>
                      {user.last_login
                        ? format(parseISO(user.last_login), 'dd.MM.yyyy HH:mm', { locale: ru })
                        : '—'}
                    </td>
                    <td>
                      {format(parseISO(user.created_at), 'dd.MM.yyyy', { locale: ru })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <Pagination
            page={data.page}
            pages={data.pages}
            total={data.total}
            size={data.size}
            onPageChange={setPage}
          />
        </>
      )}

      {/* Create user modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Новый пользователь</h3>
              <button className="modal-close" onClick={() => setShowModal(false)}>×</button>
            </div>
            <form onSubmit={handleSubmit(onSubmit)}>
              <div className="modal-body">
                {createUser.isError && (
                  <div className="alert alert-error">Ошибка при создании пользователя</div>
                )}
                <div className="form-group">
                  <label className="form-label">
                    ФИО <span className="required">*</span>
                  </label>
                  <input
                    type="text"
                    className={`form-input${errors.full_name ? ' error' : ''}`}
                    {...register('full_name')}
                  />
                  {errors.full_name && <span className="form-error">{errors.full_name.message}</span>}
                </div>
                <div className="form-group">
                  <label className="form-label">
                    Email <span className="required">*</span>
                  </label>
                  <input
                    type="email"
                    className={`form-input${errors.email ? ' error' : ''}`}
                    {...register('email')}
                  />
                  {errors.email && <span className="form-error">{errors.email.message}</span>}
                </div>
                <div className="form-group">
                  <label className="form-label">
                    Пароль <span className="required">*</span>
                  </label>
                  <input
                    type="password"
                    className={`form-input${errors.password ? ' error' : ''}`}
                    {...register('password')}
                  />
                  {errors.password && <span className="form-error">{errors.password.message}</span>}
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">
                      Роль <span className="required">*</span>
                    </label>
                    <select
                      className={`form-select${errors.roles ? ' error' : ''}`}
                      {...register('roles')}
                    >
                      <option value="">— Выберите роль —</option>
                      <option value="admin">Администратор</option>
                      <option value="engineer">Инженер</option>
                      <option value="manager">Менеджер</option>
                      <option value="svc_mgr">Руководитель сервиса</option>
                      <option value="director">Директор</option>
                      <option value="sales_mgr">Менеджер продаж</option>
                    </select>
                    {errors.roles && <span className="form-error">{errors.roles.message}</span>}
                  </div>
                  <div className="form-group">
                    <label className="form-label">Телефон</label>
                    <input type="tel" className="form-input" {...register('phone')} />
                  </div>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                  Отмена
                </button>
                <button type="submit" className="btn btn-primary" disabled={createUser.isPending}>
                  {createUser.isPending ? 'Создание...' : 'Создать'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  )
}
