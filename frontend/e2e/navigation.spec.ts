/**
 * E2E — Navigation
 * SPA routing: sidebar links work without full page reload, back/forward work.
 */
import { test, expect } from '@playwright/test'
import { login, logout, ADMIN, MANAGER, ENGINEER } from './helpers'

test.describe('Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, ADMIN)
  })

  test('sidebar is visible after login', async ({ page }) => {
    await expect(page.locator('nav, .sidebar, aside').first()).toBeVisible()
  })

  test('navigate to Clients page', async ({ page }) => {
    await page.getByRole('link', { name: /клиенты/i }).click()
    await expect(page).toHaveURL(/\/clients/)
    await expect(page.locator('h1, h2').filter({ hasText: /клиент/i })).toBeVisible()
  })

  test('navigate to Equipment page', async ({ page }) => {
    await page.getByRole('link', { name: /оборудован/i }).click()
    await expect(page).toHaveURL(/\/equipment/)
  })

  test('navigate to Parts page', async ({ page }) => {
    await page.getByRole('link', { name: /склад|запчаст/i }).click()
    await expect(page).toHaveURL(/\/parts/)
  })

  test('navigate to Invoices page', async ({ page }) => {
    await page.getByRole('link', { name: /счет|счёт|invoic/i }).click()
    await expect(page).toHaveURL(/\/invoices/)
  })

  test('navigate to Notifications page', async ({ page }) => {
    await page.getByRole('link', { name: /уведомл/i }).click()
    await expect(page).toHaveURL(/\/notifications/)
  })

  test('navigate to Users page (admin only)', async ({ page }) => {
    await page.getByRole('link', { name: /пользоват/i }).click()
    await expect(page).toHaveURL(/\/users/)
  })

  test('navigate back to Tickets from Clients', async ({ page }) => {
    await page.getByRole('link', { name: /клиенты/i }).click()
    await expect(page).toHaveURL(/\/clients/)
    await page.getByRole('link', { name: /заявк/i }).click()
    await expect(page).toHaveURL(/\/tickets/)
  })

  test('browser back button works', async ({ page }) => {
    await page.getByRole('link', { name: /клиенты/i }).click()
    await expect(page).toHaveURL(/\/clients/)
    await page.goBack()
    await expect(page).toHaveURL(/\/tickets/)
  })

  test('no re-login required between pages', async ({ page }) => {
    // Navigate to several pages in sequence — should stay logged in throughout
    const links = [/клиенты/i, /оборудован/i, /заявк/i]
    for (const name of links) {
      const link = page.getByRole('link', { name })
      if (await link.isVisible()) {
        await link.click()
        await page.waitForLoadState('networkidle')
        await expect(page).not.toHaveURL(/\/login/)
      }
    }
  })

  test('engineer sees tickets page without re-login', async ({ page }) => {
    await logout(page)
    await login(page, ENGINEER)
    await expect(page).toHaveURL(/\/tickets/)
    await expect(page).not.toHaveURL(/\/login/)
  })

  test('direct URL navigation stays logged in', async ({ page }) => {
    await page.goto('/clients')
    await expect(page).not.toHaveURL(/\/login/)
    await page.goto('/equipment')
    await expect(page).not.toHaveURL(/\/login/)
  })
})
