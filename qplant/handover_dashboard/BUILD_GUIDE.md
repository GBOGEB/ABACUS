# Build Guide — QPLANT Cryogenic Dashboard v4.0.0

## Quick Start

```bash
# Full build (config validation → generation → tests → verification)
./build_all.sh

# Build without tests (faster)
./build_all.sh --skip-tests

# Verbose output
./build_all.sh --verbose
```

## Prerequisites

- Python 3.10+
- Required packages: `pip install -r requirements.txt`
  - numpy, pandas, plotly, scipy, pyyaml, pytest, pytest-cov

## Build Pipeline

```
data/config.yaml (SSoT)
    │
    ▼
[Step 0] Validate configuration
    │
    ▼
[Step 1] src/generate_standards_stats.py
    │    → docs/index_v3.html (32 slides)
    │    → docs/visualizations_v3/ (15 charts)
    │    → docs/standards/ (compliance docs)
    │    → docs/statistical/ (MC, PCA)
    │
    ▼
[Step 2] src/build_v3_1.py
    │    → docs/visualizations_v3/ (6 additional charts)
    │    → docs/compressors/*.html (2 pages)
    │    → docs/liquid_he/*.html (1 page)
    │    → docs/index_v3_1.html (40 slides)
    │
    ▼
[Step 3] src/build_dense_slides.py
    │    → docs/index_v3_1.html (40 slides, overwrite)
    │    → docs/STAKEHOLDER_PRESENTATION.html (10 slides)
    │
    ▼
[Step 4] sed transform v3.1→v4.0
    │    → docs/index_v4_0.html (canonical v4.0.0 navigator)
    │
    ▼
[Step 5] src/build_dashboard.py
    │    → docs/index.html (landing hub)
    │    → docs/manifest.json
    │
    ▼
[Step 6] pytest tests/
    │    → dist/test-report.html
    │
    ▼
[Step 7] src/verify_triage.py --all
         → TRIAGE_GAP_ANALYSIS.md
         → TRIAGE_COMPLIANCE_REPORT.json
         → docs/triage_compliance.html
```

## Configuration (Single Source of Truth)

All design parameters are in `data/config.yaml`. **Never hardcode values** in Python or HTML.

### Key parameters:
| Parameter | Path in config.yaml | Value |
|-----------|-------------------|-------|
| HP compressor count | `compressor_specifications.hp_compressors.count` | 3 |
| Motor power | `compressor_specifications.fsd575.motor_power_kW` | 315 |
| Package power | `compressor_specifications.fsd575.package_power_kW` | 348.54 |
| Max total flow | `compressor_specifications.three_skid_totals.max_total_flow_gs` | 337.62 |
| System CAPEX | `financial.compressor_capex.total_system_eur` | 1,420,000 |

### Using config in Python:
```python
from src.config_loader import cfg

count = cfg.get('compressor_specifications.hp_compressors.count')  # 3
power = cfg.get('compressor_specifications.fsd575.motor_power_kW')  # 315
```

## Individual Build Scripts

| Script | Purpose | Output |
|--------|---------|--------|
| `build.sh` | Legacy build (standards + dashboard) | `docs/index_v3.html`, `docs/index.html` |
| `build_all.sh` | **Master build** (all steps) | Everything |
| `setup.sh` | Environment setup | venv, dependencies |
| `validate.sh` | Validation checks | Validation report |
| `package.sh` | Create distribution ZIP | `dist/handover.zip` |

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ -v --cov=src --cov-report=html:htmlcov

# Run specific test
python -m pytest tests/test_calc_leak_rate.py -v
```

## Outputs

| Directory | Contents |
|-----------|----------|
| `docs/` | All HTML pages, charts, presentations |
| `docs/visualizations_v3/` | 22 interactive Plotly charts |
| `docs/visualizations/` | 27 v2.5 charts |
| `docs/plots/` | 5 core triage plots |
| `dist/` | Build logs, test reports, distribution ZIP |
| `outputs/` | Data tables, manifests |

## Version Management

- Version stored in: `VERSION` (plain text), `VERSION.json` (detailed), `data/config.yaml`
- To update version: edit all three, then run `./build_all.sh`
- Generated files automatically pick up version from `VERSION` file
