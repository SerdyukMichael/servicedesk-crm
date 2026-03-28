import { useState } from 'react'
import { format, parseISO, isPast } from 'date-fns'
import { ru } from 'date-fns/locale'
import { useEquipment } from '../hooks/useEquipment'
import { useClients } from '../hooks/useClients'
import Pagination from '../components/Pagination'

const EQUIPMENT_STATUS_LABELS: Record<string, string> = {
  active: 'Активно',
  inactive: 'Неактивно',
  decommissioned: 'Списано',
  in_repair: 'В ремонте',
}

export default function EquipmentPage() {
  const [page, setPage] = useState(1)
  const [clientFilter, setClientFilter] = useState<string>('')
  const [statusFilter, setStatusFilter] = useState<string>('')

  const params: Record<string, unknown> = { page, size: 20 }
  if (clientFilter) params.client_id = clientFilter
  if (statusFilter) params.status = statusFilter

  const { data, isLoading, isError } = useEquipment(params)
  const { data: clientsData } = useClients({ size: 200 })

  const clients = clientsData?.items ?? []

  const handleClientChange = (val: string) => {
    setClientFilter(val)
    setPage(1)
  }

  const handleStatusChange = (val: string) => {
    setStatusFilter(val)
    setPage(1)
  }

  return (
    <>
      <div className="page-header">
        <h1>Оборудование</h1>
      </div>

      <div className="filters-bar">
        <select
          className="form-select"
          value={clientFilter}
          onChange={e => handleClientChange(e.target.value)}
        >
          <option value="">Все клиенты</option>
          {clients.map(c => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <select
          className="form-select"
          value={statusFilter}
          onChange={e => handleStatusChange(e.target.value)}
        >
          <option value="">Все статусы</option>
          <option value="active">Активно</option>
          <option value="inactive">Неактивно</option>
          <option value="in_repair">В ремонте</option>
          <option value="decommissioned">Списано</option>
        </select>
      </div>

      {isLoading && (
        <div className="loading-center">
          <span className="spinner spinner-lg" />
        </div>
      )}
      {isError && (
        <div className="alert alert-error">Ошибка загрузки оборудования</div>
      )}

      {data && (
        <>
          <div className="table-wrap">
            <table className="table table-hover">
              <thead>
                <tr>
                  <th>Серийный №</th>
                  <th>Модель</th>
                  <th>Клиент</th>
                  <th>Адрес</th>
                  <th>Статус</th>
                  <th>Гарантия до</th>
                </tr>
              </thead>
              <tbody>
                {data.items.length === 0 && (
                  <tr>
                    <td
                      colSpan={6}
                      style={{
                        textAlign: 'center',
                        padding: '40px',
                        color: 'var(--text-muted)',
                      }}
                    >
                      Оборудование не найдено
                    </td>
                  </tr>
                )}
                {data.items.map(eq => {
                  const warrantyExpired =
                    !eq.warranty_end || isPast(parseISO(eq.warranty_end))

                  return (
                    <tr key={eq.id}>
                      <td>
                        <span style={{ fontFamily: 'monospace', fontSize: 12 }}>
                          {eq.serial_number}
                        </span>
                      </td>
                      <td>{eq.model?.name ?? '—'}</td>
                      <td>{eq.client?.name ?? '—'}</td>
                      <td style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {eq.address ?? '—'}
                      </td>
                      <td>
                        <span
                          className="badge"
                          style={{
                            background:
                              eq.status === 'active'
                                ? '#dcfce7'
                                : eq.status === 'in_repair'
                                ? '#fef9c3'
                                : '#f1f5f9',
                            color:
                              eq.status === 'active'
                                ? '#166534'
                                : eq.status === 'in_repair'
                                ? '#854d0e'
                                : '#475569',
                          }}
                        >
                          {EQUIPMENT_STATUS_LABELS[eq.status] ?? eq.status}
                        </span>
                      </td>
                      <td>
                        {eq.warranty_end ? (
                          <span
                            style={{
                              color: warrantyExpired ? 'var(--danger)' : 'var(--success)',
                              fontWeight: warrantyExpired ? 600 : 400,
                            }}
                          >
                            {format(parseISO(eq.warranty_end), 'dd.MM.yyyy', {
                              locale: ru,
                            })}
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
