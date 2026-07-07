# Security Policy

Werk Platform is a **research preview**. It is intended for local and trusted
environments; review the notes below before any shared deployment.

## Supported versions

| Version | Supported |
|---|---|
| v0.1.x (latest release) | ✅ |
| anything older | ❌ |

## Reporting a vulnerability

Email **vincentploum@gmail.com** with a description, reproduction steps, and
impact. You'll get an acknowledgement within 72 hours. Please don't open a
public issue for security reports.

## Security posture (research preview)

- **Demo credentials** exist only in debug mode (`DEBUG=true`). With
  `DEBUG=false` no users are seeded and registration is disabled — wire up a
  real user store before shared use.
- **SECRET_KEY**: the backend refuses to start with a known placeholder key
  outside debug mode. Generate one with `openssl rand -hex 32`.
- **Code execution** (the Developer→Tester workspace) is off by default and
  gated behind `ENABLE_CODE_EXECUTION`. Enable only for local/trusted use.
- **TLS certificates** are generated locally by
  `infrastructure/scripts/generate_certs.sh` and are never committed.
- **CORS** is permissive (`*`) in this preview — restrict it before exposing
  the API beyond localhost.
- Dependency scanning (pip-audit, npm audit, Trivy) runs in CI on every
  change to the dependency manifests. See `docs/security.md` for the security
  architecture.
