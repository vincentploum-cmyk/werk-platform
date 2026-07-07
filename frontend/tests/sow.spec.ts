import { test, expect } from '@playwright/test'
import { setupMocks } from './mock'

test.describe('SOW intake — upload, extract parameters, deploy team', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page)
  })

  test('upload → extract parameters → review team → deploy', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: 'Deploy from SOW' }).click()
    await expect(page.getByRole('heading', { name: /Deploy a team from a signed SOW/ })).toBeVisible()

    // upload an SOW into the (hidden) file input
    await page.locator('input[type="file"]').setInputFiles({
      name: 'sow.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('Hybrid delivery, 3 releases across US and UK, 5 test cycles.'),
    })
    await page.getByRole('button', { name: 'Analyze SOW' }).click()

    // critical parameters were extracted and populated
    await expect(page.getByText('Project parameters', { exact: false })).toBeVisible()
    await expect(page.getByLabel('Delivery approach')).toHaveValue('hybrid')

    // the team is shown, derived from the parameters
    await expect(page.getByRole('heading', { name: /Recommended team/ })).toBeVisible()
    await expect(page.getByText('UX Agent', { exact: true })).toBeVisible()

    // recompute, then deploy
    await page.getByRole('button', { name: /Update recommended team/ }).click()
    await page.getByRole('button', { name: /Deploy \d+ agents/ }).click()
  })
})
