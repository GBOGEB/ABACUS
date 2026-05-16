# ABACUS v0.31 — Canonical Foundation
> *Reconstructed from code — 2026-05-16 22:34*

## ⚠️ IMPORTANT: v0.31 is ACTIVE, not archived
v0.31 is the foundational layer for ALL subsequent versions. Its canonical indexes and DOW 
configuration are CRITICAL dependencies.

## Key Artifacts  
| File | Purpose | Size |
|------|---------|------|
| `canonical.index.json` | Machine-readable artifact registry | 111KB |
| `dow_engine_config.yaml` | DOW Engine pipeline configuration | 1.3KB |
| `artifact_rankings.json` | Quality scoring system | — |
| `run_direct_improvements.py` | Direct improvement execution | — |

## Role in Architecture
- Provides the **Single Source of Truth** for artifact locations
- Defines the DOW governance pipeline configuration
- Establishes quality ranking baselines
- Referenced by v0.32, UNIFIED, v2.3, and v3.3

## Dependencies
- All later versions import canonical patterns from v0.31
- DOW engine config is the authoritative pipeline definition
