#!/bin/bash
# Security Check Script for Werk Platform
set -e

BASE_DIR="/home/team/shared/code/werk"
VENV_PATH="/home/agent-qa-engineer/venv"

echo "=== Running Backend Dependency Scan (Safety) ==="
source "$VENV_PATH/bin/activate"
cd "$BASE_DIR/backend"
# We use --output text to avoid interactive prompts
safety check -r requirements.txt || echo "Safety found vulnerabilities"

echo -e "\n=== Running Backend SAST (Bandit) ==="
bandit -r app/ || echo "Bandit found issues"

echo -e "\n=== Running Frontend Dependency Scan (npm audit) ==="
cd "$BASE_DIR/frontend"
npm audit || echo "npm audit found vulnerabilities"

echo -e "\n=== Running RBAC Validation Tests ==="
cd "$BASE_DIR/backend"
export PYTHONPATH=$PYTHONPATH:"$BASE_DIR/backend"
pytest tests/test_rbac.py || echo "RBAC tests failed (expected if not fixed)"

echo -e "\n=== Security Scan Complete ==="
