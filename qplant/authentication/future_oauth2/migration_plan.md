# Migration Plan: API Keys → OAuth2/JWT

**From:** API Key authentication (v4.4.0)  
**To:** OAuth2 + JWT (v5.0.0)  
**Duration:** Estimated 2–3 sprints

---

## Phase A — Dual-Mode (v5.0.0-alpha)

1. Keep API key validation as-is
2. Add `/oauth/token` endpoint (client_credentials grant)
3. Accept both `X-API-Key` and `Authorization: Bearer` headers
4. Log which auth method each client uses

## Phase B — Migration Window (v5.0.0-beta)

1. Generate OAuth2 client credentials for all existing API key holders
2. Communicate deprecation timeline (90 days)
3. Provide migration scripts: `migrate_key_to_oauth.py`
4. Monitor API key usage — flag clients not yet migrated

## Phase C — Deprecation (v5.0.0)

1. API keys emit deprecation warning header
2. Rate-limit API key requests more aggressively
3. Block new API key generation
4. Final cutover date communicated

## Phase D — Removal (v5.1.0)

1. Remove API key middleware
2. OAuth2/JWT is sole auth mechanism
3. Archive `api_key_manager.py` and `key_cli.py`

---

## Rollback Plan

If OAuth2 causes issues, revert to dual-mode (Phase A) by
re-enabling API key middleware. No data loss — keys database
is preserved.

## Testing Checklist

- [ ] All 14 API endpoints accept JWT
- [ ] Scope enforcement works (read vs. write)
- [ ] Token expiration rejects expired JWTs
- [ ] Rate limiting works with JWT key_id (jti)
- [ ] Multi-tenant isolation verified
- [ ] Load test with JWT overhead < 5ms per request
