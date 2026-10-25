# delta1_bridge

Minimal, additive, standard-library-only bridge/adapter for the **DELTA_1
federation** (GBOGEB/CODEX · GBOGEB/ABACUS · GBOGEB/cryoplant-project).

It gives the three repos one shared implementation for three concerns that are
currently handled three different ways:

| Concern | Module | Replaces / unifies |
|---|---|---|
| Shared DMAIC metrics schema | `schema.py` | per-repo (or missing) validation of `docs/api/*metrics.json` |
| Uniform federation status / `assimilate()` | `adapter.py` | `cryoplant/src/federation.py`, `CODEX/src/bridge_adapter.py`, ABACUS stub |
| Bradley-Terry pairwise ranking | `ranking.py` | canonical `CODEX/pca_engine` delegation + pure-Python fallback |

## Install / use

No install needed — it is stdlib-only. Put the `delta1_bridge/` folder on the
import path (it is vendored at each repo root).

```bash
# Uniform status for the current repo
python -m delta1_bridge status --repo-root . --json

# Validate a metrics feed against the shared schema
python -m delta1_bridge validate-metrics docs/api/metrics.json

# Bradley-Terry ranking demo (uses canonical pca_engine if importable)
python -m delta1_bridge rank-demo
```

```python
from delta1_bridge import federation_status, validate_metrics, fit_bradley_terry

status = federation_status(".")            # {repo, plane, status, metrics, ...}
issues = validate_metrics(payload)         # [] == valid
result = fit_bradley_terry(ids, comps)     # {strengths, ranking, engine, ...}
```

## Design rules
- **Additive**: never deletes or restructures existing repo code.
- **Read-only**: no network, no writes to governed SSOT.
- **No hard deps**: NumPy is optional (only used by the canonical BT engine).

## Tests
```bash
python -m pytest delta1_bridge/tests -q    # 14 tests
```

See the repo-root `BRIDGE_REPORT.md` (in the bridge working set) for the full
cross-repo overlap analysis and the Greek-letter managed trace.
