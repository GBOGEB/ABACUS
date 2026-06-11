# ABACUS-v031 — Canonical Foundation

**Status:** ACTIVE (NOT archived) | **Role:** Foundation layer for ALL subsequent versions

## Purpose
Contains the canonical indexes, DOW engine configuration, and core DMAIC infrastructure (phases 0-5) that serve as the foundation for the entire ABACUS system.

## Key Files
| File | Purpose |
|------|---------|
| `canonical.index.json` | Machine-readable artifact registry with checksums |
| `canonical.index.yaml` | Human-readable artifact index |
| `canonical.index.run1.json` | Iteration 1 canonical snapshot |
| `canonical.index.run2.json` | Iteration 2 canonical snapshot |
| `dow_engine_config.yaml` | DOW Engine pipeline configuration |
| `artifact_rankings.json` | Quality scoring system |
| `.pre-commit-config.yaml` | Quality gate hooks |
| `run_direct_improvements.py` | DMAICEngine (phases 0-5) |
| `requirements.txt` | ⚠️ Empty — needs population |

## Lineage
- **Feeds into:** v0.32 (extends phases 0-5 to 0-9), UNIFIED (merged), DMAIC_V3 (references config)
- **Canonical indexes** are the single source of truth for artifact tracking
- **DOW engine config** defines the governance pipeline used by all versions

## CRITICAL: Do NOT treat as archived
This directory's canonical indexes and DOW configuration are foundational. All later versions depend on patterns established here.
