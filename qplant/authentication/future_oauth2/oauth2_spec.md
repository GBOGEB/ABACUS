# OAuth2 / JWT Authentication — Future Specification

**Status:** PLANNED (v5.0.0)  
**Current:** API Key authentication (v4.4.0)  
**Target:** OAuth2 + JWT tokens for enterprise multi-tenant access

---

## 1. Overview

When the QPLANT system scales to multi-site, multi-tenant deployments
(MYRRHA + partner facilities), API key authentication will be upgraded
to a full OAuth2 / JWT flow. This document specifies the planned
architecture.

## 2. Auth Flow

```
Client → POST /oauth/token (client_credentials) → JWT access_token
Client → GET /api/v1/config (Authorization: Bearer <jwt>) → 200
```

### Supported Grant Types

| Grant | Use Case |
|-------|----------|
| `client_credentials` | Machine-to-machine (primary) |
| `authorization_code` | Human operator dashboard access |
| `refresh_token` | Long-lived sessions |

## 3. JWT Token Structure

```json
{
  "sub": "service:config-reader",
  "iss": "qplant-auth",
  "aud": "qplant-api",
  "iat": 1716000000,
  "exp": 1716003600,
  "scope": ["read:config", "read:flows", "write:none"],
  "tenant": "myrrha-sck",
  "role": "operator"
}
```

## 4. Scopes

| Scope | Description |
|-------|-------------|
| `read:config` | Read SSOT configuration |
| `read:flows` | Read flow/pressure data |
| `read:calcs` | Execute calculations |
| `write:config` | Modify configuration (admin) |
| `admin:keys` | Manage API keys |

## 5. Migration Plan

See `migration_plan.md` for step-by-step migration from API keys.

## 6. Dependencies

- `python-jose[cryptography]` for JWT
- `passlib[bcrypt]` for password hashing
- Redis or PostgreSQL for token storage
- HTTPS mandatory (TLS 1.3)
