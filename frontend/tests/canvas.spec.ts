import { test, expect } from '@playwright/test'
import { setupMocks, AGENTS } from './mock'

test.describe('Agent Canvas (landing page)', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page, {
      tasks: [
        { id: 't1', project_id: 'p1', title: 'Draft login requirements', description: null, status: 'backlog', assigned_agent_id: null, parent_task_id: null, priority: 0, artifacts: [], result: null, created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
      ],
    })
  })

  test('renders the canvas with all seven agents', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('heading', { name: 'Agent Canvas' })).toBeVisible()
    for (const a of AGENTS) {
      await expect(page.getByText(a.name, { exact: true }).first()).toBeVisible()
    }
  })

  test('shows the unassigned task tray', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('heading', { name: 'Unassigned tasks' })).toBeVisible()
    await expect(page.getByText('Draft login requirements', { exact: true })).toBeVisible()
  })

  test('clicking an agent opens its panel with tuning + chat sections', async ({ page }) => {
    await page.goto('/')
    await page.getByText('Requirements Agent', { exact: true }).first().click()
    await expect(page.getByRole('heading', { name: 'Instructions' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Examples' })).toBeVisible()
    await expect(page.getByText('Chat with', { exact: false })).toBeVisible()
  })

  test('can open the New Task modal', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: '+ New task' }).click()
    await expect(page.getByRole('heading', { name: 'New task' })).toBeVisible()
    await expect(page.getByPlaceholder('What needs to be done?')).toBeVisible()
  })
})
