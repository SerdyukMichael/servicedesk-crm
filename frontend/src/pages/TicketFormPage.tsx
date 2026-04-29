import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useCreateTicket, useWorkTemplates } from '../hooks/useTickets'
import { useClients } from '../hooks/useClients'
import { useClientEquipment, useEquipment, useEquipmentLookup } from '../hooks/useEquipment'
import { useAuth } from '../context/AuthContext'
import type { AxiosError } from 'axios'

const schema = z.object({
  title: z.string().min(3, 'Заголовок должен содержать минимум 3 символа'),
  client_id: z.coerce.number().min(1, 'Выберите клиента'),
  equipment_id: z.coerce.number().optional(),
  type: z.enum(['repair', 'maintenance', 'installation', 'consultation', 'other']),
  priority: z.enum(['critical', 'high', 'medium', 'low']),
  description: z.string().optional(),
  work_template_id: z.coerce.number().optional(),
})

type FormData = z.infer<typeof schema>

export default function TicketFormPage() {
  const navigate = useNavigate()
  const { hasRole } = useAuth()
  const isClientUser = hasRole('client_user')

  const createTicket = useCreateTicket()
  const { data: clientsData } = useClients({ size: 200 })
  const { data: templates } = useWorkTemplates()

  const [selectedClientId, setSelectedClientId] = useState<number>(0)
  const [serialInput, setSerialInput] = useState('')
  const [debouncedSerial, setDebouncedSerial] = useState('')
  const [serialLocked, setSerialLocked] = useState(false)
  const [serialError, setSerialError] = useState<string | null>(null)

  const { data: clientEquipmentData } = useClientEquipment(selectedClientId)
  // client_user: get own equipment via GET /equipment (backend filters by org)
  const { data: ownEquipmentData } = useEquipment(isClientUser ? { size: 200 } : undefined)

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      type: 'repair',
      priority: 'medium',
    },
  })

  const watchedClientId = watch('client_id')

  // Sync client selector → equipment list
  useEffect(() => {
    if (isClientUser) return
    const cid = Number(watchedClientId)
    if (cid !== selectedClientId) {
      setSelectedClientId(cid)
      if (!serialLocked) {
        setValue('equipment_id', undefined)
      }
    }
  }, [watchedClientId, selectedClientId, setValue, serialLocked, isClientUser])

  // Debounce serial input (400ms)
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSerial(serialInput)
    }, 400)
    return () => clearTimeout(timer)
  }, [serialInput])

  const {
    data: lookupResult,
    error: lookupError,
    isFetching: lookupFetching,
    isSuccess: lookupSuccess,
    isError: lookupIsError,
  } = useEquipmentLookup(debouncedSerial)

  const clients = clientsData?.items ?? []
  const equipment = isClientUser
    ? (ownEquipmentData?.items ?? [])
    : (clientEquipmentData ?? [])

  // Apply lookup result
  useEffect(() => {
    if (!lookupSuccess || !lookupResult) return

    setSerialError(null)
    setValue('equipment_id', lookupResult.equipment_id)

    if (!isClientUser) {
      setValue('client_id', lookupResult.client_id)
      setSelectedClientId(lookupResult.client_id)
    }

    // Set type to repair only if not already changed by user
    setValue('type', 'repair')
    setSerialLocked(true)
  }, [lookupSuccess, lookupResult, setValue, isClientUser])

  // Re-apply equipment_id after options load (timing: setValue fires before options render)
  useEffect(() => {
    if (serialLocked && lookupResult && equipment.length > 0) {
      setValue('equipment_id', lookupResult.equipment_id)
    }
  }, [equipment, serialLocked, lookupResult, setValue])

  // Handle lookup error
  useEffect(() => {
    if (!lookupIsError || !debouncedSerial || debouncedSerial.length < 3) {
      if (!debouncedSerial) setSerialError(null)
      return
    }
    const err = lookupError as AxiosError<{ error: string; message: string }>
    const httpStatus = err?.response?.status
    if (httpStatus === 404) {
      setSerialError(`Оборудование с серийным номером «${debouncedSerial}» не найдено`)
    } else if (httpStatus === 403) {
      setSerialError('Данное оборудование не принадлежит вашей организации')
    } else {
      setSerialError('Ошибка поиска оборудования')
    }
    setSerialLocked(false)
  }, [lookupIsError, lookupError, debouncedSerial])

  const handleSerialChange = (value: string) => {
    setSerialInput(value)
    if (!value.trim()) {
      setDebouncedSerial('')
      setSerialError(null)
      setSerialLocked(false)
      setValue('equipment_id', undefined)
      if (!isClientUser) {
        setValue('client_id', 0 as unknown as number)
        setSelectedClientId(0)
      }
    }
  }

  const onSubmit = async (data: FormData) => {
    const payload: Record<string, unknown> = { ...data }
    if (!payload.equipment_id) delete payload.equipment_id
    if (!payload.work_template_id) delete payload.work_template_id
    if (!payload.description) delete payload.description

    try {
      const ticket = await createTicket.mutateAsync(payload)
      navigate(`/tickets/${ticket.id}`)
    } catch {
      // error displayed via mutation state
    }
  }

  return (
    <>
      <div className="page-header">
        <div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>
            <span style={{ cursor: 'pointer' }} onClick={() => navigate('/tickets')}>
              Заявки
            </span>{' '}
            / Новая заявка
          </div>
          <h1>Создать заявку</h1>
        </div>
      </div>

      {createTicket.isError && (
        <div className="alert alert-error">Ошибка при создании заявки</div>
      )}

      <div className="card" style={{ maxWidth: 700 }}>
        <div className="card-body">
          <form onSubmit={handleSubmit(onSubmit)} noValidate>
            <div className="form-group">
              <label className="form-label">
                Заголовок <span className="required">*</span>
              </label>
              <input
                type="text"
                className={`form-input${errors.title ? ' error' : ''}`}
                placeholder="Краткое описание проблемы"
                {...register('title')}
              />
              {errors.title && (
                <span className="form-error">{errors.title.message}</span>
              )}
            </div>

            {/* Serial number lookup */}
            <div className="form-group">
              <label className="form-label">Серийный номер</label>
              <div style={{ position: 'relative' }}>
                <input
                  type="text"
                  className={`form-input${serialError ? ' error' : ''}`}
                  placeholder="Введите серийный номер для автозаполнения..."
                  value={serialInput}
                  onChange={e => handleSerialChange(e.target.value)}
                />
                {lookupFetching && debouncedSerial.length >= 3 && (
                  <span style={{
                    position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
                    fontSize: 12, color: 'var(--text-muted)',
                  }}>
                    Поиск...
                  </span>
                )}
                {serialLocked && (
                  <span style={{
                    position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
                    fontSize: 14, color: 'var(--color-success)',
                  }} title="Поля определены по серийному номеру">
                    ✓
                  </span>
                )}
              </div>
              {serialError && <span className="form-error">{serialError}</span>}
              {!serialError && serialLocked && lookupResult && (
                <span style={{ fontSize: 12, color: 'var(--color-success)', marginTop: 4, display: 'block' }}>
                  Клиент и оборудование определены автоматически
                </span>
              )}
            </div>

            <div className="form-row">
              {/* Client selector — hidden for client_user */}
              {!isClientUser && (
                <div className="form-group">
                  <label className="form-label">
                    Клиент <span className="required">*</span>
                  </label>
                  <div style={{ position: 'relative' }}>
                    <select
                      className={`form-select${errors.client_id ? ' error' : ''}`}
                      disabled={serialLocked}
                      {...register('client_id')}
                    >
                      <option value="">— Выберите клиента —</option>
                      {clients.map(c => (
                        <option key={c.id} value={c.id}>
                          {c.name}
                        </option>
                      ))}
                    </select>
                    {serialLocked && (
                      <span style={{
                        position: 'absolute', right: 32, top: '50%', transform: 'translateY(-50%)',
                        fontSize: 11, color: 'var(--text-muted)',
                      }} title="Определено по серийному номеру">
                        🔒
                      </span>
                    )}
                  </div>
                  {errors.client_id && (
                    <span className="form-error">{errors.client_id.message}</span>
                  )}
                  {serialLocked && lookupResult && (
                    <span style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2, display: 'block' }}>
                      {lookupResult.client_name}
                    </span>
                  )}
                </div>
              )}

              <div className="form-group">
                <label className="form-label">Оборудование</label>
                <div style={{ position: 'relative' }}>
                  <select
                    className="form-select"
                    disabled={serialLocked || (!isClientUser && !selectedClientId)}
                    {...register('equipment_id')}
                  >
                    <option value="">— Не указано —</option>
                    {equipment.map(eq => (
                      <option key={eq.id} value={eq.id}>
                        {eq.model?.name ?? 'Без модели'} (s/n: {eq.serial_number})
                      </option>
                    ))}
                  </select>
                  {serialLocked && (
                    <span style={{
                      position: 'absolute', right: 32, top: '50%', transform: 'translateY(-50%)',
                      fontSize: 11, color: 'var(--text-muted)',
                    }} title="Определено по серийному номеру">
                      🔒
                    </span>
                  )}
                </div>
                {serialLocked && lookupResult && (
                  <span style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2, display: 'block' }}>
                    {lookupResult.model_name}
                    {lookupResult.is_under_warranty && (
                      <span style={{ marginLeft: 6, color: 'var(--color-success)' }}>• На гарантии</span>
                    )}
                  </span>
                )}
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label className="form-label">
                  Тип <span className="required">*</span>
                </label>
                <select className="form-select" {...register('type')}>
                  <option value="repair">Ремонт</option>
                  <option value="maintenance">ТО</option>
                  <option value="installation">Установка</option>
                  <option value="consultation">Консультация</option>
                  <option value="other">Прочее</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">
                  Приоритет <span className="required">*</span>
                </label>
                <select className="form-select" {...register('priority')}>
                  <option value="critical">Критический</option>
                  <option value="high">Высокий</option>
                  <option value="medium">Средний</option>
                  <option value="low">Низкий</option>
                </select>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Шаблон работ</label>
              <select className="form-select" {...register('work_template_id')}>
                <option value="">— Без шаблона —</option>
                {templates?.map(t => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Описание</label>
              <textarea
                className="form-textarea"
                rows={5}
                placeholder="Подробное описание проблемы или задачи..."
                {...register('description')}
              />
            </div>

            <div className="form-actions">
              <button
                type="submit"
                className="btn btn-primary"
                disabled={isSubmitting || createTicket.isPending}
              >
                {isSubmitting || createTicket.isPending ? 'Создание...' : 'Создать заявку'}
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => navigate('/tickets')}
              >
                Отмена
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  )
}
