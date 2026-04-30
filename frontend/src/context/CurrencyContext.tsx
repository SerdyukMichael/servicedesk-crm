import React, { createContext, useContext, useEffect, useState } from 'react'
import { getCurrency } from '../api/endpoints'
import type { CurrencySetting } from '../api/types'

interface CurrencyContextValue {
  currency: CurrencySetting
  reload: () => void
}

const DEFAULT: CurrencySetting = { currency_code: 'RUB', currency_name: 'Российский рубль' }

const CurrencyContext = createContext<CurrencyContextValue>({
  currency: DEFAULT,
  reload: () => {},
})

export const CurrencyProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currency, setCurrency] = useState<CurrencySetting>(DEFAULT)

  const load = () => {
    getCurrency().then(setCurrency).catch(() => {})
  }

  useEffect(() => {
    if (localStorage.getItem('token')) load()
  }, [])

  return (
    <CurrencyContext.Provider value={{ currency, reload: load }}>
      {children}
    </CurrencyContext.Provider>
  )
}

export const useCurrency = () => useContext(CurrencyContext)
