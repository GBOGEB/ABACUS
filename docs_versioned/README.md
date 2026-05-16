# ABACUS Versioned Documentation

> **Generated:** 2026-05-16 22:34 | **Status:** Reconstructed from code analysis

## Version Directory

| Version | Status | Role | Directory |
|---------|--------|------|-----------|
| v2.1 | Production Baseline | Original deployment target | [v2.1/](v2.1/) |
| v0.31 | Active Foundation | Canonical indexes, DOW config | [v0.31/](v0.31/) |
| v0.32 | Active Pipeline | Extended 10-phase DMAIC | [v0.32/](v0.32/) |
| v2.3 | Active Development | MCP integration, agent framework | [v2.3/](v2.3/) |
| v3.3 | Current Engine | DMAIC V3 engine, 12-cluster orchestrator | [v3.3/](v3.3/) |

## Version Lineage

```
v2.1 (Production Baseline)
 └─→ v0.31 (Canonical Foundation) 
      └─→ v0.32 (Production Pipeline, extends phases 0-5 → 0-9)
           └─→ ABACUS-UNIFIED (Merged Knowledge, 92.5/100 quality)
                └─→ v2.3 (MCP Integration, Agent Framework)
                     └─→ v3.3 (DMAIC V3 Engine, 12-Cluster Orchestrator)
```

## Cross-Cutting Documentation
- [Handover Book](handover_book/) — 12-Chapter comprehensive handover
- [Migration Guides](#migration-paths) — Version-to-version migration paths
- [Deprecation Notices](#deprecations) — What changed between versions

## Migration Paths
- [v2.1 → v0.31](v2.1/migration/to_v031.md)
- [v0.31 → v0.32](v0.31/migration/to_v032.md)
- [v0.32 → v2.3](v0.32/migration/to_v23.md)
- [v2.3 → v3.3](v2.3/migration/to_v33.md)

> ℹ️ This documentation was **reconstructed from code analysis** of the ABACUS repository.
> Content was inferred from README references, code comments, docstrings, and SSOT artifacts.
