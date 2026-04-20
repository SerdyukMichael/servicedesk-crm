import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { useCurrency } from '../context/CurrencyContext'
import { updateCurrency } from '../api/endpoints'

export default function SettingsPage() {
  const { user } = useAuth()
  const { currency, reload } = useCurrency()
  const [code, setCode] = useState(currency.currency_code)
  const [name, setName] = useState(currency.currency_name)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    setCode(currency.currency_code)
    setName(currency.currency_name)
  }, [currency])

  const isAdmin = user?.roles?.includes('admin') ?? false

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

  return (
    <>
      <div className="page-header">
        <h1>Настройки системы</h1>
      </div>

      <div className="card" style={{ maxWidth: 560 }}>
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
              <button
                className="btn btn-primary"
                onClick={handleSave}
                disabled={saving}
              >
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
    </>
  )
}
