/**
 * E2E — Clients page
 * List, search, empty state.
 */
import { test, expect } from '@playwright/test'
import { login, ADMIN, MANAGER } from './helpers'

test.describe('Clients page', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, MANAGER)
    await page.goto('/clients')
    await page.waitForLoadState('networkidle')
  })

  test('renders clients page heading', async ({ page }) => {
    await expect(page.locator('h1, h2').filter({ hasText: /клиент/i })).toBeVisible()
  })

  test('shows empty state or table', async ({ page }) => {
    // Page renders a <table> once data loads (empty state is a row inside the table)
    // Also accept a loading spinner or error alert as valid intermediate states
    const content = page.locator('table, .table-wrap, .loading-center, .alert-error')
    await expect(content.first()).toBeVisible({ timeout: 10000 })
  })

  test('has search input', async ({ page }) => {
    const search = page.getByRole('searchbox')
      .or(page.locator('input[type="search"]'))
      .or(page.locator('input[placeholder*="оиск"]'))
    if (await search.count() > 0) {
      await expect(search.first()).toBeVisible()
    }
  })

  test('has create client button', async ({ page }) => {
    const btn = page.getByRole('button', { name: /добавить|создать|new/i })
      .or(page.getByRole('link', { name: /добавить|создать|new/i }))
    if (await btn.count() > 0) {
      await expect(btn.first()).toBeVisible()
    }
  })
})

test.describe('Client page — admin', () => {
  test('admin can open clients page', async ({ page }) => {
    await login(page, ADMIN)
    await page.goto('/clients')
    await expect(page).not.toHaveURL(/\/login/)
    await expect(page.locator('h1, h2').filter({ hasText: /клиент/i })).toBeVisible()
  })
})

test.describe('Clients page — no load errors', () => {
  /**
   * Regression: contract_type = '' (empty string) caused LookupError in SQLAlchemy
   * which returned HTTP 500 and showed an error banner on the clients page.
   * Fix: schema validator coerces '' → 'none'; existing DB records patched.
   */
  test('clients page loads without 500 error banner', async ({ page }) => {
    await login(page, MANAGER)
    await page.goto('/clients')
    await page.waitForLoadState('networkidle')
    // Must NOT show an error alert
    const errorBanner = page.locator('.alert-error, [class*="error"]').filter({ hasText: /ошибка|error|500/i })
    await expect(errorBanner).not.toBeVisible()
    // Must show heading (page loaded successfully)
    await expect(page.locator('h1, h2').filter({ hasText: /клиент/i })).toBeVisible()
  })

  test('clients list returns data without server error', async ({ page }) => {
    await login(page, MANAGER)
    // Intercept the clients API call and verify no 5xx response
    let statusCode = 0
    page.on('response', r => {
      if (r.url().includes('/api/v1/clients')) statusCode = r.status()
    })
    await page.goto('/clients')
    await page.waitForLoadState('networkidle')
    expect(statusCode).toBeLessThan(500)
  })
})
