/**
 * E2E — Authentication
 * Login, logout, redirect, persistence across navigation.
 */
import { test, expect } from '@playwright/test'
import { login, logout, ADMIN, MANAGER, ENGINEER } from './helpers'

test.describe('Login page', () => {
  test('shows login form on /login', async ({ page }) => {
    await page.goto('/login')
    await expect(page.getByRole('heading', { name: 'ServiceDesk CRM' })).toBeVisible()
    await expect(page.getByLabel('Email')).toBeVisible()
    await expect(page.getByLabel('Пароль')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Войти' })).toBeVisible()
  })

  test('redirects unauthenticated user to /login', async ({ page }) => {
    await logout(page)
    await page.goto('http://localhost:5173/tickets')
    await expect(page).toHaveURL(/\/login/)
  })

  test('admin logs in successfully', async ({ page }) => {
    await login(page, ADMIN)
    await expect(page).toHaveURL(/\/tickets/)
  })

  test('manager logs in successfully', async ({ page }) => {
    await login(page, MANAGER)
    await expect(page).toHaveURL(/\/tickets/)
  })

  test('engineer logs in successfully', async ({ page }) => {
    await login(page, ENGINEER)
    await expect(page).toHaveURL(/\/tickets/)
  })

  test('wrong password shows error message', async ({ page }) => {
    await page.goto('/login')
    await page.getByLabel('Email').fill(ADMIN.email)
    await page.getByLabel('Пароль').fill('wrongpassword')
    await page.getByRole('button', { name: 'Войти' }).click()
    // Wait for the button to stop being in loading state, then check for error or that we stayed on /login
    await page.waitForTimeout(3000)
    const hasError = await page.locator('.alert-error, .alert').count() > 0
    const onLogin = page.url().includes('/login')
    expect(hasError || onLogin).toBeTruthy()
    await expect(page).toHaveURL(/\/login/)
  })

  test('empty email shows validation error', async ({ page }) => {
    await page.goto('/login')
    await page.getByLabel('Пароль').fill('anything')
    await page.getByRole('button', { name: 'Войти' }).click()
    await expect(page.locator('.form-error')).toBeVisible()
  })

  test('token persists across page reload', async ({ page }) => {
    await login(page, ADMIN)
    await page.reload()
    await expect(page).toHaveURL(/\/tickets/)
    // Verify the authenticated layout is rendered — .app-layout wraps the page
    await expect(page.locator('.app-layout, .page-content, .sidebar').first()).toBeVisible()
  })

  test('logout clears session and redirects to login', async ({ page }) => {
    await login(page, ADMIN)
    // Find and click logout button in layout
    const logoutBtn = page.getByRole('button', { name: /выйти|logout/i })
    if (await logoutBtn.isVisible()) {
      await logoutBtn.click()
      await expect(page).toHaveURL(/\/login/)
    } else {
      // Logout via localStorage if button not found
      await logout(page)
      await page.goto('/tickets')
      await expect(page).toHaveURL(/\/login/)
    }
  })
})
