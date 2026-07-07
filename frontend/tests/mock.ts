import type { Page } from '@playwright/test'

// Shared API mocks so the UI specs run without a live backend.

export const AGENTS = [
  { id: 'a-req', name: 'Requirements Agent', type: 'functional', role: 'requirements', capabilities: ['prd-generation'], status: 'idle', created_at: new Date().toISOString(), instructions: 'You are the Requirements Agent.', instructions_custom: false, examples: [] },
  { id: 'a-ux', name: 'UX Agent', type: 'functional', role: 'ux', capabilities: ['wireframing'], status: 'idle', created_at: new Date().toISOString(), instructions: 'You are the UX Agent.', instructions_custom: false, examples: [] },
  { id: 'a-biz', name: 'Business Logic Agent', type: 'functional', role: 'business', capabilities: ['data-modeling'], status: 'idle', created_at: new Date().toISOString(), instructions: '', instructions_custom: false, examples: [] },
  { id: 'a-arch', name: 'Architect Agent', type: 'technical', role: 'architect', capabilities: ['system-design'], status: 'idle', created_at: new Date().toISOString(), instructions: '', instructions_custom: false, examples: [] },
  { id: 'a-dev', name: 'Developer Agent', type: 'technical', role: 'developer', capabilities: ['code-generation'], status: 'idle', created_at: new Date().toISOString(), instructions: '', instructions_custom: false, examples: [] },
  { id: 'a-test', name: 'Tester Agent', type: 'technical', role: 'tester', capabilities: ['unit-testing'], status: 'idle', created_at: new Date().toISOString(), instructions: '', instructions_custom: false, examples: [] },
  { id: 'a-ops', name: 'DevOps Agent', type: 'technical', role: 'devops', capabilities: ['ci-cd-config'], status: 'idle', created_at: new Date().toISOString(), instructions: '', instructions_custom: false, examples: [] },
]

export const PROJECTS = [
  { id: 'p1', name: 'Acme MVP', description: 'A test project', status: 'active', config: {}, created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
]

export async function setupMocks(page: Page, opts: { tasks?: unknown[] } = {}) {
  const tasks = opts.tasks ?? []

  // Catch-all (lowest priority) — any unlisted API call returns a benign OK.
  await page.route('**/api/v1/**', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: '{}' }),
  )

  await page.route('**/api/v1/auth/login', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ access_token: 'test-token', token_type: 'bearer', expires_in_minutes: 60 }) }),
  )
  await page.route(/\/api\/v1\/agents\/?(?:\?.*)?$/, (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ agents: AGENTS }) }),
  )
  await page.route('**/api/v1/agents/*/chat', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ agent_id: 'a-req', agent_name: 'Requirements Agent', role: 'requirements', reply: 'Here is how I would approach it.', source: 'persona' }) }),
  )
  await page.route(/\/api\/v1\/projects\/?(?:\?.*)?$/, (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ projects: PROJECTS }) }),
  )
  await page.route(/\/api\/v1\/tasks(?:\/.*)?(?:\?.*)?$/, (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ tasks }) }),
  )
  const SOW_AGENTS = [
    { role: 'requirements', name: 'Requirements Agent', rationale: 'Core role for every engagement.', instructions: 'You are the Requirements Agent.' },
    { role: 'ux', name: 'UX Agent', rationale: '2 countries', instructions: 'You are the UX Agent.' },
    { role: 'developer', name: 'Developer Agent', rationale: 'Implement the features.', instructions: 'You are the Developer Agent.' },
  ]
  const SOW_DEFS = [
    { key: 'approach', label: 'Delivery approach', type: 'select', options: ['agile', 'waterfall', 'devops', 'hybrid'] },
    { key: 'releases', label: 'Releases', type: 'number' },
    { key: 'test_cycles', label: 'Test cycles', type: 'number' },
    { key: 'countries', label: 'Countries', type: 'list' },
  ]
  await page.route('**/api/v1/sow/parameters/definitions', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ definitions: SOW_DEFS }) }),
  )
  await page.route('**/api/v1/sow/analyze', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
      project_name: 'Project Phoenix', summary: 'A customer portal', source: 'heuristic',
      filename: 'sow.txt', char_count: 200,
      parameters: { releases: 3, countries: ['US', 'UK'], test_cycles: 5, approach: 'hybrid' },
      definitions: SOW_DEFS,
      agents: SOW_AGENTS,
    }) }),
  )
  await page.route('**/api/v1/sow/team', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ agents: SOW_AGENTS }) }),
  )
  await page.route('**/api/v1/sow/deploy', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
      project_id: 'p-sow', project_name: 'Project Phoenix', tasks_created: 3,
      agents: [{ id: 'x', name: 'Requirements Agent', role: 'requirements', type: 'functional' }],
    }) }),
  )
}
