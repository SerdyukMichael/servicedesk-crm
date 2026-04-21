import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { useCurrency } from '../context/CurrencyContext'
import {
  updateCurrency,
  getExchangeRates,
  createExchangeRate,
  getExchangeRateHistory,
} from '../api/endpoints'
import type { ExchangeRate, ExchangeRateHistoryItem } from '../api/types'

const CURRENCY_OPTIONS = ['USD', 'EUR', 'RUB', 'KZT']

function todayDatetimeLocal() {
  const now = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}`
}

export default function SettingsPage() {
  const { user } = useAuth()
  const { currency, reload } = useCurrency()
  const [code, setCode] = useState(currency.currency_code)
  const [name, setName] = useState(currency.currency_name)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  // Exchange rates state
  const [rates, setRates] = useState<ExchangeRate[]>([])
  const [ratesLoading, setRatesLoading] = useState(false)
  const [newCurrency, setNewCurrency] = useState('USD')
  const [newRate, setNewRate] = useState('')
  const [newSetAt, setNewSetAt] = useState(todayDatetimeLocal)
  const [rateError, setRateError] = useState<string | null>(null)
  const [rateSaving, setRateSaving] = useState(false)
  const [historyFor, setHistoryFor] = useState<string | null>(null)
  const [history, setHistory] = useState<ExchangeRateHistoryItem[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyTotal, setHistoryTotal] = useState(0)
  const [historyPage, setHistoryPage] = useState(1)

  useEffect(() => {
    setCode(currency.currency_code)
    setName(currency.currency_name)
  }, [currency])

  useEffect(() => {
    loadRates()
  }, [])

  const loadRates = async () => {
    setRatesLoading(true)
    try {
      const data = await getExchangeRates()
      setRates(data)
    } finally {
      setRatesLoading(false)
    }
  }

  const loadHistory = async (cur: string, page = 1) => {
    setHistoryLoading(true)
    setHistoryPage(page)
    try {
      const data = await getExchangeRateHistory(cur, page, 10)
      setHistory(data.items)
      setHistoryTotal(data.total)
    } finally {
      setHistoryLoading(false)
    }
  }

  const openHistory = (cur: string) => {
    setHistoryFor(cur)
    loadHistory(cur, 1)
  }

  const closeHistory = () => {
    setHistoryFor(null)
    setHistory([])
  }

  const isAdmin = user?.roles?.includes('admin') ?? false
  const isAccountant = user?.roles?.includes('accountant') ?? false
  const canEditRates = isAdmin || isAccountant

  const handleSave = async () => {
    setError(null)
    setSuccess(false)
    if (!code.match(/^[A-Z]{3}$/)) {
      setError('Код валюты — 3 заглавные латинские буквы (например, RUB, USD, EUR)')
      return
    }
    if (!name.trim()) {
      setError('Наименование валюты не может быть пустым')
      return
    }
    setSaving(true)
    try {
      await updateCurrency({ currency_code: code, currency_name: name })
      reload()
      setSuccess(true)
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      setError(err?.response?.data?.detail || 'Ошибка сохранения')
    } finally {
      setSaving(false)
    }
  }

  const handleAddRate = async () => {
    setRateError(null)
    const rateVal = parseFloat(newRate)
    if (isNaN(rateVal) || rateVal <= 0) {
      setRateError('Курс должен быть положительным числом')
      return
    }
    setRateSaving(true)
    try {
      const payload: { currency: string; rate: string; set_at?: string } = {
        currency: newCurrency,
        rate: newRate,
      }
      if (newSetAt) payload.set_at = new Date(newSetAt).toISOString()
      await createExchangeRate(payload)
      setNewCurrency('USD')
      setNewRate('')
      setNewSetAt(todayDatetimeLocal())
      await loadRates()
      if (historyFor === newCurrency) {
        await loadHistory(newCurrency, 1)
      }
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      setRateError(err?.response?.data?.detail || 'Ошибка сохранения')
    } finally {
      setRateSaving(false)
    }
  }

  const formatRate = (rate: string) => {
    const n = parseFloat(rate)
    return isNaN(n) ? rate : n.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 4 })
  }

  // Только дата, без времени — для таблицы актуальных курсов
  const formatDateOnly = (dt: string) =>
    new Date(dt).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' })

  // Дата + время — для истории
  const formatDateTime = (dt: string) =>
    new Date(dt).toLocaleString('ru-RU', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    })

  const historyPages = Math.ceil(historyTotal / 10)

  return (
    <>
      <div className="page-header">
        <h1>Настройки системы</h1>
      </div>

      {/* Системная валюта */}
      <div className="card" style={{ maxWidth: 560, marginBottom: 24 }}>
        <div className="card-header">
          <h3>Системная валюта</h3>
        </div>
        <div className="card-body">
          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 20 }}>
            Код и наименование валюты отображаются во всех денежных значениях системы: счетах, складе, прайс-листе услуг.
          </p>

          <div className="form-row" style={{ marginBottom: 16 }}>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label">
                Код валюты (ISO 4217) <span className="required">*</span>
              </label>
              <input
                type="text"
                className="form-input"
                value={code}
                onChange={e => { setCode(e.target.value.toUpperCase()); setSuccess(false) }}
                maxLength={3}
                disabled={!isAdmin}
                placeholder="RUB"
              />
              <span style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4, display: 'block' }}>
                3 заглавные латинские буквы
              </span>
            </div>

            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label">
                Наименование валюты <span className="required">*</span>
              </label>
              <input
                type="text"
                className="form-input"
                value={name}
                onChange={e => { setName(e.target.value); setSuccess(false) }}
                disabled={!isAdmin}
                placeholder="Российский рубль"
              />
            </div>
          </div>

          {error && (
            <div className="alert alert-error" style={{ marginBottom: 16 }}>{error}</div>
          )}
          {success && (
            <div className="alert alert-success" style={{ marginBottom: 16 }}>
              ✓ Валюта успешно сохранена
            </div>
          )}

          {isAdmin ? (
            <div className="form-actions" style={{ marginTop: 0 }}>
              <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
                {saving ? 'Сохранение...' : 'Сохранить'}
              </button>
              <button
                className="btn btn-secondary"
                onClick={() => { setCode(currency.currency_code); setName(currency.currency_name); setError(null); setSuccess(false) }}
                disabled={saving}
              >
                Сбросить
              </button>
            </div>
          ) : (
            <div className="alert alert-info" style={{ marginTop: 0 }}>
              Изменение системной валюты доступно только администратору.
            </div>
          )}
        </div>
      </div>

      {/* Курсы иностранных валют */}
      <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start' }}>
        {/* Левая колонка: таблица + форма */}
        <div className="card" style={{ flex: '0 0 auto', width: 560 }}>
          <div className="card-header">
            <h3>Курсы иностранных валют</h3>
          </div>
          <div className="card-body">
            <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 20 }}>
              Курс показывает, сколько единиц системной валюты ({currency.currency_code}) стоит 1 единица иностранной валюты.
              История всех изменений сохраняется.
            </p>

            {/* Текущие курсы */}
            {ratesLoading ? (
              <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>Загрузка...</p>
            ) : rates.length === 0 ? (
              <p style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 20 }}>
                Курсы валют не установлены.
              </p>
            ) : (
              <table className="table" style={{ marginBottom: 24 }}>
                <thead>
                  <tr>
                    <th>Валюта</th>
                    <th style={{ textAlign: 'right' }}>Курс к {currency.currency_code}</th>
                    <th>Дата курса</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {rates.map(r => (
                    <tr key={r.currency}>
                      <td><strong>{r.currency}</strong></td>
                      <td style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
                        {formatRate(r.rate)}
                      </td>
                      <td style={{ color: 'var(--text-muted)', fontSize: 13 }}>{formatDateOnly(r.set_at)}</td>
                      <td>
                        <button
                          className="btn btn-link"
                          style={{ fontSize: 12, padding: '2px 8px' }}
                          onClick={() => historyFor === r.currency ? closeHistory() : openHistory(r.currency)}
                        >
                          {historyFor === r.currency ? 'Скрыть историю' : 'История'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            {/* Форма добавления */}
            {canEditRates ? (
              <div style={{ borderTop: '1px solid var(--border-color, #e5e7eb)', paddingTop: 20 }}>
                <h4 style={{ fontSize: 14, marginBottom: 12 }}>Установить курс</h4>
                <div className="form-row" style={{ marginBottom: 12, alignItems: 'flex-end', flexWrap: 'wrap', gap: 12 }}>
                  <div className="form-group" style={{ marginBottom: 0, flex: '0 0 120px' }}>
                    <label className="form-label">Валюта <span className="required">*</span></label>
                    <select
                      className="form-select"
                      value={newCurrency}
                      onChange={e => { setNewCurrency(e.target.value); setRateError(null) }}
                    >
                      {CURRENCY_OPTIONS.map(c => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group" style={{ marginBottom: 0, flex: '1 1 140px' }}>
                    <label className="form-label">Курс к {currency.currency_code} <span className="required">*</span></label>
                    <input
                      type="number"
                      className="form-input"
                      placeholder="450.00"
                      min="0.0001"
                      step="0.01"
                      value={newRate}
                      onChange={e => { setNewRate(e.target.value); setRateError(null) }}
                    />
                  </div>
                  <div className="form-group" style={{ marginBottom: 0, flex: '1 1 200px' }}>
                    <label className="form-label">Дата курса</label>
                    <input
                      type="datetime-local"
                      className="form-input"
                      value={newSetAt}
                      onChange={e => { setNewSetAt(e.target.value); setRateError(null) }}
                    />
                  </div>
                  <div style={{ flex: '0 0 auto', marginBottom: 0 }}>
                    <button
                      className="btn btn-primary"
                      onClick={handleAddRate}
                      disabled={rateSaving}
                      style={{ whiteSpace: 'nowrap' }}
                    >
                      {rateSaving ? 'Сохранение...' : 'Сохранить курс'}
                    </button>
                  </div>
                </div>
                {rateError && (
                  <div className="alert alert-error">{rateError}</div>
                )}
              </div>
            ) : (
              <div className="alert alert-info">
                Установка курсов доступна администратору и бухгалтеру.
              </div>
            )}
          </div>
        </div>

        {/* Правая колонка: история выбранной валюты */}
        {historyFor && (
          <div className="card" style={{ flex: '1 1 0', minWidth: 0 }}>
            <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ margin: 0 }}>История курса {historyFor}</h3>
              <span style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 400 }}>всего: {historyTotal}</span>
            </div>
            <div className="card-body">
              {historyLoading ? (
                <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Загрузка...</p>
              ) : (
                <>
                  <table className="table" style={{ fontSize: 13 }}>
                    <thead>
                      <tr>
                        <th style={{ textAlign: 'right' }}>Курс к {currency.currency_code}</th>
                        <th>Дата курса</th>
                        <th>Добавлено</th>
                        <th>Установил</th>
                      </tr>
                    </thead>
                    <tbody>
                      {history.map(h => (
                        <tr key={h.id}>
                          <td style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>{formatRate(h.rate)}</td>
                          <td>{formatDateTime(h.set_at)}</td>
                          <td style={{ color: 'var(--text-muted)' }}>{formatDateTime(h.created_at)}</td>
                          <td style={{ color: 'var(--text-muted)' }}>{h.set_by_name}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {historyPages > 1 && (
                    <div style={{ display: 'flex', gap: 8, marginTop: 8, justifyContent: 'flex-end' }}>
                      <button
                        className="btn btn-secondary"
                        style={{ padding: '4px 12px', fontSize: 12 }}
                        disabled={historyPage <= 1}
                        onClick={() => loadHistory(historyFor, historyPage - 1)}
                      >
                        ← Пред.
                      </button>
                      <span style={{ fontSize: 12, lineHeight: '30px', color: 'var(--text-muted)' }}>
                        {historyPage} / {historyPages}
                      </span>
                      <button
                        className="btn btn-secondary"
                        style={{ padding: '4px 12px', fontSize: 12 }}
                        disabled={historyPage >= historyPages}
                        onClick={() => loadHistory(historyFor, historyPage + 1)}
                      >
                        След. →
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </>
  )
}
