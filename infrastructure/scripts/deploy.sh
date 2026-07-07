#!/bin/bash
# Werk Platform — Deployment Script
# Orchestrates infrastructure startup for local dev / staging
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"

echo "╔══════════════════════════════════════════╗"
echo "║      Werk Platform — Deploy Script       ║"
echo "╚══════════════════════════════════════════╝"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# --- Argument parsing ---
ACTION="${1:-up}"
ENV_FILE="$REPO_ROOT/.env"

if [ ! -f "$ENV_FILE" ]; then
    warn "No .env file found at $ENV_FILE"
    warn "Copying from .env.example — customize as needed"
    cp "$SCRIPT_DIR/.env.example" "$ENV_FILE"
fi

# --- Generate self-signed SSL certs if they don't exist ---
SSL_DIR="$SCRIPT_DIR/nginx/ssl"
if [ ! -f "$SSL_DIR/werk.crt" ] || [ ! -f "$SSL_DIR/werk.key" ]; then
    info "Generating self-signed SSL certificates..."
    mkdir -p "$SSL_DIR"
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$SSL_DIR/werk.key" \
        -out "$SSL_DIR/werk.crt" \
        -subj "/CN=localhost" 2>/dev/null
    info "SSL certificates generated."
fi

case "$ACTION" in
    up)
        info "Starting all services..."
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d
        info "Services started. Run '$0 status' to check health."
        ;;
    down)
        info "Stopping all services..."
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down
        info "All services stopped."
        ;;
    restart)
        info "Restarting all services..."
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" restart
        info "Services restarted."
        ;;
    status)
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps
        ;;
    logs)
        shift
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs -f "$@"
        ;;
    build)
        info "Rebuilding images..."
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build
        info "Build complete."
        ;;
    init)
        info "Initializing infrastructure..."
        bash "$SCRIPT_DIR/setup.sh"
        ;;
    clean)
        warn "This will remove all containers, volumes, and data!"
        read -p "Are you sure? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down -v
            info "All data removed."
        fi
        ;;
    *)
        echo "Usage: $0 {up|down|restart|status|logs|build|init|clean}"
        exit 1
        ;;
esac