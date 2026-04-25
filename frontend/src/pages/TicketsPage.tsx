import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { format, isPast, parseISO } from 'date-fns'
import { ru } from 'date-fns/locale'
import { useTickets } from '../hooks/useTickets'
import { useClients } from '../hooks/useClients'
import { useAuth } from '../context/AuthContext'
import StatusBadge from '../components/StatusBadge'
import PriorityBadge from '../components/PriorityBadge'
import Pagination from '../components/Pagination'
import type { TicketStatus, TicketPriority } from '../api/types'

const STATUS_OPTIONS: { value: TicketStatus | ''; label: string }[] = [
  { value: '', label: 'Все статусы' },
  { value: 'new', label: 'Новая' },
  { value: 'assigned', label: 'Назначена' },
  { value: 'in_progress', label: 'В работе' },
  { value: 'waiting_part', label: 'Ожидание запчасти' },
  { value: 'on_review', label: 'На проверке' },
  { value: 'completed', label: 'Завершена' },
  { value: 'closed', label: 'Закрыта' },
  { value: 'cancelled', label: 'Отменена' },
]

const PRIORITY_OPTIONS: { value: TicketPriority | ''; label: string }[] = [
  { value: '', label: 'Все приоритеты' },
  { value: 'critical', label: 'Критический' },
  { value: 'high', label: 'Высокий' },
  { value: 'medium', label: 'Средний' },
  { value: 'low', label: 'Низкий' },
]

export default function TicketsPage() {
  const navigate = useNavigate()
  const { hasRole } = useAuth()

  const [page, setPage] = useState(1)
  const [status, setStatus] = useState<TicketStatus | ''>('')
  const [priority, setPriority] = useState<TicketPriority | ''>('')
  const [search, setSearch] = useState('')
  const [clientId, setClientId] = useState<number | ''>('')
  const [slaViolated, setSlaViolated] = useState(false)

  const params: Record<string, unknown> = { page, size: 20 }
  if (status) params.status = status
  if (priority) params.priority = priority
  if (search) params.search = search
  if (clientId) params.client_id = clientId
  if (slaViolated) params.sla_violated = true

  const { data, isLoading, isError } = useTickets(params)
  const { data: clientsData } = useClients({ size: 200 })

  const canCreate = hasRole('admin', 'svc_mgr', 'manager')

  const handleSearch = (val: string) => {
    setSearch(val)
    setPage(1)
  }

  const handleStatusChange = (val: string) => {
    setStatus(val as TicketStatus | '')
    setPage(1)
  }

  const handlePriorityChange = (val: string) => {
    setPriority(val as TicketPriority | '')
    setPage(1)
  }

  const handleClientChange = (val: string) => {
    setClientId(val ? parseInt(val, 10) : '')
    setPage(1)
  }

  return (
    <>
      <div className="page-header">
        <h1>Заявки</h1>
        {canCreate && (
          <button
            className="btn btn-primary"
            onClick={() => navigate('/tickets/new')}
          >
            + Создать заявку
          </button>
        )}
      </div>

      <div className="filters-bar">
        <input
          type="text"
          className="form-input"
          placeholder="Поиск по заголовку..."
          value={search}
          onChange={e => handleSearch(e.target.value)}
          style={{ minWidth: 200 }}
        />
        <select
          className="form-select"
          value={status}
          onChange={e => handleStatusChange(e.target.value)}
        >
          {STATUS_OPTIONS.map(o => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <select
          className="form-select"
          value={priority}
          onChange={e => handlePriorityChange(e.target.value)}
        >
          {PRIORITY_OPTIONS.map(o => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <select
          className="form-select"
          value={clientId}
          onChange={e => handleClientChange(e.target.value)}
        >
          <option value="">Все клиенты</option>
          {clientsData?.items.map(c => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
        <button
          className={`btn btn-sm ${slaViolated ? 'btn-danger' : 'btn-secondary'}`}
          onClick={() => { setSlaViolated(v => !v); setPage(1) }}
          title="Показать только заявки с нарушением SLA"
        >
          {slaViolated ? '🔴 SLA нарушен' : 'SLA нарушен'}
        </button>
      </div>

      {isLoading && (
        <div className="loading-center">
          <span className="spinner spinner-lg" />
        </div>
      )}

      {isError && (
        <div className="alert alert-error">Ошибка загрузки заявок</div>
      )}

      {data && (
        <>
          <div className="table-wrap">
            <table className="table table-hover">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Заголовок</th>
                  <th>Клиент</th>
                  <th>Приоритет</th>
                  <th>Статус</th>
                  <th>Инженер</th>
                  <th>Создана</th>
                  <th>SLA</th>
                </tr>
              </thead>
              <tbody>
                {data.items.length === 0 && (
                  <tr>
                    <td colSpan={8} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                      Заявки не найдены
                    </td>
                  </tr>
                )}
                {data.items.map(ticket => {
                  const isOverdue =
                    ticket.sla_deadline &&
                    isPast(parseISO(ticket.sla_deadline)) &&
                    !['completed', 'closed', 'cancelled'].includes(ticket.status)

                  return (
                    <tr
                      key={ticket.id}
                      onClick={() => navigate(`/tickets/${ticket.id}`)}
                    >
                      <td>
                        <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                          {ticket.number}
                        </span>
                      </td>
                      <td>
                        <span style={{ fontWeight: 500 }}>{ticket.title}</span>
                      </td>
                      <td>{ticket.client?.name ?? '—'}</td>
                      <td>
                        <PriorityBadge priority={ticket.priority} />
                      </td>
                      <td>
                        <StatusBadge status={ticket.status} />
                      </td>
                      <td>{ticket.engineer?.full_name ?? '—'}</td>
                      <td>
                        {format(parseISO(ticket.created_at), 'dd.MM.yyyy', { locale: ru })}
                      </td>
                      <td>
                        {ticket.sla_deadline ? (
                          <span className={isOverdue ? 'sla-overdue' : ''}>
                            {format(parseISO(ticket.sla_deadline), 'dd.MM.yyyy HH:mm')}
                          </span>
                        ) : (
                          '—'
                        )}
                      </td>
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
    </>
  )
}
