#!/usr/bin/env bash
# Werk Platform — end-to-end smoke test
# Exercises: health -> auth -> create project -> read back -> create task -> list
# -> verify row actually persisted in Postgres.
#
# Run from anywhere while the stack is up:  bash infrastructure/scripts/smoke_test.sh
set -uo pipefail

API="${API:-http://localhost:8000}"
COMPOSE_DIR="$(cd "$(dirname "$0")/.." && pwd)"   # -> infrastructure/
PASS=0; FAIL=0
ok()   { echo "  ✅ $1"; PASS=$((PASS+1)); }
bad()  { echo "  ❌ $1"; FAIL=$((FAIL+1)); }
hr()   { echo "────────────────────────────────────────────"; }

# tiny JSON field extractor (no jq dependency — uses python3, present on macOS)
field(){ python3 -c "import sys,json;print(json.load(sys.stdin).get('$1',''))" 2>/dev/null; }

echo "Werk smoke test → $API"
hr

# 1. Health ------------------------------------------------------------------
echo "1) Health check"
H=$(curl -fsS "$API/health" 2>/dev/null) && ok "GET /health → $H" || { bad "backend not reachable at $API"; echo "Is the stack up? (docker-compose ps)"; exit 1; }

# 2. Login -------------------------------------------------------------------
echo "2) Authenticate as admin"
TOKEN=$(curl -fsS -X POST "$API/api/v1/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' | field access_token)
[ -n "$TOKEN" ] && ok "got JWT (${TOKEN:0:18}…)" || { bad "login failed"; exit 1; }
AUTH=(-H "Authorization: Bearer $TOKEN")

# 3. Create project ----------------------------------------------------------
echo "3) Create project"
PNAME="Smoke Test $(date +%H%M%S)"
PROJ=$(curl -fsS -X POST "$API/api/v1/projects/" "${AUTH[@]}" \
  -H 'Content-Type: application/json' \
  -d "{\"name\":\"$PNAME\",\"description\":\"created by smoke_test.sh\"}")
PID=$(echo "$PROJ" | field id)
[ -n "$PID" ] && ok "created project id=$PID" || { bad "create project failed → $PROJ"; exit 1; }

# 4. Read it back ------------------------------------------------------------
echo "4) Read project back"
GOT=$(curl -fsS "$API/api/v1/projects/$PID" "${AUTH[@]}" | field name)
[ "$GOT" = "$PNAME" ] && ok "GET /projects/$PID returned matching name" || bad "readback mismatch (got '$GOT')"

# 5. Create task under it ----------------------------------------------------
echo "5) Create task in project"
TASK=$(curl -fsS -X POST "$API/api/v1/tasks/" "${AUTH[@]}" \
  -H 'Content-Type: application/json' \
  -d "{\"project_id\":\"$PID\",\"title\":\"Smoke task\",\"description\":\"e2e\"}")
TID=$(echo "$TASK" | field id)
TST=$(echo "$TASK" | field status)
[ -n "$TID" ] && ok "created task id=$TID status=$TST" || bad "create task failed → $TASK"

# 6. List tasks for project --------------------------------------------------
echo "6) List tasks for project"
CNT=$(curl -fsS "$API/api/v1/tasks/?project_id=$PID" "${AUTH[@]}" \
  | python3 -c "import sys,json;print(len(json.load(sys.stdin).get('tasks',[])))" 2>/dev/null)
[ "${CNT:-0}" -ge 1 ] && ok "task list returned $CNT task(s)" || bad "task not in list"

# 7. Verify persistence directly in Postgres --------------------------------
echo "7) Verify row in Postgres (request → DB path)"
ROW=$(cd "$COMPOSE_DIR" && docker-compose exec -T postgres \
  psql -U postgres -d werk -tAc \
  "SELECT name FROM projects WHERE id='$PID';" 2>/dev/null | tr -d '[:space:]')
[ "$ROW" = "${PNAME// /}" ] || [ -n "$ROW" ] && ok "row present in projects table: '$ROW'" || bad "row not found in DB"

hr
echo "Passed: $PASS   Failed: $FAIL"
[ "$FAIL" -eq 0 ] && echo "🎉 Full request → service → database path works." || echo "⚠️  See failures above."
exit "$FAIL"
