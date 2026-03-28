/**
 * E2E — Role-Based Access Control
 * Checks that the UI enforces permissions correctly per role.
 */
import { test, expect } from '@playwright/test'
import { login, logout, ADMIN, MANAGER, ENGINEER } from './helpers'

test.describe('RBAC — Admin', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, ADMIN)
  })

  test('admin sees Users link in sidebar', async ({ page }) => {
    await expect(page.getByRole('link', { name: /пользоват/i })).toBeVisible()
  })

  test('admin can access /users via sidebar link', async ({ page }) => {
    // Monitor API responses to detect unexpected 401s
    const apiErrors: string[] = []
    page.on('response', r => {
      if (r.url().includes('/api/') && r.status() === 401) {
        apiErrors.push(`401 on ${r.url()}`)
      }
    })
    await page.getByRole('link', { name: /пользоват/i }).click()
    await expect(page).toHaveURL(/\/users/)
    // Wait briefly for any pending API calls
    await page.waitForTimeout(1500)
    // Verify no 401 caused a redirect to login
    expect(apiErrors, `Unexpected 401s: ${apiErrors.join(', ')}`).toHaveLength(0)
    await expect(page).not.toHaveURL(/\/login/)
  })

  test('admin sees all nav items', async ({ page }) => {
    await expect(page.locator('.sidebar').first()).toBeVisible()
    await expect(page.getByRole('link', { name: /заявк/i })).toBeVisible()
    await expect(page.getByRole('link', { name: /клиент/i })).toBeVisible()
  })
})

test.describe('RBAC — Engineer', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, ENGINEER)
  })

  test('engineer lands on tickets page', async ({ page }) => {
    await expect(page).toHaveURL(/\/tickets/)
  })

  test('engineer cannot access /users', async ({ page }) => {
    await page.goto('/users')
    await page.waitForLoadState('domcontentloaded')
    // PrivateRoute shows forbidden view at /users URL — check for lock icon or "нет доступа" text
    const noAccess = page.getByText(/нет доступа/i)
    const lock = page.getByText('🔒')
    const redirectedToLogin = page.url().includes('/login')
    const hasForbidden = await noAccess.isVisible().catch(() => false)
      || await lock.isVisible().catch(() => false)
    expect(hasForbidden || redirectedToLogin).toBeTruthy()
  })

  test('engineer does not see Users link', async ({ page }) => {
    const usersLink = page.getByRole('link', { name: /^пользоват/i })
    const visible = await usersLink.isVisible().catch(() => false)
    expect(visible).toBeFalsy()
  })
})

test.describe('RBAC — Manager', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, MANAGER)
  })

  test('manager can see tickets', async ({ page }) => {
    await page.goto('/tickets')
    await expect(page).not.toHaveURL(/\/login/)
  })

  test('manager can see clients', async ({ page }) => {
    await page.goto('/clients')
    await expect(page).not.toHaveURL(/\/login/)
  })
})

test.describe('Unauthenticated access', () => {
  test('/ redirects to /login when not logged in', async ({ page }) => {
    await logout(page)
    await page.goto('http://localhost:5173/')
    await expect(page).toHaveURL(/\/login/)
  })

  test('/tickets redirects to /login when not logged in', async ({ page }) => {
    await logout(page)
    await page.goto('http://localhost:5173/tickets')
    await expect(page).toHaveURL(/\/login/)
  })

  test('/users redirects to /login when not logged in', async ({ page }) => {
    await logout(page)
    await page.goto('http://localhost:5173/users')
    await expect(page).toHaveURL(/\/login/)
  })
})
