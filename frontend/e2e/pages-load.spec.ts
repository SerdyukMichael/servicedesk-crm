/**
 * E2E — Pages load without errors
 * Regression suite: equipment, parts (склад), invoices showed "ошибка загрузки"
 * because list endpoints still returned {skip,limit,has_more} after PaginatedResponse
 * was changed to require {page,size,pages} — Pydantic validation failure → HTTP 500.
 */
import { test, expect } from '@playwright/test'
import { login, ADMIN, MANAGER } from './helpers'

// ─── Helper ────────────────────────────────────────────────────────────────

async function captureApiStatus(page: import('@playwright/test').Page, pattern: string) {
  let status = 0
  page.on('response', r => {
    if (r.url().includes(pattern)) status = r.status()
  })
  return () => status
}

// ─── Equipment ─────────────────────────────────────────────────────────────

test.describe('Equipment page', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, ADMIN)
    await page.goto('/equipment')
    await page.waitForLoadState('networkidle')
  })

  test('renders equipment page heading', async ({ page }) => {
    await expect(page.locator('h1, h2').filter({ hasText: /оборудован/i })).toBeVisible()
  })

  test('shows table or empty state (no error banner)', async ({ page }) => {
    const errorBanner = page.locator('.alert-error').filter({ hasText: /ошибка|error/i })
    await expect(errorBanner).not.toBeVisible()
    const content = page.locator('table, .table-wrap, .loading-center')
    await expect(content.first()).toBeVisible({ timeout: 10000 })
  })
})

test.describe('Equipment page — no load errors', () => {
  test('equipment API returns 200 with page/size/pages', async ({ page }) => {
    await login(page, ADMIN)
    let body: Record<string, unknown> = {}
    page.on('response', async r => {
      if (r.url().includes('/api/v1/equipment') && r.status() === 200) {
        body = await r.json().catch(() => ({}))
      }
    })
    await page.goto('/equipment')
    await page.waitForLoadState('networkidle')
    expect(body.page).toBeDefined()
    expect(body.size).toBeDefined()
    expect(body.pages).toBeDefined()
    expect(typeof body.total).toBe('number')
  })

  test('equipment page loads without JS errors', async ({ page }) => {
    const errors: string[] = []
    page.on('pageerror', err => errors.push(err.message))
    await login(page, ADMIN)
    await page.goto('/equipment')
    await page.waitForLoadState('networkidle')
    await expect(page.locator('h1, h2').filter({ hasText: /оборудован/i })).toBeVisible()
    expect(errors, `JS errors: ${errors.join('; ')}`).toHaveLength(0)
  })
})

// ─── Parts (Склад) ─────────────────────────────────────────────────────────

test.describe('Parts page (Склад)', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, ADMIN)
    await page.goto('/parts')
    await page.waitForLoadState('networkidle')
  })

  test('renders parts page heading', async ({ page }) => {
    await expect(page.locator('h1, h2').filter({ hasText: /склад|запчаст|детал/i })).toBeVisible()
  })

  test('shows table or empty state (no error banner)', async ({ page }) => {
    const errorBanner = page.locator('.alert-error').filter({ hasText: /ошибка|error/i })
    await expect(errorBanner).not.toBeVisible()
    const content = page.locator('table, .table-wrap, .loading-center')
    await expect(content.first()).toBeVisible({ timeout: 10000 })
  })
})

test.describe('Parts page — no load errors', () => {
  test('parts API returns 200 with page/size/pages', async ({ page }) => {
    await login(page, ADMIN)
    let body: Record<string, unknown> = {}
    page.on('response', async r => {
      if (r.url().includes('/api/v1/parts') && r.status() === 200) {
        body = await r.json().catch(() => ({}))
      }
    })
    await page.goto('/parts')
    await page.waitForLoadState('networkidle')
    expect(body.page).toBeDefined()
    expect(body.size).toBeDefined()
    expect(body.pages).toBeDefined()
    expect(typeof body.total).toBe('number')
  })

  test('parts page loads without JS errors', async ({ page }) => {
    const errors: string[] = []
    page.on('pageerror', err => errors.push(err.message))
    await login(page, ADMIN)
    await page.goto('/parts')
    await page.waitForLoadState('networkidle')
    await expect(page.locator('h1, h2').filter({ hasText: /склад|запчаст|детал/i })).toBeVisible()
    expect(errors, `JS errors: ${errors.join('; ')}`).toHaveLength(0)
  })
})

// ─── Invoices (Счета) ──────────────────────────────────────────────────────

test.describe('Invoices page (Счета)', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, ADMIN)
    await page.goto('/invoices')
    await page.waitForLoadState('networkidle')
  })

  test('renders invoices page heading', async ({ page }) => {
    await expect(page.locator('h1, h2').filter({ hasText: /счет|инвойс|invoice/i })).toBeVisible()
  })

  test('shows table or empty state (no error banner)', async ({ page }) => {
    const errorBanner = page.locator('.alert-error').filter({ hasText: /ошибка|error/i })
    await expect(errorBanner).not.toBeVisible()
    const content = page.locator('table, .table-wrap, .loading-center')
    await expect(content.first()).toBeVisible({ timeout: 10000 })
  })
})

test.describe('Invoices page — no load errors', () => {
  test('invoices API returns 200 with page/size/pages', async ({ page }) => {
    await login(page, ADMIN)
    let body: Record<string, unknown> = {}
    page.on('response', async r => {
      if (r.url().includes('/api/v1/invoices') && r.status() === 200) {
        body = await r.json().catch(() => ({}))
      }
    })
    await page.goto('/invoices')
    await page.waitForLoadState('networkidle')
    expect(body.page).toBeDefined()
    expect(body.size).toBeDefined()
    expect(body.pages).toBeDefined()
    expect(typeof body.total).toBe('number')
  })

  test('invoices page loads without JS errors', async ({ page }) => {
    const errors: string[] = []
    page.on('pageerror', err => errors.push(err.message))
    await login(page, ADMIN)
    await page.goto('/invoices')
    await page.waitForLoadState('networkidle')
    await expect(page.locator('h1, h2').filter({ hasText: /счет|инвойс|invoice/i })).toBeVisible()
    expect(errors, `JS errors: ${errors.join('; ')}`).toHaveLength(0)
  })
})
