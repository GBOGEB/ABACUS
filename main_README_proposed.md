# ABACUS — 12-Cluster Cryogenic Engineering Analysis System

**Project:** Multi-Agent DMAIC-Driven Analysis for QPLANT Cryoplant (SCK CEN)  
**Architecture:** 12-Cluster Parallel Agent Orchestration  
**Governance:** DOW (Design of Work) — Omnipotent Oversight Layer

---

## 🎯 What Is ABACUS?

A recursive, self-improving multi-agent system that applies **DMAIC methodology** (Define, Measure, Analyze, Improve, Control) to cryogenic engineering analysis. Built around the **12-Cluster Architecture** with DOW governance, KEB execution, and GBOGEB observability.

### The 12 Clusters
| Tier | Clusters | Function |
|------|----------|----------|
| **Analysis** | C1-C4 | DMAIC Core (Define, Measure, Analyze, Improve) |
| **Documentation** | C5-C6 | Doc Generation, Version Tracking |
| **Recursive** | C7-C8 | Self-Improvement, Orchestration Hub |
| **Knowledge** | C9-C12 | KEB, GBOGEB, Temporal Scanner, Metrics |

---

## 🚀 Quick Start

```bash
# 1. Test core import
python -c "from DMAIC_V3.config import DMAICConfig; print('OK')"

# 2. Run orchestrator
python local_mcp/agent_orchestrator_v3.0.py

# 3. Launch dashboard
open cryo_dashboard_v0_3_0/index.html
```

---

## 📂 Repository Structure

| Directory | Purpose | README |
|-----------|---------|--------|
| `ABACUS-v031/` | Canonical foundation (indexes, DOW config) | [→](section_readmes/ABACUS-v031_README.md) |
| `ABACUS-v032/` | Production pipeline (phases 0-9) | [→](section_readmes/ABACUS-v032_README.md) |
| `ABACUS-UNIFIED/` | Merged knowledge base (92.5/100) | [→](section_readmes/ABACUS-UNIFIED_README.md) |
| `DMAIC_V3/` | Core engine (12-cluster, agents) | [→](section_readmes/DMAIC_V3_README.md) |
| `local_mcp/` | V2.3 agents & MCP integration | [→](section_readmes/local_mcp_README.md) |
| `scripts/` | Build, deploy, validate utilities | [→](section_readmes/scripts_README.md) |
| `staging/` | Integration bridges | [→](section_readmes/staging_README.md) |
| `cryo_dashboard_v0_3_0/` | CRYO metrics dashboard | [→](cryo_dashboard_v0_3_0/README.md) |
| `.github/workflows/` | 32 CI/CD workflows | [→](.github/workflows/README.md) |

---

## 📊 Key Documents

| Document | Purpose |
|----------|---------|
| [12-Cluster Architecture](12CLUSTER_ARCHITECTURE_BOOK.md) | Primary architecture spec |
| [12-Cluster Vision](12_cluster_vision.md) | Elevated cluster model documentation |
| [Version Lineage](lineage_analysis.md) | Complete version heritage analysis |
| [Tool Ecosystem](tool_ecosystem_map.md) | DOW, KEB, GBOGEB interconnections |
| [SSOT Catalog](ssot_artifacts_catalog.md) | Truth artifact inventory |
| [Integration Tests](integration_test_results.md) | Smoke test results |
| [Recovery Report](recovery_report.md) | Corrupted file recovery |

---

## 🔧 Component Overview

```
DOW (Governance) ──→ 12-Cluster Orchestrator ──→ DMAIC Phases (0-9)
       │                      │                         │
       ├── KEB (Execution)    ├── C1-C4 (Analysis)      ├── Define
       ├── GBOGEB (Observe)   ├── C5-C6 (Documentation) ├── Measure
       └── MCP (IDE)          ├── C7-C8 (Recursive)     ├── Analyze
                              └── C9-C12 (Knowledge)    ├── Improve
                                                        └── Control + Knowledge + Recursive
```

---

## 📋 Version Lineage

All versions are **active and valuable** — none should be deleted:
- **v0.31** → Canonical foundation (indexes, DOW config) 
- **v0.32** → Production pipeline (full DMAIC 0-9)
- **UNIFIED** → Merged knowledge (6 agents, 4 orchestrators, 19 knowledge packs)
- **V2.3** → Active development (6/6 agents upgraded)
- **V3.3** → Engine + documentation

*See [lineage_analysis.md](lineage_analysis.md) for complete heritage.*
