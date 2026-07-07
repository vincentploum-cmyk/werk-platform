import { test, expect } from '@playwright/test'
import { setupMocks } from './mock'

test.describe('Agent tuning (instructions + examples)', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page)
  })

  test('can edit and save an agent’s instructions', async ({ page }) => {
    await page.goto('/')
    await page.getByText('Architect Agent', { exact: true }).first().click()

    // expand the Instructions editor
    await page.getByRole('heading', { name: 'Instructions' }).click()
    const box = page.locator('textarea').first()
    await expect(box).toBeVisible()
    await box.fill('Always propose two architecture options with trade-offs.')
    await page.getByRole('button', { name: 'Save instructions' }).click()
    await expect(page.getByText(/applies to new replies/i)).toBeVisible()
  })

  test('can add a few-shot example', async ({ page }) => {
    await page.goto('/')
    await page.getByText('Requirements Agent', { exact: true }).first().click()
    await page.getByRole('heading', { name: 'Examples' }).click()
    await page.getByRole('button', { name: '+ Add example' }).click()
    await expect(page.getByPlaceholder('…this is a good output.')).toBeVisible()
  })

  test('chat returns an agent reply', async ({ page }) => {
    await page.goto('/')
    await page.getByText('Requirements Agent', { exact: true }).first().click()
    await page.getByPlaceholder('Type a message…').fill('How do you start?')
    await page.getByRole('button', { name: 'Send' }).click()
    await expect(page.getByText('Here is how I would approach it.')).toBeVisible()
  })
})
