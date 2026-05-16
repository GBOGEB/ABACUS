# Deployment Matrix

> Tool deployment status and hosting feasibility

| Tool Name | Path | Type | GH Pages Feasible | Needs Backend | Dependencies | Entry Point | Status |
|---|---|---|---|---|---|---|---|
| FINAL_HANDOVER | docs/FINAL_HANDOVER.html | HTML Dashboard | Yes | No | Browser | docs/FINAL_HANDOVER.html | Working |
| dashboard | docs/dashboard.html | HTML Dashboard | Yes | No | Browser | docs/dashboard.html | Working |
| index | docs/index.html | HTML Dashboard | Yes | No | Browser | docs/index.html | Working |
| deep_analysis_dashboard | docs/deep_analysis_dashboard.html | HTML Dashboard | Yes | No | Browser | docs/deep_analysis_dashboard.html | Working |
| handover_book | docs/handover_book.html | HTML Dashboard | Yes | No | Browser | docs/handover_book.html | Working |
| index | cryo_dashboard_v0_3_0/index.html | HTML Dashboard | Yes | No | Browser | cryo_dashboard_v0_3_0/index.html | Working |
| DMAIC V3 Engine | DMAIC_V3/ | Python Engine | No | Yes | Python 3.8+ | DMAIC_V3/full_pipeline_orchestrator.py | Working |
| 12-Cluster Orchestrator | DMAIC_V3/core/twelve_cluster_orchestrator.py | Python | No | Yes | Python 3.8+, threading | Import TwelveClusterOrchestrator | Working |
| RTM Integration | rtm_integration/ | Python + Excel | No | Yes | Python, openpyxl | rtm_integration/ | Working |
| CI/CD Orchestrator | cicd_github_orchestrator.py | Python | No | Yes | Python, requests | cicd_github_orchestrator.py | Working |
| Smoke Tests | abacus_v21_smoke_tests.py | Python | No | Yes | Python 3.8+ | abacus_v21_smoke_tests.py | Working |
| Demo System | demo_integrated_system.py | Python | No | Yes | Python 3.8+ | demo_integrated_system.py | Needs Config |
| DOW Bridge | staging/GBOGEB_ABACUS_DOW_INTEGRATION_BRIDGE.py | Python | No | Yes | Python 3.8+ | staging/ | Working |
