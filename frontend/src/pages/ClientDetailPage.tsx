import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { format, parseISO, isPast } from 'date-fns'
import { ru } from 'date-fns/locale'
import { useClient, useClientContacts } from '../hooks/useClients'
import { useClientEquipment } from '../hooks/useEquipment'
import { useClientTickets } from '../hooks/useTickets'
import { useAuth } from '../context/AuthContext'
import StatusBadge from '../components/StatusBadge'
import PriorityBadge from '../components/PriorityBadge'

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

  const { data: client, isLoading, isError } = useClient(clientId)
  const { data: contacts } = useClientContacts(clientId)
  const { data: equipment } = useClientEquipment(clientId)
  const { data: tickets } = useClientTickets(clientId)

  const canEdit = hasRole('admin', 'sales_mgr')

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
          <button className="btn btn-secondary">Редактировать</button>
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
                  <tr key={eq.id}>
                    <td>{eq.serial_number}</td>
                    <td>{eq.model?.name ?? '—'}</td>
                    <td>{eq.address ?? '—'}</td>
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
