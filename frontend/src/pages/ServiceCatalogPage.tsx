import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { useCurrency } from '../context/CurrencyContext'
import {
  useServiceCatalog,
  useCreateServiceCatalogItem,
  useUpdateServiceCatalogItem,
  useDeleteServiceCatalogItem,
} from '../hooks/useServiceCatalog'
import Pagination from '../components/Pagination'
import type { ServiceCatalogItem, ServiceCategory, ServiceUnit } from '../api/types'

const CATEGORY_LABELS: Record<ServiceCategory, string> = {
  repair: 'Ремонт',
  maintenance: 'ТО',
  diagnostics: 'Диагностика',
  visit: 'Выезд',
  other: 'Прочее',
}

const UNIT_LABELS: Record<ServiceUnit, string> = {
  pcs: 'шт',
  hour: 'час',
  visit: 'визит',
  kit: 'комплект',
}

interface FormState {
  code: string
  name: string
  description: string
  category: ServiceCategory
  unit: ServiceUnit
  unit_price: string
}

const EMPTY_FORM: FormState = {
  code: '',
  name: '',
  description: '',
  category: 'repair',
  unit: 'pcs',
  unit_price: '',
}

export default function ServiceCatalogPage() {
  const { hasRole } = useAuth()
  const { currency } = useCurrency()
  const canWrite = hasRole('admin', 'svc_mgr')

  const [page, setPage] = useState(1)
  const [category, setCategory] = useState('')
  const [includeInactive, setIncludeInactive] = useState(false)

  const [showForm, setShowForm] = useState(false)
  const [editItem, setEditItem] = useState<ServiceCatalogItem | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [formError, setFormError] = useState<string | null>(null)

  const [deleteId, setDeleteId] = useState<number | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const params: Record<string, unknown> = { page, size: 20 }
  if (category) params.category = category
  if (includeInactive) params.include_inactive = true

  const { data, isLoading, isError } = useServiceCatalog(params)
  const createItem = useCreateServiceCatalogItem()
  const updateItem = useUpdateServiceCatalogItem()
  const deleteItem = useDeleteServiceCatalogItem()

  const openCreate = () => {
    setEditItem(null)
    setForm(EMPTY_FORM)
    setFormError(null)
    setShowForm(true)
  }

  const openEdit = (item: ServiceCatalogItem) => {
    setEditItem(item)
    setForm({
      code: item.code,
      name: item.name,
      description: item.description ?? '',
      category: item.category,
      unit: item.unit,
      unit_price: item.unit_price,
    })
    setFormError(null)
    setShowForm(true)
  }

  const handleSave = () => {
    if (!form.code.trim() || !form.name.trim() || !form.unit_price) {
      setFormError('Заполните обязательные поля: код, название, цена')
      return
    }
    setFormError(null)

    if (editItem) {
      updateItem.mutate(
        { id: editItem.id, data: form },
        { onSuccess: () => setShowForm(false) }
      )
    } else {
      createItem.mutate(form, {
        onSuccess: () => {
          setShowForm(false)
          setForm(EMPTY_FORM)
        },
        onError: (err: unknown) => {
          const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
          setFormError(msg ?? 'Ошибка создания')
        },
      })
    }
  }

  const handleToggleActive = (item: ServiceCatalogItem) => {
    updateItem.mutate({ id: item.id, data: { is_active: !item.is_active } })
  }

  const handleDelete = () => {
    if (!deleteId) return
    setDeleteError(null)
    deleteItem.mutate(deleteId, {
      onSuccess: () => setDeleteId(null),
      onError: (err: unknown) => {
        const detail = (err as { response?: { data?: { detail?: { message?: string } | string } } })
          ?.response?.data?.detail
        const msg = typeof detail === 'object' ? detail?.message : detail
        setDeleteError(msg ?? 'Удаление невозможно')
      },
    })
  }

  return (
    <>
      <div className="page-header">
        <h1>Прайс-лист услуг</h1>
        {canWrite && (
          <button className="btn btn-primary btn-sm" onClick={openCreate}>
            + Добавить услугу
          </button>
        )}
      </div>

      <div className="filters-bar">
        <select
          className="form-select"
          value={category}
          onChange={e => { setCategory(e.target.value); setPage(1) }}
        >
          <option value="">Все категории</option>
          {(Object.keys(CATEGORY_LABELS) as ServiceCategory[]).map(c => (
            <option key={c} value={c}>{CATEGORY_LABELS[c]}</option>
          ))}
        </select>
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={includeInactive}
            onChange={e => { setIncludeInactive(e.target.checked); setPage(1) }}
          />
          Показать неактивные
        </label>
      </div>

      {isLoading && (
        <div className="loading-center"><span className="spinner spinner-lg" /></div>
      )}
      {isError && (
        <div className="alert alert-error">Ошибка загрузки прайс-листа</div>
      )}

      {data && (
        <>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Код</th>
                  <th>Название</th>
                  <th>Категория</th>
                  <th>Ед. изм.</th>
                  <th>Цена</th>
                  <th>Статус</th>
                  {canWrite && <th></th>}
                </tr>
              </thead>
              <tbody>
                {data.items.length === 0 && (
                  <tr>
                    <td colSpan={canWrite ? 7 : 6} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                      Услуги не найдены
                    </td>
                  </tr>
                )}
                {data.items.map(item => (
                  <tr key={item.id} style={{ opacity: item.is_active ? 1 : 0.5 }}>
                    <td>
                      <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{item.code}</span>
                    </td>
                    <td style={{ fontWeight: 500 }}>
                      {item.name}
                      {item.description && (
                        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                          {item.description}
                        </div>
                      )}
                    </td>
                    <td>{CATEGORY_LABELS[item.category]}</td>
                    <td>{UNIT_LABELS[item.unit]}</td>
                    <td style={{ fontWeight: 600 }}>{parseFloat(item.unit_price).toLocaleString('ru-RU')} {currency.currency_code}</td>
                    <td>
                      {item.is_active ? (
                        <span className="badge badge-completed">Активна</span>
                      ) : (
                        <span className="badge badge-cancelled">Неактивна</span>
                      )}
                    </td>
                    {canWrite && (
                      <td>
                        <div style={{ display: 'flex', gap: 6 }}>
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => openEdit(item)}
                          >
                            Изменить
                          </button>
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => handleToggleActive(item)}
                            title={item.is_active ? 'Деактивировать' : 'Активировать'}
                          >
                            {item.is_active ? 'Откл.' : 'Вкл.'}
                          </button>
                          <button
                            className="btn btn-danger btn-sm"
                            onClick={() => { setDeleteId(item.id); setDeleteError(null) }}
                          >
                            Удалить
                          </button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
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

      {/* Create/Edit modal */}
      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 520 }}>
            <div className="modal-header">
              <h3>{editItem ? 'Изменить услугу' : 'Добавить услугу'}</h3>
              <button className="modal-close" onClick={() => setShowForm(false)}>×</button>
            </div>
            <div className="modal-body">
              {formError && <div className="alert alert-error" style={{ marginBottom: 12 }}>{formError}</div>}
              <div className="form-group">
                <label className="form-label">Код *</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="Например: SRV-DIAG-001"
                  value={form.code}
                  onChange={e => setForm(f => ({ ...f, code: e.target.value }))}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Название *</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="Название услуги"
                  value={form.name}
                  onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Описание</label>
                <textarea
                  className="form-textarea"
                  placeholder="Краткое описание (необязательно)"
                  value={form.description}
                  rows={2}
                  onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div className="form-group">
                  <label className="form-label">Категория</label>
                  <select
                    className="form-select"
                    value={form.category}
                    onChange={e => setForm(f => ({ ...f, category: e.target.value as ServiceCategory }))}
                  >
                    {(Object.entries(CATEGORY_LABELS) as [ServiceCategory, string][]).map(([k, v]) => (
                      <option key={k} value={k}>{v}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Ед. измерения</label>
                  <select
                    className="form-select"
                    value={form.unit}
                    onChange={e => setForm(f => ({ ...f, unit: e.target.value as ServiceUnit }))}
                  >
                    {(Object.entries(UNIT_LABELS) as [ServiceUnit, string][]).map(([k, v]) => (
                      <option key={k} value={k}>{v}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="form-group">
                <label className="form-label">Цена ({currency.currency_code}) *</label>
                <input
                  type="number"
                  className="form-input"
                  placeholder="0.00"
                  step="0.01"
                  min="0"
                  value={form.unit_price}
                  onChange={e => setForm(f => ({ ...f, unit_price: e.target.value }))}
                />
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setShowForm(false)}>Отмена</button>
              <button
                className="btn btn-primary"
                onClick={handleSave}
                disabled={createItem.isPending || updateItem.isPending}
              >
                {createItem.isPending || updateItem.isPending ? 'Сохранение...' : 'Сохранить'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete confirm modal */}
      {deleteId && (
        <div className="modal-overlay" onClick={() => setDeleteId(null)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 400 }}>
            <div className="modal-header">
              <h3>Удалить услугу?</h3>
              <button className="modal-close" onClick={() => setDeleteId(null)}>×</button>
            </div>
            <div className="modal-body">
              {deleteError && <div className="alert alert-error">{deleteError}</div>}
              {!deleteError && (
                <p style={{ fontSize: 14 }}>Услуга будет удалена безвозвратно. Продолжить?</p>
              )}
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setDeleteId(null)}>Отмена</button>
              {!deleteError && (
                <button
                  className="btn btn-danger"
                  onClick={handleDelete}
                  disabled={deleteItem.isPending}
                >
                  {deleteItem.isPending ? 'Удаление...' : 'Удалить'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  )
}
