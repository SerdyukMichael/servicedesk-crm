/**
 * E2E — Users page
 * List, roles rendering, no blank screen.
 */
import { test, expect } from '@playwright/test'
import { login, ADMIN } from './helpers'

test.describe('Users page', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, ADMIN)
    await page.goto('/users')
    await page.waitForLoadState('networkidle')
  })

  test('renders users page heading', async ({ page }) => {
    await expect(page.locator('h1, h2').filter({ hasText: /пользоват/i })).toBeVisible()
  })

  test('shows table with users (not blank)', async ({ page }) => {
    await expect(page.locator('table')).toBeVisible({ timeout: 10000 })
    // At least one user row should appear (seeded users exist)
    const rows = page.locator('table tbody tr')
    await expect(rows.first()).toBeVisible()
  })

  test('shows Add User button for admin', async ({ page }) => {
    const btn = page.getByRole('button', { name: /добавить|создать/i })
    await expect(btn.first()).toBeVisible()
  })
})

test.describe('Users page — no load errors', () => {
  /**
   * Regression: PaginatedResponse mismatch — backend returned {skip,limit,has_more}
   * but frontend expected {page,size,pages} → Pagination component received undefined
   * values → NaN arithmetic → rendering broke, showing blank screen.
   * Also: UserResponse.roles was stored as JSON string in SQLite; user.roles.map()
   * would throw TypeError if roles wasn't parsed to array.
   * Fix: backend now returns {page,size,pages}; added field_validator for roles.
   */
  test('users page loads without blank screen', async ({ page }) => {
    await login(page, ADMIN)
    // Listen for any unhandled errors
    const errors: string[] = []
    page.on('pageerror', err => errors.push(err.message))
    await page.goto('/users')
    await page.waitForLoadState('networkidle')
    // Page must show content, not blank
    await expect(page.locator('h1, h2').filter({ hasText: /пользоват/i })).toBeVisible()
    // No unhandled JS errors
    expect(errors, `JS errors: ${errors.join('; ')}`).toHaveLength(0)
  })

  test('users API returns paginated response with page/size/pages fields', async ({ page }) => {
    await login(page, ADMIN)
    let responseBody: Record<string, unknown> = {}
    page.on('response', async r => {
      if (r.url().includes('/api/v1/users') && r.status() === 200) {
        responseBody = await r.json().catch(() => ({}))
      }
    })
    await page.goto('/users')
    await page.waitForLoadState('networkidle')
    expect(typeof responseBody.page).toBe('number')
    expect(typeof responseBody.size).toBe('number')
    expect(typeof responseBody.pages).toBe('number')
    expect(Array.isArray(responseBody.items)).toBeTruthy()
  })

  test('roles are rendered as badges (not raw JSON string)', async ({ page }) => {
    await login(page, ADMIN)
    await page.goto('/users')
    await page.waitForLoadState('networkidle')
    // Role badges should show human-readable text, not JSON strings like '["admin"]'
    const rawJson = page.getByText(/\[".*"\]/)
    const visible = await rawJson.isVisible().catch(() => false)
    expect(visible).toBeFalsy()
    // Should show at least one role badge
    const roleBadge = page.locator('.badge').filter({ hasText: /Администратор|Инженер|Менеджер|Руководитель/i })
    await expect(roleBadge.first()).toBeVisible()
  })
})
