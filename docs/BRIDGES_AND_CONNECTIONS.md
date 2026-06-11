# 🌉 Bridges & Connections — ABACUS Integration Map

[![Tuple Validation](https://img.shields.io/badge/tuple--validation-passing-brightgreen?style=flat-square)](../scripts/validate_tuple_metadata.py)
[![Bridges](https://img.shields.io/badge/bridges-6%20connected-blue?style=flat-square)](#bridge-catalog)

> This document maps explicit connections between validated tuples, handoff logs, metadata workflows, and CI/CD pipelines across the ABACUS system. Each bridge is documented with source, target, validation method, and current status.

**Last Updated:** 2026-05-18  
**Related:** [README.md](../README.md) | [Progress Tracker](progress_tracker.html) | [Tool Ecosystem](../tool_ecosystem_map.md)

---

## Bridge Catalog

### 1. Tuple → Handoff Log

**Purpose:** Validated tuple metadata entries are consumed by the handover package to produce structured handoff logs.

| Attribute | Detail |
|-----------|--------|
| **Source** | [`src/dmaic/tuple_metadata.py`](../src/dmaic/tuple_metadata.py) |
| **Target** | [`deepagent-handover-package/handover/`](../deepagent-handover-package/handover/) |
| **Validator** | [`scripts/validate_tuple_metadata.py`](../scripts/validate_tuple_metadata.py) |
| **CI Check** | [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) |
| **Status** | ✅ Connected |

**Flow:**
```
tuple_metadata.py  →  validate_tuple_metadata.py  →  01_conversation_tuple_document.md
                                                   →  02_tuple_summary.md
                                                   →  04_handover_manifest.yaml
```

**Required Fields:** `tuple_id`, `source`, `validation_log`, `downstream_consumer`, `status`  
**Valid Statuses:** `planned`, `in_progress`, `validated`, `blocked`, `released`

---

### 2. Handoff → CI Pipeline

**Purpose:** Tuple validation scripts are invoked as part of the CI pipeline to enforce schema integrity on every push.

| Attribute | Detail |
|-----------|--------|
| **Source** | [`scripts/validate_tuple_metadata.py`](../scripts/validate_tuple_metadata.py) |
| **Target** | [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) |
| **Test Suite** | [`DMAIC_V3/tests/test_tuple_metadata_validation.py`](../DMAIC_V3/tests/test_tuple_metadata_validation.py) |
| **Status** | ✅ Connected |

**Validation Chain:**
```
Push/PR  →  ci.yml  →  validate_tuple_metadata.py  →  Pass/Fail
                    →  smoke-test.yml  →  test_tuple_metadata_validation.py  →  Pass/Fail
```

---

### 3. Metadata → Knowledge Engine

**Purpose:** The temporal metadata engine feeds versioned state changes into the Phase 6 knowledge engine for cross-phase learning.

| Attribute | Detail |
|-----------|--------|
| **Source** | [`DMAIC_V3/core/temporal_metadata_engine.py`](../DMAIC_V3/core/temporal_metadata_engine.py) |
| **Target** | [`DMAIC_V3/phases/phase6_knowledge.py`](../DMAIC_V3/phases/phase6_knowledge.py) |
| **Integration** | [`local_mcp/knowledge_integration_v2.3.py`](../local_mcp/knowledge_integration_v2.3.py) |
| **Status** | ✅ Connected |

**Data Flow:**
```
temporal_metadata_engine.py  →  StateManager  →  phase6_knowledge.py
                                              →  KnowledgeReference objects
                                              →  knowledge_packages/
```

---

### 4. Handover → Execution State

**Purpose:** The handover bridge translates documentation artifacts into actionable execution state for the agent orchestrator.

| Attribute | Detail |
|-----------|--------|
| **Source** | [`DMAIC_V3/core/handover_bridge.py`](../DMAIC_V3/core/handover_bridge.py) |
| **Target** | [`local_mcp/agent_orchestrator_v3.0.py`](../local_mcp/agent_orchestrator_v3.0.py) |
| **Agents** | [`local_mcp/agents/`](../local_mcp/agents/) (6 V2.3 agents) |
| **Status** | ✅ Connected |

**Execution Chain:**
```
handover_bridge.py  →  agent_orchestrator_v3.0.py  →  V2.3 Agents (6)
                                                    →  Task Tracking (tasks.json)
                                                    →  Code Index (code_index.yaml)
```

---

### 5. CI → Dashboard

**Purpose:** CI/CD workflow outputs feed into the interactive dashboards and progress tracker hosted on GitHub Pages.

| Attribute | Detail |
|-----------|--------|
| **Source** | [`.github/workflows/`](../.github/workflows/) |
| **Target** | [`docs/progress_tracker.html`](progress_tracker.html) |
| **Generator** | [`scripts/generate_docs_html.py`](../scripts/generate_docs_html.py) |
| **Export** | [`scripts/export_docs.py`](../scripts/export_docs.py) |
| **Status** | ✅ Connected |

**Pipeline:**
```
GitHub Actions  →  generate_docs_html.py  →  docs/*.html
               →  export_docs.py          →  GitHub Pages
               →  export-docs.yml         →  progress_tracker.html
```

---

### 6. Tuple Tests → CI

**Purpose:** Dedicated tuple metadata tests run as part of the smoke test suite to catch schema regressions early.

| Attribute | Detail |
|-----------|--------|
| **Source** | [`DMAIC_V3/tests/test_tuple_metadata_validation.py`](../DMAIC_V3/tests/test_tuple_metadata_validation.py) |
| **Target** | [`.github/workflows/smoke-test.yml`](../.github/workflows/smoke-test.yml) |
| **Schema** | [`src/dmaic/tuple_metadata.py`](../src/dmaic/tuple_metadata.py) |
| **Status** | ✅ Connected |

---

## Connection Matrix

```
                    Tuples    Handoff    CI/CD    Knowledge    Dashboards    Execution
Tuples               —         ✅         ✅        —            —             —
Handoff              ✅         —         ✅        —            —             —
CI/CD                ✅        ✅          —        —            ✅            —
Knowledge            —         —          —         —            —             ✅
Dashboards           —         —         ✅        —             —             —
Execution            —         ✅         —        ✅            —              —
```

---

## Metadata Workflow Integration

The metadata workflow connects the following components into a unified pipeline:

1. **Input:** Tuple metadata entries are defined in `src/dmaic/tuple_metadata.py`
2. **Validation:** `scripts/validate_tuple_metadata.py` enforces schema (required fields, valid statuses)
3. **Testing:** `DMAIC_V3/tests/test_tuple_metadata_validation.py` provides unit-level regression checks
4. **CI Gate:** `.github/workflows/ci.yml` and `smoke-test.yml` run validation on every push/PR
5. **Knowledge:** `temporal_metadata_engine.py` tracks state changes over time
6. **Phase 6:** `phase6_knowledge.py` extracts knowledge references for cross-phase learning
7. **Handover:** `handover_bridge.py` translates artifacts into execution state
8. **Dashboard:** Results are visualized in `docs/progress_tracker.html` and GitHub Pages dashboards

---

## Cross-References

| Document | Relevance |
|----------|-----------|
| [README.md](../README.md#-bridges--connections) | Bridges summary table in main README |
| [Progress Tracker](progress_tracker.html) | Visual bridge connections graph |
| [Tool Ecosystem Map](../tool_ecosystem_map.md) | DOW/KEB/GBOGEB tool interconnections |
| [CI/CD Automation README](../CI_CD_AUTOMATION_README.md) | Workflow details and CI pipeline docs |
| [DMAIC Master Index](../DMAIC_MASTER_INDEX.md) | DMAIC phase index with phase6 references |
| [Handover Package](../deepagent-handover-package/handover/) | Tuple documents and manifests |
| [Session Tuple Analyzer](../abacus_v21_session_tuple_analyzer.py) | Session-level tuple analysis tool |

---

*This document is part of the ABACUS v4.4.0 documentation suite. See the [README](../README.md) for the full project overview.*
