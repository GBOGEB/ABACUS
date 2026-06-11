# SSOT (Single Source of Truth) Artifacts Catalog

**Generated:** 2026-05-16 | **Repository:** GBOGEB/ABACUS

---

## Overview

This document catalogs all user-created truth artifacts in the repository. The ABACUS project is a **cryogenic engineering analysis system** (QPLANT cryoplant) being developed at SCK CEN, with DMAIC methodology applied to requirements traceability, system analysis, and documentation generation.

---

## SSOT Artifact Inventory

### Excel Files (Requirements & Traceability)

#### 1. `rtm_integration/automation/docs/rtm/QPLANT_RTM.xlsx`
- **Type:** Requirements Traceability Matrix
- **Sheets:** Navigation, RTM (17 requirements), SBS (System Breakdown Structure), Summary, BySystem, ByType
- **Content:** 16 formal requirements for the QPLANT cryogenic system
- **Key Requirements:**
  - RTM-01: Uninterrupted 2K operation for ≥90 consecutive days
  - RTM-02: Maintenance schedule (6mo/1yr/5yr/10yr constraints)
  - RTM-03: 40-year lifetime requirement
  - RTM-04: ≥50 warm-up/cool-down cycles (300K ↔ 2K)
- **SBS Hierarchy:** QSYS → QSYS-PR → QPLANT/QINFRA/QCELL/QDIST → WCS/QRB
- **Priority Distribution:** 15 High, 1 Medium, 0 Safety-specific

#### 2. `rtm_integration/deliverables/QPLANT_Requirements_Traceability_Matrix_v2.xlsx`
- **Type:** Enhanced RTM (version 2)
- **Relationship:** Extended version of QPLANT_RTM.xlsx with additional traceability

### WORD_MASTER Files
- **Status:** ❌ No WORD_MASTER_*.docx files found in repository
- **Note:** These may exist in the user's local workspace but have not been committed to GitHub
- **Recommendation:** If WORD_MASTER files contain critical truth data, they should be added to the repository

### PDF Files
- **Status:** ❌ No PDF files found in repository
- **Note:** PDF versions may be generated locally but not committed

### PowerPoint Files
- **Status:** ❌ No .pptx files found in repository
- **Note:** Slide generation exists via `slides/qplant_sckcen_template.py`

---

## Key Documentation Artifacts (Markdown SSOT)

### Master Indexes
| File | Lines | Purpose |
|------|-------|---------|
| `DMAIC_V3_MASTER_INDEX.md` | Master index for V3 | Version map |
| `ABACUS_V21_MASTER_INDEX.md` | V2.1 master index | Legacy reference |
| `MASTER_INDEX_V3.1_2025-11-10.md` | V3.1 index snapshot | Temporal reference |
| `MASTER_INDEX_V3.3_20251110.md` | V3.3 index snapshot | Latest reference |

### Canonical Configuration Files
| File | Format | Purpose |
|------|--------|---------|
| `ABACUS-v031/canonical.index.json` | JSON | Machine-readable artifact registry |
| `ABACUS-v031/canonical.index.yaml` | YAML | Human-readable artifact index |
| `ABACUS-v031/canonical.index.run1.json` | JSON | Iteration 1 snapshot |
| `ABACUS-v031/canonical.index.run2.json` | JSON | Iteration 2 snapshot |
| `ABACUS-UNIFIED/canonical_index.json` | JSON | Merged canonical index |
| `ABACUS-v031/dow_engine_config.yaml` | YAML | DOW Engine configuration |
| `ABACUS-v031/artifact_rankings.json` | JSON | Quality scoring data |

### Handover Documents (Critical Truth Artifacts)
| File | Purpose | Status |
|------|---------|--------|
| `ENGINE_DOW_handover_min.md` | DOW v0.5 lean bootstrap spec | ✅ Active |
| `COMPREHENSIVE_12_CLUSTER_HANDOVER_WITH_EXECUTION_TRACKING.md` | Phase 1 handover | ✅ Active |
| `DMAIC_V3_CANONICAL_HANDOVER_BOOK.md` | Canonical handover | ❌ Empty (0 bytes) |
| `HANDOVER_PACKAGE_INDEX.md` | Package listing | ✅ Active |
| `FINAL_HANDOVER.html` | Interactive progress snapshot | ✅ Active |
| `Integrated_handover_user.md` | User-facing handover | ✅ Active |

### Version Status Documents
| File | Version | Claims |
|------|---------|--------|
| `ABACUS_V21_DEPLOYMENT_COMPLETE_SUMMARY.md` | V2.1 | Deployment complete |
| `V2.2_IMPLEMENTATION_COMPLETE.md` | V2.2 | Implementation complete |
| `DMAIC_V2.3_IMPLEMENTATION_COMPLETE.md` | V2.3 | Implementation complete |
| `DMAIC_V3.3_HANDOVER_COMPLETE.md` | V3.3 | Handover complete |

---

## Cross-Reference: Intent vs Implementation

### Goal Analysis (from documentation)
| Stated Goal | Document Source | Actual Status |
|------------|----------------|---------------|
| "V2.3.0 100% complete" | README.md | ✅ Agent upgrades done (6/6), ⚠️ Deployment/testing pending |
| "12-cluster orchestration" | 12CLUSTER_ARCHITECTURE_BOOK.md | ⚠️ Partial (Phase 0 done, C8 is blocker) |
| "Recursive DMAIC with convergence" | V3 docs | ⚠️ Engine exists but convergence untested end-to-end |
| "DOW governance layer" | ENGINE_DOW_handover_min.md | ⚠️ Agents exist, full integration pending |
| "QPLANT cryoplant analysis" | QPLANT_RTM.xlsx | ✅ 16 requirements defined, traceability matrix built |
| "Production deployment" | Multiple | ❌ Not yet deployed (CI/CD workflows ready but untested) |

### Coverage Gap: 100% vs 26.7% Claims
- **100% claim** refers to: V2.3 agent upgrade completion (all 6 agents upgraded to V2.3_OPTIMIZED)
- **26.7% reality** (approx) refers to: Full system integration and deployment readiness
- **Breakdown:**
  - Agent code: ✅ 100% upgraded
  - Orchestrator: ⚠️ ~75% (V3.0 partial)
  - KEB/GBOGEB: ⚠️ ~60% (timeout issues)
  - 12-Cluster integration: ⚠️ ~30% (C8 blocker)
  - End-to-end testing: ❌ ~10%
  - Production deployment: ❌ 0%
  - Documentation completeness: ⚠️ ~70% (missing docs_versioned/)

---

## Missing SSOT Artifacts

### Expected but Not Found
1. **WORD_MASTER_*.docx** — User's primary truth documents (not in repo)
2. **docs_versioned/** — Entire directory referenced in README
3. **DMAIC_V3/docs/handover/Chapter_01.md through Chapter_12.md** — 12-chapter handover book
4. **tools_v2.3/** — Tool directory referenced in README
5. **tracking_v2.3/** — Tracking directory referenced in README

### Recommendations
1. **Commit WORD_MASTER files** to repository if they exist locally
2. **Create docs_versioned/** with actual content matching README promises
3. **Generate the 12-chapter handover book** from existing code and documentation
4. **Build tools_v2.3/ and tracking_v2.3/** or update README to reflect actual structure
