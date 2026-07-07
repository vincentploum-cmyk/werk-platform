import { test, expect } from '@playwright/test'
import { setupMocks } from './mock'

test.describe('Project view, kanban board, and the workflow gate', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page, {
      tasks: [
        {
          id: 't1', project_id: 'p1', title: 'Generate PRD', description: null,
          status: 'done', assigned_agent_id: 'a-req', parent_task_id: null, priority: 0,
          artifacts: [], result: 'PRD content', created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ],
    })
  })

  test('shows the board and the Run full workflow control', async ({ page }) => {
    await page.goto('/project/p1')
    await expect(page.getByRole('button', { name: /Run full workflow/ })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Generate PRD' })).toBeVisible()
  })

  test('back link returns to the Projects list', async ({ page }) => {
    await page.goto('/project/p1')
    await expect(page.getByRole('link', { name: '← Projects' })).toBeVisible()
  })
})
