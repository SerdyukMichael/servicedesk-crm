import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAdjustQuantity } from '../hooks/useParts'
import Pagination from '../components/Pagination'
import {
  setPartPrice,
  getPartPriceHistory,
  getWarehouses,
  getWarehouseStock,
  getStockReceipts,
  createStockReceipt,
  postStockReceipt,
  cancelStockReceipt,
  getPartsTransfers,
  createPartsTransfer,
  postPartsTransfer,
  cancelPartsTransfer,
  getVendors,
  getParts,
} from '../api/endpoints'
import type {
  WarehouseStock,
  SparePartPriceUpdate,
  PriceHistoryEntry,
  Warehouse,
  StockReceipt,
  StockReceiptCreate,
  PartsTransfer,
  PartsTransferCreate,
} from '../api/types'
import { useAuth } from '../context/AuthContext'
import { useCurrency } from '../context/CurrencyContext'

type Tab = 'parts' | 'receipts' | 'transfers'
type PriceTarget = { id: number; name: string; sku: string; unit_price: string }

const STATUS_LABEL: Record<string, string> = {
  draft: 'Черновик',
  posted: 'Проведён',
  cancelled: 'Отменён',
}

const STATUS_CLASS: Record<string, string> = {
  draft: 'badge-new',
  posted: 'badge-completed',
  cancelled: 'badge-cancelled',
}

interface ApiError {
  response?: { data?: { detail?: unknown } }
}

function extractError(e: ApiError): string {
  const detail = e?.response?.data?.detail
  if (detail && typeof detail === 'object' && !Array.isArray(detail) && 'message' in detail) {
    return (detail as { message: string }).message
  }
  if (Array.isArray(detail)) return detail.map((d: { msg: string }) => d.msg).join(', ')
  if (typeof detail === 'string') return detail
  return 'Произошла ошибка'
}

function todayStr(): string {
  return new Date().toISOString().slice(0, 10)
}

type RcpFormItem = { part_id: string; quantity: string; unit_price: string }
type TrfFormItem = { part_id: string; quantity: string }

const EMPTY_RCP_ITEM: RcpFormItem = { part_id: '', quantity: '1', unit_price: '0.00' }
const EMPTY_TRF_ITEM: TrfFormItem = { part_id: '', quantity: '1' }

export default function PartsPage() {
  const { hasRole } = useAuth()
  const { currency } = useCurrency()
  const canManagePrice = hasRole('admin', 'svc_mgr')
  const canWrite = hasRole('admin', 'svc_mgr')

  const [activeTab, setActiveTab] = useState<Tab>('parts')

  // ── Parts tab state ───────────────────────────────────────────────────────────
  const [stockPage, setStockPage] = useState(1)
  const [stockWarehouseId, setStockWarehouseId] = useState<number | ''>('')
  const [category, setCategory] = useState('')
  const [lowStock, setLowStock] = useState(false)
  const [adjustPartId, setAdjustPartId] = useState<number | null>(null)
  const [adjustDelta, setAdjustDelta] = useState('')
  const [adjustReason, setAdjustReason] = useState('')
  const [pricePart, setPricePart] = useState<PriceTarget | null>(null)
  const [priceValue, setPriceValue] = useState('')
  const [priceReason, setPriceReason] = useState('')
  const [priceError, setPriceError] = useState<string | null>(null)
  const [historyPartId, setHistoryPartId] = useState<number | null>(null)

  // ── Receipts tab state ────────────────────────────────────────────────────────
  const [rcpPage, setRcpPage] = useState(1)
  const [rcpStatusFilter, setRcpStatusFilter] = useState('')
  const [rcpWarehouseFilter, setRcpWarehouseFilter] = useState<number | ''>('')
  const [showRcpCreate, setShowRcpCreate] = useState(false)
  const [viewReceipt, setViewReceipt] = useState<StockReceipt | null>(null)
  const [rcpItems, setRcpItems] = useState<RcpFormItem[]>([{ ...EMPTY_RCP_ITEM }])
  const [rcpWarehouse, setRcpWarehouse] = useState('')
  const [rcpDate, setRcpDate] = useState(todayStr())
  const [rcpVendor, setRcpVendor] = useState('')
  const [rcpDocNum, setRcpDocNum] = useState('')
  const [rcpNotes, setRcpNotes] = useState('')
  const [rcpError, setRcpError] = useState<string | null>(null)

  // ── Transfers tab state ───────────────────────────────────────────────────────
  const [trfPage, setTrfPage] = useState(1)
  const [trfStatusFilter, setTrfStatusFilter] = useState('')
  const [showTrfCreate, setShowTrfCreate] = useState(false)
  const [viewTransfer, setViewTransfer] = useState<PartsTransfer | null>(null)
  const [trfItems, setTrfItems] = useState<TrfFormItem[]>([{ ...EMPTY_TRF_ITEM }])
  const [trfFrom, setTrfFrom] = useState('')
  const [trfTo, setTrfTo] = useState('')
  const [trfDate, setTrfDate] = useState(todayStr())
  const [trfNotes, setTrfNotes] = useState('')
  const [trfError, setTrfError] = useState<string | null>(null)

  const qc = useQueryClient()

  // ── Parts queries ─────────────────────────────────────────────────────────────
  const adjustQty = useAdjustQuantity()

  const { data: allPartsData } = useQuery({
    queryKey: ['parts-all'],
    queryFn: () => getParts({ size: 200 }),
  })
  const allParts = allPartsData?.items ?? []

  // ── Warehouse queries ─────────────────────────────────────────────────────────
  const { data: warehousesData } = useQuery({
    queryKey: ['warehouses'],
    queryFn: () => getWarehouses({ active_only: true }),
  })
  const warehouseList: Warehouse[] = warehousesData ?? []
  const bankWarehouses = warehouseList.filter(w => w.type === 'bank')

  // ── Stock queries (unified view for Запчасти tab) ─────────────────────────────
  const stockParams: Record<string, unknown> = { page: stockPage, size: 50 }
  if (stockWarehouseId) stockParams.warehouse_id = stockWarehouseId
  if (lowStock) stockParams.low_stock = true
  const { data: stockData, isLoading: stockLoading } = useQuery({
    queryKey: ['warehouse-stock', stockPage, stockWarehouseId, lowStock],
    queryFn: () => getWarehouseStock(stockParams),
    enabled: activeTab === 'parts',
  })

  // ── Receipt queries / mutations ───────────────────────────────────────────────
  const rcpParams: Record<string, unknown> = { page: rcpPage, size: 20 }
  if (rcpStatusFilter) rcpParams.status = rcpStatusFilter
  if (rcpWarehouseFilter) rcpParams.warehouse_id = rcpWarehouseFilter
  const { data: rcpData, isLoading: rcpLoading } = useQuery({
    queryKey: ['stock-receipts', rcpPage, rcpStatusFilter, rcpWarehouseFilter],
    queryFn: () => getStockReceipts(rcpParams),
    enabled: activeTab === 'receipts',
  })

  const { data: vendorsData } = useQuery({
    queryKey: ['vendors-all'],
    queryFn: () => getVendors({ size: 200 }),
    enabled: activeTab === 'receipts',
  })
  const vendorList = vendorsData?.items ?? []

  const createRcpMut = useMutation({
    mutationFn: (d: StockReceiptCreate) => createStockReceipt(d),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['stock-receipts'] })
      qc.invalidateQueries({ queryKey: ['warehouse-stock'] })
      setShowRcpCreate(false)
      resetRcpForm()
    },
    onError: (e: ApiError) => setRcpError(extractError(e)),
  })

  const postRcpMut = useMutation({
    mutationFn: (id: number) => postStockReceipt(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['stock-receipts'] })
      qc.invalidateQueries({ queryKey: ['warehouse-stock'] })
      qc.invalidateQueries({ queryKey: ['parts'] })
      setViewReceipt(null)
    },
    onError: (e: ApiError) => alert(extractError(e)),
  })

  const cancelRcpMut = useMutation({
    mutationFn: (id: number) => cancelStockReceipt(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['stock-receipts'] })
      setViewReceipt(null)
    },
  })

  // ── Transfer queries / mutations ──────────────────────────────────────────────
  const trfParams: Record<string, unknown> = { page: trfPage, size: 20 }
  if (trfStatusFilter) trfParams.status = trfStatusFilter
  const { data: trfData, isLoading: trfLoading } = useQuery({
    queryKey: ['parts-transfers', trfPage, trfStatusFilter],
    queryFn: () => getPartsTransfers(trfParams),
    enabled: activeTab === 'transfers',
  })

  const createTrfMut = useMutation({
    mutationFn: (d: PartsTransferCreate) => createPartsTransfer(d),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['parts-transfers'] })
      setShowTrfCreate(false)
      resetTrfForm()
    },
    onError: (e: ApiError) => setTrfError(extractError(e)),
  })

  const postTrfMut = useMutation({
    mutationFn: (id: number) => postPartsTransfer(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['parts-transfers'] })
      qc.invalidateQueries({ queryKey: ['warehouse-stock'] })
      qc.invalidateQueries({ queryKey: ['parts'] })
      setViewTransfer(null)
    },
    onError: (e: ApiError) => alert(extractError(e)),
  })

  const cancelTrfMut = useMutation({
    mutationFn: (id: number) => cancelPartsTransfer(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['parts-transfers'] })
      setViewTransfer(null)
    },
  })

  // ── Price mutations ───────────────────────────────────────────────────────────
  const setPrice = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: SparePartPriceUpdate }) =>
      setPartPrice(id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['parts'] })
      qc.invalidateQueries({ queryKey: ['warehouse-stock'] })
      setPricePart(null)
      setPriceValue('')
      setPriceReason('')
      setPriceError(null)
    },
    onError: (e: ApiError) => {
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

  // ── Handlers ──────────────────────────────────────────────────────────────────
  function resetRcpForm() {
    setRcpItems([{ ...EMPTY_RCP_ITEM }])
    setRcpWarehouse('')
    setRcpDate(todayStr())
    setRcpVendor('')
    setRcpDocNum('')
    setRcpNotes('')
    setRcpError(null)
  }

  function resetTrfForm() {
    setTrfItems([{ ...EMPTY_TRF_ITEM }])
    setTrfFrom('')
    setTrfTo('')
    setTrfDate(todayStr())
    setTrfNotes('')
    setTrfError(null)
  }

  const handleAdjust = () => {
    if (!adjustPartId || !adjustDelta) return
    adjustQty.mutate(
      { id: adjustPartId, delta: parseInt(adjustDelta, 10), reason: adjustReason },
      {
        onSuccess: () => {
          qc.invalidateQueries({ queryKey: ['warehouse-stock'] })
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
      payload: { new_price: priceValue, currency: currency.currency_code, reason: priceReason },
    })
  }

  const openPriceModal = (stock: WarehouseStock) => {
    setPricePart({
      id: stock.part_id,
      name: stock.part_name,
      sku: stock.part_sku,
      unit_price: stock.unit_price_snapshot ?? '0',
    })
    setPriceValue(parseFloat(stock.unit_price_snapshot ?? '0').toFixed(2))
    setPriceReason('')
    setPriceError(null)
  }

  const submitRcpForm = () => {
    setRcpError(null)
    if (!rcpWarehouse) { setRcpError('Выберите склад'); return }
    if (rcpItems.some(i => !i.part_id)) { setRcpError('Выберите запчасть для каждой строки'); return }
    const payload: StockReceiptCreate = {
      warehouse_id: parseInt(rcpWarehouse),
      receipt_date: rcpDate,
      vendor_id: rcpVendor ? parseInt(rcpVendor) : undefined,
      supplier_doc_number: rcpDocNum || undefined,
      notes: rcpNotes || undefined,
      items: rcpItems.map(i => ({
        part_id: parseInt(i.part_id),
        quantity: parseInt(i.quantity),
        unit_price: i.unit_price,
      })),
    }
    createRcpMut.mutate(payload)
  }

  const submitTrfForm = () => {
    setTrfError(null)
    if (!trfFrom) { setTrfError('Выберите склад-источник'); return }
    if (!trfTo) { setTrfError('Выберите склад-получатель'); return }
    if (trfFrom === trfTo) { setTrfError('Склады должны быть разными'); return }
    if (trfItems.some(i => !i.part_id)) { setTrfError('Выберите запчасть для каждой строки'); return }
    const payload: PartsTransferCreate = {
      from_warehouse_id: parseInt(trfFrom),
      to_warehouse_id: parseInt(trfTo),
      transfer_date: trfDate,
      notes: trfNotes || undefined,
      items: trfItems.map(i => ({
        part_id: parseInt(i.part_id),
        quantity: parseInt(i.quantity),
      })),
    }
    createTrfMut.mutate(payload)
  }

  const categories = stockData
    ? [...new Set(stockData.items.map(s => s.part_category).filter(Boolean))]
    : []
  const adjustPart = stockData?.items.find(
    s => s.part_id === adjustPartId && s.warehouse_type === 'company'
  )

  const TABS: { id: Tab; label: string }[] = [
    { id: 'parts', label: 'Запчасти' },
    { id: 'receipts', label: 'Приходы' },
    { id: 'transfers', label: 'Передачи' },
  ]

  return (
    <>
      <div className="page-header">
        <h1>Склад запчастей</h1>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 20, borderBottom: '1px solid var(--border)', paddingBottom: 0 }}>
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            style={{
              padding: '8px 18px',
              border: 'none',
              background: 'none',
              cursor: 'pointer',
              fontSize: 14,
              fontWeight: activeTab === t.id ? 600 : 400,
              color: activeTab === t.id ? 'var(--primary)' : 'var(--text-muted)',
              borderBottom: activeTab === t.id ? '2px solid var(--primary)' : '2px solid transparent',
              marginBottom: -1,
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Parts tab (unified warehouse view) ────────────────────────────────── */}
      {activeTab === 'parts' && (
        <>
          <div className="filters-bar">
            <select
              className="form-select"
              value={stockWarehouseId}
              onChange={e => { setStockWarehouseId(e.target.value ? parseInt(e.target.value) : ''); setStockPage(1) }}
            >
              <option value="">Все склады</option>
              {warehouseList.map(w => (
                <option key={w.id} value={w.id}>
                  {w.name} ({w.type === 'company' ? 'компания' : 'банк'})
                </option>
              ))}
            </select>
            <select
              className="form-select"
              value={category}
              onChange={e => setCategory(e.target.value)}
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
                onChange={e => { setLowStock(e.target.checked); setStockPage(1) }}
              />
              Только заканчивающиеся
            </label>
          </div>

          {stockLoading && <div className="loading-center"><span className="spinner spinner-lg" /></div>}

          {stockData && (
            <>
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Склад</th>
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
                    {stockData.items.length === 0 && (
                      <tr>
                        <td colSpan={9} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                          Запчасти не найдены
                        </td>
                      </tr>
                    )}
                    {stockData.items
                      .filter(s => !category || s.part_category === category)
                      .map(s => {
                        const isBank = s.warehouse_type === 'bank'
                        const price = isBank ? 0 : parseFloat(s.unit_price_snapshot ?? '0')
                        const hasPriceSet = !isBank && price > 0
                        const isLow = s.quantity < s.part_min_quantity
                        return (
                          <tr key={s.id} className={isLow && !isBank ? 'part-row-low' : ''}>
                            <td>
                              <span style={{ fontWeight: 500 }}>{s.warehouse_name}</span>
                              {' '}
                              <span className={`badge ${isBank ? 'badge-new' : 'badge-assigned'}`} style={{ fontSize: 10 }}>
                                {isBank ? 'банк' : 'компания'}
                              </span>
                            </td>
                            <td><span style={{ fontFamily: 'monospace', fontSize: 12 }}>{s.part_sku}</span></td>
                            <td style={{ fontWeight: 500 }}>{s.part_name}</td>
                            <td style={{ color: 'var(--text-muted)' }}>{s.part_category ?? '—'}</td>
                            <td>
                              <span className={isLow && !isBank ? 'qty-low' : 'qty-ok'}>{s.quantity}</span>
                            </td>
                            <td style={{ color: 'var(--text-muted)' }}>{s.part_min_quantity}</td>
                            <td>
                              {isBank ? (
                                <span style={{ color: 'var(--text-muted)' }}>0 (банк)</span>
                              ) : (
                                <>
                                  <span style={{ fontWeight: hasPriceSet ? 600 : 400, color: hasPriceSet ? 'inherit' : 'var(--text-muted)' }}>
                                    {hasPriceSet ? `${price.toFixed(2)} ${currency.currency_code}` : '—'}
                                  </span>
                                  {hasPriceSet && (
                                    <button
                                      style={{ marginLeft: 6, fontSize: 11, background: 'none', border: 'none', color: 'var(--primary)', cursor: 'pointer', padding: 0 }}
                                      onClick={() => setHistoryPartId(s.part_id)}
                                    >
                                      история
                                    </button>
                                  )}
                                </>
                              )}
                            </td>
                            <td>
                              {isBank
                                ? <span className="badge badge-new">Банк</span>
                                : isLow
                                  ? <span className="badge priority-high">Мало</span>
                                  : <span className="badge badge-completed">В наличии</span>
                              }
                            </td>
                            <td style={{ display: 'flex', gap: 4, flexWrap: 'nowrap' }}>
                              {!isBank && canWrite && (
                                <button className="btn btn-secondary btn-sm" onClick={() => setAdjustPartId(s.part_id)}>
                                  Кол-во
                                </button>
                              )}
                              {!isBank && canManagePrice && (
                                <button className="btn btn-primary btn-sm" onClick={() => openPriceModal(s)}>
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
              <Pagination page={stockData.page} pages={stockData.pages} total={stockData.total} size={stockData.size} onPageChange={setStockPage} />
            </>
          )}
        </>
      )}

      {/* ── Receipts tab ──────────────────────────────────────────────────────── */}
      {activeTab === 'receipts' && (
        <>
          <div className="filters-bar">
            <select
              className="form-select"
              value={rcpStatusFilter}
              onChange={e => { setRcpStatusFilter(e.target.value); setRcpPage(1) }}
            >
              <option value="">Все статусы</option>
              <option value="draft">Черновик</option>
              <option value="posted">Проведён</option>
              <option value="cancelled">Отменён</option>
            </select>
            <select
              className="form-select"
              value={rcpWarehouseFilter}
              onChange={e => { setRcpWarehouseFilter(e.target.value ? parseInt(e.target.value) : ''); setRcpPage(1) }}
            >
              <option value="">Все склады</option>
              {warehouseList.map(w => (
                <option key={w.id} value={w.id}>{w.name}</option>
              ))}
            </select>
            {canWrite && (
              <button className="btn btn-primary btn-sm" onClick={() => { resetRcpForm(); setShowRcpCreate(true) }}>
                + Приходный ордер
              </button>
            )}
          </div>

          {rcpLoading && <div className="loading-center"><span className="spinner spinner-lg" /></div>}

          {rcpData && (
            <>
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Номер</th>
                      <th>Склад</th>
                      <th>Дата</th>
                      <th>Позиций</th>
                      <th>Статус</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {rcpData.items.length === 0 && (
                      <tr>
                        <td colSpan={6} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                          Приходных ордеров нет
                        </td>
                      </tr>
                    )}
                    {rcpData.items.map(r => (
                      <tr key={r.id}>
                        <td><span style={{ fontFamily: 'monospace', fontSize: 12 }}>{r.receipt_number}</span></td>
                        <td>{r.warehouse_name}</td>
                        <td>{r.receipt_date}</td>
                        <td>{r.items.length}</td>
                        <td>
                          <span className={`badge ${STATUS_CLASS[r.status] ?? ''}`}>
                            {STATUS_LABEL[r.status] ?? r.status}
                          </span>
                        </td>
                        <td>
                          <button className="btn btn-secondary btn-sm" onClick={() => setViewReceipt(r)}>
                            Открыть
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <Pagination page={rcpData.page} pages={rcpData.pages} total={rcpData.total} size={rcpData.size} onPageChange={setRcpPage} />
            </>
          )}
        </>
      )}

      {/* ── Transfers tab ─────────────────────────────────────────────────────── */}
      {activeTab === 'transfers' && (
        <>
          <div className="filters-bar">
            <select
              className="form-select"
              value={trfStatusFilter}
              onChange={e => { setTrfStatusFilter(e.target.value); setTrfPage(1) }}
            >
              <option value="">Все статусы</option>
              <option value="draft">Черновик</option>
              <option value="posted">Проведён</option>
              <option value="cancelled">Отменён</option>
            </select>
            {canWrite && (
              <button className="btn btn-primary btn-sm" onClick={() => { resetTrfForm(); setShowTrfCreate(true) }}>
                + Передача
              </button>
            )}
          </div>

          {trfLoading && <div className="loading-center"><span className="spinner spinner-lg" /></div>}

          {trfData && (
            <>
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Номер</th>
                      <th>Откуда</th>
                      <th>Куда</th>
                      <th>Дата</th>
                      <th>Позиций</th>
                      <th>Статус</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {trfData.items.length === 0 && (
                      <tr>
                        <td colSpan={7} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                          Передач нет
                        </td>
                      </tr>
                    )}
                    {trfData.items.map(t => (
                      <tr key={t.id}>
                        <td><span style={{ fontFamily: 'monospace', fontSize: 12 }}>{t.transfer_number}</span></td>
                        <td>{t.from_warehouse_name}</td>
                        <td>{t.to_warehouse_name}</td>
                        <td>{t.transfer_date}</td>
                        <td>{t.items.length}</td>
                        <td>
                          <span className={`badge ${STATUS_CLASS[t.status] ?? ''}`}>
                            {STATUS_LABEL[t.status] ?? t.status}
                          </span>
                        </td>
                        <td>
                          <button className="btn btn-secondary btn-sm" onClick={() => setViewTransfer(t)}>
                            Открыть
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <Pagination page={trfData.page} pages={trfData.pages} total={trfData.total} size={trfData.size} onPageChange={setTrfPage} />
            </>
          )}
        </>
      )}

      {/* ══ Modals ════════════════════════════════════════════════════════════════ */}

      {/* Adjust quantity */}
      {adjustPartId && adjustPart && (
        <div className="modal-overlay" onClick={() => setAdjustPartId(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Изменить количество</h3>
              <button className="modal-close" onClick={() => setAdjustPartId(null)}>×</button>
            </div>
            <div className="modal-body">
              <p style={{ fontSize: 13, marginBottom: 16 }}>
                <strong>{adjustPart.part_name}</strong> — текущий остаток: <strong>{adjustPart.quantity}</strong>
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

      {/* Set / change price */}
      {pricePart && (
        <div className="modal-overlay" onClick={() => setPricePart(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{parseFloat(pricePart.unit_price) > 0 ? 'Изменить цену' : 'Установить цену'}</h3>
              <button className="modal-close" onClick={() => setPricePart(null)}>×</button>
            </div>
            <div className="modal-body">
              <p style={{ fontSize: 13, marginBottom: 16 }}>
                <strong>{pricePart.name}</strong>{' '}
                <span style={{ color: 'var(--text-muted)', fontFamily: 'monospace', fontSize: 12 }}>SKU: {pricePart.sku}</span>
              </p>
              {priceError && <div className="alert alert-error" style={{ marginBottom: 12 }}>{priceError}</div>}
              <div className="form-group">
                <label className="form-label">Цена ({currency.currency_code}) <span className="required">*</span></label>
                <input type="number" min="0" step="0.01" className="form-input" placeholder="0.00"
                  value={priceValue} onChange={e => setPriceValue(e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">Причина изменения * (мин. 5 символов)</label>
                <input type="text" className="form-input" placeholder="Например: обновление прайса поставщика"
                  value={priceReason} onChange={e => setPriceReason(e.target.value)} />
              </div>
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" onClick={() => setPricePart(null)}>Отмена</button>
              <button type="button" className="btn btn-primary" onClick={handleSetPrice}
                disabled={!priceValue || priceReason.trim().length < 5 || setPrice.isPending}>
                {setPrice.isPending ? 'Сохранение...' : 'Сохранить'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Price history */}
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
                <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '20px 0' }}>История пуста</p>
              )}
              {priceHistory && priceHistory.length > 0 && (
                <table className="table" style={{ fontSize: 13 }}>
                  <thead>
                    <tr><th>Дата</th><th>Было</th><th>Стало</th><th>Причина</th></tr>
                  </thead>
                  <tbody>
                    {(priceHistory as PriceHistoryEntry[]).map(h => (
                      <tr key={h.id}>
                        <td style={{ whiteSpace: 'nowrap' }}>{new Date(h.changed_at).toLocaleString('ru-RU')}</td>
                        <td style={{ color: 'var(--text-muted)' }}>{parseFloat(h.old_price).toFixed(2)} {h.currency}</td>
                        <td style={{ fontWeight: 600 }}>{parseFloat(h.new_price).toFixed(2)} {h.currency}</td>
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

      {/* Create Receipt */}
      {showRcpCreate && (
        <div className="modal-overlay" onClick={() => { setShowRcpCreate(false); resetRcpForm() }}>
          <div className="modal" style={{ maxWidth: 720 }} onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Новый приходный ордер</h3>
              <button className="modal-close" onClick={() => { setShowRcpCreate(false); resetRcpForm() }}>×</button>
            </div>
            <div className="modal-body" style={{ maxHeight: '65vh', overflowY: 'auto' }}>
              {rcpError && <div className="alert alert-error" style={{ marginBottom: 12 }}>{rcpError}</div>}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div className="form-group">
                  <label className="form-label">Склад <span className="required">*</span></label>
                  <select className="form-select" value={rcpWarehouse}
                    onChange={e => setRcpWarehouse(e.target.value)}>
                    <option value="">Выберите склад</option>
                    {warehouseList.map(w => (
                      <option key={w.id} value={w.id}>{w.name}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Дата прихода <span className="required">*</span></label>
                  <input type="date" className="form-input" value={rcpDate}
                    onChange={e => setRcpDate(e.target.value)} />
                </div>
                <div className="form-group">
                  <label className="form-label">Поставщик</label>
                  <select className="form-select" value={rcpVendor}
                    onChange={e => setRcpVendor(e.target.value)}>
                    <option value="">—</option>
                    {vendorList.map(v => (
                      <option key={v.id} value={v.id}>{v.name}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Документ поставщика</label>
                  <input type="text" className="form-input" placeholder="Например: ТН-1234"
                    value={rcpDocNum} onChange={e => setRcpDocNum(e.target.value)} />
                </div>
              </div>
              <div className="form-group">
                <label className="form-label">Примечание</label>
                <input type="text" className="form-input" value={rcpNotes}
                  onChange={e => setRcpNotes(e.target.value)} />
              </div>

              <div style={{ marginTop: 16 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <strong style={{ fontSize: 14 }}>Позиции</strong>
                  <button type="button" className="btn btn-secondary btn-sm"
                    onClick={() => setRcpItems(prev => [...prev, { ...EMPTY_RCP_ITEM }])}>
                    + Добавить строку
                  </button>
                </div>
                <table className="table" style={{ fontSize: 13 }}>
                  <thead>
                    <tr>
                      <th>Запчасть</th>
                      <th style={{ width: 80 }}>Кол-во</th>
                      <th style={{ width: 120 }}>Цена за ед.</th>
                      <th style={{ width: 36 }}></th>
                    </tr>
                  </thead>
                  <tbody>
                    {rcpItems.map((item, idx) => (
                      <tr key={idx}>
                        <td>
                          <select className="form-select" value={item.part_id}
                            onChange={e => setRcpItems(prev => prev.map((it, i) => i === idx ? { ...it, part_id: e.target.value } : it))}>
                            <option value="">Выберите...</option>
                            {allParts.map(p => (
                              <option key={p.id} value={p.id}>{p.name} ({p.sku})</option>
                            ))}
                          </select>
                        </td>
                        <td>
                          <input type="number" min="1" className="form-input" value={item.quantity}
                            onChange={e => setRcpItems(prev => prev.map((it, i) => i === idx ? { ...it, quantity: e.target.value } : it))} />
                        </td>
                        <td>
                          <input type="number" min="0" step="0.01" className="form-input" value={item.unit_price}
                            onChange={e => setRcpItems(prev => prev.map((it, i) => i === idx ? { ...it, unit_price: e.target.value } : it))} />
                        </td>
                        <td>
                          {rcpItems.length > 1 && (
                            <button type="button" className="btn btn-secondary btn-sm" style={{ padding: '2px 8px' }}
                              onClick={() => setRcpItems(prev => prev.filter((_, i) => i !== idx))}>×</button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary"
                onClick={() => { setShowRcpCreate(false); resetRcpForm() }}>Отмена</button>
              <button type="button" className="btn btn-primary" onClick={submitRcpForm}
                disabled={createRcpMut.isPending}>
                {createRcpMut.isPending ? 'Создание...' : 'Создать черновик'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* View Receipt */}
      {viewReceipt && (
        <div className="modal-overlay" onClick={() => setViewReceipt(null)}>
          <div className="modal" style={{ maxWidth: 680 }} onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Приходный ордер {viewReceipt.receipt_number}</h3>
              <button className="modal-close" onClick={() => setViewReceipt(null)}>×</button>
            </div>
            <div className="modal-body">
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 13, marginBottom: 16 }}>
                <div><span style={{ color: 'var(--text-muted)' }}>Склад:</span> {viewReceipt.warehouse_name}</div>
                <div><span style={{ color: 'var(--text-muted)' }}>Дата:</span> {viewReceipt.receipt_date}</div>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Статус: </span>
                  <span className={`badge ${STATUS_CLASS[viewReceipt.status] ?? ''}`}>
                    {STATUS_LABEL[viewReceipt.status] ?? viewReceipt.status}
                  </span>
                </div>
                {viewReceipt.supplier_doc_number && (
                  <div><span style={{ color: 'var(--text-muted)' }}>Документ поставщика:</span> {viewReceipt.supplier_doc_number}</div>
                )}
                {viewReceipt.notes && (
                  <div style={{ gridColumn: '1 / -1' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Примечание:</span> {viewReceipt.notes}
                  </div>
                )}
              </div>
              <table className="table" style={{ fontSize: 13 }}>
                <thead>
                  <tr><th>SKU</th><th>Запчасть</th><th>Кол-во</th><th>Цена</th><th>Сумма</th></tr>
                </thead>
                <tbody>
                  {viewReceipt.items.map(item => (
                    <tr key={item.id}>
                      <td><span style={{ fontFamily: 'monospace', fontSize: 11 }}>{item.part_sku}</span></td>
                      <td>{item.part_name}</td>
                      <td>{item.quantity}</td>
                      <td>{parseFloat(item.unit_price).toFixed(2)}</td>
                      <td style={{ fontWeight: 600 }}>
                        {(item.quantity * parseFloat(item.unit_price)).toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" onClick={() => setViewReceipt(null)}>Закрыть</button>
              {canWrite && viewReceipt.status === 'draft' && (
                <>
                  <button type="button" className="btn btn-secondary"
                    onClick={() => cancelRcpMut.mutate(viewReceipt.id)}
                    disabled={cancelRcpMut.isPending}>
                    Отменить
                  </button>
                  <button type="button" className="btn btn-primary"
                    onClick={() => postRcpMut.mutate(viewReceipt.id)}
                    disabled={postRcpMut.isPending}>
                    {postRcpMut.isPending ? 'Проведение...' : 'Провести'}
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Create Transfer */}
      {showTrfCreate && (
        <div className="modal-overlay" onClick={() => { setShowTrfCreate(false); resetTrfForm() }}>
          <div className="modal" style={{ maxWidth: 680 }} onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Новая передача запчастей</h3>
              <button className="modal-close" onClick={() => { setShowTrfCreate(false); resetTrfForm() }}>×</button>
            </div>
            <div className="modal-body" style={{ maxHeight: '65vh', overflowY: 'auto' }}>
              {trfError && <div className="alert alert-error" style={{ marginBottom: 12 }}>{trfError}</div>}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div className="form-group">
                  <label className="form-label">Склад-источник <span className="required">*</span></label>
                  <select className="form-select" value={trfFrom}
                    onChange={e => setTrfFrom(e.target.value)}>
                    <option value="">Выберите...</option>
                    {warehouseList.map(w => (
                      <option key={w.id} value={w.id}>
                        {w.name} ({w.type === 'company' ? 'компания' : 'банк'})
                      </option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Склад банка-получателя <span className="required">*</span></label>
                  <select className="form-select" value={trfTo}
                    onChange={e => setTrfTo(e.target.value)}>
                    <option value="">Выберите...</option>
                    {bankWarehouses.map(w => (
                      <option key={w.id} value={w.id}>{w.name}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Дата передачи <span className="required">*</span></label>
                  <input type="date" className="form-input" value={trfDate}
                    onChange={e => setTrfDate(e.target.value)} />
                </div>
                <div className="form-group">
                  <label className="form-label">Примечание</label>
                  <input type="text" className="form-input" value={trfNotes}
                    onChange={e => setTrfNotes(e.target.value)} />
                </div>
              </div>

              <div style={{ marginTop: 16 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <strong style={{ fontSize: 14 }}>Запчасти</strong>
                  <button type="button" className="btn btn-secondary btn-sm"
                    onClick={() => setTrfItems(prev => [...prev, { ...EMPTY_TRF_ITEM }])}>
                    + Добавить строку
                  </button>
                </div>
                <table className="table" style={{ fontSize: 13 }}>
                  <thead>
                    <tr>
                      <th>Запчасть</th>
                      <th style={{ width: 90 }}>Кол-во</th>
                      <th style={{ width: 36 }}></th>
                    </tr>
                  </thead>
                  <tbody>
                    {trfItems.map((item, idx) => (
                      <tr key={idx}>
                        <td>
                          <select className="form-select" value={item.part_id}
                            onChange={e => setTrfItems(prev => prev.map((it, i) => i === idx ? { ...it, part_id: e.target.value } : it))}>
                            <option value="">Выберите...</option>
                            {allParts.map(p => (
                              <option key={p.id} value={p.id}>{p.name} ({p.sku})</option>
                            ))}
                          </select>
                        </td>
                        <td>
                          <input type="number" min="1" className="form-input" value={item.quantity}
                            onChange={e => setTrfItems(prev => prev.map((it, i) => i === idx ? { ...it, quantity: e.target.value } : it))} />
                        </td>
                        <td>
                          {trfItems.length > 1 && (
                            <button type="button" className="btn btn-secondary btn-sm" style={{ padding: '2px 8px' }}
                              onClick={() => setTrfItems(prev => prev.filter((_, i) => i !== idx))}>×</button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary"
                onClick={() => { setShowTrfCreate(false); resetTrfForm() }}>Отмена</button>
              <button type="button" className="btn btn-primary" onClick={submitTrfForm}
                disabled={createTrfMut.isPending}>
                {createTrfMut.isPending ? 'Создание...' : 'Создать черновик'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* View Transfer */}
      {viewTransfer && (
        <div className="modal-overlay" onClick={() => setViewTransfer(null)}>
          <div className="modal" style={{ maxWidth: 680 }} onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Передача {viewTransfer.transfer_number}</h3>
              <button className="modal-close" onClick={() => setViewTransfer(null)}>×</button>
            </div>
            <div className="modal-body">
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 13, marginBottom: 16 }}>
                <div><span style={{ color: 'var(--text-muted)' }}>Откуда:</span> {viewTransfer.from_warehouse_name}</div>
                <div><span style={{ color: 'var(--text-muted)' }}>Куда:</span> {viewTransfer.to_warehouse_name}</div>
                <div><span style={{ color: 'var(--text-muted)' }}>Дата:</span> {viewTransfer.transfer_date}</div>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Статус: </span>
                  <span className={`badge ${STATUS_CLASS[viewTransfer.status] ?? ''}`}>
                    {STATUS_LABEL[viewTransfer.status] ?? viewTransfer.status}
                  </span>
                </div>
                {viewTransfer.notes && (
                  <div style={{ gridColumn: '1 / -1' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Примечание:</span> {viewTransfer.notes}
                  </div>
                )}
              </div>
              <table className="table" style={{ fontSize: 13 }}>
                <thead>
                  <tr><th>SKU</th><th>Запчасть</th><th>Кол-во</th><th>В наличии</th></tr>
                </thead>
                <tbody>
                  {viewTransfer.items.map(item => (
                    <tr key={item.id}>
                      <td><span style={{ fontFamily: 'monospace', fontSize: 11 }}>{item.part_sku}</span></td>
                      <td>{item.part_name}</td>
                      <td>{item.quantity}</td>
                      <td style={{ color: item.available_qty < item.quantity ? 'var(--danger, #dc2626)' : 'var(--text-muted)' }}>
                        {item.available_qty}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" onClick={() => setViewTransfer(null)}>Закрыть</button>
              {canWrite && viewTransfer.status === 'draft' && (
                <>
                  <button type="button" className="btn btn-secondary"
                    onClick={() => cancelTrfMut.mutate(viewTransfer.id)}
                    disabled={cancelTrfMut.isPending}>
                    Отменить
                  </button>
                  <button type="button" className="btn btn-primary"
                    onClick={() => postTrfMut.mutate(viewTransfer.id)}
                    disabled={postTrfMut.isPending}>
                    {postTrfMut.isPending ? 'Проведение...' : 'Провести'}
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  )
}
