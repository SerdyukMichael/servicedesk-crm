import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { format, parseISO } from 'date-fns'
import { ru } from 'date-fns/locale'
import { useEquipment, useEquipmentModels, useCreateEquipment, useUpdateEquipment } from '../hooks/useEquipment'
import { useClients } from '../hooks/useClients'
import Pagination from '../components/Pagination'
import type { Equipment } from '../api/types'

const EQUIPMENT_STATUS_LABELS: Record<string, string> = {
  active: 'Активно',
  inactive: 'Неактивно',
  decommissioned: 'Списано',
  in_repair: 'В ремонте',
  written_off: 'Списано',
  transferred: 'Передано',
}

const WARRANTY_STATUS_LABELS: Record<string, string> = {
  on_warranty: 'На гарантии',
  expiring: 'Истекает',
  expired: 'Истекла',
  unknown: '—',
}

const WARRANTY_STATUS_COLORS: Record<string, { bg: string; color: string }> = {
  on_warranty: { bg: '#dcfce7', color: '#166534' },
  expiring: { bg: '#fef9c3', color: '#854d0e' },
  expired: { bg: '#fee2e2', color: '#991b1b' },
  unknown: { bg: '#f1f5f9', color: '#475569' },
}

const optionalDate = z.preprocess(
  v => (v === '' ? undefined : v),
  z.string().optional()
)

const createSchema = z.object({
  client_id: z.coerce.number().min(1, 'Выберите клиента'),
  model_id: z.coerce.number().min(1, 'Выберите модель'),
  serial_number: z.string().min(1, 'Обязательное поле'),
  location: z.string().min(1, 'Обязательное поле'),
  status: z.string().default('active'),
  manufacture_date: optionalDate,
  sale_date: optionalDate,
  installed_at: optionalDate,
  warranty_start: optionalDate,
  warranty_until: optionalDate,
  firmware_version: optionalDate,
  notes: optionalDate,
})

type FormValues = z.infer<typeof createSchema>

function EquipmentFormModal({
  title,
  defaultValues,
  onClose,
  onSubmit,
  isLoading,
  error,
}: {
  title: string
  defaultValues: Partial<FormValues>
  onClose: () => void
  onSubmit: (data: FormValues) => void
  isLoading: boolean
  error?: string
}) {
  const { data: modelsData } = useEquipmentModels()
  const { data: clientsData } = useClients({ size: 200 })
  const models = modelsData ?? []
  const clients = clientsData?.items ?? []

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(createSchema),
    defaultValues,
  })

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal"
        style={{ maxWidth: 640, width: '100%' }}
        onClick={e => e.stopPropagation()}
      >
        <div className="modal-header">
          <h2>{title}</h2>
          <button className="btn-icon" onClick={onClose}>✕</button>
        </div>
        <form onSubmit={handleSubmit(onSubmit)}>
          <div className="modal-body" style={{ display: 'grid', gap: 12 }}>
            {error && <div className="alert alert-error">{error}</div>}

            <div className="form-row" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div className="form-group">
                <label className="form-label">Клиент *</label>
                <select className="form-select" {...register('client_id')}>
                  <option value="">— выберите —</option>
                  {clients.map(c => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
                {errors.client_id && <p className="form-error">{errors.client_id.message}</p>}
              </div>
              <div className="form-group">
                <label className="form-label">Модель *</label>
                <select className="form-select" {...register('model_id')}>
                  <option value="">— выберите —</option>
                  {models.map(m => (
                    <option key={m.id} value={m.id}>{m.name}</option>
                  ))}
                </select>
                {errors.model_id && <p className="form-error">{errors.model_id.message}</p>}
              </div>
            </div>

            <div className="form-row" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div className="form-group">
                <label className="form-label">Серийный номер *</label>
                <input className="form-input" {...register('serial_number')} />
                {errors.serial_number && <p className="form-error">{errors.serial_number.message}</p>}
              </div>
              <div className="form-group">
                <label className="form-label">Статус</label>
                <select className="form-select" {...register('status')}>
                  <option value="active">Активно</option>
                  <option value="in_repair">В ремонте</option>
                  <option value="decommissioned">Списано</option>
                  <option value="written_off">Выведено из эксплуатации</option>
                  <option value="transferred">Передано</option>
                </select>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Адрес установки *</label>
              <input className="form-input" {...register('location')} />
              {errors.location && <p className="form-error">{errors.location.message}</p>}
            </div>

            <div className="form-row" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div className="form-group">
                <label className="form-label">Дата производства</label>
                <input type="date" className="form-input" {...register('manufacture_date')} />
              </div>
              <div className="form-group">
                <label className="form-label">Дата продажи</label>
                <input type="date" className="form-input" {...register('sale_date')} />
              </div>
            </div>

            <div className="form-row" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div className="form-group">
                <label className="form-label">Дата установки</label>
                <input type="date" className="form-input" {...register('installed_at')} />
              </div>
              <div className="form-group">
                <label className="form-label">Версия прошивки</label>
                <input className="form-input" placeholder="v1.0.0" {...register('firmware_version')} />
              </div>
            </div>

            <div className="form-row" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div className="form-group">
                <label className="form-label">Начало гарантии</label>
                <input type="date" className="form-input" {...register('warranty_start')} />
              </div>
              <div className="form-group">
                <label className="form-label">Конец гарантии</label>
                <input type="date" className="form-input" {...register('warranty_until')} />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Примечания</label>
              <textarea className="form-input" rows={2} {...register('notes')} />
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Отмена
            </button>
            <button type="submit" className="btn btn-primary" disabled={isLoading}>
              {isLoading ? <span className="spinner" /> : 'Сохранить'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function EquipmentPage() {
  const [page, setPage] = useState(1)
  const [clientFilter, setClientFilter] = useState<string>('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [showCreate, setShowCreate] = useState(false)
  const [editEquipment, setEditEquipment] = useState<Equipment | null>(null)
  const [formError, setFormError] = useState<string>('')

  const params: Record<string, unknown> = { page, size: 20 }
  if (clientFilter) params.client_id = clientFilter
  if (statusFilter) params.status = statusFilter

  const { data, isLoading, isError } = useEquipment(params)
  const { data: clientsData } = useClients({ size: 200 })
  const createMutation = useCreateEquipment()
  const updateMutation = useUpdateEquipment(editEquipment?.id ?? 0)

  const clients = clientsData?.items ?? []

  const handleCreate = async (values: FormValues) => {
    setFormError('')
    try {
      await createMutation.mutateAsync(values as Parameters<typeof createMutation.mutateAsync>[0])
      setShowCreate(false)
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { message?: string } } })?.response?.data
      setFormError(detail?.message ?? 'Ошибка при создании')
    }
  }

  const handleUpdate = async (values: FormValues) => {
    setFormError('')
    try {
      await updateMutation.mutateAsync(values as Parameters<typeof updateMutation.mutateAsync>[0])
      setEditEquipment(null)
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { message?: string } } })?.response?.data
      setFormError(detail?.message ?? 'Ошибка при сохранении')
    }
  }

  const openEdit = (eq: Equipment) => {
    setFormError('')
    setEditEquipment(eq)
  }

  return (
    <>
      <div className="page-header">
        <h1>Оборудование</h1>
        <button className="btn btn-primary" onClick={() => { setFormError(''); setShowCreate(true) }}>
          + Добавить
        </button>
      </div>

      <div className="filters-bar">
        <select
          className="form-select"
          value={clientFilter}
          onChange={e => { setClientFilter(e.target.value); setPage(1) }}
        >
          <option value="">Все клиенты</option>
          {clients.map(c => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
        <select
          className="form-select"
          value={statusFilter}
          onChange={e => { setStatusFilter(e.target.value); setPage(1) }}
        >
          <option value="">Все статусы</option>
          <option value="active">Активно</option>
          <option value="in_repair">В ремонте</option>
          <option value="decommissioned">Списано</option>
          <option value="written_off">Выведено из эксплуатации</option>
          <option value="transferred">Передано</option>
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
                  <th>Гар. статус</th>
                </tr>
              </thead>
              <tbody>
                {data.items.length === 0 && (
                  <tr>
                    <td colSpan={7} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                      Оборудование не найдено
                    </td>
                  </tr>
                )}
                {data.items.map(eq => {
                  const ws = eq.warranty_status ?? 'unknown'
                  const wsColors = WARRANTY_STATUS_COLORS[ws] ?? WARRANTY_STATUS_COLORS.unknown

                  return (
                    <tr key={eq.id} style={{ cursor: 'pointer' }} onClick={() => openEdit(eq)}>
                      <td>
                        <span style={{ fontFamily: 'monospace', fontSize: 12 }}>
                          {eq.serial_number}
                        </span>
                      </td>
                      <td>{eq.model?.name ?? '—'}</td>
                      <td>{eq.client?.name ?? '—'}</td>
                      <td style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {eq.address ?? eq.location ?? '—'}
                      </td>
                      <td>
                        <span
                          className="badge"
                          style={{
                            background:
                              eq.status === 'active' ? '#dcfce7'
                              : eq.status === 'in_repair' ? '#fef9c3'
                              : '#f1f5f9',
                            color:
                              eq.status === 'active' ? '#166534'
                              : eq.status === 'in_repair' ? '#854d0e'
                              : '#475569',
                          }}
                        >
                          {EQUIPMENT_STATUS_LABELS[eq.status] ?? eq.status}
                        </span>
                      </td>
                      <td>
                        {eq.warranty_end || eq.warranty_until ? (
                          <span>
                            {format(
                              parseISO((eq.warranty_end ?? eq.warranty_until)!),
                              'dd.MM.yyyy',
                              { locale: ru }
                            )}
                          </span>
                        ) : (
                          <span style={{ color: 'var(--text-muted)' }}>—</span>
                        )}
                      </td>
                      <td>
                        <span
                          className="badge"
                          style={{ background: wsColors.bg, color: wsColors.color }}
                        >
                          {WARRANTY_STATUS_LABELS[ws]}
                        </span>
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

      {showCreate && (
        <EquipmentFormModal
          title="Добавить оборудование"
          defaultValues={{ status: 'active' }}
          onClose={() => setShowCreate(false)}
          onSubmit={handleCreate}
          isLoading={createMutation.isPending}
          error={formError}
        />
      )}

      {editEquipment && (
        <EquipmentFormModal
          title={`Редактировать: ${editEquipment.serial_number}`}
          defaultValues={{
            client_id: editEquipment.client_id,
            model_id: editEquipment.model_id ?? undefined,
            serial_number: editEquipment.serial_number,
            location: editEquipment.location ?? editEquipment.address ?? '',
            status: editEquipment.status,
            manufacture_date: editEquipment.manufacture_date ?? '',
            sale_date: editEquipment.sale_date ?? '',
            installed_at: editEquipment.installed_at ?? editEquipment.installation_date ?? '',
            warranty_start: editEquipment.warranty_start ?? '',
            warranty_until: editEquipment.warranty_end ?? editEquipment.warranty_until ?? '',
            firmware_version: editEquipment.firmware_version ?? '',
            notes: editEquipment.notes ?? '',
          }}
          onClose={() => setEditEquipment(null)}
          onSubmit={handleUpdate}
          isLoading={updateMutation.isPending}
          error={formError}
        />
      )}
    </>
  )
}
