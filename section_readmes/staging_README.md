# staging/ — Integration Bridges & Pre-Production

**Status:** ACTIVE | **Role:** Integration bridges between GBOGEB, ABACUS, and DOW

## Key Files
| File | Purpose |
|------|---------|
| `GBOGEB_ABACUS_DOW_INTEGRATION_BRIDGE.py` | Full DOW↔ABACUS integration bridge |
| `test_integration_bridge.py` | Integration bridge tests |

## Integration Modes
The bridge supports 5 integration modes:
1. `DOW_ONLY` — DOW pipeline execution only
2. `DMAIC_ONLY` — DMAIC methodology only
3. `UNIFIED` — Combined DOW+DMAIC
4. `PARALLEL` — Parallel execution
5. `SEQUENTIAL` — Sequential execution
