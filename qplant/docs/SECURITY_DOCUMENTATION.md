# Security Documentation

**Project:** MYRRHA QPLANT Cryogenic System  
**Version:** v4.4.0  
**Classification:** Security Architecture

---

## 1. Authentication Architecture

### Current: API Key Authentication (v4.4.0)
- **Key Format:** `qplant_` + 32-byte URL-safe random token
- **Storage:** PBKDF2-HMAC-SHA256 hash with per-key salt — plaintext never persisted
- **Transport:** `X-API-Key` header (HTTPS required in production)
- **Expiration:** Configurable (default 365 days)
- **Rate Limiting:** Token-bucket algorithm per key

### Future: OAuth2 + JWT (v5.0.0)
- Client credentials flow for machine-to-machine
- Authorization code flow for operator access
- Scope-based access control (read:config, write:config, admin)
- Multi-tenant support

## 2. Data Protection

### SSOT Configuration
- Kubernetes ConfigMap marked `immutable: true`
- Init container validates SHA-256 hash before pod starts
- Read-only volume mounts in all containers

### API Keys Database
- Default path: `/home/ubuntu/authentication/api_keys.json`
- Override path with `QPLANT_API_KEYS_DB` environment variable
- Should be mounted as a Kubernetes Secret in production
- Keys stored as PBKDF2-HMAC-SHA256 hashes with per-key salts
- Audit trail: creation, last use, usage count, revocation timestamps

### Secrets Management
- Kubernetes Secrets for API keys in production
- Environment variables for sensitive configuration
- No hardcoded credentials in source code

## 3. Network Security

### Kubernetes Network Policy
- Ingress: Only from nginx ingress namespace on port 8000
- Egress: HTTPS (443) and DNS (53) only
- Inter-pod communication restricted

### TLS
- Ingress terminates TLS 1.3 (cert-manager + Let's Encrypt)
- All external communication over HTTPS
- Internal cluster communication secured by Kubernetes RBAC

### CORS
- Restricted to configured origins
- Production: only the HBHS Engineering Portal domain

## 4. Rate Limiting

| Tier | Limit | Purpose |
|------|-------|---------|
| Admin | 5,000 req/hr | Administrative access |
| Monitoring | 10,000 req/hr | Automated monitoring |
| Standard | 1,000 req/hr | Normal API clients |

### Implementation
- Token-bucket algorithm with per-second refill
- Thread-safe with locking
- HTTP 429 response with `Retry-After` header

## 5. Vulnerability Management

### Scanning
- Python: `pip-audit` for known CVEs
- SBOM: CycloneDX 1.5 format with dependency tracking
- Automated scanning in CI/CD pipeline

### Current Status
- **Critical:** 0
- **High:** 0
- **Medium:** 0
- **247 dependencies** scanned and catalogued

## 6. Compliance

| Standard | Status |
|----------|--------|
| PED 2014/68/EU | ✅ Applied |
| ASME B31.3 | ✅ Applied |
| EN 13185 | ✅ Applied |
| ISO 5208 | ✅ Applied |
| License compliance | ✅ No copyleft conflicts |

## 7. Security Checklist

- [x] API key authentication implemented
- [x] Rate limiting active
- [x] Secrets not hardcoded
- [x] Network policies configured
- [x] TLS configured (Ingress)
- [x] CORS restricted
- [x] SBOM generated
- [x] Vulnerability scan clean
- [x] Immutable configuration
- [x] Audit logging
