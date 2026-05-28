# Recursive Versioning Framework — Complete Guide

> **Version:** 1.0  
> **Date:** 2026-05-12  
> **Project:** MYRRHA QPLANT Cryogenic Leak Rate Dashboard  
> **Framework:** Edit_WORD_Roundtrip  
> **SSOT:** QPS (Addendum II)_Master.docx (Rev. 52)  

---

## 1. Overview

This framework establishes a **recursive versioning architecture** for the QPLANT Cryogenic Dashboard project. It provides:

- **Canonical SSOT** from QPS contract documents
- **Recursive versioning** with knowledge nodes per phase
- **Temporal lineage** tracking from baseline to current
- **Idempotent review** capability across all phases
- **Human-readable views** of all SSOT documents

### 1.1 Architecture Summary

```
┌─────────────────────────────────────────────────────────────┐
│                    SSOT Architecture                         │
├─────────────────────────────────────────────────────────────┤
│  MASTER_Input.docx ──→ Version Manifest ──→ Knowledge Graphs│
│  CONTRACT_Baseline.pdf  Document Schema     Phase Diagrams  │
│                         Change Log          Review Dashboard│
│                         Approval Registry   Review Scripts  │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Directory Structure

```
/home/ubuntu/
├── ssot_architecture/           # SSOT canonical sources
│   ├── MASTER_Input.docx        # Primary SSOT (QPS Addendum II)
│   ├── CONTRACT_Baseline.pdf    # Contract reference
│   ├── version_manifest.yaml    # Version tracking with Git SHA
│   ├── document_schema.json     # Document structure definition
│   ├── change_log.md            # Human-readable change history
│   └── approval_registry.yaml   # Approval lineage tracking
│
├── ssot_repository/             # Git repository for SSOT lineage
│   ├── .git/                    # Git with hooks (pre-commit, etc.)
│   ├── .gitattributes           # DOCX binary tracking
│   ├── knowledge_graphs/        # Phase knowledge graphs
│   └── phase_diagrams/          # ASCII diagrams
│
├── knowledge_graphs/            # Phase knowledge graphs
│   ├── phase_1_knowledge_graph.yaml
│   ├── phase_2_knowledge_graph.yaml
│   ├── phase_3_knowledge_graph.yaml
│   ├── phase_4_knowledge_graph.yaml
│   └── cross_phase_lineage.yaml
│
├── phase_diagrams/              # ASCII phase diagrams
│   ├── phase_N_state.txt        # State diagrams (×4)
│   ├── phase_N_lineage.txt      # Lineage diagrams (×4)
│   └── phase_N_nodes.txt        # Node network diagrams (×4)
│
├── recursive_reviews/           # Backward recursive reviews
│   ├── phase_4_to_3_review.md
│   ├── phase_3_to_2_review.md
│   ├── phase_2_to_1_review.md
│   ├── phase_1_to_baseline_review.md
│   └── recursive_synthesis.md
│
├── idempotent_review_system/    # Review scripts
│   ├── review_phase_N.py        # Per-phase review
│   ├── review_item_across_phases.py  # Cross-phase item tracing
│   └── full_recursive_review.py # Complete recursive review
│
├── human_readable_views/        # HTML/MD views
│   ├── MASTER_Input.html/.md    # SSOT document views
│   ├── CONTRACT_Baseline.html/.md
│   ├── phase_N_summary.html     # Phase summaries (×4)
│   ├── requirements_traceability_matrix.html
│   ├── test_coverage_matrix.html
│   ├── approval_audit_trail.html
│   └── kpi_dashboard.html
│
├── recursive_review_dashboard.html  # Interactive dashboard
├── phase_versioning_framework.md    # Versioning convention
├── phase_4_baseline.md              # Phase 4 definition
├── RECURSIVE_FRAMEWORK_GUIDE.md     # This guide
└── SSOT_LINEAGE_REPORT.md           # Thread of evidence
```

---

## 3. Versioning Convention

### 3.1 Version Format

```
SSOT:  v<MAJOR>.<MINOR>         (e.g., v0.1, v1.0)
Phase: v4.<PHASE>.<ITERATION>   (e.g., v4.1.0, v4.2.3)
Node:  v4.<P>.<I>-node<ID>      (e.g., v4.2.1-node-015)
```

### 3.2 Current Versions

| Level | Version | Description |
|-------|---------|-------------|
| SSOT | v0.1 | QPS baseline (defacto) |
| Phase 1 | v4.1.3 | Stabilization + DMAIC ✓ |
| Phase 2 | v4.2.3 | Integration + DMAIC ✓ |
| Phase 3 | v4.3.3 | Enterprise + DMAIC ✓ |
| Phase 4 | v4.4.0 | Recursive Framework (active) |
| SSOT Target | v1.0 | First approved release |

---

## 4. How to Use

### 4.1 Review a Specific Phase

```bash
python3 idempotent_review_system/review_phase_N.py --phase 1
python3 idempotent_review_system/review_phase_N.py --phase all
python3 idempotent_review_system/review_phase_N.py --phase 3 --output report.json
```

### 4.2 Trace an Item Across Phases

```bash
# By node ID
python3 idempotent_review_system/review_item_across_phases.py --node v4.1.0-node-002

# By SSOT reference
python3 idempotent_review_system/review_item_across_phases.py --ssot "section-4.3"

# By keyword
python3 idempotent_review_system/review_item_across_phases.py --keyword "config"
```

### 4.3 Run Full Recursive Review

```bash
# Full review with validation
python3 idempotent_review_system/full_recursive_review.py

# Validate and exit with status code
python3 idempotent_review_system/full_recursive_review.py --validate

# JSON output
python3 idempotent_review_system/full_recursive_review.py --format json --output review.json
```

### 4.4 View the Dashboard

Open `recursive_review_dashboard.html` in a browser for:
- Phase overview with KPIs
- Knowledge node explorer with search/filter
- Temporal timeline visualization
- Version lineage graph
- SSOT traceability matrix
- Phase comparison mode

### 4.5 Git Operations

```bash
cd /home/ubuntu/ssot_repository

# View branches
git branch -a

# View tags
git tag -l

# View log
git log --oneline --graph

# The repository has pre-commit hooks that validate:
# - YAML syntax
# - JSON syntax
# - Commit message format
```

---

## 5. Knowledge Node Structure

Each knowledge node follows this schema:

```yaml
node_id: "v4.2.1-node-015"
phase: 2
iteration: 1
type: requirement | implementation | test | improvement | artifact
parent_nodes: [...]        # Backward references
ssot_refs: [...]           # SSOT document references
status: planned | in-progress | review | approved | archived
dmaic_phase: define | measure | analyze | improve | control
kpis: [{metric, value, target}]
artifacts: [file paths]
```

---

## 6. DMAIC Integration

Each phase follows a DMAIC cycle:

1. **Define** — Scope from previous phase + SSOT requirements
2. **Measure** — Baseline metrics from previous phase
3. **Analyze** — Root cause analysis of gaps
4. **Improve** — Implementation of improvements
5. **Control** — Sustainability checks and documentation

The recursive review direction is: **Phase 4 → 3 → 2 → 1 → Baseline**

---

## 7. SSOT Traceability

All knowledge nodes should reference SSOT sections:

```
MASTER_Input.docx#section-4.1   → General Requirements
MASTER_Input.docx#section-4.3   → Global Design Criteria
MASTER_Input.docx#section-4.4.3 → WCS Compressor Requirements
CONTRACT_Baseline.pdf#page-15   → Contract specification
config.yaml#compressor.count    → Config parameter
```

---

## 8. Idempotency Guarantee

The review system produces **deterministic output**: given the same knowledge graph inputs, the review scripts will always produce the same report. This is verified via the **idempotency hash** included in every report.

```json
{
  "idempotency_hash": "858b070614b3856c...",
  "review_generated": "2026-05-12T19:05:51Z"
}
```

If the hash changes, it means the underlying data has changed (which is expected during development, but not for approved phases).

---

## 9. File Inventory

| # | Path | Type | Description |
|---|------|------|-------------|
| 1 | `ssot_architecture/MASTER_Input.docx` | SSOT | Canonical source document |
| 2 | `ssot_architecture/CONTRACT_Baseline.pdf` | SSOT | Contract reference |
| 3 | `ssot_architecture/version_manifest.yaml` | Config | Version tracking |
| 4 | `ssot_architecture/document_schema.json` | Config | Structure definition |
| 5 | `ssot_architecture/change_log.md` | Docs | Change history |
| 6 | `ssot_architecture/approval_registry.yaml` | Config | Approval chain |
| 7-11 | `knowledge_graphs/*.yaml` | Data | Phase knowledge graphs |
| 12-23 | `phase_diagrams/*.txt` | Docs | ASCII diagrams |
| 24 | `recursive_review_dashboard.html` | UI | Interactive dashboard |
| 25 | `phase_versioning_framework.md` | Docs | Versioning spec |
| 26 | `phase_4_baseline.md` | Docs | Phase 4 definition |
| 27-31 | `recursive_reviews/*.md` | Docs | Recursive reviews |
| 32-34 | `idempotent_review_system/*.py` | Code | Review scripts |
| 35-46 | `human_readable_views/*` | Views | HTML/MD views |
| 47 | `RECURSIVE_FRAMEWORK_GUIDE.md` | Docs | This guide |
| 48 | `SSOT_LINEAGE_REPORT.md` | Docs | Thread of evidence |
