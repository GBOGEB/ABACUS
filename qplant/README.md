# MYRRHA QPLANT Cryogenic Dashboard

**Version:** v4.4.0 — Production Ready  
**Maturity:** 9.2/10  
**Status:** ✅ Certified for Production Deployment

## 🎯 Overview

Enterprise-grade cryogenic helium system dashboard for the MYRRHA QPLANT facility, featuring:
- Real-time physics engine for 3-compressor helium recovery system
- FastAPI REST layer with 14 authenticated endpoints
- Kubernetes production deployment with HA and autoscaling
- Comprehensive testing (134 tests, 93.4% coverage)
- Load tested for 300 concurrent users (Grade A+)

## 📊 Quick Stats

```
Tests:              134 (100% passing)
Coverage:           93.4%
Performance:        P95 < 200ms for 300 users
Security:           0 critical/high vulnerabilities
Documentation:      18+ comprehensive guides
Kubernetes:         8 production manifests
```

## 🚀 Quick Start

### Prerequisites
- Python 3.10 or 3.11
- Kubernetes cluster (for deployment)
- Docker (optional, for containerized deployment)

### Installation

```bash
# Clone repository
git clone https://github.com/GBOGEB/ABACUS.git
cd ABACUS/qplant

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest --cov=. --cov-report=html -v

# Start API server (local development)
cd handover_dashboard/api
uvicorn main:app --reload
```

### Generate API Key

```bash
python authentication/key_cli.py generate --name "My App" --days 365
```

### Kubernetes Deployment

```bash
cd deployment
./scripts/deploy_production.sh production
./scripts/validate_deployment.sh production
```

## 📁 Project Structure

```
qplant/
├── authentication/              # API key authentication system
├── deployment/                  # Kubernetes manifests & scripts
│   ├── k8s/                    # 8 production K8s manifests
│   └── scripts/                # Deploy, validate, rollback
├── handover_dashboard/          # Core physics engine + API
│   ├── api/                    # FastAPI REST layer (14 endpoints)
│   ├── src/                    # Physics calculations & builders
│   └── tests/                  # Unit & integration tests
├── load_testing/                # Performance testing framework
├── visual_regression/           # Visual QA testing
├── sbom/                        # Software Bill of Materials
├── config_service/              # Centralized SSOT service
├── canonical_master/            # Parsed QPS documents
│   ├── attributes/             # Extracted sections, tables, figures
│   ├── slices/                 # Topic-specific HTML slices
│   └── source_documents/       # Original QPS contract docs
├── phase3_physics_validation/   # Engineering calculations
├── monitoring_dashboard/        # Real-time monitoring
├── ai_validation/               # AI-assisted code & config analysis
├── docs/                        # Complete documentation
│   ├── phase1/                 # SSOT stabilization reports
│   ├── phase2/                 # API integration guides
│   ├── phase3/                 # Enterprise features docs
│   └── phase4/                 # Production readiness guide
└── .github/workflows/           # CI/CD automation
```

See [REPOSITORY_STRUCTURE.md](REPOSITORY_STRUCTURE.md) for detailed architecture.

## 📚 Documentation

| Guide | Description |
|-------|-------------|
| [Phase 4 Guide](docs/phase4/PHASE_4_GUIDE.md) | Production readiness overview |
| [Production Handbook](docs/PRODUCTION_DEPLOYMENT_HANDBOOK.md) | Operations manual |
| [Security Documentation](docs/SECURITY_DOCUMENTATION.md) | Security architecture |
| [Performance Benchmarks](docs/PERFORMANCE_BENCHMARKS.md) | Load test results |
| [K8s Deployment Guide](deployment/K8S_DEPLOYMENT_GUIDE.md) | Kubernetes setup |
| [CHANGELOG](CHANGELOG.md) | Version history (v0.1.0 → v4.4.0) |
| [CONTRIBUTING](CONTRIBUTING.md) | Contribution guidelines |

## 🔐 API Authentication

All API endpoints in the production profile require authentication.  
If upgrading from earlier unauthenticated/internal deployments, this is a breaking client behavior change and existing callers must add an API key header.

```bash
curl -H "X-API-Key: qplant_YOUR_KEY_HERE" \
  https://api.qplant.myrrha.example.com/api/v1/config
```

## 🧪 Testing

```bash
# Run all tests
pytest --cov=. --cov-report=html -v

# Run specific test categories
pytest authentication/tests/         # Auth tests
pytest load_testing/tests/           # Load tests
pytest visual_regression/            # Visual tests

# Run smoke load test
cd load_testing
./run_load_tests.sh smoke_test
```

## 🎯 Performance

Tested and validated for:
- **300 concurrent users** (Grade A+)
- **P50 latency:** 52ms
- **P95 latency:** 178ms (target: <200ms)
- **P99 latency:** 294ms (target: <300ms)
- **Error rate:** 0.02% (target: <0.1%)

## 🔒 Security

- API key authentication (PBKDF2-HMAC-SHA256 + per-key salt)
- Rate limiting (1000 req/hour default)
- 0 critical/high vulnerabilities
- Complete SBOM (247 dependencies)
- License compliance validated

## 📦 Deployment

Production deployment via Kubernetes:

```bash
# Deploy
kubectl apply -f deployment/k8s/

# Verify
kubectl get pods -n qplant-production
kubectl get svc -n qplant-production
```

Docker Compose (staging):

```bash
cd deployment
docker-compose -f docker-compose.yml -f docker-compose.staging.yml up -d
```

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## 📄 License

Proprietary — MYRRHA/SCK-CEN

## 👥 Team

**Project:** MYRRHA QPLANT Cryogenic Dashboard  
**Organization:** GBOGEB  
**Repository:** https://github.com/GBOGEB/ABACUS

---

**Version:** v4.4.0  
**Last Updated:** 2026-05-17  
**Maturity:** Production Ready (9.2/10)
