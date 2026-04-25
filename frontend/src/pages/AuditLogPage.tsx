import { useState } from 'react'
import { format, parseISO } from 'date-fns'
import { ru } from 'date-fns/locale'
import { useAuditLog } from '../hooks/useAuditLog'
import { useUsers } from '../hooks/useUsers'
import Pagination from '../components/Pagination'
import { getAuditLogExportUrl } from '../api/endpoints'

const ACTION_OPTIONS = [
  { value: '', label: 'Все действия' },
  { value: 'LOGIN', label: 'Вход' },
  { value: 'LOGOUT', label: 'Выход' },
  { value: 'CREATE', label: 'Создание' },
  { value: 'UPDATE', label: 'Изменение' },
  { value: 'DELETE', label: 'Удаление' },
  { value: 'ASSIGN', label: 'Назначение' },
  { value: 'STATUS_CHANGE', label: 'Смена статуса' },
]

const ENTITY_OPTIONS = [
  { value: '', label: 'Все объекты' },
  { value: 'ticket', label: 'Заявка' },
  { value: 'user', label: 'Пользователь' },
  { value: 'client', label: 'Клиент' },
  { value: 'equipment', label: 'Оборудование' },
  { value: 'invoice', label: 'Счёт' },
  { value: 'work_act', label: 'Акт' },
]

function formatDt(s: string) {
  try {
    return format(parseISO(s), 'dd.MM.yyyy HH:mm:ss', { locale: ru })
  } catch {
    return s
  }
}

function ValuesDiff({ oldValues, newValues }: { oldValues?: Record<string, unknown> | null; newValues?: Record<string, unknown> | null }) {
  const allKeys = Array.from(new Set([
    ...Object.keys(oldValues ?? {}),
    ...Object.keys(newValues ?? {}),
  ]))
  if (allKeys.length === 0) return <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>Нет данных</span>
  return (
    <table style={{ fontSize: 12, borderCollapse: 'collapse', width: '100%' }}>
      <thead>
        <tr>
          <th style={{ textAlign: 'left', padding: '2px 8px', color: 'var(--text-muted)', fontWeight: 500 }}>Поле</th>
          <th style={{ textAlign: 'left', padding: '2px 8px', color: '#e74c3c', fontWeight: 500 }}>Было</th>
          <th style={{ textAlign: 'left', padding: '2px 8px', color: '#27ae60', fontWeight: 500 }}>Стало</th>
        </tr>
      </thead>
      <tbody>
        {allKeys.map(k => {
          const ov = oldValues?.[k]
          const nv = newValues?.[k]
          const changed = JSON.stringify(ov) !== JSON.stringify(nv)
          return (
            <tr key={k} style={{ background: changed ? 'rgba(241,196,15,0.08)' : undefined }}>
              <td style={{ padding: '2px 8px', fontFamily: 'monospace', color: 'var(--text-muted)' }}>{k}</td>
              <td style={{ padding: '2px 8px', fontFamily: 'monospace', color: '#e74c3c' }}>
                {ov == null ? <em>—</em> : JSON.stringify(ov)}
              </td>
              <td style={{ padding: '2px 8px', fontFamily: 'monospace', color: '#27ae60' }}>
                {nv == null ? <em>—</em> : JSON.stringify(nv)}
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

export default function AuditLogPage() {
  const [page, setPage] = useState(1)
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set())
  const [userId, setUserId] = useState<number | ''>('')
  const [action, setAction] = useState('')
  const [entityType, setEntityType] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [ipAddress, setIpAddress] = useState('')

  const params: Parameters<typeof useAuditLog>[0] = { page, size: 50 }
  if (userId) params.user_id = userId as number
  if (action) params.action = action
  if (entityType) params.entity_type = entityType
  if (dateFrom) params.date_from = dateFrom
  if (dateTo) params.date_to = dateTo
  if (ipAddress) params.ip_address = ipAddress

  const { data, isLoading, isError } = useAuditLog(params)
  const { data: usersData } = useUsers({ size: 200, include_deleted: false })

  function handleReset() {
    setPage(1)
    setUserId('')
    setAction('')
    setEntityType('')
    setDateFrom('')
    setDateTo('')
    setIpAddress('')
  }

  const exportParams: Record<string, string | number | undefined> = {}
  if (userId) exportParams.user_id = userId as number
  if (action) exportParams.action = action
  if (entityType) exportParams.entity_type = entityType
  if (dateFrom) exportParams.date_from = dateFrom
  if (dateTo) exportParams.date_to = dateTo
  if (ipAddress) exportParams.ip_address = ipAddress

  const exportUrl = getAuditLogExportUrl(exportParams)

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Аудит-лог</h1>
          <p className="page-subtitle">История действий пользователей в системе</p>
        </div>
        <a
          href={`${exportUrl}&token=${localStorage.getItem('token') || ''}`}
          className="btn btn-secondary"
          style={{ textDecoration: 'none' }}
          onClick={(e) => {
            // inject auth header via fetch instead of anchor href
            e.preventDefault()
            fetch(exportUrl, { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } })
              .then(r => r.blob())
              .then(blob => {
                const url = URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url
                a.download = 'audit_log.csv'
                a.click()
                URL.revokeObjectURL(url)
              })
          }}
        >
          Экспорт CSV
        </a>
      </div>

      {/* Filters */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label">Пользователь</label>
            <select
              className="form-control"
              value={userId}
              onChange={e => { setPage(1); setUserId(e.target.value ? Number(e.target.value) : '') }}
            >
              <option value="">Все пользователи</option>
              {usersData?.items?.map(u => (
                <option key={u.id} value={u.id}>{u.full_name} ({u.email})</option>
              ))}
            </select>
          </div>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label">Действие</label>
            <select className="form-control" value={action} onChange={e => { setPage(1); setAction(e.target.value) }}>
              {ACTION_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label">Тип объекта</label>
            <select className="form-control" value={entityType} onChange={e => { setPage(1); setEntityType(e.target.value) }}>
              {ENTITY_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label">С даты</label>
            <input
              type="datetime-local"
              className="form-control"
              value={dateFrom}
              onChange={e => { setPage(1); setDateFrom(e.target.value) }}
            />
          </div>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label">По дату</label>
            <input
              type="datetime-local"
              className="form-control"
              value={dateTo}
              onChange={e => { setPage(1); setDateTo(e.target.value) }}
            />
          </div>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label">IP-адрес</label>
            <input
              type="text"
              className="form-control"
              placeholder="192.168.0.1"
              value={ipAddress}
              onChange={e => { setPage(1); setIpAddress(e.target.value) }}
            />
          </div>
        </div>
        <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
          <button className="btn btn-secondary btn-sm" onClick={handleReset}>
            Сбросить фильтры
          </button>
        </div>
      </div>

      {isLoading && <div className="loading-spinner" />}
      {isError && <div className="empty-state"><p>Ошибка загрузки данных</p></div>}

      {data && (
        <>
          <div className="card" style={{ padding: 0 }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Время</th>
                  <th>Пользователь</th>
                  <th>Действие</th>
                  <th>Объект</th>
                  <th>ID объекта</th>
                  <th>IP</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {data.items.length === 0 ? (
                  <tr>
                    <td colSpan={7} style={{ textAlign: 'center', padding: 32, color: 'var(--text-muted)' }}>
                      Записей не найдено
                    </td>
                  </tr>
                ) : data.items.map(entry => {
                  const hasDiff = !!(entry.old_values || entry.new_values)
                  const isExpanded = expandedRows.has(entry.id)
                  return (
                    <>
                      <tr key={entry.id}>
                        <td style={{ whiteSpace: 'nowrap', fontFamily: 'monospace', fontSize: 13 }}>
                          {formatDt(entry.created_at)}
                        </td>
                        <td>
                          {entry.user ? (
                            <span title={entry.user.email}>{entry.user.full_name}</span>
                          ) : (
                            <span style={{ color: 'var(--text-muted)' }}>Система</span>
                          )}
                        </td>
                        <td>
                          <span className="badge" style={{ background: actionColor(entry.action), color: '#fff', fontSize: 12 }}>
                            {entry.action}
                          </span>
                        </td>
                        <td style={{ color: 'var(--text-muted)' }}>{entry.entity_type}</td>
                        <td style={{ color: 'var(--text-muted)' }}>{entry.entity_id ?? '—'}</td>
                        <td style={{ fontFamily: 'monospace', fontSize: 12, color: 'var(--text-muted)' }}>
                          {entry.ip_address ?? '—'}
                        </td>
                        <td>
                          {hasDiff && (
                            <button
                              className="btn btn-sm btn-secondary"
                              style={{ padding: '2px 8px', fontSize: 12 }}
                              onClick={() => setExpandedRows(prev => {
                                const next = new Set(prev)
                                if (next.has(entry.id)) next.delete(entry.id)
                                else next.add(entry.id)
                                return next
                              })}
                            >
                              {isExpanded ? '▲' : '▼'} Подробнее
                            </button>
                          )}
                        </td>
                      </tr>
                      {isExpanded && hasDiff && (
                        <tr key={`${entry.id}-diff`} style={{ background: 'var(--bg-secondary)' }}>
                          <td colSpan={7} style={{ padding: '8px 16px' }}>
                            <ValuesDiff
                              oldValues={entry.old_values as Record<string, unknown> | null}
                              newValues={entry.new_values as Record<string, unknown> | null}
                            />
                          </td>
                        </tr>
                      )}
                    </>
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
    </div>
  )
}

function actionColor(action: string): string {
  if (action === 'DELETE') return '#e74c3c'
  if (action === 'CREATE') return '#27ae60'
  if (action === 'UPDATE') return '#f39c12'
  if (action === 'LOGIN') return '#3498db'
  if (action === 'LOGOUT') return '#95a5a6'
  return '#7f8c8d'
}
