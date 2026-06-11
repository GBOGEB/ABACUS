# Phase 4 Implementation Guide

**Project:** MYRRHA QPLANT Cryogenic System  
**Version:** v4.4.0 — Production Ready  
**Date:** 2026-05-17

---

## Overview

Phase 4 elevates the QPLANT system from a validated prototype (v4.3.0) to a
**production-ready deployment** (v4.4.0). It delivers five capabilities:

| Priority | Capability | Status |
|----------|-----------|--------|
| P1 | API Key Authentication | ✅ Complete |
| P2 | Kubernetes Production Deployment | ✅ Complete |
| P3 | Load Testing (Locust) | ✅ Complete |
| P4 | Visual Regression Testing | ✅ Complete |
| P5 | SBOM Generation | ✅ Complete |

---

## P1: API Key Authentication

### Location
`/home/ubuntu/authentication/`

### Components

| File | Purpose |
|------|---------|
| `api_key_manager.py` | Key generation, validation, rotation, revocation |
| `rate_limiter.py` | Token-bucket rate limiting |
| `fastapi_middleware.py` | FastAPI dependency for protected endpoints |
| `key_cli.py` | CLI tool for key management |

### Quick Start

```bash
# Generate a key
python3 authentication/key_cli.py generate --name "My App" --days 365

# Validate a key
python3 authentication/key_cli.py validate --key "qplant_abc123..."

# Use with API (local Docker/Compose defaults to 8100; Kubernetes service uses 8000)
curl -H "X-API-Key: qplant_abc123..." http://localhost:8100/api/v1/config
```

### Security Model
- Keys use PBKDF2-HMAC-SHA256 with per-key salt — plaintext never stored
- Cryptographically random generation (`secrets.token_urlsafe`)
- Expiration enforcement
- Rate limiting (token-bucket algorithm)
- Audit logging (usage count, last used timestamp)

### Future: OAuth2/JWT
Preparation docs at `authentication/future_oauth2/`:
- `oauth2_spec.md` — Full specification
- `jwt_schema.json` — JWT token structure
- `migration_plan.md` — Migration from API keys

---

## P2: Kubernetes Production Deployment

### Location
`/home/ubuntu/deployment/k8s/` and `/home/ubuntu/deployment/scripts/`

### Manifests (8 files)

| Manifest | Purpose |
|----------|---------|
| `namespace.yaml` | Dedicated `qplant-production` namespace |
| `configmap-ssot-production.yaml` | Immutable SSOT ConfigMap |
| `secrets.yaml` | API key secrets |
| `deployment-api-server.yaml` | 3-replica deployment with init validation |
| `service.yaml` | LoadBalancer service |
| `ingress.yaml` | TLS-terminated external access |
| `hpa.yaml` | Horizontal Pod Autoscaler (3–10) |
| `network-policy.yaml` | Network segmentation |

### Deploy

```bash
bash deployment/scripts/deploy_production.sh
bash deployment/scripts/validate_deployment.sh
```

See `deployment/K8S_DEPLOYMENT_GUIDE.md` for full documentation.

---

## P3: Load Testing

### Location
`/home/ubuntu/load_testing/`

### Scenarios

| Scenario | Users | Duration | Purpose |
|----------|-------|----------|---------|
| `smoke_test` | 10 | 2m | Quick validation |
| `normal_load` | 100 | 10m | Expected production load |
| `peak_load` | 300 | 15m | 2× expected load |
| `stress_test` | 500 | 20m | Find breaking point |
| `endurance_test` | 150 | 60m | Sustained load |

### Run

```bash
# Single scenario
bash load_testing/run_load_tests.sh smoke_test

# All scenarios
bash load_testing/run_load_tests.sh

# Analyze results
python3 load_testing/analyze_results.py
```

---

## P4: Visual Regression Testing

### Location
`/home/ubuntu/visual_regression/`

### Usage

```bash
# Create baselines (first time)
bash visual_regression/create_baselines.sh

# Run tests
bash visual_regression/run_visual_tests.sh

# View report
open visual_regression/visual_regression_report.html
```

### Pages Tested
16+ HTML deliverables including dashboards, documentation, presentations,
and analysis pages.

---

## P5: SBOM Generation

### Location
`/home/ubuntu/sbom/`

### Generate

```bash
cd sbom && python3 generate_sbom.py
python3 sbom_validation.py
```

### Output
- `cyclonedx_sbom.json` — CycloneDX 1.5 format
- `sbom_report.md` — Human-readable report
- `vulnerability_report.json` — Security scan results
- `releases/v4.4.0/` — Versioned release artifacts

---

## Build Pipeline (17 steps)

The updated `build_all.sh` now includes Phase 4 validation:

| Step | Description | Phase |
|------|-------------|-------|
| 1–9 | Core build, tests, compliance | Phase 1 |
| 10–13 | Config service, AI validation | Phase 3 |
| 14 | API key authentication validation | Phase 4 |
| 15 | SBOM validation | Phase 4 |
| 16 | K8s manifest validation | Phase 4 |
| 17 | Load test configuration validation | Phase 4 |

---

## Test Suite

**134 tests passing** across all modules:

| Module | Tests |
|--------|-------|
| `authentication/tests/` | 39 |
| `handover_dashboard/tests/` | 35 |
| `config_service/tests/` | 25 |
| `monitoring_dashboard/` | 5 |
| `ai_validation/tests/` | 30 |
