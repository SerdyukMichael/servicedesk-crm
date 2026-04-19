import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useParts, useAdjustQuantity } from '../hooks/useParts'
import Pagination from '../components/Pagination'
import { setPartPrice, getPartPriceHistory } from '../api/endpoints'
import type { SparePart, SparePartPriceUpdate, PriceHistoryEntry } from '../api/types'
import { useAuth } from '../context/AuthContext'
import { useCurrency } from '../context/CurrencyContext'

export default function PartsPage() {
  const { hasRole } = useAuth()
  const { currency } = useCurrency()
  const canManagePrice = hasRole('admin', 'svc_mgr')

  const [page, setPage] = useState(1)
  const [category, setCategory] = useState('')
  const [lowStock, setLowStock] = useState(false)

  // Quantity adjust state
  const [adjustPartId, setAdjustPartId] = useState<number | null>(null)
  const [adjustDelta, setAdjustDelta] = useState('')
  const [adjustReason, setAdjustReason] = useState('')

  // Price modal state
  const [pricePart, setPricePart] = useState<SparePart | null>(null)
  const [priceValue, setPriceValue] = useState('')
  const [priceCurrency, setPriceCurrency] = useState('RUB')
  const [priceReason, setPriceReason] = useState('')
  const [priceError, setPriceError] = useState<string | null>(null)

  // History modal state
  const [historyPartId, setHistoryPartId] = useState<number | null>(null)

  const qc = useQueryClient()
  const params: Record<string, unknown> = { page, size: 20 }
  if (category) params.category = category
  if (lowStock) params.low_stock = true

  const { data, isLoading, isError } = useParts(params)
  const adjustQty = useAdjustQuantity()

  const setPrice = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: SparePartPriceUpdate }) =>
      setPartPrice(id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['parts'] })
      setPricePart(null)
      setPriceValue('')
      setPriceReason('')
      setPriceError(null)
    },
    onError: (e: { response?: { data?: { detail?: unknown } } }) => {
      const detail = e?.response?.data?.detail
      if (Array.isArray(detail)) {
        setPriceError(detail.map((d: { msg: string }) => d.msg).join(', '))
      } else if (typeof detail === 'string') {
        setPriceError(detail)
      } else {
        setPriceError('Ошибка при сохранении цены')
      }
    },
  })

  const { data: priceHistory } = useQuery({
    queryKey: ['price-history', historyPartId],
    queryFn: () => getPartPriceHistory(historyPartId!),
    enabled: historyPartId !== null,
  })

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

  const handleSetPrice = () => {
    if (!pricePart || !priceValue) return
    setPriceError(null)
    setPrice.mutate({
      id: pricePart.id,
      payload: { new_price: priceValue, currency: priceCurrency, reason: priceReason },
    })
  }

  const openPriceModal = (part: SparePart) => {
    setPricePart(part)
    setPriceValue(parseFloat(String(part.unit_price ?? 0)).toFixed(2))
    setPriceCurrency(part.currency ?? 'RUB')
    setPriceReason('')
    setPriceError(null)
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
            <option key={c} value={c!}>{c}</option>
          ))}
        </select>
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, cursor: 'pointer', color: 'var(--text)' }}>
          <input
            type="checkbox"
            checked={lowStock}
            onChange={e => { setLowStock(e.target.checked); setPage(1) }}
          />
          Только заканчивающиеся
        </label>
      </div>

      {isLoading && <div className="loading-center"><span className="spinner spinner-lg" /></div>}
      {isError && <div className="alert alert-error">Ошибка загрузки склада</div>}

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
                  <th>Мин.</th>
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
                  const price = parseFloat(String(part.unit_price ?? 0))
                  const isLow = part.quantity < part.min_quantity
                  const hasPriceSet = price > 0
                  return (
                    <tr key={part.id} className={isLow ? 'part-row-low' : ''}>
                      <td><span style={{ fontFamily: 'monospace', fontSize: 12 }}>{part.sku}</span></td>
                      <td style={{ fontWeight: 500 }}>{part.name}</td>
                      <td>{part.category ?? '—'}</td>
                      <td>
                        <span className={isLow ? 'qty-low' : 'qty-ok'}>{part.quantity}</span>
                      </td>
                      <td style={{ color: 'var(--text-muted)' }}>{part.min_quantity}</td>
                      <td>
                        <span style={{ fontWeight: hasPriceSet ? 600 : 400, color: hasPriceSet ? 'inherit' : 'var(--text-muted)' }}>
                          {hasPriceSet ? `${price.toFixed(2)} ${currency.currency_code}` : '—'}
                        </span>
                        {hasPriceSet && (
                          <button
                            style={{ marginLeft: 6, fontSize: 11, background: 'none', border: 'none', color: 'var(--primary)', cursor: 'pointer', padding: 0 }}
                            onClick={() => setHistoryPartId(part.id)}
                          >
                            история
                          </button>
                        )}
                      </td>
                      <td>
                        {isLow
                          ? <span className="badge priority-high">Мало</span>
                          : <span className="badge badge-completed">В наличии</span>
                        }
                      </td>
                      <td style={{ display: 'flex', gap: 4, flexWrap: 'nowrap' }}>
                        <button className="btn btn-secondary btn-sm" onClick={() => setAdjustPartId(part.id)}>
                          Кол-во
                        </button>
                        {canManagePrice && (
                          <button className="btn btn-primary btn-sm" onClick={() => openPriceModal(part)}>
                            {hasPriceSet ? 'Цена' : 'Уст. цену'}
                          </button>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          <Pagination page={data.page} pages={data.pages} total={data.total} size={data.size} onPageChange={setPage} />
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
                <strong>{adjustPart.name}</strong> — текущий остаток: <strong>{adjustPart.quantity}</strong>
              </p>
              <div className="form-group">
                <label className="form-label">Изменение (+ добавить / − списать)</label>
                <input type="number" className="form-input" placeholder="Например: 10 или -5"
                  value={adjustDelta} onChange={e => setAdjustDelta(e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">Причина</label>
                <input type="text" className="form-input" placeholder="Например: поступление, списание..."
                  value={adjustReason} onChange={e => setAdjustReason(e.target.value)} />
              </div>
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" onClick={() => setAdjustPartId(null)}>Отмена</button>
              <button type="button" className="btn btn-primary" onClick={handleAdjust}
                disabled={!adjustDelta || adjustQty.isPending}>
                {adjustQty.isPending ? 'Сохранение...' : 'Применить'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Set / change price modal */}
      {pricePart && (
        <div className="modal-overlay" onClick={() => setPricePart(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>
                {parseFloat(String(pricePart.unit_price ?? 0)) > 0
                  ? 'Изменить цену'
                  : 'Установить цену'}
              </h3>
              <button className="modal-close" onClick={() => setPricePart(null)}>×</button>
            </div>
            <div className="modal-body">
              <p style={{ fontSize: 13, marginBottom: 16 }}>
                <strong>{pricePart.name}</strong>{' '}
                <span style={{ color: 'var(--text-muted)', fontFamily: 'monospace', fontSize: 12 }}>
                  SKU: {pricePart.sku}
                </span>
              </p>
              {priceError && (
                <div className="alert alert-error" style={{ marginBottom: 12 }}>{priceError}</div>
              )}
              <div className="form-group">
                <label className="form-label">Новая цена *</label>
                <input
                  type="number" min="0" step="0.01" className="form-input"
                  placeholder="0.00" value={priceValue}
                  onChange={e => setPriceValue(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Валюта</label>
                <select className="form-select" value={priceCurrency} onChange={e => setPriceCurrency(e.target.value)}>
                  <option value="RUB">RUB</option>
                  <option value="USD">USD</option>
                  <option value="EUR">EUR</option>
                  <option value="PLN">PLN</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Причина изменения * (мин. 5 символов)</label>
                <input
                  type="text" className="form-input"
                  placeholder="Например: обновление прайса поставщика"
                  value={priceReason}
                  onChange={e => setPriceReason(e.target.value)}
                />
              </div>
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" onClick={() => setPricePart(null)}>Отмена</button>
              <button
                type="button" className="btn btn-primary" onClick={handleSetPrice}
                disabled={!priceValue || priceReason.trim().length < 5 || setPrice.isPending}
              >
                {setPrice.isPending ? 'Сохранение...' : 'Сохранить'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Price history modal */}
      {historyPartId !== null && (
        <div className="modal-overlay" onClick={() => setHistoryPartId(null)}>
          <div className="modal" style={{ maxWidth: 620 }} onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>История цен</h3>
              <button className="modal-close" onClick={() => setHistoryPartId(null)}>×</button>
            </div>
            <div className="modal-body">
              {!priceHistory && <div className="loading-center"><span className="spinner" /></div>}
              {priceHistory && priceHistory.length === 0 && (
                <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '20px 0' }}>
                  История пуста
                </p>
              )}
              {priceHistory && priceHistory.length > 0 && (
                <table className="table" style={{ fontSize: 13 }}>
                  <thead>
                    <tr>
                      <th>Дата</th>
                      <th>Было</th>
                      <th>Стало</th>
                      <th>Причина</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(priceHistory as PriceHistoryEntry[]).map(h => (
                      <tr key={h.id}>
                        <td style={{ whiteSpace: 'nowrap' }}>
                          {new Date(h.changed_at).toLocaleString('ru-RU')}
                        </td>
                        <td style={{ color: 'var(--text-muted)' }}>
                          {parseFloat(h.old_price).toFixed(2)} {h.currency}
                        </td>
                        <td style={{ fontWeight: 600 }}>
                          {parseFloat(h.new_price).toFixed(2)} {h.currency}
                        </td>
                        <td>{h.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  )
}
