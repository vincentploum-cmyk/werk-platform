# Security Architecture & Hardening — Werk Platform

## Overview

This document defines the security architecture for the Werk platform, covering authentication, authorization, secrets management, container isolation, network security, and compliance considerations.

---

## 1. Authentication — JWT-based

### 1.1 Token Structure

Werk uses **JSON Web Tokens (JWT)** with the following claims:

```json
{
  "sub": "usr-admin-001",
  "username": "admin",
  "role": "admin",
  "exp": 1717000000
}
```

- **Algorithm:** HS256 (HMAC with SHA-256)
- **Secret Key:** Configurable via `SECRET_KEY` environment variable
- **Default Expiry:** 60 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)

### 1.2 Token Flow

```
Client                     Backend
  │                          │
  │── POST /api/v1/auth/login ──►  Validate credentials
  │◄── { access_token }       │  Returns JWT
  │                          │
  │── GET /api/v1/projects ──►   Auth middleware validates JWT
  │   Authorization: Bearer <token>
  │◄── { projects: [...] }   │
```

### 1.3 Implementation

File: `backend/app/core/security.py`
- `create_access_token()` — Signs a JWT with user claims
- `decode_access_token()` — Validates and decodes a JWT
- `verify_password()` / `get_password_hash()` — bcrypt password hashing

File: `backend/app/core/auth.py`
- `get_current_user()` — FastAPI dependency that extracts user from Bearer token
- `RequirePermission()` — FastAPI dependency factory for permission checks
- `RequireRole()` — FastAPI dependency factory for role-level checks

---

## 2. Authorization — Role-Based Access Control (RBAC)

### 2.1 Role Hierarchy

| Role | Level | Description |
|---|---|---|
| **admin** | 100 | Full system access, user management, all operations |
| **lead** | 80 | Project management, task creation, deployment trigger |
| **developer** | 60 | Code implementation, artifact creation, task updates |
| **viewer** | 40 | Read-only access to projects, tasks, artifacts |
| **agent** | 20 | Automated agent operations (task read/update, artifact create) |

### 2.2 Permission Matrix

| Permission | admin | lead | developer | viewer | agent |
|---|---|---|---|---|---|
| projects:create | ✅ | ✅ | ❌ | ❌ | ❌ |
| projects:read | ✅ | ✅ | ✅ | ✅ | ❌ |
| projects:update | ✅ | ✅ | ❌ | ❌ | ❌ |
| projects:delete | ✅ | ❌ | ❌ | ❌ | ❌ |
| tasks:create | ✅ | ✅ | ❌ | ❌ | ❌ |
| tasks:read | ✅ | ✅ | ✅ | ✅ | ✅ |
| tasks:update | ✅ | ✅ | ✅ | ❌ | ✅ |
| agents:read | ✅ | ✅ | ✅ | ✅ | ❌ |
| artifacts:create | ✅ | ✅ | ✅ | ❌ | ✅ |
| artifacts:read | ✅ | ✅ | ✅ | ✅ | ✅ |
| deploy:trigger | ✅ | ✅ | ❌ | ❌ | ❌ |
| users:manage | ✅ | ❌ | ❌ | ❌ | ❌ |

### 2.3 Implementation

File: `backend/app/core/security.py` — `RBAC_POLICIES` dictionary defines the matrix
Usage: `Depends(RequirePermission("tasks:read"))` in FastAPI route handlers

---

## 3. Secrets Management

### 3.1 Principles

1. **Never hardcode secrets** in source code or configuration files
2. **Use environment variables** for runtime configuration
3. **Provide `.env.example`** for documentation, never check in `.env`
4. **Support HashiCorp Vault** integration for production deployments

### 3.2 Environment Variables

| Variable | Purpose | Default |
|---|---|---|
| `SECRET_KEY` | JWT signing key | `werk-dev-secret-key-change-in-production` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://postgres:postgres@localhost:5432/werk` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `OPENAI_API_KEY` | OpenAI API key | (empty) |
| `ANTHROPIC_API_KEY` | Anthropic API key | (empty) |
| `POSTGRES_PASSWORD` | Database password | `postgres` |
| `MINIO_ACCESS_KEY` | MinIO access key | `minioadmin` |
| `MINIO_SECRET_KEY` | MinIO secret key | `minioadmin` |

### 3.3 HashiCorp Vault Integration (Future)

The config module (`backend/app/core/config.py`) has `vault_addr` and `vault_token` fields. When `use_vault: true`, secrets will be fetched from Vault instead of environment variables.

### 3.4 Files

- `.env.example` — Template for local development
- `.gitignore` — `.env` and `.env.*.local` are gitignored
- `docker-compose.yml` — Passes secrets via `environment` blocks and `env_file`

---

## 4. Agent Sandboxing

### 4.1 Docker Container Isolation

Each agent execution runs in an isolated Docker container with:

- **Read-only root filesystem** (`read_only: true`)
- **Dropped capabilities** (`cap_drop: ALL`)
- **Minimal capabilities added** only as needed (CHOWN, SETUID, SETGID)
- **Temporary filesystem** (`tmpfs`) for runtime state
- **Non-root user** (`user: "1000:1000"`)
- **Separate volume mounts** scoped to project workspace

### 4.2 Service Hardening (docker-compose.yml)

| Service | Security Measures |
|---|---|
| **postgres** | Read-only rootfs, tmpfs for runtime, minimal caps, healthcheck |
| **redis** | Read-only rootfs, optional password, minimal caps |
| **minio** | Minimal caps, healthcheck |
| **backend** | Non-root user, read-only rootfs, tmpfs, dropped ALL caps |
| **nginx** | Read-only rootfs, tmpfs for cache, NET_BIND_SERVICE only |

### 4.3 Cross-Project Isolation

- Each project gets its own database rows (scoped by `project_id` foreign key)
- Artifact storage paths are prefixed by `project_id`
- Agent execution environments are ephemeral Docker containers
- No shared writable filesystem between projects

---

## 5. Network Security

### 5.1 Nginx Configuration

File: `infrastructure/nginx/nginx.conf`

| Security Header | Value |
|---|---|
| `X-Frame-Options` | `SAMEORIGIN` |
| `X-Content-Type-Options` | `nosniff` |
| `X-XSS-Protection` | `1; mode=block` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | Restricted (no camera/mic/geolocation) |
| `Content-Security-Policy` | Strict default-src 'self' |
| `Strict-Transport-Security` | 1 year, includeSubDomains, preload |

### 5.2 Rate Limiting

| Zone | Rate | Burst | Applied To |
|---|---|---|---|
| `api_limit` | 30 req/s | 20 | All `/api/` routes |
| `auth_limit` | 10 req/m | 5 | `/api/v1/auth/` (brute force protection) |

### 5.3 SSL/TLS

| Setting | Value |
|---|---|
| Protocols | TLSv1.2, TLSv1.3 |
| Ciphers | Strong ciphers only (ECDHE + AES-GCM) |
| HSTS | Enabled (max-age=31536000) |
| OCSP Stapling | Enabled |
| Session Tickets | Disabled |

### 5.4 Access Control

- `/health` endpoint restricted to internal networks only
- All hidden files (`.env`, `.git`, etc.) blocked by Nginx
- `server_tokens` disabled (no version disclosure)

---

## 6. Compliance & Auditing

### 6.1 Logging

- All authentication attempts are logged (including failures)
- All API requests are logged with user ID, IP, timestamp, and action
- Agent events are recorded in the `agent_events` database table
- Nginx access and error logs capture all HTTP traffic

### 6.2 Audit Trail

Every state change in the orchestrator is captured:
- Task status transitions (Backlog → In-Progress → Review → Done)
- Artifact creation events
- Agent assignment changes
- Sign-off decisions (approve/reject with reviewer comment)

### 6.3 Data Protection

| Area | Measure |
|---|---|
| **Passwords** | bcrypt hashing (12 rounds) |
| **Tokens** | JWT with expiry, no sensitive data in payload |
| **Database** | PostgreSQL with SSL support (configurable) |
| **Transit** | TLS 1.2+ for all external traffic |
| **Storage** | MinIO with bucket-level access control |

---

## 7. Security Checklist

### Development
- [x] JWT authentication implemented
- [x] RBAC with role hierarchy defined
- [x] bcrypt password hashing (12 rounds)
- [x] Rate limiting on auth endpoints (10 req/min)
- [x] CORS middleware configured
- [x] `.env` files in `.gitignore`
- [x] `.env.example` provided (no secrets)
- [x] SSL cert generation script provided
- [x] Nginx security headers configured
- [x] Docker service hardening (read-only, cap_drop, non-root)
- [x] Agent sandboxing via Docker isolation
- [x] Hidden file blocking in Nginx
- [x] Server version hiding

### Staging/Production (Future)
- [ ] Replace self-signed certs with Let's Encrypt / CA certs
- [ ] Integrate HashiCorp Vault for secrets management
- [ ] Set up WAF (Web Application Firewall)
- [ ] Enable database encryption at rest
- [ ] Configure DDoS protection
- [ ] Implement IP allowlisting for admin endpoints
- [ ] Set up SIEM integration (Security Information and Event Management)
- [ ] Run third-party penetration testing
- [ ] Implement session revocation (deny-list for tokens)
- [ ] Set up automated vulnerability scanning
- [ ] Enable audit logging shipping to secure storage