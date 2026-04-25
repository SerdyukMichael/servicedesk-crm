import { useState } from 'react'
import { format, subDays } from 'date-fns'
import { useTicketReport } from '../hooks/useReports'
import { useUsers } from '../hooks/useUsers'
import { useClients } from '../hooks/useClients'
import { getTicketReportExportUrl } from '../api/endpoints'

const today = format(new Date(), 'yyyy-MM-dd')
const monthAgo = format(subDays(new Date(), 30), 'yyyy-MM-dd')

const STATUS_LABELS: Record<string, string> = {
  new: 'Новая', assigned: 'Назначена', in_progress: 'В работе',
  waiting_part: 'Ожидание запчасти', on_review: 'На проверке',
  completed: 'Завершена', closed: 'Закрыта', cancelled: 'Отменена',
}

const TYPE_LABELS: Record<string, string> = {
  repair: 'Ремонт', maintenance: 'ТО', diagnostics: 'Диагностика',
  installation: 'Установка', consultation: 'Консультация',
}

const PRIORITY_LABELS: Record<string, string> = {
  critical: 'Критический', high: 'Высокий', medium: 'Средний', low: 'Низкий',
}

const PRIORITY_COLORS: Record<string, string> = {
  critical: '#e74c3c', high: '#e67e22', medium: '#3498db', low: '#95a5a6',
}

function BarChart({ data, labels, colors }: {
  data: Record<string, number>
  labels?: Record<string, string>
  colors?: Record<string, string>
}) {
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1])
  const max = Math.max(...entries.map(e => e[1]), 1)
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {entries.map(([key, val]) => (
        <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ width: 120, textAlign: 'right', fontSize: 13, color: 'var(--text-muted)', flexShrink: 0 }}>
            {labels?.[key] ?? key}
          </div>
          <div style={{ flex: 1, background: 'var(--bg-secondary)', borderRadius: 4, height: 20, overflow: 'hidden' }}>
            <div
              style={{
                width: `${(val / max) * 100}%`,
                height: '100%',
                background: colors?.[key] ?? 'var(--primary)',
                borderRadius: 4,
                minWidth: val > 0 ? 4 : 0,
                transition: 'width 0.3s',
              }}
            />
          </div>
          <div style={{ width: 32, fontSize: 13, fontWeight: 600 }}>{val}</div>
        </div>
      ))}
      {entries.length === 0 && <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>Нет данных</div>}
    </div>
  )
}

export default function ReportsPage() {
  const [dateFrom, setDateFrom] = useState(monthAgo)
  const [dateTo, setDateTo] = useState(today)
  const [engineerId, setEngineerId] = useState<number | ''>('')
  const [clientId, setClientId] = useState<number | ''>('')

  const params = {
    date_from: dateFrom,
    date_to: dateTo,
    engineer_id: engineerId || undefined,
    client_id: clientId || undefined,
  }

  const { data, isLoading, isError, refetch } = useTicketReport(params as { date_from: string; date_to: string })
  const { data: usersData } = useUsers({ size: 200 })
  const { data: clientsData } = useClients({ size: 200 })

  const engineers = usersData?.items?.filter(u => u.roles?.includes('engineer') || u.roles?.includes('svc_mgr')) ?? []

  const exportParams: Record<string, string | number | undefined> = {
    date_from: dateFrom,
    date_to: dateTo,
  }
  if (engineerId) exportParams.engineer_id = engineerId as number
  if (clientId) exportParams.client_id = clientId as number

  const exportUrl = getTicketReportExportUrl(exportParams)

  function handleExport(e: React.MouseEvent) {
    e.preventDefault()
    fetch(exportUrl, { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } })
      .then(r => r.blob())
      .then(blob => {
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `tickets_report_${dateFrom}_${dateTo}.xlsx`
        a.click()
        URL.revokeObjectURL(url)
      })
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Отчёт по заявкам</h1>
          <p className="page-subtitle">Сводная аналитика за период</p>
        </div>
        <button
          className="btn btn-secondary"
          onClick={handleExport}
          disabled={!data || data.total === 0}
          title={!data || data.total === 0 ? 'Нет данных для экспорта' : undefined}
        >
          Экспорт XLSX
        </button>
      </div>

      {/* Filters */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label">С даты</label>
            <input type="date" className="form-control" value={dateFrom} onChange={e => setDateFrom(e.target.value)} />
          </div>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label">По дату</label>
            <input type="date" className="form-control" value={dateTo} onChange={e => setDateTo(e.target.value)} />
          </div>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label">Инженер</label>
            <select className="form-control" value={engineerId} onChange={e => setEngineerId(e.target.value ? Number(e.target.value) : '')}>
              <option value="">Все инженеры</option>
              {engineers.map(u => <option key={u.id} value={u.id}>{u.full_name}</option>)}
            </select>
          </div>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label">Клиент</label>
            <select className="form-control" value={clientId} onChange={e => setClientId(e.target.value ? Number(e.target.value) : '')}>
              <option value="">Все клиенты</option>
              {clientsData?.items?.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
        </div>
        <div style={{ marginTop: 12 }}>
          <button className="btn btn-primary btn-sm" onClick={() => refetch()}>
            Применить
          </button>
        </div>
      </div>

      {isLoading && <div className="loading-spinner" />}
      {isError && <div className="empty-state"><p>Ошибка загрузки отчёта</p></div>}

      {data && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
          {/* Summary card */}
          <div className="card" style={{ gridColumn: '1 / -1' }}>
            <div style={{ display: 'flex', gap: 32, flexWrap: 'wrap', alignItems: 'center' }}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 40, fontWeight: 700, color: 'var(--primary)' }}>{data.total}</div>
                <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>Всего заявок</div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{
                  fontSize: 32, fontWeight: 700,
                  color: data.sla_reaction_compliance_pct == null ? 'var(--text-muted)'
                    : data.sla_reaction_compliance_pct >= 90 ? '#27ae60'
                    : data.sla_reaction_compliance_pct >= 70 ? '#f39c12'
                    : '#e74c3c',
                }}>
                  {data.sla_reaction_compliance_pct == null ? '—' : `${data.sla_reaction_compliance_pct}%`}
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>SLA реакции</div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{
                  fontSize: 32, fontWeight: 700,
                  color: data.sla_resolution_compliance_pct == null ? 'var(--text-muted)'
                    : data.sla_resolution_compliance_pct >= 90 ? '#27ae60'
                    : data.sla_resolution_compliance_pct >= 70 ? '#f39c12'
                    : '#e74c3c',
                }}>
                  {data.sla_resolution_compliance_pct == null ? '—' : `${data.sla_resolution_compliance_pct}%`}
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>SLA решения</div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 32, fontWeight: 700, color: 'var(--text-primary)' }}>
                  {data.avg_resolution_hours == null ? '—' : `${data.avg_resolution_hours}ч`}
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>Среднее время решения</div>
              </div>
              <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: 14 }}>
                <div>{data.period_from}</div>
                <div>—</div>
                <div>{data.period_to}</div>
              </div>
            </div>
          </div>

          {/* By status */}
          <div className="card">
            <h3 style={{ marginBottom: 16, fontSize: 15 }}>По статусам</h3>
            <BarChart data={data.by_status} labels={STATUS_LABELS} />
          </div>

          {/* By priority */}
          <div className="card">
            <h3 style={{ marginBottom: 16, fontSize: 15 }}>По приоритетам</h3>
            <BarChart data={data.by_priority} labels={PRIORITY_LABELS} colors={PRIORITY_COLORS} />
          </div>

          {/* By type */}
          <div className="card">
            <h3 style={{ marginBottom: 16, fontSize: 15 }}>По типам</h3>
            <BarChart data={data.by_type} labels={TYPE_LABELS} />
          </div>

          {/* By engineer */}
          <div className="card">
            <h3 style={{ marginBottom: 16, fontSize: 15 }}>По инженерам</h3>
            <BarChart data={data.by_engineer} />
          </div>
        </div>
      )}
    </div>
  )
}
