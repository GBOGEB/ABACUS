# QPLANT Cryogenic Dashboard — Deployment Guide

> **Version:** 4.2.0  
> **Date:** 2026-05-12  
> **Environments:** Development, Staging, Production, Disaster Recovery  

---

## Quick Start (Development)

```bash
# 1. Clone and enter project
cd /home/ubuntu

# 2. Install dependencies
cd handover_dashboard && pip install -r requirements.txt && cd ..

# 3. Run tests
python -m pytest handover_dashboard/tests/ config_service/tests/ monitoring_dashboard/tests/ ai_validation/tests/ -v

# 4. Start services
# Dashboard API (port 8100)
cd handover_dashboard && uvicorn api.main:app --host 0.0.0.0 --port 8100 --reload &

# Config Service (port 8200)
cd /home/ubuntu && uvicorn config_service.api:app --host 0.0.0.0 --port 8200 --reload &

# 5. Verify
curl http://localhost:8100/api/v1/health
curl http://localhost:8200/api/v1/health
```

---

## Environment Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    Deployment Environments                        │
├──────────┬──────────┬──────────────┬────────────────────────────┤
│   Dev    │ Staging  │  Production  │  Disaster Recovery (DR)    │
│ (local)  │ (pre-    │   (live)     │  (passive standby)         │
│          │  prod)   │              │                            │
│ Port:    │ Port:    │ Port: 80/443 │  Mirror of production      │
│ 8100     │ 8100     │ (nginx)      │  with cold standby         │
│          │          │              │                            │
│ Workers: │ Workers: │ Workers: 4   │  Workers: 2 (when active)  │
│ 1        │ 2        │              │                            │
└──────────┴──────────┴──────────────┴────────────────────────────┘
```

---

## Docker Deployment

### Development

```bash
cd /home/ubuntu/deployment
cp .env.template .env
# Edit .env as needed

docker-compose up -d
# Services: dashboard-api:8100, config-service:8200, monitoring:8300
```

### Staging

```bash
docker-compose -f docker-compose.yml -f docker-compose.staging.yml up -d
```

### Production

```bash
docker-compose -f docker-compose.yml -f docker-compose.production.yml up -d
# Includes nginx reverse proxy on ports 80/443
```

---

## Service Endpoints

| Service | Port | Health Check | Docs |
|---------|------|-------------|------|
| Dashboard API | 8100 | `/api/v1/health` | `/docs` |
| Config Service | 8200 | `/api/v1/health` | `/docs` |
| Monitoring | 8300 | `GET /` | N/A |
| Nginx (prod) | 80/443 | `/health` | N/A |

---

## CI/CD Pipeline

### Automated Testing (on every commit)

```
commit → lint → test → build → validate → [merge to main] → docker build
```

### Deployment (manual trigger)

```
dispatch → validate → build & push → deploy → health check → [rollback on failure]
```

### GitHub Actions Workflows

| Workflow | Trigger | File |
|----------|---------|------|
| CI | Push to main/develop, PR | `.github/workflows/ci.yml` |
| Deploy | Manual dispatch | `.github/workflows/deploy.yml` |

---

## Configuration Management

### Environment-Specific Configs

```
handover_dashboard/data/
├── config.yaml              # Base SSoT (all environments)
├── config.dev.yaml          # Dev overrides
├── config.staging.yaml      # Staging overrides
├── config.prod.yaml         # Production overrides
└── config.dr.yaml           # DR overrides
└── backups/                 # Timestamped backups
```

### Config Migration

```bash
# Check migration status
python -m config_service.migrate --check --config handover_dashboard/data/config.yaml

# Execute migration
python -m config_service.migrate --execute --version 4.2.0 --config handover_dashboard/data/config.yaml

# Rollback
python -m config_service.migrate --rollback --config handover_dashboard/data/config.yaml
```

---

## Troubleshooting

### Common Issues

| Issue | Symptom | Solution |
|-------|---------|----------|
| API won't start | `ModuleNotFoundError` | Ensure `PYTHONPATH` includes project root |
| Config not loading | `FileNotFoundError` | Check `QPLANT_CONFIG_PATH` env var |
| CORS errors | Browser console 403 | Check `allow_origins` in API CORS middleware |
| Tests failing | Import errors | Activate venv, install requirements |
| Build timeout | >60s build time | Check for slow steps in build log |

### Logs

```bash
# Docker logs
docker-compose logs dashboard-api
docker-compose logs config-service

# Build logs
cat handover_dashboard/dist/build_all.log
```

### Health Checks

```bash
# All services
curl -s http://localhost:8100/api/v1/health | python -m json.tool
curl -s http://localhost:8200/api/v1/health | python -m json.tool

# Config validation
curl -s http://localhost:8200/api/v1/config/validate | python -m json.tool

# Cross-link validation
python validate_cross_links.py
```

---

## Rollback Procedures

### Application Rollback

```bash
# Docker: revert to previous image
docker-compose down
docker-compose -f docker-compose.yml -f docker-compose.production.yml up -d --no-build

# Config rollback
python -m config_service.migrate --rollback --config handover_dashboard/data/config.yaml
```

### Blue-Green Deployment

```bash
# 1. Deploy new version on alternate ports
QPLANT_API_PORT=8101 docker-compose -f docker-compose.yml up -d

# 2. Verify health
curl http://localhost:8101/api/v1/health

# 3. Switch nginx upstream
# Update nginx.conf: server dashboard-api:8101

# 4. Reload nginx
docker exec qplant-nginx nginx -s reload
```

---

## Scaling Strategies

### Horizontal Scaling

```yaml
# docker-compose.production.yml
services:
  dashboard-api:
    deploy:
      replicas: 3
```

### Vertical Scaling

```yaml
# Increase worker count
command: uvicorn ... --workers 8
deploy:
  resources:
    limits:
      cpus: "4.0"
      memory: 2G
```

### Performance Benchmarks

| Metric | Development | Staging | Production Target |
|--------|------------|---------|-------------------|
| API p95 latency | <100ms | <200ms | <300ms |
| Config fetch | <20ms | <30ms | <50ms |
| Build time | <30s | <30s | <30s |
| Concurrent users | 1 | 10 | 100 |
| Test suite | <5s | <10s | <15s |

---

## Security Considerations

| Area | Development | Production |
|------|-------------|-----------|
| CORS | Allow all origins | Whitelist specific origins |
| API Authentication | None | API key or JWT |
| HTTPS | Optional | Required (SSL/TLS) |
| Config access | Read/write | Read-only via API |
| Secrets | `.env` file | Vault/KMS |
| Network | Bridge | Isolated VPC |

---

*Deployment Guide — QPLANT Cryogenic Dashboard v4.2.0*
