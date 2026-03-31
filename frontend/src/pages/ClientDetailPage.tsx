import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { format, parseISO, isPast } from 'date-fns'
import { ru } from 'date-fns/locale'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useClient, useClientContacts, useUpdateClient } from '../hooks/useClients'
import { useClientEquipment } from '../hooks/useEquipment'
import { useClientTickets } from '../hooks/useTickets'
import { useUsers } from '../hooks/useUsers'
import { useAuth } from '../context/AuthContext'
import StatusBadge from '../components/StatusBadge'
import PriorityBadge from '../components/PriorityBadge'
import type { ContractType } from '../api/types'

const editSchema = z.object({
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

type EditFormData = z.infer<typeof editSchema>

type Tab = 'info' | 'contacts' | 'equipment' | 'tickets'

const CONTRACT_TYPE_LABELS: Record<string, string> = {
  full_service: 'Полное обслуживание',
  partial: 'Частичное',
  time_and_material: 'Время и материалы',
  warranty: 'Гарантия',
}

export default function ClientDetailPage() {
  const { id } = useParams<{ id: string }>()
  const clientId = parseInt(id ?? '0', 10)
  const navigate = useNavigate()
  const { hasRole } = useAuth()

  const [activeTab, setActiveTab] = useState<Tab>('info')
  const [showEditModal, setShowEditModal] = useState(false)

  const { data: client, isLoading, isError } = useClient(clientId)
  const { data: contacts } = useClientContacts(clientId)
  const { data: equipment } = useClientEquipment(clientId)
  const { data: tickets } = useClientTickets(clientId)
  const updateClient = useUpdateClient(clientId)
  const { data: usersData } = useUsers({ size: 200, is_active: true })

  const canEdit = hasRole('admin', 'sales_mgr', 'svc_mgr')

  const {
    register: regEdit,
    handleSubmit: handleEditSubmit,
    reset: resetEdit,
    formState: { errors: editErrors },
  } = useForm<EditFormData>({ resolver: zodResolver(editSchema) })

  const openEdit = () => {
    resetEdit({
      name: client?.name ?? '',
      inn: client?.inn ?? '',
      contract_type: client?.contract_type ?? '',
      contract_number: client?.contract_number ?? '',
      contract_start: client?.contract_start ?? '',
      contract_end: client?.contract_end ?? '',
      manager_id: client?.manager_id ?? ('' as unknown as number),
      address: client?.address ?? '',
      city: client?.city ?? '',
    })
    setShowEditModal(true)
  }

  const onEditSubmit = async (data: EditFormData) => {
    await updateClient.mutateAsync({
      ...data,
      contract_type: data.contract_type as ContractType | undefined,
    })
    setShowEditModal(false)
  }

  if (isLoading)
    return (
      <div className="loading-center">
        <span className="spinner spinner-lg" />
      </div>
    )
  if (isError || !client)
    return <div className="alert alert-error">Ошибка загрузки клиента</div>

  const contractExpired =
    client.contract_end && isPast(parseISO(client.contract_end))

  return (
    <>
      <div className="page-header">
        <div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>
            <span style={{ cursor: 'pointer' }} onClick={() => navigate('/clients')}>
              Клиенты
            </span>{' '}
            / {client.name}
          </div>
          <h1>{client.name}</h1>
        </div>
        {canEdit && (
          <button className="btn btn-secondary" onClick={openEdit}>Редактировать</button>
        )}
      </div>

      <div className="tabs">
        {([
          { key: 'info', label: 'Информация' },
          { key: 'contacts', label: `Контакты (${contacts?.length ?? 0})` },
          { key: 'equipment', label: `Оборудование (${equipment?.length ?? 0})` },
          { key: 'tickets', label: `Заявки (${tickets?.length ?? 0})` },
        ] as { key: Tab; label: string }[]).map(tab => (
          <button
            key={tab.key}
            className={`tab-btn${activeTab === tab.key ? ' active' : ''}`}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'info' && (
        <div className="card" style={{ maxWidth: 640 }}>
          <div className="card-body">
            <ul className="info-list">
              <li>
                <span className="info-list-label">Название</span>
                <span className="info-list-value">{client.name}</span>
              </li>
              <li>
                <span className="info-list-label">ИНН</span>
                <span className="info-list-value">{client.inn ?? '—'}</span>
              </li>
              <li>
                <span className="info-list-label">Город</span>
                <span className="info-list-value">{client.city ?? '—'}</span>
              </li>
              <li>
                <span className="info-list-label">Адрес</span>
                <span className="info-list-value">{client.address ?? '—'}</span>
              </li>
              <li>
                <span className="info-list-label">Тип договора</span>
                <span className="info-list-value">
                  {client.contract_type
                    ? CONTRACT_TYPE_LABELS[client.contract_type] ?? client.contract_type
                    : '—'}
                </span>
              </li>
              <li>
                <span className="info-list-label">Договор №</span>
                <span className="info-list-value">{client.contract_number ?? '—'}</span>
              </li>
              <li>
                <span className="info-list-label">Начало договора</span>
                <span className="info-list-value">
                  {client.contract_start
                    ? format(parseISO(client.contract_start), 'dd.MM.yyyy', { locale: ru })
                    : '—'}
                </span>
              </li>
              <li>
                <span className="info-list-label">Конец договора</span>
                <span className="info-list-value">
                  {client.contract_end ? (
                    <span style={{ color: contractExpired ? 'var(--danger)' : 'inherit' }}>
                      {format(parseISO(client.contract_end), 'dd.MM.yyyy', { locale: ru })}
                      {contractExpired && ' — истёк'}
                    </span>
                  ) : (
                    '—'
                  )}
                </span>
              </li>
              <li>
                <span className="info-list-label">Менеджер</span>
                <span className="info-list-value">
                  {client.manager?.full_name ?? '—'}
                </span>
              </li>
              <li>
                <span className="info-list-label">Добавлен</span>
                <span className="info-list-value">
                  {format(parseISO(client.created_at), 'dd.MM.yyyy', { locale: ru })}
                </span>
              </li>
            </ul>
          </div>
        </div>
      )}

      {activeTab === 'contacts' && (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Имя</th>
                <th>Должность</th>
                <th>Телефон</th>
                <th>Email</th>
                <th>Основной</th>
              </tr>
            </thead>
            <tbody>
              {(!contacts || contacts.length === 0) && (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                    Контакты не добавлены
                  </td>
                </tr>
              )}
              {contacts?.map(c => (
                <tr key={c.id}>
                  <td style={{ fontWeight: 500 }}>{c.name}</td>
                  <td>{c.position ?? '—'}</td>
                  <td>{c.phone ?? '—'}</td>
                  <td>{c.email ?? '—'}</td>
                  <td>{c.is_primary ? '✓' : ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'equipment' && (
        <div className="table-wrap">
          <table className="table table-hover">
            <thead>
              <tr>
                <th>Серийный №</th>
                <th>Модель</th>
                <th>Адрес</th>
                <th>Статус</th>
                <th>Гарантия до</th>
              </tr>
            </thead>
            <tbody>
              {(!equipment || equipment.length === 0) && (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                    Оборудование не добавлено
                  </td>
                </tr>
              )}
              {equipment?.map(eq => {
                const warrantyExpired =
                  !eq.warranty_end || isPast(parseISO(eq.warranty_end))
                return (
                  <tr
                    key={eq.id}
                    style={{ cursor: 'pointer' }}
                    onClick={() => navigate(`/equipment/${eq.id}`)}
                  >
                    <td style={{ fontFamily: 'monospace', fontSize: 12 }}>{eq.serial_number}</td>
                    <td>{eq.model?.name ?? '—'}</td>
                    <td>{eq.address ?? eq.location ?? '—'}</td>
                    <td>{eq.status}</td>
                    <td>
                      {eq.warranty_end ? (
                        <span style={{ color: warrantyExpired ? 'var(--danger)' : 'var(--success)' }}>
                          {format(parseISO(eq.warranty_end), 'dd.MM.yyyy', { locale: ru })}
                        </span>
                      ) : (
                        <span style={{ color: 'var(--danger)' }}>Нет</span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Edit modal */}
      {showEditModal && (
        <div className="modal-overlay" onClick={() => setShowEditModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Редактировать клиента</h3>
              <button className="modal-close" onClick={() => setShowEditModal(false)}>×</button>
            </div>
            <form onSubmit={handleEditSubmit(onEditSubmit)}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label">
                    Название <span className="required">*</span>
                  </label>
                  <input
                    type="text"
                    className={`form-input${editErrors.name ? ' error' : ''}`}
                    {...regEdit('name')}
                  />
                  {editErrors.name && <span className="form-error">{editErrors.name.message}</span>}
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">ИНН <span className="required">*</span></label>
                    <input type="text" className={`form-input${editErrors.inn ? ' error' : ''}`} {...regEdit('inn')} />
                    {editErrors.inn && <span className="form-error">{editErrors.inn.message}</span>}
                  </div>
                  <div className="form-group">
                    <label className="form-label">Город <span className="required">*</span></label>
                    <input type="text" className={`form-input${editErrors.city ? ' error' : ''}`} {...regEdit('city')} />
                    {editErrors.city && <span className="form-error">{editErrors.city.message}</span>}
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Тип договора <span className="required">*</span></label>
                    <select className={`form-select${editErrors.contract_type ? ' error' : ''}`} {...regEdit('contract_type')}>
                      <option value="">— Не указан —</option>
                      <option value="full_service">Полное обслуживание</option>
                      <option value="partial">Частичное</option>
                      <option value="time_and_material">Время и материалы</option>
                      <option value="warranty">Гарантия</option>
                    </select>
                    {editErrors.contract_type && <span className="form-error">{editErrors.contract_type.message}</span>}
                  </div>
                  <div className="form-group">
                    <label className="form-label">Номер договора <span className="required">*</span></label>
                    <input type="text" className={`form-input${editErrors.contract_number ? ' error' : ''}`} {...regEdit('contract_number')} />
                    {editErrors.contract_number && <span className="form-error">{editErrors.contract_number.message}</span>}
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Начало договора <span className="required">*</span></label>
                    <input type="date" className={`form-input${editErrors.contract_start ? ' error' : ''}`} {...regEdit('contract_start')} />
                    {editErrors.contract_start && <span className="form-error">{editErrors.contract_start.message}</span>}
                  </div>
                  <div className="form-group">
                    <label className="form-label">Конец договора</label>
                    <input type="date" className="form-input" {...regEdit('contract_end')} />
                  </div>
                </div>
                <div className="form-group">
                  <label className="form-label">Менеджер <span className="required">*</span></label>
                  <select className={`form-select${editErrors.manager_id ? ' error' : ''}`} {...regEdit('manager_id')}>
                    <option value="">— Выберите менеджера —</option>
                    {usersData?.items.map(u => (
                      <option key={u.id} value={u.id}>{u.full_name}</option>
                    ))}
                  </select>
                  {editErrors.manager_id && <span className="form-error">{editErrors.manager_id.message}</span>}
                </div>
                <div className="form-group">
                  <label className="form-label">Адрес</label>
                  <input type="text" className="form-input" {...regEdit('address')} />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowEditModal(false)}>
                  Отмена
                </button>
                <button type="submit" className="btn btn-primary" disabled={updateClient.isPending}>
                  {updateClient.isPending ? 'Сохранение...' : 'Сохранить'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {activeTab === 'tickets' && (
        <div className="table-wrap">
          <table className="table table-hover">
            <thead>
              <tr>
                <th>#</th>
                <th>Заголовок</th>
                <th>Приоритет</th>
                <th>Статус</th>
                <th>Создана</th>
              </tr>
            </thead>
            <tbody>
              {(!tickets || tickets.length === 0) && (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                    Заявки не найдены
                  </td>
                </tr>
              )}
              {tickets?.map(t => (
                <tr key={t.id} onClick={() => navigate(`/tickets/${t.id}`)}>
                  <td style={{ color: 'var(--text-muted)', fontSize: 12 }}>{t.number}</td>
                  <td style={{ fontWeight: 500 }}>{t.title}</td>
                  <td><PriorityBadge priority={t.priority} /></td>
                  <td><StatusBadge status={t.status} /></td>
                  <td>{format(parseISO(t.created_at), 'dd.MM.yyyy', { locale: ru })}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
