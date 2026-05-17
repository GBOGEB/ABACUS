# Phase 2 Integration Guide — QPLANT Cryogenic Dashboard

> **Version:** 4.0.0 → 4.1.0  
> **Date:** 2026-05-12  
> **Scope:** API Integration, Presentation Automation, Monitoring, Cross-Linking  

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                    QPLANT System Architecture                     │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────────────┐  │
│  │ config.yaml │───►│config_loader │───►│  Python Engine     │  │
│  │   (SSoT)    │    │ (singleton)  │    │ • calc_leak_rate   │  │
│  └─────────────┘    └──────────────┘    │ • monte_carlo      │  │
│                                          │ • compressor_rel   │  │
│                                          │ • wcs_scenarios    │  │
│                                          │ • liquid_he_loss   │  │
│                                          └────────┬───────────┘  │
│                                                   │              │
│                    ┌──────────────────────────────┤              │
│                    │                              │              │
│  ┌────────────────▼──────┐    ┌──────────────────▼───────────┐  │
│  │   FastAPI REST API     │    │   HTML Generators            │  │
│  │   (api/main.py)        │    │   • build_dense_slides.py    │  │
│  │   Port: 8100           │    │   • build_v3_1.py            │  │
│  │   14 endpoints         │    │   • generate_standards.py    │  │
│  └────────┬───────────────┘    │   • generate_dashboard.py    │  │
│           │                    └──────────────────┬───────────┘  │
│           │                                       │              │
│  ┌────────▼───────────────┐    ┌──────────────────▼───────────┐  │
│  │   Next.js Portal       │    │   Static HTML Docs            │  │
│  │   (HBHS Engineering)   │    │   • 54 Plotly charts          │  │
│  │   Port: 3000           │    │   • 5 triage pages            │  │
│  └────────────────────────┘    │   • 3 navigators              │  │
│                                └──────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────┐    ┌──────────────────────────────┐  │
│  │ Monitoring Dashboard   │    │  Presentation Generator      │  │
│  │ (monitoring_dashboard/)│    │  (scripts/generate_pres.py)  │  │
│  └────────────────────────┘    └──────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Cross-Link Registry (cross_link_registry.json)             │  │
│  │ 50 artifacts · 48 dependency edges · validated             │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Component 1: FastAPI REST API

### Setup

```bash
cd /home/ubuntu/handover_dashboard
pip install fastapi uvicorn pydantic
```

### Run

```bash
# Development (with auto-reload)
uvicorn api.main:app --host 0.0.0.0 --port 8100 --reload

# Production
uvicorn api.main:app --host 0.0.0.0 --port 8100 --workers 4
```

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | System health check |
| GET | `/api/v1/config` | SSoT config summary |
| GET | `/api/v1/config/full` | Complete config as JSON |
| GET | `/api/v1/config/{section}` | Specific config section |
| POST | `/api/v1/leak-rate` | Single leak-rate calculation |
| POST | `/api/v1/leak-rate/batch` | Batch leak-rate calculations |
| POST | `/api/v1/monte-carlo` | Monte Carlo simulation |
| POST | `/api/v1/compressors/reliability` | Compressor reliability analysis |
| GET | `/api/v1/compressors/specs` | Compressor specifications |
| GET | `/api/v1/visualizations/catalog` | List available charts |
| GET | `/api/v1/visualizations/compressor-availability` | Chart data |
| GET | `/api/v1/build/status` | Build pipeline status |
| POST | `/api/v1/build/trigger` | Trigger build pipeline |

### Documentation

- **Swagger UI:** http://localhost:8100/docs
- **ReDoc:** http://localhost:8100/redoc
- **OpenAPI Spec:** `api/openapi.json`

### Next.js Integration

```typescript
// In Next.js: lib/api-client.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8100';

export async function getConfig() {
  const res = await fetch(`${API_BASE}/api/v1/config`);
  return res.json();
}

export async function calculateLeakRate(params: {
  leak_rate_mbar_l_s: number;
  temperature_k: number;
  pressure_bar_abs: number;
}) {
  const res = await fetch(`${API_BASE}/api/v1/leak-rate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  return res.json();
}
```

### CORS Configuration

```bash
# Set allowed origins via environment variable
export CORS_ORIGINS="http://localhost:3000,http://localhost:3001,https://your-domain.com"
```

---

## Component 2: Presentation Generator

### Quick Start

```bash
cd /home/ubuntu/handover_dashboard

# Generate for specific audience
python scripts/generate_presentation.py --audience=executive
python scripts/generate_presentation.py --audience=technical
python scripts/generate_presentation.py --audience=financial

# Generate all audiences
python scripts/generate_presentation.py --audience=all --verbose
```

### Output

Generated presentations are saved to `docs/presentations/`:
- `PRESENTATION_EXECUTIVE_v4_0_0.html`
- `PRESENTATION_TECHNICAL_v4_0_0.html`
- `PRESENTATION_FINANCIAL_v4_0_0.html`

### Templates

Templates are in `templates/`:
- `presentation_executive.html` — Executive and financial audiences
- `presentation_technical.html` — Technical deep-dive

### Customization

All data is auto-injected from `config.yaml` via Jinja2 template variables. To customize:

1. Edit templates in `templates/`
2. Add new context variables in `scripts/generate_presentation.py`
3. Re-run the generator

---

## Component 3: Monitoring Dashboard

### Access

Open `monitoring_dashboard/index.html` in a browser.

### Features

- **KPI Row:** Tests, compliance, build status, TODOs, config alignment
- **Build Pipeline:** 9-step pipeline status with timing
- **Config Health:** SSoT drift detection table
- **Test Suite:** Per-file test results and pass rates
- **Version Tracking:** Multi-artifact version alignment
- **TODO Progress:** Priority-based progress tracking
- **Activity Log:** Chronological event feed
- **Tabs:** Overview, Build, Config, TODOs, History

### Metrics Collection

```bash
# Run health check
python monitoring_dashboard/collect_metrics.py --check

# Generate full metrics JSON
python monitoring_dashboard/collect_metrics.py
```

### Data Sources

| Data | Source | Refresh |
|------|--------|---------|
| Test results | `pytest tests/` | On demand |
| Compliance | `TRIAGE_COMPLIANCE_REPORT.json` | Post-build |
| Config drift | `config_loader.py` validation | On demand |
| Version info | `config.yaml`, `VERSION.json`, git | On demand |
| TODOs | `phase1_consolidated_todos.md` | Manual |

---

## Component 4: Cross-Link Registry

### Registry File

`/home/ubuntu/cross_link_registry.json` contains:
- **50 artifact entries** with paths, types, roles, and relationships
- **48 dependency edges** (directed: source → consumer)
- **Validation results** (paths, edges, orphans, cycles)

### Validation

```bash
python validate_cross_links.py
```

### Registry Structure

```json
{
  "artifact_index": {
    "ARTIFACT_ID": {
      "path": "relative/path",
      "type": "source_code|documentation|api|...",
      "role": "specific_role",
      "description": "...",
      "depends_on": ["OTHER_ID"],
      "generates": ["OUTPUT_ID"]
    }
  },
  "dependency_graph": {
    "edges": [["SOURCE_ID", "TARGET_ID"], ...]
  }
}
```

---

## Build Pipeline Integration

All Phase 2 components are integrated with the build pipeline:

```bash
# Full build (includes Phase 2 components)
./build_all.sh

# Generate presentations after build
python scripts/generate_presentation.py --audience=all

# Collect monitoring metrics
python monitoring_dashboard/collect_metrics.py

# Validate cross-links
python validate_cross_links.py

# Start API server
uvicorn api.main:app --port 8100
```

---

## Security Considerations

| Area | Implementation |
|------|---------------|
| CORS | Restricted to configured origins |
| Input Validation | Pydantic models with strict types |
| Build Trigger | POST endpoint (consider auth for production) |
| Config Access | Read-only through API (write via file only) |
| Error Handling | All endpoints wrapped in try/except with logging |

---

## Performance

| Operation | Expected Time |
|-----------|--------------|
| API health check | <50ms |
| Leak rate calculation | <10ms |
| Monte Carlo (10k iterations) | <500ms |
| Compressor reliability | <10ms |
| Full build pipeline | ~4s |
| Presentation generation (all 3) | <2s |
| Cross-link validation | <1s |

---

*Phase 2 Integration Guide — Generated 2026-05-12*
