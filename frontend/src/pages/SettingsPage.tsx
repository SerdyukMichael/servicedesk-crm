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
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Ошибка сохранения')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="p-6 max-w-lg">
      <h1 className="text-2xl font-bold mb-6">Настройки системы</h1>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Системная валюта</h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Код валюты (ISO 4217)
            </label>
            <input
              type="text"
              value={code}
              onChange={e => setCode(e.target.value.toUpperCase())}
              maxLength={3}
              disabled={!isAdmin}
              placeholder="RUB"
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm disabled:bg-gray-50 disabled:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Наименование валюты
            </label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              disabled={!isAdmin}
              placeholder="Российский рубль"
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm disabled:bg-gray-50 disabled:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {error && (
            <div className="text-red-600 text-sm">{error}</div>
          )}
          {success && (
            <div className="text-green-600 text-sm">Валюта успешно сохранена</div>
          )}

          {isAdmin && (
            <button
              onClick={handleSave}
              disabled={saving}
              className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? 'Сохранение...' : 'Сохранить'}
            </button>
          )}

          {!isAdmin && (
            <p className="text-sm text-gray-500">Изменение валюты доступно только администратору.</p>
          )}
        </div>
      </div>
    </div>
  )
}
