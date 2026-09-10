# MIP Rollout — codespace_jyperter

`integration/codespace_jyperter` is tracked as an ABACUS sub-surface, not as a standalone Git repository.

MIP scope for this surface:

| Lane | Local meaning | Evidence |
| --- | --- | --- |
| `repo_self_index` | Census this integration surface and expose exact denominators. | `MIP/receipts/surface_self_index.json` |
| `repo_self_assess_debug_ldab` | Check whether notebook parsing and federation errors have useful diagnostics. | Receipt assessment |
| `repo_self_assess_runners_mcp` | Classify tests, federation manifest, contract, and runnable entrypoints. | Receipt assessment |
| `repo_self_assess_codz_health_selfheal` | Find stale/TODO/repair candidates in the integration code. | Receipt assessment |
| `repo_self_produce` | Identify whether this can produce a reusable CODESPACE/Jupyter federation skill or agent. | Receipt assessment |

## DoD

1. Surface self-index runs with only Python stdlib.
2. Receipt records parent repo SHA plus local file census.
3. First red/amber lane becomes the next repair target.

## DoV

Withheld until the smoke test and self-index are both bound to the same parent commit SHA, and one reusable CODESPACE/Jupyter candidate is packaged or rejected with evidence.

