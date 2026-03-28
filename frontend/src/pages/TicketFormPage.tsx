import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useCreateTicket, useWorkTemplates } from '../hooks/useTickets'
import { useClients } from '../hooks/useClients'
import { useClientEquipment } from '../hooks/useEquipment'

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
  const createTicket = useCreateTicket()
  const { data: clientsData } = useClients({ size: 200 })
  const { data: templates } = useWorkTemplates()

  const [selectedClientId, setSelectedClientId] = useState<number>(0)
  const { data: clientEquipment } = useClientEquipment(selectedClientId)

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

  useEffect(() => {
    const cid = Number(watchedClientId)
    if (cid !== selectedClientId) {
      setSelectedClientId(cid)
      setValue('equipment_id', undefined)
    }
  }, [watchedClientId, selectedClientId, setValue])

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

  const clients = clientsData?.items ?? []
  const equipment = clientEquipment ?? []

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

            <div className="form-row">
              <div className="form-group">
                <label className="form-label">
                  Клиент <span className="required">*</span>
                </label>
                <select
                  className={`form-select${errors.client_id ? ' error' : ''}`}
                  {...register('client_id')}
                >
                  <option value="">— Выберите клиента —</option>
                  {clients.map(c => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
                {errors.client_id && (
                  <span className="form-error">{errors.client_id.message}</span>
                )}
              </div>

              <div className="form-group">
                <label className="form-label">Оборудование</label>
                <select
                  className="form-select"
                  {...register('equipment_id')}
                  disabled={!selectedClientId}
                >
                  <option value="">— Не указано —</option>
                  {equipment.map(eq => (
                    <option key={eq.id} value={eq.id}>
                      {eq.model?.name ?? 'Без модели'} (s/n: {eq.serial_number})
                    </option>
                  ))}
                </select>
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
