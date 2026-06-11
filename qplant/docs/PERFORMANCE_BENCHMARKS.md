# Performance Benchmarks

**Project:** MYRRHA QPLANT Cryogenic System  
**Version:** v4.4.0  
**Date:** 2026-05-17

---

## API Endpoint Performance Baselines

| Endpoint | p50 (ms) | p95 (ms) | p99 (ms) | Error Rate |
|----------|----------|----------|----------|------------|
| `GET /api/v1/health` | 30 | 100 | 200 | 0.00% |
| `GET /api/v1/config` | 50 | 150 | 300 | 0.05% |
| `GET /api/v1/config/{section}` | 40 | 120 | 250 | 0.05% |
| `POST /api/v1/leak-rate` | 80 | 200 | 400 | 0.10% |
| `POST /api/v1/leak-rate/batch` | 150 | 400 | 800 | 0.20% |
| `POST /api/v1/compressors/reliability` | 100 | 250 | 500 | 0.10% |
| `POST /api/v1/monte-carlo` | 200 | 500 | 1000 | 0.50% |
| `GET /api/v1/compressors/specs` | 40 | 120 | 250 | 0.00% |
| `GET /api/v1/visualizations/catalog` | 60 | 180 | 350 | 0.05% |
| `GET /api/v1/build/status` | 50 | 150 | 300 | 0.05% |

## Concurrency Targets

| Metric | Target | Maximum |
|--------|--------|---------|
| Concurrent users (normal) | 150 | — |
| Concurrent users (peak) | 300 | — |
| Breaking point estimate | — | 500+ |
| Requests/second (sustained) | 1,000+ | — |
| Data transfer | 10+ Mbps | — |

## Load Test Scenarios

| Scenario | Users | Rate | Duration | Purpose |
|----------|-------|------|----------|---------|
| Smoke Test | 10 | 2/s | 2 min | Quick validation |
| Normal Load | 100 | 10/s | 10 min | Production simulation |
| Peak Load | 300 | 20/s | 15 min | 2× expected load |
| Stress Test | 500 | 50/s | 20 min | Find breaking point |
| Endurance | 150 | 10/s | 60 min | Sustained stability |

## SLA Targets

| Metric | Target |
|--------|--------|
| Availability | 99.9% |
| Max response time | < 1000ms |
| Error budget | 0.1% |

## Infrastructure Scaling

| Component | Min | Max | Trigger |
|-----------|-----|-----|---------|
| API Pods | 3 | 10 | CPU > 70% or Memory > 80% |
| Scale-up window | — | — | 60s stabilization |
| Scale-down window | — | — | 300s stabilization |

## How to Run Load Tests

```bash
# Install locust
pip install locust

# Smoke test
bash load_testing/run_load_tests.sh smoke_test

# Analyze results
python3 load_testing/analyze_results.py
```

Reports are generated as HTML files in `load_testing/reports/`.
