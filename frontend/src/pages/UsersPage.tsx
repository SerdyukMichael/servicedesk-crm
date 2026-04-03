import { useState } from 'react'
import { format, parseISO } from 'date-fns'
import { ru } from 'date-fns/locale'
import { useUsers, useCreateUser, useUpdateUser } from '../hooks/useUsers'
import { useAuth } from '../context/AuthContext'
import Pagination from '../components/Pagination'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import type { User, UserRole } from '../api/types'

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

const editSchema = z.object({
  full_name: z.string().min(2, 'Введите ФИО'),
  email: z.string().email('Введите корректный email'),
  roles: z.string().min(1, 'Выберите роль'),
  phone: z.preprocess(v => (v === '' ? undefined : v), z.string().optional()),
})

type CreateFormData = z.infer<typeof createSchema>
type EditFormData = z.infer<typeof editSchema>

export default function UsersPage() {
  const { hasRole, user: currentUser } = useAuth()
  const [page, setPage] = useState(1)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingUser, setEditingUser] = useState<User | null>(null)
  const [deactivateTarget, setDeactivateTarget] = useState<User | null>(null)

  const { data, isLoading, isError } = useUsers({ page, size: 20 })
  const createUser = useCreateUser()
  const updateUser = useUpdateUser(editingUser?.id ?? 0)
  const toggleActiveUser = useUpdateUser(deactivateTarget?.id ?? 0)

  const canManage = hasRole('admin')

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CreateFormData>({ resolver: zodResolver(createSchema) })

  const {
    register: regEdit,
    handleSubmit: handleEditSubmit,
    reset: resetEdit,
    formState: { errors: editErrors },
  } = useForm<EditFormData>({ resolver: zodResolver(editSchema) })

  const onCreateSubmit = async (data: CreateFormData) => {
    await createUser.mutateAsync({ ...data, roles: [data.roles as UserRole] })
    reset()
    setShowCreateModal(false)
  }

  const openEdit = (u: User) => {
    setEditingUser(u)
    resetEdit({
      full_name: u.full_name,
      email: u.email,
      roles: u.roles[0] ?? 'engineer',
      phone: u.phone ?? '',
    })
  }

  const onEditSubmit = async (data: EditFormData) => {
    if (!editingUser) return
    await updateUser.mutateAsync({ ...data, roles: [data.roles as UserRole] })
    setEditingUser(null)
  }

  const onToggleActive = async () => {
    if (!deactivateTarget) return
    await toggleActiveUser.mutateAsync({ is_active: !deactivateTarget.is_active })
    setDeactivateTarget(null)
  }

  return (
    <>
      <div className="page-header">
        <h1>Пользователи</h1>
        {canManage && (
          <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
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
                  {canManage && <th>Действия</th>}
                </tr>
              </thead>
              <tbody>
                {data.items.length === 0 && (
                  <tr>
                    <td colSpan={canManage ? 7 : 6} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                      Пользователи не найдены
                    </td>
                  </tr>
                )}
                {data.items.map(user => (
                  <tr key={user.id} style={{ opacity: user.is_active ? 1 : 0.55 }}>
                    <td style={{ fontWeight: 500 }}>{user.full_name}</td>
                    <td style={{ color: 'var(--text-muted)' }}>{user.email}</td>
                    <td>
                      {user.roles.map(r => (
                        <span key={r} className="badge badge-assigned" style={{ marginRight: 4 }}>
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
                    {canManage && (
                      <td>
                        <div style={{ display: 'flex', gap: 6 }}>
                          <button
                            className="btn btn-secondary"
                            style={{ padding: '2px 10px', fontSize: 12 }}
                            onClick={() => openEdit(user)}
                          >
                            Редактировать
                          </button>
                          {user.id !== currentUser?.id && (
                            <button
                              className="btn btn-secondary"
                              style={{
                                padding: '2px 10px',
                                fontSize: 12,
                                color: user.is_active ? 'var(--danger)' : 'var(--success)',
                              }}
                              onClick={() => setDeactivateTarget(user)}
                            >
                              {user.is_active ? 'Деактивировать' : 'Активировать'}
                            </button>
                          )}
                        </div>
                      </td>
                    )}
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

      {/* Create modal */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Новый пользователь</h3>
              <button className="modal-close" onClick={() => setShowCreateModal(false)}>×</button>
            </div>
            <form onSubmit={handleSubmit(onCreateSubmit)}>
              <div className="modal-body">
                {createUser.isError && (
                  <div className="alert alert-error">Ошибка при создании пользователя</div>
                )}
                <div className="form-group">
                  <label className="form-label">ФИО <span className="required">*</span></label>
                  <input type="text" className={`form-input${errors.full_name ? ' error' : ''}`} {...register('full_name')} />
                  {errors.full_name && <span className="form-error">{errors.full_name.message}</span>}
                </div>
                <div className="form-group">
                  <label className="form-label">Email <span className="required">*</span></label>
                  <input type="email" className={`form-input${errors.email ? ' error' : ''}`} {...register('email')} />
                  {errors.email && <span className="form-error">{errors.email.message}</span>}
                </div>
                <div className="form-group">
                  <label className="form-label">Пароль <span className="required">*</span></label>
                  <input type="password" className={`form-input${errors.password ? ' error' : ''}`} {...register('password')} />
                  {errors.password && <span className="form-error">{errors.password.message}</span>}
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Роль <span className="required">*</span></label>
                    <select className={`form-select${errors.roles ? ' error' : ''}`} {...register('roles')}>
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
                <button type="button" className="btn btn-secondary" onClick={() => setShowCreateModal(false)}>Отмена</button>
                <button type="submit" className="btn btn-primary" disabled={createUser.isPending}>
                  {createUser.isPending ? 'Создание...' : 'Создать'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit modal */}
      {editingUser && (
        <div className="modal-overlay" onClick={() => setEditingUser(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Редактировать пользователя</h3>
              <button className="modal-close" onClick={() => setEditingUser(null)}>×</button>
            </div>
            <form onSubmit={handleEditSubmit(onEditSubmit)}>
              <div className="modal-body">
                {updateUser.isError && (
                  <div className="alert alert-error">Ошибка при сохранении</div>
                )}
                <div className="form-group">
                  <label className="form-label">ФИО <span className="required">*</span></label>
                  <input type="text" className={`form-input${editErrors.full_name ? ' error' : ''}`} {...regEdit('full_name')} />
                  {editErrors.full_name && <span className="form-error">{editErrors.full_name.message}</span>}
                </div>
                <div className="form-group">
                  <label className="form-label">Email <span className="required">*</span></label>
                  <input type="email" className={`form-input${editErrors.email ? ' error' : ''}`} {...regEdit('email')} />
                  {editErrors.email && <span className="form-error">{editErrors.email.message}</span>}
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Роль <span className="required">*</span></label>
                    <select className={`form-select${editErrors.roles ? ' error' : ''}`} {...regEdit('roles')}>
                      <option value="admin">Администратор</option>
                      <option value="engineer">Инженер</option>
                      <option value="manager">Менеджер</option>
                      <option value="svc_mgr">Руководитель сервиса</option>
                      <option value="director">Директор</option>
                      <option value="sales_mgr">Менеджер продаж</option>
                    </select>
                    {editErrors.roles && <span className="form-error">{editErrors.roles.message}</span>}
                  </div>
                  <div className="form-group">
                    <label className="form-label">Телефон</label>
                    <input type="tel" className="form-input" {...regEdit('phone')} />
                  </div>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setEditingUser(null)}>Отмена</button>
                <button type="submit" className="btn btn-primary" disabled={updateUser.isPending}>
                  {updateUser.isPending ? 'Сохранение...' : 'Сохранить'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Deactivate/Activate confirm */}
      {deactivateTarget && (
        <div className="modal-overlay" onClick={() => setDeactivateTarget(null)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 400 }}>
            <div className="modal-header">
              <h3>{deactivateTarget.is_active ? 'Деактивировать' : 'Активировать'} пользователя</h3>
              <button className="modal-close" onClick={() => setDeactivateTarget(null)}>×</button>
            </div>
            <div className="modal-body">
              <p>
                {deactivateTarget.is_active
                  ? <>Заблокировать пользователя <strong>{deactivateTarget.full_name}</strong>? Он не сможет войти в систему.</>
                  : <>Активировать пользователя <strong>{deactivateTarget.full_name}</strong>?</>
                }
              </p>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setDeactivateTarget(null)}>Отмена</button>
              <button
                className={`btn ${deactivateTarget.is_active ? 'btn-danger' : 'btn-primary'}`}
                onClick={onToggleActive}
                disabled={toggleActiveUser.isPending}
              >
                {toggleActiveUser.isPending
                  ? 'Обновление...'
                  : deactivateTarget.is_active ? 'Деактивировать' : 'Активировать'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
