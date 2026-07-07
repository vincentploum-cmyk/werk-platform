#!/bin/bash
# Generate self-signed SSL certificates for development
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SSL_DIR="$SCRIPT_DIR/../nginx/ssl"   # where docker-compose mounts /etc/nginx/ssl from
mkdir -p "$SSL_DIR"
KEY_FILE="$SSL_DIR/werk.key"
CRT_FILE="$SSL_DIR/werk.crt"

if [ -f "$KEY_FILE" ] && [ -f "$CRT_FILE" ]; then
    echo "SSL certificates already exist. Skipping generation."
    exit 0
fi

echo "Generating self-signed SSL certificates..."
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$KEY_FILE" \
    -out "$CRT_FILE" \
    -subj "/C=US/ST=Development/L=Local/O=Werk/CN=localhost" 2>/dev/null

echo "Certificates generated:"
echo "  Key:  $KEY_FILE"
echo "  Cert: $CRT_FILE"