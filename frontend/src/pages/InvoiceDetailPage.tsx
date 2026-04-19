import { Link, useParams, useNavigate } from 'react-router-dom'
import { format, parseISO, isPast } from 'date-fns'
import { ru } from 'date-fns/locale'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as api from '../api/endpoints'
import { useAuth } from '../context/AuthContext'
import { useCurrency } from '../context/CurrencyContext'
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

export default function InvoiceDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { hasRole } = useAuth()
  const { currency } = useCurrency()
  const qc = useQueryClient()
  const invoiceId = Number(id)

  const { data: inv, isLoading, isError } = useQuery({
    queryKey: ['invoice', invoiceId],
    queryFn: () => api.getInvoice(invoiceId),
    enabled: !!invoiceId,
  })

  const sendMutation = useMutation({
    mutationFn: () => api.sendInvoice(invoiceId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['invoice', invoiceId] }),
  })

  const payMutation = useMutation({
    mutationFn: () => api.payInvoice(invoiceId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['invoice', invoiceId] }),
  })

  if (isLoading) {
    return (
      <div className="loading-center">
        <span className="spinner spinner-lg" />
      </div>
    )
  }

  if (isError || !inv) {
    return <div className="alert alert-error">Счёт не найден</div>
  }

  const canWrite = hasRole('admin', 'accountant', 'svc_mgr')
  const isOverdue = inv.due_date && isPast(parseISO(inv.due_date)) && inv.status !== 'paid'
  const vatAmount = parseFloat(String(inv.vat_amount))
  const totalAmount = parseFloat(String(inv.total_amount))

  return (
    <>
      <div className="page-header">
        <div>
          <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 4 }}>
            <Link to="/invoices">Счета</Link>
            {inv.ticket_id && (
              <> / <Link to={`/tickets/${inv.ticket_id}`}>Заявка #{inv.ticket_id}</Link></>
            )}
            {' / '}{inv.number}
          </div>
          <h1 style={{ margin: 0 }}>{inv.number}</h1>
        </div>
        <span className="badge" style={{ ...STATUS_STYLE[inv.status], fontSize: 14, padding: '6px 14px' }}>
          {STATUS_LABELS[inv.status]}
        </span>
      </div>

      {/* Реквизиты */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-header">
          <h3 className="card-title">Реквизиты</h3>
        </div>
        <div className="card-body">
          <ul className="info-list">
            {inv.client && (
              <li>
                <span className="info-list-label">Клиент</span>
                <span className="info-list-value">
                  <Link to={`/clients/${inv.client_id}`}>{inv.client.name}</Link>
                </span>
              </li>
            )}
            {inv.ticket_id && (
              <li>
                <span className="info-list-label">Заявка</span>
                <span className="info-list-value">
                  <Link to={`/tickets/${inv.ticket_id}`}>#{inv.ticket_id}</Link>
                </span>
              </li>
            )}
            <li>
              <span className="info-list-label">Тип</span>
              <span className="info-list-value">
                {inv.type === 'service' ? 'Услуги' : inv.type === 'parts' ? 'Запчасти' : 'Комбинированный'}
              </span>
            </li>
            <li>
              <span className="info-list-label">Дата выставления</span>
              <span className="info-list-value">
                {format(parseISO(inv.issue_date), 'dd MMMM yyyy', { locale: ru })}
              </span>
            </li>
            {inv.due_date && (
              <li>
                <span className="info-list-label">Срок оплаты</span>
                <span className="info-list-value" style={{ color: isOverdue ? 'var(--danger)' : 'inherit', fontWeight: isOverdue ? 600 : 'normal' }}>
                  {format(parseISO(inv.due_date), 'dd MMMM yyyy', { locale: ru })}
                  {isOverdue && ' — просрочен'}
                </span>
              </li>
            )}
            {inv.paid_at && (
              <li>
                <span className="info-list-label">Дата оплаты</span>
                <span className="info-list-value" style={{ color: '#166534', fontWeight: 600 }}>
                  ✓ {format(parseISO(inv.paid_at), 'dd MMMM yyyy', { locale: ru })}
                </span>
              </li>
            )}
            {inv.notes && (
              <li>
                <span className="info-list-label">Примечания</span>
                <span className="info-list-value">{inv.notes}</span>
              </li>
            )}
          </ul>
        </div>
      </div>

      {/* Позиции */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-header">
          <h3 className="card-title">Позиции</h3>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          <table className="table" style={{ margin: 0 }}>
            <thead>
              <tr>
                <th>Наименование</th>
                <th style={{ textAlign: 'center' }}>Кол-во</th>
                <th>Ед.</th>
                <th style={{ textAlign: 'right' }}>Цена</th>
                <th style={{ textAlign: 'right' }}>Сумма</th>
              </tr>
            </thead>
            <tbody>
              {inv.items.length === 0 && (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', padding: '24px', color: 'var(--text-muted)' }}>
                    Позиции отсутствуют
                  </td>
                </tr>
              )}
              {inv.items.map(item => (
                <tr key={item.id}>
                  <td>{item.description}</td>
                  <td style={{ textAlign: 'center' }}>{parseFloat(String(item.quantity))}</td>
                  <td>{item.unit}</td>
                  <td style={{ textAlign: 'right' }}>{parseFloat(String(item.unit_price)).toLocaleString('ru-RU')} {currency.currency_code}</td>
                  <td style={{ textAlign: 'right', fontWeight: 600 }}>{parseFloat(String(item.total)).toLocaleString('ru-RU')} {currency.currency_code}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr style={{ background: 'var(--surface-alt, var(--surface))' }}>
                <td colSpan={4} style={{ textAlign: 'right', fontWeight: 700 }}>Итого:</td>
                <td style={{ textAlign: 'right', fontWeight: 700, fontSize: 16 }}>
                  {totalAmount.toLocaleString('ru-RU', { minimumFractionDigits: 2 })} {currency.currency_code}
                </td>
              </tr>
              {vatAmount > 0 && (
                <tr>
                  <td colSpan={4} style={{ textAlign: 'right', color: 'var(--text-muted)', fontSize: 13 }}>
                    в т.ч. НДС ({parseFloat(String(inv.vat_rate))}%):
                  </td>
                  <td style={{ textAlign: 'right', color: 'var(--text-muted)', fontSize: 13 }}>
                    {vatAmount.toLocaleString('ru-RU', { minimumFractionDigits: 2 })} {currency.currency_code}
                  </td>
                </tr>
              )}
            </tfoot>
          </table>
        </div>
      </div>

      {/* Действия */}
      {canWrite && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Действия</h3>
          </div>
          <div className="card-body" style={{ display: 'flex', gap: 8 }}>
            {inv.status === 'draft' && (
              <button
                className="btn btn-primary btn-sm"
                onClick={() => sendMutation.mutate()}
                disabled={sendMutation.isPending}
              >
                {sendMutation.isPending ? 'Отправка...' : '📤 Отправить клиенту'}
              </button>
            )}
            {(inv.status === 'sent' || inv.status === 'overdue') && (
              <button
                className="btn btn-success btn-sm"
                onClick={() => payMutation.mutate()}
                disabled={payMutation.isPending}
              >
                {payMutation.isPending ? 'Сохранение...' : '✓ Отметить оплаченным'}
              </button>
            )}
            {sendMutation.isError && (
              <span style={{ color: 'var(--danger)', fontSize: 13 }}>Ошибка отправки</span>
            )}
            {payMutation.isError && (
              <span style={{ color: 'var(--danger)', fontSize: 13 }}>Ошибка оплаты</span>
            )}
          </div>
        </div>
      )}

      <div style={{ marginTop: 16 }}>
        <button className="btn btn-secondary btn-sm" onClick={() => navigate(-1)}>
          ← Назад
        </button>
      </div>
    </>
  )
}
