import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import {
  useProductCatalog,
  useCreateProductCatalogItem,
  useUpdateProductCatalogItem,
  useDeleteProductCatalogItem,
} from '../hooks/useProductCatalog'
import Pagination from '../components/Pagination'
import type { ProductCatalogItem, ProductCategory, ProductUnit } from '../api/types'

const CATEGORY_LABELS: Record<ProductCategory, string> = {
  spare_part: 'Запчасть',
  other: 'Прочее',
}

const UNIT_LABELS: Record<ProductUnit, string> = {
  pcs: 'шт',
  pack: 'упак',
  kit: 'комплект',
}

interface FormState {
  code: string
  name: string
  description: string
  category: ProductCategory
  unit: ProductUnit
  unit_price: string
}

const EMPTY_FORM: FormState = {
  code: '',
  name: '',
  description: '',
  category: 'spare_part',
  unit: 'pcs',
  unit_price: '',
}

export default function ProductCatalogPage() {
  const { hasRole } = useAuth()
  const canWrite = hasRole('admin', 'svc_mgr')

  const [page, setPage] = useState(1)
  const [category, setCategory] = useState('')
  const [includeInactive, setIncludeInactive] = useState(false)

  const [showForm, setShowForm] = useState(false)
  const [editItem, setEditItem] = useState<ProductCatalogItem | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [formError, setFormError] = useState<string | null>(null)

  const [deleteId, setDeleteId] = useState<number | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const { data, isLoading } = useProductCatalog({
    include_inactive: includeInactive || undefined,
    category: category || undefined,
    page,
    size: 20,
  })
  const createMut = useCreateProductCatalogItem()
  const updateMut = useUpdateProductCatalogItem()
  const deleteMut = useDeleteProductCatalogItem()

  function openCreate() {
    setEditItem(null)
    setForm(EMPTY_FORM)
    setFormError(null)
    setShowForm(true)
  }

  function openEdit(item: ProductCatalogItem) {
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

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setFormError(null)
    if (!form.code.trim() || !form.name.trim() || !form.unit_price) {
      setFormError('Заполните все обязательные поля')
      return
    }
    try {
      if (editItem) {
        await updateMut.mutateAsync({ id: editItem.id, data: { ...form } })
      } else {
        await createMut.mutateAsync({ ...form })
      }
      setShowForm(false)
    } catch (err: any) {
      const msg = err?.response?.data?.detail?.message ?? 'Ошибка сохранения'
      setFormError(msg)
    }
  }

  async function handleDeactivate(item: ProductCatalogItem) {
    await updateMut.mutateAsync({ id: item.id, data: { is_active: false } })
  }

  async function handleActivate(item: ProductCatalogItem) {
    await updateMut.mutateAsync({ id: item.id, data: { is_active: true } })
  }

  async function handleDelete() {
    if (!deleteId) return
    setDeleteError(null)
    try {
      await deleteMut.mutateAsync(deleteId)
      setDeleteId(null)
    } catch (err: any) {
      const msg = err?.response?.data?.detail?.message ?? 'Ошибка удаления'
      setDeleteError(msg)
    }
  }

  const items = data?.items ?? []
  const totalPages = data?.pages ?? 1
  const totalItems = data?.total ?? 0
  const pageSize = data?.size ?? 20

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Прайс-лист товаров</h1>
        {canWrite && (
          <button className="btn btn-primary" onClick={openCreate}>
            + Добавить товар
          </button>
        )}
      </div>

      {/* Filters */}
      <div className="filters-row" style={{ marginBottom: 16, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        <select
          value={category}
          onChange={e => { setCategory(e.target.value); setPage(1) }}
          className="form-select"
          style={{ width: 180 }}
        >
          <option value="">Все категории</option>
          {(Object.keys(CATEGORY_LABELS) as ProductCategory[]).map(c => (
            <option key={c} value={c}>{CATEGORY_LABELS[c]}</option>
          ))}
        </select>
        <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <input
            type="checkbox"
            checked={includeInactive}
            onChange={e => { setIncludeInactive(e.target.checked); setPage(1) }}
          />
          Показать неактивные
        </label>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="loading">Загрузка...</div>
      ) : items.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📦</div>
          <p>Товары не найдены</p>
          {canWrite && <button className="btn btn-primary" onClick={openCreate}>Добавить первый товар</button>}
        </div>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Код</th>
              <th>Наименование</th>
              <th>Категория</th>
              <th>Ед.</th>
              <th>Цена</th>
              <th>Валюта</th>
              <th>Статус</th>
              {canWrite && <th>Действия</th>}
            </tr>
          </thead>
          <tbody>
            {items.map(item => (
              <tr key={item.id} style={{ opacity: item.is_active ? 1 : 0.5 }}>
                <td><code>{item.code}</code></td>
                <td>{item.name}</td>
                <td>{CATEGORY_LABELS[item.category] ?? item.category}</td>
                <td>{UNIT_LABELS[item.unit] ?? item.unit}</td>
                <td style={{ textAlign: 'right' }}>{parseFloat(item.unit_price).toLocaleString('ru-RU')}</td>
                <td>{item.currency}</td>
                <td>
                  <span className={`badge ${item.is_active ? 'badge-success' : 'badge-secondary'}`}>
                    {item.is_active ? 'Активен' : 'Неактивен'}
                  </span>
                </td>
                {canWrite && (
                  <td>
                    <button className="btn btn-sm btn-secondary" onClick={() => openEdit(item)}>Изменить</button>
                    {item.is_active
                      ? <button className="btn btn-sm btn-warning" style={{ marginLeft: 4 }} onClick={() => handleDeactivate(item)}>Деактивировать</button>
                      : <button className="btn btn-sm btn-success" style={{ marginLeft: 4 }} onClick={() => handleActivate(item)}>Активировать</button>
                    }
                    <button className="btn btn-sm btn-danger" style={{ marginLeft: 4 }} onClick={() => { setDeleteId(item.id); setDeleteError(null) }}>Удалить</button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <Pagination page={page} pages={totalPages} total={totalItems} size={pageSize} onPageChange={setPage} />

      {/* Create/Edit Modal */}
      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{editItem ? 'Редактировать товар' : 'Добавить товар'}</h2>
              <button className="modal-close" onClick={() => setShowForm(false)}>✕</button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Код *</label>
                <input
                  className="form-input"
                  value={form.code}
                  onChange={e => setForm(f => ({ ...f, code: e.target.value }))}
                  placeholder="PROD-001"
                  disabled={!!editItem}
                />
              </div>
              <div className="form-group">
                <label>Наименование *</label>
                <input
                  className="form-input"
                  value={form.name}
                  onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  placeholder="Картридж для ATM"
                />
              </div>
              <div className="form-group">
                <label>Описание</label>
                <textarea
                  className="form-input"
                  rows={2}
                  value={form.description}
                  onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                />
              </div>
              <div className="form-group">
                <label>Категория *</label>
                <select
                  className="form-select"
                  value={form.category}
                  onChange={e => setForm(f => ({ ...f, category: e.target.value as ProductCategory }))}
                >
                  {(Object.keys(CATEGORY_LABELS) as ProductCategory[]).map(c => (
                    <option key={c} value={c}>{CATEGORY_LABELS[c]}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Единица измерения *</label>
                <select
                  className="form-select"
                  value={form.unit}
                  onChange={e => setForm(f => ({ ...f, unit: e.target.value as ProductUnit }))}
                >
                  {(Object.keys(UNIT_LABELS) as ProductUnit[]).map(u => (
                    <option key={u} value={u}>{UNIT_LABELS[u]}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Цена *</label>
                <input
                  className="form-input"
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.unit_price}
                  onChange={e => setForm(f => ({ ...f, unit_price: e.target.value }))}
                  placeholder="0.00"
                />
              </div>
              {formError && <div className="error-message">{formError}</div>}
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowForm(false)}>Отмена</button>
                <button type="submit" className="btn btn-primary" disabled={createMut.isPending || updateMut.isPending}>
                  {createMut.isPending || updateMut.isPending ? 'Сохранение...' : 'Сохранить'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirm Modal */}
      {deleteId !== null && (
        <div className="modal-overlay" onClick={() => setDeleteId(null)}>
          <div className="modal modal-sm" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Удалить товар?</h2>
            </div>
            <p>Это действие нельзя отменить. Если товар используется в документах — удаление будет заблокировано.</p>
            {deleteError && <div className="error-message">{deleteError}</div>}
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setDeleteId(null)}>Отмена</button>
              <button className="btn btn-danger" onClick={handleDelete} disabled={deleteMut.isPending}>
                {deleteMut.isPending ? 'Удаление...' : 'Удалить'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
