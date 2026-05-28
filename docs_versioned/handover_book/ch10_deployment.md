# Chapter 10: Entry Points, Deployment & Operations

## 10.1 Quick Start

```bash
# Test core imports
python3 -c "from DMAIC_V3.config import DMAICConfig; print('Config OK')"

# Run orchestrator
python3 -c "from DMAIC_V3.core.twelve_cluster_orchestrator import TwelveClusterOrchestrator; print('Orchestrator OK')"

# Launch dashboard
open docs/deep_analysis_dashboard.html
```

## 10.2 Entry Points

### Python Entry Points
| Entry Point | Path | Purpose | Status |
|-------------|------|---------|--------|
| Full Pipeline | `DMAIC_V3/full_pipeline_orchestrator.py` | Run all DMAIC phases | 🟢 |
| 12-Cluster | `DMAIC_V3/core/twelve_cluster_orchestrator.py` | Parallel execution | 🟢 |
| v032 Pipeline | `ABACUS-v032/execute_full_dmaic_phases_0_to_9_v033.py` | v032 pipeline | 🟢 |
| Demo System | `demo_integrated_system.py` | Integration demo | 🟡 |
| Deployment | `run_comprehensive_deployment.py` | Full deploy | 🟡 |
| CI/CD | `cicd_github_orchestrator.py` | Workflow management | 🟢 |
| Smoke Tests | `abacus_v21_smoke_tests.py` | Validation | 🟢 |

### HTML Entry Points
| Entry Point | Path | Purpose | GH Pages? |
|-------------|------|---------|-----------|
| Docs Portal | `docs/index.html` | Main documentation | ✅ Yes |
| Dashboard | `docs/deep_analysis_dashboard.html` | Analysis dashboard | ✅ Yes |
| Cryo Dash | `cryo_dashboard_v0_3_0/index.html` | Cryo visualization | ✅ Yes |
| Handover | `docs/FINAL_HANDOVER.html` | Handover document | ✅ Yes |

### Shell Entry Points
| Entry Point | Path | Purpose |
|-------------|------|---------|
| Deploy | `scripts/deploy_to_github.sh` | GitHub deployment |
| Setup | `setup_github.sh` | Git configuration |
| Permissions | `test_permissions.sh` | Permission validation |

## 10.3 Docker Deployment

```bash
cd ABACUS-v032/
docker-compose up -d
```

## 10.4 GitHub Actions Workflows

32+ workflows configured in `.github/workflows/`:
- CI pipelines for code quality
- CD pipelines for deployment
- DMAIC phase-specific workflows
- Documentation generation

## 10.5 Environment Configuration

```bash
# .env.example provides template
cp .env.example .env
# Configure: API keys, paths, thresholds
```

## 10.6 GitHub Pages Deployment

The `docs/` directory is GitHub Pages-ready:
- `docs/_config.yml` — Jekyll configuration
- `docs/index.html` — Landing page
- All HTML dashboards are static (no backend required)
