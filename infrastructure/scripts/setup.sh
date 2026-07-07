#!/bin/bash
# Initialize Werk infrastructure: create MinIO bucket and verify services
set -e

echo "=== Werk Infrastructure Setup ==="

# Wait for MinIO to be ready
echo "Waiting for MinIO..."
until curl -sf http://localhost:9000/minio/health/live > /dev/null 2>&1; do
  sleep 2
done
echo "MinIO is ready."

# Create the artifacts bucket
apt-get update -qq && apt-get install -y -qq curl 2>/dev/null || true
mc alias set local http://localhost:9000 minioadmin minioadmin
mc mb local/werk-artifacts --ignore-existing
echo "MinIO bucket 'werk-artifacts' ready."

# Wait for PostgreSQL
echo "Waiting for PostgreSQL..."
until pg_isready -h localhost -U postgres > /dev/null 2>&1; do
  sleep 2
done
echo "PostgreSQL is ready."

# Wait for Redis
echo "Waiting for Redis..."
until redis-cli -h localhost ping > /dev/null 2>&1; do
  sleep 2
done
echo "Redis is ready."

echo ""
echo "=== All services are up and running! ==="
echo "PostgreSQL :5432 - werk database"
echo "Redis      :6379"
echo "MinIO API  :9000"
echo "MinIO Console :9001 (login: minioadmin/minioadmin)"