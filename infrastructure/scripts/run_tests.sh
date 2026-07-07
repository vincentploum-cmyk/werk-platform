#!/bin/bash
# Run the full Werk test suite: backend (offline) + frontend E2E.
set -e

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

echo "=== Backend tests (in-process: SQLite + fakeredis, no external services) ==="
cd "$ROOT/backend"
python -m pytest tests/

echo ""
echo "=== Frontend E2E (Playwright) ==="
cd "$ROOT/frontend"
# one-time: npx playwright install chromium
npx playwright test

echo ""
echo "=== All tests passed! ==="
