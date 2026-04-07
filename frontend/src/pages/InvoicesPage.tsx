import { useState } from 'react'
import { format, parseISO, isPast } from 'date-fns'
import { ru } from 'date-fns/locale'
import { useQuery } from '@tanstack/react-query'
import * as api from '../api/endpoints'
import { useClients } from '../hooks/useClients'
import { useAuth } from '../context/AuthContext'
import Pagination from '../components/Pagination'
import type { InvoiceStatus } from '../api/types'

const STATUS_LABELS: Record<InvoiceStatus, string> = {
  draft: 'Черновик',
  sent: 'Отправлен',
  paid: 'Оплачен',
  overdue: 'Просрочен',
  cancelled: 'Отменён',
}

const STATUS_STYLE: Record<InvoiceStatus, { background: string; color: string }> = {
  draft: { background: '#f1f5f9', color: '#475569' },
  sent: { background: '#dbeafe', color: '#1d4ed8' },
  paid: { background: '#dcfce7', color: '#166534' },
  overdue: { background: '#fecaca', color: '#991b1b' },
  cancelled: { background: '#f1f5f9', color: '#64748b' },
}

export default function InvoicesPage() {
  const { hasRole } = useAuth()
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState<InvoiceStatus | ''>('')
  const [clientFilter, setClientFilter] = useState<string>('')

  const params: Record<string, unknown> = { page, size: 20 }
  if (statusFilter) params.status = statusFilter
  if (clientFilter) params.client_id = clientFilter

  const { data, isLoading, isError } = useQuery({
    queryKey: ['invoices', params],
    queryFn: () => api.getInvoices(params),
  })

  const { data: clientsData } = useClients({ size: 200 })
  const clients = clientsData?.items ?? []

  const canCreate = hasRole('admin', 'svc_mgr', 'manager')

  return (
    <>
      <div className="page-header">
        <h1>Счета</h1>
        {canCreate && (
          <button className="btn btn-primary" disabled>
            + Выставить счёт
          </button>
        )}
      </div>

      <div className="filters-bar">
        <select
          className="form-select"
          value={statusFilter}
          onChange={e => { setStatusFilter(e.target.value as InvoiceStatus | ''); setPage(1) }}
        >
          <option value="">Все статусы</option>
          <option value="draft">Черновик</option>
          <option value="sent">Отправлен</option>
          <option value="paid">Оплачен</option>
          <option value="overdue">Просрочен</option>
          <option value="cancelled">Отменён</option>
        </select>
        <select
          className="form-select"
          value={clientFilter}
          onChange={e => { setClientFilter(e.target.value); setPage(1) }}
        >
          <option value="">Все клиенты</option>
          {clients.map(c => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </div>

      {isLoading && (
        <div className="loading-center">
          <span className="spinner spinner-lg" />
        </div>
      )}
      {isError && (
        <div className="alert alert-error">Ошибка загрузки счетов</div>
      )}

      {data && (
        <>
          <div className="table-wrap">
            <table className="table table-hover">
              <thead>
                <tr>
                  <th>№</th>
                  <th>Клиент</th>
                  <th>Тип</th>
                  <th>Статус</th>
                  <th>Сумма</th>
                  <th>Выставлен</th>
                  <th>Срок оплаты</th>
                </tr>
              </thead>
              <tbody>
                {data.items.length === 0 && (
                  <tr>
                    <td colSpan={7} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                      Счета не найдены
                    </td>
                  </tr>
                )}
                {data.items.map(inv => {
                  const isOverdue =
                    inv.due_date &&
                    isPast(parseISO(inv.due_date)) &&
                    inv.status !== 'paid'

                  return (
                    <tr key={inv.id}>
                      <td>
                        <span style={{ fontWeight: 500 }}>{inv.number}</span>
                      </td>
                      <td>{inv.client?.name ?? '—'}</td>
                      <td>
                        {inv.type === 'service'
                          ? 'Услуги'
                          : inv.type === 'parts'
                          ? 'Запчасти'
                          : 'Комбинированный'}
                      </td>
                      <td>
                        <span
                          className="badge"
                          style={STATUS_STYLE[inv.status]}
                        >
                          {STATUS_LABELS[inv.status]}
                        </span>
                      </td>
                      <td style={{ fontWeight: 500 }}>
                        {parseFloat(String(inv.total_amount)).toLocaleString('ru-RU')} ₽
                      </td>
                      <td>
                        {format(parseISO(inv.issue_date), 'dd.MM.yyyy', { locale: ru })}
                      </td>
                      <td>
                        {inv.due_date ? (
                          <span style={{ color: isOverdue ? 'var(--danger)' : 'inherit' }}>
                            {format(parseISO(inv.due_date), 'dd.MM.yyyy', { locale: ru })}
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
