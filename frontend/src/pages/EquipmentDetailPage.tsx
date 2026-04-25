import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { format, parseISO } from 'date-fns'
import { ru } from 'date-fns/locale'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useEquipmentItem, useEquipmentModels, useUpdateEquipment } from '../hooks/useEquipment'
import { useEquipmentTickets } from '../hooks/useTickets'
import { useClients } from '../hooks/useClients'
import { useAuth } from '../context/AuthContext'
import { useMaintenanceSchedule, useCreateMaintenanceSchedule, useUpdateMaintenanceSchedule } from '../hooks/useMaintenanceSchedule'
import StatusBadge from '../components/StatusBadge'
import PriorityBadge from '../components/PriorityBadge'
import type { MaintenanceFrequency } from '../api/types'

const EQUIPMENT_STATUS_LABELS: Record<string, string> = {
  active: 'Активно',
  inactive: 'Неактивно',
  decommissioned: 'Списано',
  in_repair: 'В ремонте',
  written_off: 'Выведено из эксплуатации',
  transferred: 'Передано',
}

const WARRANTY_STATUS_LABELS: Record<string, string> = {
  on_warranty: 'На гарантии',
  expiring: 'Гарантия истекает',
  expired: 'Гарантия истекла',
  unknown: 'Нет гарантии',
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

const editSchema = z.object({
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

type EditFormValues = z.infer<typeof editSchema>

export default function EquipmentDetailPage() {
  const { id } = useParams<{ id: string }>()
  const equipmentId = parseInt(id ?? '0', 10)
  const navigate = useNavigate()
  const { hasRole } = useAuth()

  const [showEdit, setShowEdit] = useState(false)
  const [formError, setFormError] = useState('')
  const [showMaintForm, setShowMaintForm] = useState(false)
  const [maintFreq, setMaintFreq] = useState<MaintenanceFrequency>('monthly')
  const [maintFirstDate, setMaintFirstDate] = useState('')
  const [maintNextDate, setMaintNextDate] = useState('')
  const [maintError, setMaintError] = useState('')

  const { data: eq, isLoading, isError } = useEquipmentItem(equipmentId)
  const { data: tickets } = useEquipmentTickets(equipmentId)
  const { data: schedule } = useMaintenanceSchedule(equipmentId)
  const createSchedule = useCreateMaintenanceSchedule(equipmentId)
  const updateSchedule = useUpdateMaintenanceSchedule(equipmentId)
  const { data: modelsData } = useEquipmentModels()
  const { data: clientsData } = useClients({ size: 200 })
  const updateMutation = useUpdateEquipment(equipmentId)

  const canEdit = hasRole('admin', 'svc_mgr')

  const { register, handleSubmit, reset, formState: { errors } } = useForm<EditFormValues>({
    resolver: zodResolver(editSchema),
  })

  const openEdit = () => {
    if (!eq) return
    setFormError('')
    reset({
      client_id: eq.client_id,
      model_id: eq.model_id ?? undefined,
      serial_number: eq.serial_number,
      location: eq.location ?? eq.address ?? '',
      status: eq.status,
      manufacture_date: eq.manufacture_date ?? '',
      sale_date: eq.sale_date ?? '',
      installed_at: eq.installed_at ?? eq.installation_date ?? '',
      warranty_start: eq.warranty_start ?? '',
      warranty_until: eq.warranty_end ?? eq.warranty_until ?? '',
      firmware_version: eq.firmware_version ?? '',
      notes: eq.notes ?? '',
    })
    setShowEdit(true)
  }

  const onSubmit = async (values: EditFormValues) => {
    setFormError('')
    try {
      await updateMutation.mutateAsync(values as Parameters<typeof updateMutation.mutateAsync>[0])
      setShowEdit(false)
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { message?: string } } })?.response?.data
      setFormError(detail?.message ?? 'Ошибка при сохранении')
    }
  }

  if (isLoading)
    return <div className="loading-center"><span className="spinner spinner-lg" /></div>
  if (isError || !eq)
    return <div className="alert alert-error">Оборудование не найдено</div>

  const ws = eq.warranty_status ?? 'unknown'
  const wsColors = WARRANTY_STATUS_COLORS[ws] ?? WARRANTY_STATUS_COLORS.unknown
  const models = modelsData ?? []
  const clients = clientsData?.items ?? []

  const fmtDate = (d?: string | null) =>
    d ? format(parseISO(d), 'dd.MM.yyyy', { locale: ru }) : '—'

  return (
    <>
      <div className="page-header">
        <div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>
            <span style={{ cursor: 'pointer' }} onClick={() => navigate('/equipment')}>
              Оборудование
            </span>{' '}
            / {eq.serial_number}
          </div>
          <h1 style={{ fontSize: 20 }}>
            {eq.model?.name ?? '—'}{' '}
            <span style={{ fontFamily: 'monospace', fontSize: 15, color: 'var(--text-muted)' }}>
              {eq.serial_number}
            </span>
          </h1>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {canEdit && (
            <button className="btn btn-secondary" onClick={openEdit}>
              Редактировать
            </button>
          )}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, maxWidth: 900 }}>
        {/* Left card — основные данные */}
        <div className="card">
          <div className="card-header" style={{ fontWeight: 600, fontSize: 14 }}>
            Паспортные данные
          </div>
          <div className="card-body">
            <ul className="info-list">
              <li>
                <span className="info-list-label">Статус</span>
                <span className="info-list-value">
                  <span className="badge" style={{
                    background: eq.status === 'active' ? '#dcfce7' : eq.status === 'in_repair' ? '#fef9c3' : '#f1f5f9',
                    color: eq.status === 'active' ? '#166534' : eq.status === 'in_repair' ? '#854d0e' : '#475569',
                  }}>
                    {EQUIPMENT_STATUS_LABELS[eq.status] ?? eq.status}
                  </span>
                </span>
              </li>
              <li>
                <span className="info-list-label">Модель</span>
                <span className="info-list-value">{eq.model?.name ?? '—'}</span>
              </li>
              <li>
                <span className="info-list-label">Серийный №</span>
                <span className="info-list-value" style={{ fontFamily: 'monospace' }}>
                  {eq.serial_number}
                </span>
              </li>
              <li>
                <span className="info-list-label">Клиент</span>
                <span
                  className="info-list-value"
                  style={{ color: 'var(--primary)', cursor: 'pointer' }}
                  onClick={() => navigate(`/clients/${eq.client_id}`)}
                >
                  {eq.client?.name ?? `id=${eq.client_id}`}
                </span>
              </li>
              <li>
                <span className="info-list-label">Адрес установки</span>
                <span className="info-list-value">{eq.location ?? eq.address ?? '—'}</span>
              </li>
              <li>
                <span className="info-list-label">Версия прошивки</span>
                <span className="info-list-value" style={{ fontFamily: 'monospace' }}>
                  {eq.firmware_version ?? '—'}
                </span>
              </li>
              <li>
                <span className="info-list-label">Примечания</span>
                <span className="info-list-value">{eq.notes ?? '—'}</span>
              </li>
            </ul>
          </div>
        </div>

        {/* Right card — даты и гарантия */}
        <div className="card">
          <div className="card-header" style={{ fontWeight: 600, fontSize: 14 }}>
            Гарантия и даты
          </div>
          <div className="card-body">
            <ul className="info-list">
              <li>
                <span className="info-list-label">Гар. статус</span>
                <span className="info-list-value">
                  <span className="badge" style={{ background: wsColors.bg, color: wsColors.color }}>
                    {WARRANTY_STATUS_LABELS[ws]}
                  </span>
                </span>
              </li>
              <li>
                <span className="info-list-label">Начало гарантии</span>
                <span className="info-list-value">{fmtDate(eq.warranty_start)}</span>
              </li>
              <li>
                <span className="info-list-label">Конец гарантии</span>
                <span className="info-list-value">
                  {fmtDate(eq.warranty_end ?? eq.warranty_until)}
                </span>
              </li>
              <li>
                <span className="info-list-label">Дата производства</span>
                <span className="info-list-value">{fmtDate(eq.manufacture_date)}</span>
              </li>
              <li>
                <span className="info-list-label">Дата продажи</span>
                <span className="info-list-value">{fmtDate(eq.sale_date)}</span>
              </li>
              <li>
                <span className="info-list-label">Дата установки</span>
                <span className="info-list-value">
                  {fmtDate(eq.installed_at ?? eq.installation_date)}
                </span>
              </li>
              <li>
                <span className="info-list-label">В системе с</span>
                <span className="info-list-value">{fmtDate(eq.created_at)}</span>
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* Tickets */}
      <div style={{ maxWidth: 900, marginTop: 16 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 10 }}>
          Заявки{tickets && tickets.length > 0 ? ` (${tickets.length})` : ''}
        </h2>
        <div className="table-wrap">
          <table className="table table-hover">
            <thead>
              <tr>
                <th>#</th>
                <th>Заголовок</th>
                <th>Приоритет</th>
                <th>Статус</th>
                <th>Инженер</th>
                <th>Создана</th>
              </tr>
            </thead>
            <tbody>
              {(!tickets || tickets.length === 0) && (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
                    Заявок по этому оборудованию нет
                  </td>
                </tr>
              )}
              {tickets
                ?.slice()
                .sort((a, b) => a.created_at.localeCompare(b.created_at))
                .map(t => (
                  <tr
                    key={t.id}
                    style={{ cursor: 'pointer' }}
                    onClick={() => navigate(`/tickets/${t.id}`)}
                  >
                    <td style={{ color: 'var(--text-muted)', fontSize: 12, whiteSpace: 'nowrap' }}>
                      {t.number}
                    </td>
                    <td style={{ fontWeight: 500 }}>{t.title}</td>
                    <td><PriorityBadge priority={t.priority} /></td>
                    <td><StatusBadge status={t.status} /></td>
                    <td style={{ color: 'var(--text-muted)', fontSize: 13 }}>
                      {t.engineer?.full_name ?? '—'}
                    </td>
                    <td style={{ whiteSpace: 'nowrap', fontSize: 13 }}>
                      {format(parseISO(t.created_at), 'dd.MM.yyyy', { locale: ru })}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Maintenance Schedule */}
      <div style={{ maxWidth: 900, marginTop: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <h2 style={{ fontSize: 16, fontWeight: 600 }}>График планового ТО</h2>
          {hasRole('admin', 'svc_mgr') && !schedule && (
            <button className="btn btn-primary btn-sm" onClick={() => setShowMaintForm(true)}>
              Создать график
            </button>
          )}
        </div>

        {schedule ? (
          <div className="card" style={{ maxWidth: 500 }}>
            <ul className="info-list">
              <li>
                <span className="info-list-label">Периодичность</span>
                <span className="info-list-value">
                  {{ monthly: 'Ежемесячно', quarterly: 'Ежеквартально', semiannual: 'Раз в полгода', annual: 'Ежегодно' }[schedule.frequency] ?? schedule.frequency}
                </span>
              </li>
              <li>
                <span className="info-list-label">Первая дата</span>
                <span className="info-list-value">{schedule.first_date}</span>
              </li>
              <li>
                <span className="info-list-label">Следующее ТО</span>
                <span className="info-list-value" style={{ fontWeight: 600 }}>{schedule.next_date}</span>
              </li>
              <li>
                <span className="info-list-label">Статус</span>
                <span className="info-list-value">
                  <span className={`badge ${schedule.is_active ? 'badge-success' : 'badge-secondary'}`}>
                    {schedule.is_active ? 'Активен' : 'Приостановлен'}
                  </span>
                </span>
              </li>
            </ul>
            {hasRole('admin', 'svc_mgr') && (
              <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => {
                    setMaintFreq(schedule.frequency)
                    setMaintNextDate(schedule.next_date)
                    setShowMaintForm(true)
                  }}
                >
                  Изменить
                </button>
                <button
                  className={`btn btn-sm ${schedule.is_active ? 'btn-warning' : 'btn-success'}`}
                  onClick={() => updateSchedule.mutate({ is_active: !schedule.is_active })}
                >
                  {schedule.is_active ? 'Приостановить' : 'Возобновить'}
                </button>
              </div>
            )}
          </div>
        ) : (
          <div style={{ color: 'var(--text-muted)', fontSize: 14 }}>
            График ТО не настроен
          </div>
        )}
      </div>

      {/* Maintenance modal */}
      {showMaintForm && (
        <div className="modal-overlay" onClick={() => setShowMaintForm(false)}>
          <div className="modal" style={{ maxWidth: 440, width: '100%' }} onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{schedule ? 'Изменить график ТО' : 'Создать график ТО'}</h2>
              <button className="btn-icon" onClick={() => setShowMaintForm(false)}>✕</button>
            </div>
            <div className="modal-body" style={{ display: 'grid', gap: 14 }}>
              {maintError && <div className="alert alert-error">{maintError}</div>}
              <div className="form-group">
                <label className="form-label">Периодичность *</label>
                <select className="form-select" value={maintFreq} onChange={e => setMaintFreq(e.target.value as MaintenanceFrequency)}>
                  <option value="monthly">Ежемесячно</option>
                  <option value="quarterly">Ежеквартально</option>
                  <option value="semiannual">Раз в полгода</option>
                  <option value="annual">Ежегодно</option>
                </select>
              </div>
              {!schedule && (
                <div className="form-group">
                  <label className="form-label">Дата первого ТО *</label>
                  <input
                    type="date"
                    className="form-control"
                    value={maintFirstDate}
                    onChange={e => setMaintFirstDate(e.target.value)}
                  />
                </div>
              )}
              {schedule && (
                <div className="form-group">
                  <label className="form-label">Следующее ТО</label>
                  <input
                    type="date"
                    className="form-control"
                    value={maintNextDate}
                    onChange={e => setMaintNextDate(e.target.value)}
                  />
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setShowMaintForm(false)}>Отмена</button>
              <button
                className="btn btn-primary"
                disabled={createSchedule.isPending || updateSchedule.isPending}
                onClick={() => {
                  setMaintError('')
                  if (schedule) {
                    const upd: { frequency?: MaintenanceFrequency; next_date?: string } = { frequency: maintFreq }
                    if (maintNextDate) upd.next_date = maintNextDate
                    updateSchedule.mutate(upd, {
                      onSuccess: () => setShowMaintForm(false),
                      onError: () => setMaintError('Ошибка сохранения'),
                    })
                  } else {
                    if (!maintFirstDate) { setMaintError('Укажите дату первого ТО'); return }
                    createSchedule.mutate({ frequency: maintFreq, first_date: maintFirstDate }, {
                      onSuccess: () => setShowMaintForm(false),
                      onError: () => setMaintError('Ошибка создания графика'),
                    })
                  }
                }}
              >
                {schedule ? 'Сохранить' : 'Создать'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit modal */}
      {showEdit && (
        <div className="modal-overlay" onClick={() => setShowEdit(false)}>
          <div
            className="modal"
            style={{ maxWidth: 640, width: '100%' }}
            onClick={e => e.stopPropagation()}
          >
            <div className="modal-header">
              <h2>Редактировать паспорт</h2>
              <button className="btn-icon" onClick={() => setShowEdit(false)}>✕</button>
            </div>
            <form onSubmit={handleSubmit(onSubmit)}>
              <div className="modal-body" style={{ display: 'grid', gap: 12 }}>
                {formError && <div className="alert alert-error">{formError}</div>}

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
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

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
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

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <div className="form-group">
                    <label className="form-label">Дата производства</label>
                    <input type="date" className="form-input" {...register('manufacture_date')} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Дата продажи</label>
                    <input type="date" className="form-input" {...register('sale_date')} />
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <div className="form-group">
                    <label className="form-label">Дата установки</label>
                    <input type="date" className="form-input" {...register('installed_at')} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Версия прошивки</label>
                    <input className="form-input" placeholder="v1.0.0" {...register('firmware_version')} />
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
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
                <button type="button" className="btn btn-secondary" onClick={() => setShowEdit(false)}>
                  Отмена
                </button>
                <button type="submit" className="btn btn-primary" disabled={updateMutation.isPending}>
                  {updateMutation.isPending ? <span className="spinner" /> : 'Сохранить'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      <div style={{ marginTop: 24 }}>
        <button className="btn btn-secondary btn-sm" onClick={() => navigate(-1)}>
          ← Назад
        </button>
      </div>
    </>
  )
}
