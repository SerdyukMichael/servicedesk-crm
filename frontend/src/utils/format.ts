export function formatMoney(amount: string | number, currencyCode: string): string {
  const num = typeof amount === 'string' ? parseFloat(amount) : amount
  if (isNaN(num)) return `— ${currencyCode}`
  return `${num.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${currencyCode}`
}
