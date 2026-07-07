import { test, expect } from '@playwright/test'
import { setupMocks } from './mock'

test.describe('Projects page + navigation', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page)
  })

  test('lists projects at /projects', async ({ page }) => {
    await page.goto('/projects')
    await expect(page.getByRole('heading', { name: 'Projects' })).toBeVisible()
    await expect(page.getByText('Acme MVP')).toBeVisible()
  })

  test('header exposes Canvas and Projects navigation', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('link', { name: 'Canvas' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Projects' })).toBeVisible()
  })
})
