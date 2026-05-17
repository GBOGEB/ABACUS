# Kubernetes Production Deployment Guide

**Project:** MYRRHA QPLANT Cryogenic System  
**Version:** v4.4.0  
**Date:** 2026-05-17

---

## Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| `kubectl` | ≥ 1.28 | Cluster management |
| `helm` | ≥ 3.14 | Optional package manager |
| Python | ≥ 3.11 | API key generation |
| Docker | ≥ 24.0 | Image building |
| Cluster access | — | `~/.kube/config` configured |

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Namespace: qplant-production                                │
│                                                              │
│  ┌────────────┐    ┌───────────────────────┐                │
│  │  Ingress   │───▶│  Service (LB)         │                │
│  │  (TLS)     │    │  Port 80 → 8000       │                │
│  └────────────┘    └───────────────────────┘                │
│                           │                                  │
│                    ┌──────┴──────┐                           │
│               ┌────┴──┐  ┌──────┴─┐  ┌──────┐             │
│               │ Pod 1 │  │ Pod 2  │  │ Pod 3│  ← HPA      │
│               │ init: │  │ init:  │  │ init:│    (3-10)    │
│               │ valid │  │ valid  │  │ valid│              │
│               └───┬───┘  └───┬────┘  └──┬───┘             │
│                   │          │          │                    │
│              ┌────┴──────────┴──────────┴────┐             │
│              │  ConfigMap: qplant-ssot-v4-4-0 │             │
│              │  (immutable)                    │             │
│              └────────────────────────────────┘             │
│                                                              │
│  ┌──────────────┐  ┌──────────────────┐                    │
│  │ Secret:      │  │ NetworkPolicy    │                    │
│  │ API Keys     │  │ Ingress/Egress   │                    │
│  └──────────────┘  └──────────────────┘                    │
└──────────────────────────────────────────────────────────────┘
```

## Quick Deploy

```bash
# One-command deployment
bash deployment/scripts/deploy_production.sh

# Validate
bash deployment/scripts/validate_deployment.sh
```

## Step-by-Step Deployment

### 1. Create Namespace

```bash
kubectl apply -f deployment/k8s/namespace.yaml
```

### 2. Generate API Keys

```bash
python3 authentication/key_cli.py generate --name "Production Admin" --days 365
# Save the printed API key securely
# Update deployment/k8s/secrets.yaml with the generated key
```

### 3. Deploy SSOT ConfigMap

```bash
kubectl apply -f deployment/k8s/configmap-ssot-production.yaml
# This ConfigMap is immutable — to update, create a new versioned ConfigMap
```

### 4. Deploy Secrets

```bash
kubectl apply -f deployment/k8s/secrets.yaml
```

### 5. Deploy Application

```bash
kubectl apply -f deployment/k8s/deployment-api-server.yaml
kubectl apply -f deployment/k8s/service.yaml
kubectl apply -f deployment/k8s/ingress.yaml
kubectl apply -f deployment/k8s/hpa.yaml
kubectl apply -f deployment/k8s/network-policy.yaml
```

### 6. Verify

```bash
kubectl rollout status deployment/qplant-api-server -n qplant-production
kubectl get all -n qplant-production
```

## Troubleshooting

| Issue | Command | Fix |
|-------|---------|-----|
| Pod CrashLoopBackOff | `kubectl logs <pod> -n qplant-production` | Check init container validation |
| SSOT validation fail | `kubectl logs <pod> -c validate-ssot -n qplant-production` | Verify ConfigMap data |
| Service unreachable | `kubectl describe svc qplant-api-service -n qplant-production` | Check selector labels |
| HPA not scaling | `kubectl describe hpa -n qplant-production` | Verify metrics-server installed |

## Disaster Recovery

### Emergency Rollback

```bash
bash deployment/scripts/rollback.sh
```

### Full Rebuild

```bash
kubectl delete namespace qplant-production
bash deployment/scripts/deploy_production.sh
```

## Monitoring

- **Logs:** `kubectl logs -f -l app=qplant-api -n qplant-production`
- **Events:** `kubectl get events -n qplant-production --sort-by='.lastTimestamp'`
- **Metrics:** `kubectl top pods -n qplant-production`
- **HPA:** `kubectl get hpa -n qplant-production -w`

## Manifest Summary

| File | Purpose |
|------|---------|
| `namespace.yaml` | Dedicated production namespace |
| `configmap-ssot-production.yaml` | Immutable SSOT configuration |
| `secrets.yaml` | API key secrets |
| `deployment-api-server.yaml` | 3-replica API server with init validation |
| `service.yaml` | LoadBalancer service |
| `ingress.yaml` | TLS-terminated external access |
| `hpa.yaml` | Auto-scaling (3–10 pods) |
| `network-policy.yaml` | Network segmentation |
