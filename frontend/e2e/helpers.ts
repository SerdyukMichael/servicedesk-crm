import { Page } from '@playwright/test'

export const ADMIN = { email: 'admin@example.com', password: 'ChangeMe123!' }
export const MANAGER = { email: 'manager@example.com', password: 'ChangeMe123!' }
export const ENGINEER = { email: 'engineer@example.com', password: 'ChangeMe123!' }

/** Login via UI form and wait for redirect away from /login */
export async function login(page: Page, creds = ADMIN) {
  await page.goto('/login')
  await page.getByLabel('Email').fill(creds.email)
  await page.getByLabel('Пароль').fill(creds.password)
  await page.getByRole('button', { name: 'Войти' }).click()
  await page.waitForURL(/\/(tickets|clients|equipment|parts|invoices|notifications|users)/, { timeout: 8000 })
}

/**
 * Clear auth state completely.
 * Must be on app origin (localhost:5173) to clear its localStorage.
 * Navigates to /login first if not already on the app, clears storage,
 * then navigates away so React unmounts and in-memory state is gone.
 */
export async function logout(page: Page) {
  const url = page.url()
  if (!url.includes('localhost:5173')) {
    await page.goto('http://localhost:5173/login', { waitUntil: 'domcontentloaded' })
  }
  await page.evaluate(() => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  })
  // Navigate away to fully unmount the React app so no in-memory token remains
  await page.goto('about:blank')
}
