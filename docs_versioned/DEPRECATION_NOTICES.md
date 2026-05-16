# ABACUS Deprecation Notices
> *Reconstructed from code — 2026-05-16 22:34*

## ⚠️ Critical: No Versions Are Deprecated
All versions (v2.1, v0.31, v0.32, v2.3, v3.3) are **ACTIVE** and contain unique content.

## Version-Specific Notes

### v2.1
- Deployment scripts remain functional but superseded by v0.32 Docker deployment
- Session analyzer still referenced by UNIFIED knowledge base

### v0.31
- **DO NOT ARCHIVE** — canonical indexes are live dependencies
- `requirements.txt` is empty placeholder (needs population)

### v0.32
- Legacy `_LEGACY_phase0_setup.py` exists but superseded by `phase0_init.py`
- v033 naming in filenames reflects incremental versioning within v0.32

### v2.3
- `local_mcp/` missing `__init__.py` — known issue, not deprecated
- Agents coexist with V3 agents

### v3.3
- `change_detector.py` syntax error FIXED in this analysis
- 4 pipeline orchestrator variants exist — consolidation recommended
- `full_pipeline_orchestrator_corrupted.py` — merge conflict artifact, use `_fixed.py`

## Files Marked for Attention
| File | Issue | Status |
|------|-------|--------|
| `DMAIC_V3_CANONICAL_HANDOVER_BOOK.md` | Zero-byte | Placeholder, needs content |
| `handover_with_code_asMardown.md` | Zero-byte | Placeholder |
| `DMAIC Implementation Manifest.md` | Zero-byte | Placeholder |
| 12 scripts in `scripts/` | Zero-byte | Placeholders for future implementation |
