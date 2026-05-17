# Production Deployment Handbook

**Project:** MYRRHA QPLANT Cryogenic System  
**Version:** v4.4.0  
**Classification:** Operations Manual

---

## 1. System Architecture

```
Internet → Ingress (TLS) → Service LB → Pods (3–10) → SSOT ConfigMap
                                          ↓
                                   API Key Auth → Rate Limiter
```

### Components
- **API Server:** FastAPI application serving 14+ REST endpoints
- **SSOT ConfigMap:** Immutable Kubernetes ConfigMap with canonical configuration
- **Authentication:** API key–based with SHA-256 hashing and rate limiting
- **Monitoring:** Health checks, liveness/readiness probes, HPA

## 2. Prerequisites

| Component | Minimum Version | Purpose |
|-----------|----------------|---------|
| Kubernetes | 1.28+ | Container orchestration |
| kubectl | 1.28+ | Cluster management |
| Python | 3.11+ | API server and tooling |
| Docker | 24.0+ | Container building |

## 3. Pre-Deployment Checklist

- [ ] Kubernetes cluster accessible (`kubectl cluster-info`)
- [ ] Docker registry credentials configured
- [ ] API keys generated (`python3 authentication/key_cli.py generate`)
- [ ] SSOT configuration validated
- [ ] All tests passing (`pytest` — 134+ tests)
- [ ] SBOM generated (`sbom/generate_sbom.py`)
- [ ] Load test baselines reviewed

## 4. Deployment Procedure

### Step 1: Build Docker Image
```bash
cd deployment
docker build -t qplant/api-server:v4.4.0 -f Dockerfile ..
```

### Step 2: Deploy to Kubernetes
```bash
bash deployment/scripts/deploy_production.sh
```

### Step 3: Validate
```bash
bash deployment/scripts/validate_deployment.sh
```

## 5. Monitoring

### Health Endpoints
- `GET /api/v1/health` — Full health check
- `GET /` — Service info

### Kubernetes Monitoring
```bash
kubectl get pods -n qplant-production -w
kubectl top pods -n qplant-production
kubectl get hpa -n qplant-production
kubectl get events -n qplant-production --sort-by=.lastTimestamp
```

### Log Access
```bash
kubectl logs -f -l app=qplant-api -n qplant-production
```

## 6. Incident Response

### Emergency Rollback
```bash
bash deployment/scripts/rollback.sh
```

### Pod Restart
```bash
kubectl rollout restart deployment/qplant-api-server -n qplant-production
```

### Full Redeploy
```bash
kubectl delete namespace qplant-production
bash deployment/scripts/deploy_production.sh
```

## 7. API Key Management

```bash
# Generate new key
python3 authentication/key_cli.py generate --name "Service A"

# List all keys
python3 authentication/key_cli.py list

# Rotate compromised key
python3 authentication/key_cli.py rotate --key-id key_abc123

# Revoke key
python3 authentication/key_cli.py revoke --key-id key_abc123
```

## 8. Configuration Updates

The SSOT ConfigMap is **immutable**. To update configuration:

1. Create new versioned ConfigMap (e.g., `qplant-ssot-v4.4.1`)
2. Update deployment to reference new ConfigMap
3. Perform rolling update
4. Verify init container validation passes

## 9. Performance Targets

| Metric | Target |
|--------|--------|
| p95 latency | < 200ms |
| Error rate | < 0.1% |
| Availability | 99.9% |
| Max concurrent users | 300 |
| Pod count | 3–10 (auto-scaled) |

## 10. Contact

- **Engineering:** HBHS Engineering
- **Operations:** SCK CEN MYRRHA
