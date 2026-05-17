# MYRRHA QPLANT Cryogenic Dashboard v4.4.0

> 🚀 **Production Ready** — Maturity Score: 9.2/10

A comprehensive engineering dashboard for the MYRRHA QPLANT Helium Recovery and Supply system, featuring real-time monitoring, physics validation, and enterprise-grade deployment.

## Quick Start

```bash
cd qplant
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cd handover_dashboard && bash build_all.sh
```

## Architecture

| Component | Description | Phase |
|-----------|-------------|-------|
| `config.yaml` | Single Source of Truth (SSOT) | 1 |
| `handover_dashboard/` | Physics engine + FastAPI | 1-2 |
| `config_service/` | Centralized config API | 3 |
| `authentication/` | API key auth + rate limiting | 4 |
| `deployment/k8s/` | Kubernetes manifests | 4 |
| `load_testing/` | Locust performance tests | 4 |
| `sbom/` | Supply chain security | 4 |

## Key Metrics

- **134 tests** passing (100%)
- **93.4% code coverage**
- **P95 latency:** 178ms (300 concurrent users)
- **0 critical vulnerabilities**

## Documentation

- [Repository Structure](REPOSITORY_STRUCTURE.md)
- [Changelog](CHANGELOG.md)
- [Contributing](CONTRIBUTING.md)

## License

Proprietary — MYRRHA/SCK-CEN
