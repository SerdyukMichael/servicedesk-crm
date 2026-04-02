/**
 * E2E — Gray overlay regression
 *
 * Reproduces the bug: after login the user is on /tickets but the entire page
 * is covered by a semi-transparent overlay (.modal-overlay) and the app is
 * completely unresponsive.
 *
 * Root causes fixed:
 *  1. LoginPage was not protected against rendering when a token already exists
 *     → in React 18 concurrent transitions, it could render on top of the
 *       authenticated layout, and any open modal in a previous page visit
 *       could survive the transition.
 *  2. App.tsx had a duplicate root path="*" <Navigate to="/"> that could
 *     trigger a redirect loop during route evaluation, leaving the app in
 *     an indeterminate render state.
 *  3. `from` could be set to "/login" causing an infinite redirect cycle.
 */
import { test, expect } from '@playwright/test'
import { login, logout, ADMIN, ENGINEER, MANAGER } from './helpers'

// ─── No overlay on /tickets after login ─────────────────────────────────────

test.describe('No gray overlay after login', () => {
  test('admin: no modal-overlay on /tickets after login', async ({ page }) => {
    await login(page, ADMIN)
    await expect(page).toHaveURL(/\/tickets/)
    // The modal-overlay must NOT exist in the DOM (or be hidden)
    const overlay = page.locator('.modal-overlay')
    await expect(overlay).toHaveCount(0)
  })

  test('engineer: no modal-overlay on /tickets after login', async ({ page }) => {
    await login(page, ENGINEER)
    await expect(page).toHaveURL(/\/tickets/)
    const overlay = page.locator('.modal-overlay')
    await expect(overlay).toHaveCount(0)
  })

  test('manager: no modal-overlay on /tickets after login', async ({ page }) => {
    await login(page, MANAGER)
    await expect(page).toHaveURL(/\/tickets/)
    const overlay = page.locator('.modal-overlay')
    await expect(overlay).toHaveCount(0)
  })

  test('/tickets page is interactive after login — sidebar links are clickable', async ({ page }) => {
    await login(page, ADMIN)
    await expect(page).toHaveURL(/\/tickets/)

    // Verify no overlay is blocking pointer events
    const overlay = page.locator('.modal-overlay')
    await expect(overlay).toHaveCount(0)

    // Should be able to click a sidebar link
    const clientsLink = page.getByRole('link', { name: /клиенты/i })
    await expect(clientsLink).toBeVisible()
    await clientsLink.click()
    await expect(page).toHaveURL(/\/clients/)
  })

  test('page header and content area are visible and unobstructed', async ({ page }) => {
    await login(page, ADMIN)
    await expect(page).toHaveURL(/\/tickets/)

    // The main page heading must be visible (would be hidden behind an overlay)
    await expect(page.locator('h1').filter({ hasText: /заявк/i })).toBeVisible()

    // Page content area is reachable
    await expect(page.locator('.page-content, main').first()).toBeVisible()
  })
})

// ─── LoginPage redirect when already authenticated ───────────────────────────

test.describe('LoginPage redirects authenticated users', () => {
  test('visiting /login while authenticated redirects to /tickets', async ({ page }) => {
    await login(page, ADMIN)
    await expect(page).toHaveURL(/\/tickets/)

    // Navigate to /login directly while still logged in
    await page.goto('/login')

    // Should be immediately redirected away from /login
    await expect(page).not.toHaveURL(/\/login/)
    await expect(page).toHaveURL(/\/tickets/)
  })

  test('login form does not render when token is present', async ({ page }) => {
    await login(page, ADMIN)
    await page.goto('/login')

    // The login form inputs must NOT be present (user was redirected)
    await expect(page.getByLabel('Email')).not.toBeVisible()
    await expect(page.getByLabel('Пароль')).not.toBeVisible()
  })
})

// ─── from-redirect sanitisation ─────────────────────────────────────────────

test.describe('from-redirect sanitisation', () => {
  test('after logout and re-login, lands on /tickets not stuck on /login', async ({ page }) => {
    await login(page, ADMIN)
    await logout(page)

    // Re-login from a clean state
    await login(page, ADMIN)
    await expect(page).toHaveURL(/\/tickets/)
    await expect(page.locator('.modal-overlay')).toHaveCount(0)
  })

  test('no JS errors on /tickets after login', async ({ page }) => {
    const jsErrors: string[] = []
    page.on('pageerror', err => jsErrors.push(err.message))

    await login(page, ADMIN)
    await expect(page).toHaveURL(/\/tickets/)
    await page.waitForLoadState('networkidle')

    expect(jsErrors, `JS errors after login: ${jsErrors.join('; ')}`).toHaveLength(0)
  })
})
