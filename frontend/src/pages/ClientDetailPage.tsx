import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { format, parseISO, isPast } from 'date-fns'
import { ru } from 'date-fns/locale'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  useClient,
  useClientContacts,
  useCreateClientContact,
  useUpdateClientContact,
  useDeactivateClientContact,
  useGrantPortalAccess,
  useRevokePortalAccess,
  useUpdateClient,
} from '../hooks/useClients'
import { useClientEquipment } from '../hooks/useEquipment'
import { useClientTickets } from '../hooks/useTickets'
import { useUsers } from '../hooks/useUsers'
import { useAuth } from '../context/AuthContext'
import StatusBadge from '../components/StatusBadge'
import PriorityBadge from '../components/PriorityBadge'
import type { ClientContact, ContractType } from '../api/types'

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

const contactSchema = z.object({
  name: z.string().min(1, 'Введите ФИО'),
  position: z.preprocess(v => (v === '' ? undefined : v), z.string().optional()),
  phone: z.preprocess(v => (v === '' ? undefined : v), z.string().optional()),
  email: z.preprocess(v => (v === '' ? undefined : v), z.string().email('Некорректный email').optional()),
  is_primary: z.boolean().default(false),
})
type ContactFormData = z.infer<typeof contactSchema>

const portalSchema = z.object({
  email: z.preprocess(v => (v === '' ? undefined : v), z.string().email('Некорректный email').optional()),
  portal_role: z.enum(['client_user', 'client_admin']).default('client_user'),
})
type PortalFormData = z.infer<typeof portalSchema>

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

  // contact modals
  const [showContactModal, setShowContactModal] = useState(false)
  const [editingContact, setEditingContact] = useState<ClientContact | null>(null)
  const [showPortalModal, setShowPortalModal] = useState(false)
  const [portalContact, setPortalContact] = useState<ClientContact | null>(null)
  const [deactivateTarget, setDeactivateTarget] = useState<ClientContact | null>(null)

  const { data: client, isLoading, isError } = useClient(clientId)
  const { data: contacts } = useClientContacts(clientId)
  const { data: equipment } = useClientEquipment(clientId)
  const { data: tickets } = useClientTickets(clientId)
  const updateClient = useUpdateClient(clientId)
  const createContact = useCreateClientContact(clientId)
  const updateContact = useUpdateClientContact(clientId)
  const deactivateContact = useDeactivateClientContact(clientId)
  const grantPortal = useGrantPortalAccess(clientId)
  const revokePortal = useRevokePortalAccess(clientId)
  const { data: usersData } = useUsers({ size: 200, is_active: true })

  const canEdit = hasRole('admin', 'sales_mgr', 'svc_mgr')

  const {
    register: regEdit,
    handleSubmit: handleEditSubmit,
    reset: resetEdit,
    formState: { errors: editErrors },
  } = useForm<EditFormData>({ resolver: zodResolver(editSchema) })

  const {
    register: regContact,
    handleSubmit: handleContactSubmit,
    reset: resetContact,
    formState: { errors: contactErrors },
  } = useForm<ContactFormData>({ resolver: zodResolver(contactSchema) })

  const {
    register: regPortal,
    handleSubmit: handlePortalSubmit,
    reset: resetPortal,
    formState: { errors: portalErrors },
  } = useForm<PortalFormData>({ resolver: zodResolver(portalSchema) })

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

  const openAddContact = () => {
    setEditingContact(null)
    resetContact({ name: '', position: '', phone: '', email: '', is_primary: false })
    setShowContactModal(true)
  }

  const openEditContact = (c: ClientContact) => {
    setEditingContact(c)
    resetContact({
      name: c.name,
      position: c.position ?? '',
      phone: c.phone ?? '',
      email: c.email ?? '',
      is_primary: c.is_primary,
    })
    setShowContactModal(true)
  }

  const onContactSubmit = async (data: ContactFormData) => {
    if (editingContact) {
      await updateContact.mutateAsync({ contactId: editingContact.id, data })
    } else {
      await createContact.mutateAsync(data)
    }
    setShowContactModal(false)
  }

  const onDeactivate = async () => {
    if (!deactivateTarget) return
    await deactivateContact.mutateAsync(deactivateTarget.id)
    setDeactivateTarget(null)
  }

  const openPortalModal = (c: ClientContact) => {
    setPortalContact(c)
    resetPortal({ email: c.email ?? '', portal_role: c.portal_role ?? 'client_user' })
    setShowPortalModal(true)
  }

  const onPortalSubmit = async (data: PortalFormData) => {
    if (!portalContact) return
    await grantPortal.mutateAsync({ contactId: portalContact.id, data })
    setShowPortalModal(false)
  }

  const onRevokePortal = async (c: ClientContact) => {
    await revokePortal.mutateAsync(c.id)
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
        <>
          {canEdit && (
            <div style={{ marginBottom: 12 }}>
              <button className="btn btn-primary" onClick={openAddContact}>
                + Добавить контакт
              </button>
            </div>
          )}
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>ФИО</th>
                  <th>Должность</th>
                  <th>Телефон</th>
                  <th>Email</th>
                  <th>Статус</th>
                  <th>Портал</th>
                  {canEdit && <th>Действия</th>}
                </tr>
              </thead>
              <tbody>
                {(!contacts || contacts.length === 0) && (
                  <tr>
                    <td colSpan={canEdit ? 7 : 6} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                      Контакты не добавлены
                    </td>
                  </tr>
                )}
                {contacts?.map(c => (
                  <tr key={c.id} style={{ opacity: c.is_active ? 1 : 0.5 }}>
                    <td style={{ fontWeight: 500 }}>
                      {c.name}
                      {c.is_primary && (
                        <span
                          style={{
                            marginLeft: 6,
                            fontSize: 10,
                            background: 'var(--primary)',
                            color: '#fff',
                            borderRadius: 4,
                            padding: '1px 5px',
                            verticalAlign: 'middle',
                          }}
                        >
                          основной
                        </span>
                      )}
                    </td>
                    <td>{c.position ?? '—'}</td>
                    <td>{c.phone ?? '—'}</td>
                    <td>{c.email ?? '—'}</td>
                    <td>
                      <span style={{ color: c.is_active ? 'var(--success)' : 'var(--text-muted)', fontSize: 12 }}>
                        {c.is_active ? 'Активен' : 'Деактивирован'}
                      </span>
                    </td>
                    <td>
                      {c.portal_access ? (
                        <span style={{ color: 'var(--success)', fontSize: 12 }}>
                          Доступ выдан
                          {c.portal_role === 'client_admin' ? ' (admin)' : ''}
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>Нет</span>
                      )}
                    </td>
                    {canEdit && (
                      <td>
                        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                          <button
                            className="btn btn-secondary"
                            style={{ padding: '2px 8px', fontSize: 12 }}
                            onClick={() => openEditContact(c)}
                          >
                            Редактировать
                          </button>
                          {c.is_active && (
                            <>
                              {c.portal_access ? (
                                <button
                                  className="btn btn-secondary"
                                  style={{ padding: '2px 8px', fontSize: 12 }}
                                  onClick={() => onRevokePortal(c)}
                                  disabled={revokePortal.isPending}
                                >
                                  Отозвать портал
                                </button>
                              ) : (
                                <button
                                  className="btn btn-secondary"
                                  style={{ padding: '2px 8px', fontSize: 12 }}
                                  onClick={() => openPortalModal(c)}
                                  disabled={!c.email}
                                  title={!c.email ? 'Для выдачи доступа укажите email контакта' : undefined}
                                >
                                  Выдать доступ к порталу
                                </button>
                              )}
                              <button
                                className="btn btn-danger"
                                style={{ padding: '2px 8px', fontSize: 12 }}
                                onClick={() => setDeactivateTarget(c)}
                              >
                                Деактивировать
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Модал создания/редактирования контакта */}
          {showContactModal && (
            <div className="modal-overlay" onClick={() => setShowContactModal(false)}>
              <div className="modal" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                  <h3>{editingContact ? 'Редактировать контакт' : 'Добавить контакт'}</h3>
                  <button className="modal-close" onClick={() => setShowContactModal(false)}>×</button>
                </div>
                <form onSubmit={handleContactSubmit(onContactSubmit)}>
                  <div className="modal-body">
                    <div className="form-group">
                      <label className="form-label">ФИО <span className="required">*</span></label>
                      <input
                        type="text"
                        className={`form-input${contactErrors.name ? ' error' : ''}`}
                        {...regContact('name')}
                      />
                      {contactErrors.name && <span className="form-error">{contactErrors.name.message}</span>}
                    </div>
                    <div className="form-group">
                      <label className="form-label">Должность</label>
                      <input type="text" className="form-input" {...regContact('position')} />
                    </div>
                    <div className="form-row">
                      <div className="form-group">
                        <label className="form-label">Телефон</label>
                        <input type="text" className="form-input" {...regContact('phone')} />
                      </div>
                      <div className="form-group">
                        <label className="form-label">Email</label>
                        <input
                          type="email"
                          className={`form-input${contactErrors.email ? ' error' : ''}`}
                          {...regContact('email')}
                        />
                        {contactErrors.email && <span className="form-error">{contactErrors.email.message}</span>}
                      </div>
                    </div>
                    <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <input type="checkbox" id="is_primary" {...regContact('is_primary')} />
                      <label htmlFor="is_primary" style={{ margin: 0 }}>
                        Основной контакт организации
                      </label>
                    </div>
                  </div>
                  <div className="modal-footer">
                    <button type="button" className="btn btn-secondary" onClick={() => setShowContactModal(false)}>
                      Отмена
                    </button>
                    <button
                      type="submit"
                      className="btn btn-primary"
                      disabled={createContact.isPending || updateContact.isPending}
                    >
                      {createContact.isPending || updateContact.isPending ? 'Сохранение...' : 'Сохранить'}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}

          {/* Модал выдачи доступа к порталу */}
          {showPortalModal && portalContact && (
            <div className="modal-overlay" onClick={() => setShowPortalModal(false)}>
              <div className="modal" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                  <h3>Выдать доступ к порталу</h3>
                  <button className="modal-close" onClick={() => setShowPortalModal(false)}>×</button>
                </div>
                <form onSubmit={handlePortalSubmit(onPortalSubmit)}>
                  <div className="modal-body">
                    <p style={{ marginBottom: 12, color: 'var(--text-muted)' }}>
                      Контакт: <strong>{portalContact.name}</strong>
                    </p>
                    <div className="form-group">
                      <label className="form-label">Email для портала</label>
                      <input
                        type="email"
                        className={`form-input${portalErrors.email ? ' error' : ''}`}
                        {...regPortal('email')}
                      />
                      {portalErrors.email && <span className="form-error">{portalErrors.email.message}</span>}
                    </div>
                    <div className="form-group">
                      <label className="form-label">Роль на портале</label>
                      <select className="form-select" {...regPortal('portal_role')}>
                        <option value="client_user">Пользователь (client_user)</option>
                        <option value="client_admin">Администратор (client_admin)</option>
                      </select>
                    </div>
                  </div>
                  <div className="modal-footer">
                    <button type="button" className="btn btn-secondary" onClick={() => setShowPortalModal(false)}>
                      Отмена
                    </button>
                    <button type="submit" className="btn btn-primary" disabled={grantPortal.isPending}>
                      {grantPortal.isPending ? 'Выдаю...' : 'Выдать доступ'}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}

          {/* Подтверждение деактивации */}
          {deactivateTarget && (
            <div className="modal-overlay" onClick={() => setDeactivateTarget(null)}>
              <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 420 }}>
                <div className="modal-header">
                  <h3>Деактивировать контакт</h3>
                  <button className="modal-close" onClick={() => setDeactivateTarget(null)}>×</button>
                </div>
                <div className="modal-body">
                  <p>
                    Деактивировать контакт <strong>{deactivateTarget.name}</strong>?
                  </p>
                  {deactivateTarget.portal_access && (
                    <p style={{ color: 'var(--warning)', marginTop: 8, fontSize: 13 }}>
                      Контакт имеет доступ к порталу — после деактивации доступ будет отозван.
                    </p>
                  )}
                  {deactivateTarget.is_primary && (
                    <p style={{ color: 'var(--warning)', marginTop: 8, fontSize: 13 }}>
                      {deactivateTarget.name} является основным контактом организации. После деактивации назначьте другой основной контакт.
                    </p>
                  )}
                </div>
                <div className="modal-footer">
                  <button className="btn btn-secondary" onClick={() => setDeactivateTarget(null)}>Отмена</button>
                  <button
                    className="btn btn-danger"
                    onClick={onDeactivate}
                    disabled={deactivateContact.isPending}
                  >
                    {deactivateContact.isPending ? 'Деактивирую...' : 'Деактивировать'}
                  </button>
                </div>
              </div>
            </div>
          )}
        </>
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
