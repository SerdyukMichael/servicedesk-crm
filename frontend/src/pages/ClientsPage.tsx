import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { format, parseISO, isPast } from 'date-fns'
import { ru } from 'date-fns/locale'
import { useClients, useCreateClient } from '../hooks/useClients'
import { useUsers } from '../hooks/useUsers'
import { useAuth } from '../context/AuthContext'
import Pagination from '../components/Pagination'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import type { ContractType } from '../api/types'

const CONTRACT_TYPE_LABELS: Record<string, string> = {
  full_service: 'Полное обслуживание',
  partial: 'Частичное',
  time_and_material: 'Время и материалы',
  warranty: 'Гарантия',
}

const createSchema = z.object({
  name: z.string().min(2, 'Введите название организации'),
  inn: z.string().min(1, 'Введите ИНН'),
  city: z.string().min(1, 'Введите город'),
  contract_type: z.string().min(1, 'Выберите тип договора'),
  contract_number: z.string().min(1, 'Введите номер договора'),
  contract_start: z.string().min(1, 'Введите дату начала договора'),
  contract_end: z.preprocess(v => (v === '' ? undefined : v), z.string().optional()),
  manager_id: z.coerce.number({ invalid_type_error: 'Выберите менеджера' }).min(1, 'Выберите менеджера'),
  address: z.preprocess(v => (v === '' ? undefined : v), z.string().optional()),
})

type CreateFormData = z.infer<typeof createSchema>

export default function ClientsPage() {
  const navigate = useNavigate()
  const { hasRole } = useAuth()

  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [showModal, setShowModal] = useState(false)

  const params: Record<string, unknown> = { page, size: 20 }
  if (search) params.search = search

  const { data, isLoading, isError } = useClients(params)
  const createClient = useCreateClient()
  const { data: usersData } = useUsers({ size: 200, is_active: true })

  const canCreate = hasRole('admin', 'sales_mgr')

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CreateFormData>({ resolver: zodResolver(createSchema) })

  const onSubmit = async (data: CreateFormData) => {
    await createClient.mutateAsync({
      ...data,
      contract_type: data.contract_type as ContractType,
    })
    reset()
    setShowModal(false)
  }

  const handleSearch = (val: string) => {
    setSearch(val)
    setPage(1)
  }

  return (
    <>
      <div className="page-header">
        <h1>Клиенты</h1>
        {canCreate && (
          <button className="btn btn-primary" onClick={() => setShowModal(true)}>
            + Добавить клиента
          </button>
        )}
      </div>

      <div className="filters-bar">
        <input
          type="text"
          className="form-input"
          placeholder="Поиск по названию..."
          value={search}
          onChange={e => handleSearch(e.target.value)}
          style={{ minWidth: 240 }}
        />
      </div>

      {isLoading && (
        <div className="loading-center">
          <span className="spinner spinner-lg" />
        </div>
      )}
      {isError && <div className="alert alert-error">Ошибка загрузки клиентов</div>}

      {data && (
        <>
          <div className="table-wrap">
            <table className="table table-hover">
              <thead>
                <tr>
                  <th>Название</th>
                  <th>ИНН</th>
                  <th>Тип договора</th>
                  <th>Договор №</th>
                  <th>Действует до</th>
                  <th>Город</th>
                </tr>
              </thead>
              <tbody>
                {data.items.length === 0 && (
                  <tr>
                    <td colSpan={6} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                      Клиенты не найдены
                    </td>
                  </tr>
                )}
                {data.items.map(client => {
                  const contractExpired =
                    client.contract_end &&
                    isPast(parseISO(client.contract_end))

                  return (
                    <tr
                      key={client.id}
                      onClick={() => navigate(`/clients/${client.id}`)}
                    >
                      <td>
                        <span style={{ fontWeight: 500 }}>{client.name}</span>
                      </td>
                      <td>{client.inn ?? '—'}</td>
                      <td>
                        {client.contract_type
                          ? CONTRACT_TYPE_LABELS[client.contract_type] ?? client.contract_type
                          : '—'}
                      </td>
                      <td>{client.contract_number ?? '—'}</td>
                      <td>
                        {client.contract_end ? (
                          <span style={{ color: contractExpired ? 'var(--danger)' : 'inherit' }}>
                            {format(parseISO(client.contract_end), 'dd.MM.yyyy', { locale: ru })}
                          </span>
                        ) : (
                          '—'
                        )}
                      </td>
                      <td>{client.city ?? '—'}</td>
                    </tr>
                  )
                })}
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

      {/* Create client modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Новый клиент</h3>
              <button className="modal-close" onClick={() => setShowModal(false)}>×</button>
            </div>
            <form onSubmit={handleSubmit(onSubmit)}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label">
                    Название <span className="required">*</span>
                  </label>
                  <input
                    type="text"
                    className={`form-input${errors.name ? ' error' : ''}`}
                    {...register('name')}
                  />
                  {errors.name && <span className="form-error">{errors.name.message}</span>}
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">ИНН <span className="required">*</span></label>
                    <input type="text" className={`form-input${errors.inn ? ' error' : ''}`} {...register('inn')} />
                    {errors.inn && <span className="form-error">{errors.inn.message}</span>}
                  </div>
                  <div className="form-group">
                    <label className="form-label">Город <span className="required">*</span></label>
                    <input type="text" className={`form-input${errors.city ? ' error' : ''}`} {...register('city')} />
                    {errors.city && <span className="form-error">{errors.city.message}</span>}
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Тип договора <span className="required">*</span></label>
                    <select className={`form-select${errors.contract_type ? ' error' : ''}`} {...register('contract_type')}>
                      <option value="">— Не указан —</option>
                      <option value="full_service">Полное обслуживание</option>
                      <option value="partial">Частичное</option>
                      <option value="time_and_material">Время и материалы</option>
                      <option value="warranty">Гарантия</option>
                    </select>
                    {errors.contract_type && <span className="form-error">{errors.contract_type.message}</span>}
                  </div>
                  <div className="form-group">
                    <label className="form-label">Номер договора <span className="required">*</span></label>
                    <input type="text" className={`form-input${errors.contract_number ? ' error' : ''}`} {...register('contract_number')} />
                    {errors.contract_number && <span className="form-error">{errors.contract_number.message}</span>}
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Начало договора <span className="required">*</span></label>
                    <input type="date" className={`form-input${errors.contract_start ? ' error' : ''}`} {...register('contract_start')} />
                    {errors.contract_start && <span className="form-error">{errors.contract_start.message}</span>}
                  </div>
                  <div className="form-group">
                    <label className="form-label">Конец договора</label>
                    <input type="date" className="form-input" {...register('contract_end')} />
                  </div>
                </div>
                <div className="form-group">
                  <label className="form-label">Менеджер <span className="required">*</span></label>
                  <select className={`form-select${errors.manager_id ? ' error' : ''}`} {...register('manager_id')}>
                    <option value="">— Выберите менеджера —</option>
                    {usersData?.items.map(u => (
                      <option key={u.id} value={u.id}>{u.full_name}</option>
                    ))}
                  </select>
                  {errors.manager_id && <span className="form-error">{errors.manager_id.message}</span>}
                </div>
                <div className="form-group">
                  <label className="form-label">Адрес</label>
                  <input type="text" className="form-input" {...register('address')} />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                  Отмена
                </button>
                <button type="submit" className="btn btn-primary" disabled={createClient.isPending}>
                  {createClient.isPending ? 'Создание...' : 'Создать'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  )
}
