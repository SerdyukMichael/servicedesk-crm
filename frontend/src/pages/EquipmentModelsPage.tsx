import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  useEquipmentModels,
  useCreateEquipmentModel,
  useUpdateEquipmentModel,
  useDeactivateEquipmentModel,
  useActivateEquipmentModel,
} from '../hooks/useEquipment'
import { useAuth } from '../context/AuthContext'
import type { EquipmentModel } from '../api/types'

const CATEGORY_LABELS: Record<string, string> = {
  atm: 'Банкомат',
  card_printer: 'Карт-принтер',
  pos_terminal: 'POS-терминал',
  other: 'Прочее',
}

const modelSchema = z.object({
  name: z.string().min(1, 'Введите наименование'),
  manufacturer: z.preprocess(v => (v === '' ? undefined : v), z.string().optional()),
  category: z.string().min(1, 'Выберите категорию'),
  description: z.preprocess(v => (v === '' ? undefined : v), z.string().optional()),
  warranty_months_default: z.preprocess(
    v => (v === '' || v === null ? undefined : Number(v)),
    z.number().int().min(1).optional(),
  ),
})

type FormData = z.infer<typeof modelSchema>

export default function EquipmentModelsPage() {
  const { hasRole } = useAuth()
  const canWrite = hasRole('admin', 'svc_mgr')

  const [showInactive, setShowInactive] = useState(false)
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState<EquipmentModel | null>(null)

  const { data: models = [], isLoading, isError } = useEquipmentModels(showInactive)
  const createModel = useCreateEquipmentModel()
  const deactivate = useDeactivateEquipmentModel()
  const activate = useActivateEquipmentModel()

  const updateModel = useUpdateEquipmentModel(editing?.id ?? 0)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(modelSchema) })

  function openCreate() {
    setEditing(null)
    reset({ name: '', manufacturer: '', category: 'atm', description: '', warranty_months_default: undefined })
    setShowModal(true)
  }

  function openEdit(m: EquipmentModel) {
    setEditing(m)
    reset({
      name: m.name,
      manufacturer: m.manufacturer ?? '',
      category: m.category ?? 'other',
      description: m.description ?? '',
      warranty_months_default: m.warranty_months_default ?? undefined,
    })
    setShowModal(true)
  }

  function closeModal() {
    setShowModal(false)
    setEditing(null)
    reset()
  }

  const onSubmit = async (data: FormData) => {
    const payload = {
      ...data,
      warranty_months_default: data.warranty_months_default ?? undefined,
    }
    if (editing) {
      await updateModel.mutateAsync(payload)
    } else {
      await createModel.mutateAsync(payload)
    }
    closeModal()
  }

  const handleDeactivate = async (m: EquipmentModel) => {
    if (window.confirm(`Деактивировать модель «${m.name}»?`)) {
      await deactivate.mutateAsync(m.id)
    }
  }

  const handleActivate = async (m: EquipmentModel) => {
    await activate.mutateAsync(m.id)
  }

  const isPending = createModel.isPending || updateModel.isPending
  const mutationError = createModel.error || updateModel.error

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Справочник моделей оборудования</h1>
          <p className="page-subtitle">
            {models.length} {showInactive ? 'всего' : 'активных'} моделей
          </p>
        </div>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 14 }}>
            <input
              type="checkbox"
              checked={showInactive}
              onChange={e => setShowInactive(e.target.checked)}
            />
            Показать деактивированные
          </label>
          {canWrite && (
            <button className="btn btn-primary" onClick={openCreate}>
              + Добавить модель
            </button>
          )}
        </div>
      </div>

      {isLoading && <div className="loading-state">Загрузка...</div>}
      {isError && <div className="error-state">Ошибка загрузки данных</div>}

      {!isLoading && !isError && (
        <div className="card" style={{ padding: 0 }}>
          <table className="table">
            <thead>
              <tr>
                <th>Наименование</th>
                <th>Производитель</th>
                <th>Категория</th>
                <th>Гарантия (мес.)</th>
                <th>Статус</th>
                {canWrite && <th style={{ width: 160 }}>Действия</th>}
              </tr>
            </thead>
            <tbody>
              {models.length === 0 ? (
                <tr>
                  <td colSpan={canWrite ? 6 : 5} style={{ textAlign: 'center', padding: '32px 0', color: 'var(--text-secondary)' }}>
                    Модели не найдены
                  </td>
                </tr>
              ) : (
                models.map(m => (
                  <tr key={m.id} style={{ opacity: m.is_active ? 1 : 0.55 }}>
                    <td><strong>{m.name}</strong></td>
                    <td>{m.manufacturer ?? '—'}</td>
                    <td>{CATEGORY_LABELS[m.category ?? 'other'] ?? m.category}</td>
                    <td>{m.warranty_months_default ?? '—'}</td>
                    <td>
                      <span className={`badge ${m.is_active ? 'badge-success' : 'badge-secondary'}`}>
                        {m.is_active ? 'Активна' : 'Деактивирована'}
                      </span>
                    </td>
                    {canWrite && (
                      <td>
                        <div style={{ display: 'flex', gap: 8 }}>
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => openEdit(m)}
                          >
                            Изменить
                          </button>
                          {m.is_active ? (
                            <button
                              className="btn btn-danger btn-sm"
                              onClick={() => handleDeactivate(m)}
                            >
                              Деактивировать
                            </button>
                          ) : (
                            <button
                              className="btn btn-secondary btn-sm"
                              onClick={() => handleActivate(m)}
                            >
                              Активировать
                            </button>
                          )}
                        </div>
                      </td>
                    )}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {showModal && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2 className="modal-title">
                {editing ? 'Редактировать модель' : 'Добавить модель'}
              </h2>
              <button className="modal-close" onClick={closeModal}>×</button>
            </div>

            <form onSubmit={handleSubmit(onSubmit)}>
              <div className="modal-body">
                {mutationError && (
                  <div className="alert alert-error" style={{ marginBottom: 16 }}>
                    {(mutationError as { response?: { data?: { message?: string } } })?.response?.data?.message
                      ?? 'Произошла ошибка. Попробуйте ещё раз.'}
                  </div>
                )}

                <div className="form-group">
                  <label className="form-label">Наименование *</label>
                  <input className="form-control" {...register('name')} />
                  {errors.name && <span className="form-error">{errors.name.message}</span>}
                </div>

                <div className="form-group">
                  <label className="form-label">Производитель</label>
                  <input className="form-control" {...register('manufacturer')} />
                </div>

                <div className="form-group">
                  <label className="form-label">Категория *</label>
                  <select className="form-control" {...register('category')}>
                    <option value="atm">Банкомат</option>
                    <option value="card_printer">Карт-принтер</option>
                    <option value="pos_terminal">POS-терминал</option>
                    <option value="other">Прочее</option>
                  </select>
                  {errors.category && <span className="form-error">{errors.category.message}</span>}
                </div>

                <div className="form-group">
                  <label className="form-label">Срок гарантии по умолчанию (мес.)</label>
                  <input
                    type="number"
                    min="1"
                    className="form-control"
                    {...register('warranty_months_default')}
                  />
                  {errors.warranty_months_default && (
                    <span className="form-error">{errors.warranty_months_default.message}</span>
                  )}
                </div>

                <div className="form-group">
                  <label className="form-label">Описание</label>
                  <textarea className="form-control" rows={3} {...register('description')} />
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={closeModal}>
                  Отмена
                </button>
                <button type="submit" className="btn btn-primary" disabled={isPending}>
                  {isPending ? 'Сохранение...' : 'Сохранить'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
