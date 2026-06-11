# Chapter 9: Version Lineage & Migration Paths

## 9.1 Version Timeline

```
2025-Q3: v2.1 (Production Baseline)
    │
2025-Q4: v0.31 (Canonical Foundation)
    │      └─ Established canonical indexes
    │
2025-Q4: v0.32 (Production Pipeline)  
    │      └─ Extended DMAIC to 10 phases
    │
2025-Q4: ABACUS-UNIFIED (Merged Knowledge Base)
    │      └─ v031 + v032 merge, 92.5/100 quality
    │
2025-Q4: v2.3 (MCP Integration)
    │      └─ Agent framework, IDE connectivity
    │
2025-Q4/Q1: v3.3 (DMAIC V3 Engine)
           └─ 12-Cluster Orchestrator, full engine
```

## 9.2 Version Directory Mapping

| Version | Directory | Key Content |
|---------|-----------|-------------|
| v2.1 | Root-level `ABACUS_V21_*` files | Deployment, migration, architecture |
| v0.31 | `ABACUS-v031/` | Canonical indexes, DOW config |
| v0.32 | `ABACUS-v032/` | Full pipeline, Docker deployment |
| UNIFIED | `ABACUS-UNIFIED/` | Merged knowledge, agent registry |
| v2.3 | `local_mcp/` | Agent orchestrator, knowledge integration |
| v3.3 | `DMAIC_V3/` | V3 engine, 12-cluster, all phases |

## 9.3 Migration Paths

### v2.1 → v0.31
- **What:** Establish canonical foundation
- **Key Change:** `canonical.index.json` becomes SSOT
- **Risk:** Low (additive)
- **Guide:** `docs_versioned/v2.1/migration/to_v031.md`

### v0.31 → v0.32
- **What:** Extend to 10-phase pipeline
- **Key Change:** Phases 6-9 added, Docker support
- **Risk:** Low (extension)
- **Guide:** `docs_versioned/v0.31/migration/to_v032.md`

### v0.32 → v2.3
- **What:** Add MCP integration layer
- **Key Change:** Agent orchestrator, IDE connectivity
- **Risk:** Medium (new dependency: MCP protocol)
- **Guide:** `docs_versioned/v0.32/migration/to_v23.md`

### v2.3 → v3.3
- **What:** DMAIC V3 engine with 12-cluster architecture
- **Key Change:** Complete engine rewrite, parallel execution
- **Risk:** Medium (structural changes)
- **Guide:** `docs_versioned/v2.3/migration/to_v33.md`

## 9.4 ⚠️ Critical: All Versions Are Active
No version should be archived or deleted. Each contains unique, irreplaceable content:
- v2.1: Deployment procedures and session analysis
- v0.31: Canonical indexes (live dependency)
- v0.32: Docker deployment and CI/CD
- v2.3: MCP integration layer
- v3.3: Current engine implementation

## 9.5 Git Heritage
- **Total Commits:** 558
- **Key Branches:** main, deep-analysis-phase2-deliverables
- **Parallel Development Streams:** 8+ identified
