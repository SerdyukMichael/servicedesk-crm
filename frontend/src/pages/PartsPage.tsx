import { useState } from 'react'
import { useParts, useAdjustQuantity } from '../hooks/useParts'
import Pagination from '../components/Pagination'

export default function PartsPage() {
  const [page, setPage] = useState(1)
  const [category, setCategory] = useState('')
  const [lowStock, setLowStock] = useState(false)
  const [adjustPartId, setAdjustPartId] = useState<number | null>(null)
  const [adjustDelta, setAdjustDelta] = useState('')
  const [adjustReason, setAdjustReason] = useState('')

  const params: Record<string, unknown> = { page, size: 20 }
  if (category) params.category = category
  if (lowStock) params.low_stock = true

  const { data, isLoading, isError } = useParts(params)
  const adjustQty = useAdjustQuantity()

  const handleAdjust = () => {
    if (!adjustPartId || !adjustDelta) return
    adjustQty.mutate(
      { id: adjustPartId, delta: parseInt(adjustDelta, 10), reason: adjustReason },
      {
        onSuccess: () => {
          setAdjustPartId(null)
          setAdjustDelta('')
          setAdjustReason('')
        },
      }
    )
  }

  const categories = data
    ? [...new Set(data.items.map(p => p.category).filter(Boolean))]
    : []

  const adjustPart = data?.items.find(p => p.id === adjustPartId)

  return (
    <>
      <div className="page-header">
        <h1>Склад запчастей</h1>
      </div>

      <div className="filters-bar">
        <select
          className="form-select"
          value={category}
          onChange={e => { setCategory(e.target.value); setPage(1) }}
        >
          <option value="">Все категории</option>
          {categories.map(c => (
            <option key={c} value={c!}>
              {c}
            </option>
          ))}
        </select>
        <label
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            fontSize: 13,
            cursor: 'pointer',
            color: 'var(--text)',
          }}
        >
          <input
            type="checkbox"
            checked={lowStock}
            onChange={e => { setLowStock(e.target.checked); setPage(1) }}
          />
          Только заканчивающиеся
        </label>
      </div>

      {isLoading && (
        <div className="loading-center">
          <span className="spinner spinner-lg" />
        </div>
      )}
      {isError && (
        <div className="alert alert-error">Ошибка загрузки склада</div>
      )}

      {data && (
        <>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>SKU</th>
                  <th>Название</th>
                  <th>Категория</th>
                  <th>Кол-во</th>
                  <th>Мин. кол-во</th>
                  <th>Цена</th>
                  <th>Статус</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {data.items.length === 0 && (
                  <tr>
                    <td colSpan={8} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                      Запчасти не найдены
                    </td>
                  </tr>
                )}
                {data.items.map(part => {
                  const isLow = part.quantity < part.min_quantity
                  return (
                    <tr key={part.id} className={isLow ? 'part-row-low' : ''}>
                      <td>
                        <span style={{ fontFamily: 'monospace', fontSize: 12 }}>
                          {part.sku}
                        </span>
                      </td>
                      <td style={{ fontWeight: 500 }}>{part.name}</td>
                      <td>{part.category ?? '—'}</td>
                      <td>
                        <span className={isLow ? 'qty-low' : 'qty-ok'}>
                          {part.quantity}
                        </span>
                      </td>
                      <td style={{ color: 'var(--text-muted)' }}>{part.min_quantity}</td>
                      <td>{part.price.toFixed(2)} ₽</td>
                      <td>
                        {isLow ? (
                          <span className="badge priority-high">Мало</span>
                        ) : (
                          <span className="badge badge-completed">В наличии</span>
                        )}
                      </td>
                      <td>
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => setAdjustPartId(part.id)}
                        >
                          Изменить
                        </button>
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

      {/* Adjust quantity modal */}
      {adjustPartId && adjustPart && (
        <div className="modal-overlay" onClick={() => setAdjustPartId(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Изменить количество</h3>
              <button className="modal-close" onClick={() => setAdjustPartId(null)}>×</button>
            </div>
            <div className="modal-body">
              <p style={{ fontSize: 13, marginBottom: 16 }}>
                <strong>{adjustPart.name}</strong> — текущий остаток:{' '}
                <strong>{adjustPart.quantity}</strong>
              </p>
              <div className="form-group">
                <label className="form-label">
                  Изменение (+ добавить / − списать)
                </label>
                <input
                  type="number"
                  className="form-input"
                  placeholder="Например: 10 или -5"
                  value={adjustDelta}
                  onChange={e => setAdjustDelta(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Причина</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="Например: поступление, списание..."
                  value={adjustReason}
                  onChange={e => setAdjustReason(e.target.value)}
                />
              </div>
            </div>
            <div className="modal-footer">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setAdjustPartId(null)}
              >
                Отмена
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleAdjust}
                disabled={!adjustDelta || adjustQty.isPending}
              >
                {adjustQty.isPending ? 'Сохранение...' : 'Применить'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
