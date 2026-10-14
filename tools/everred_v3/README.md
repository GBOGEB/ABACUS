# ABACUS · EVERRED 3.0

**Delivery:** executable local implementation scaffold + dashboard + vector architecture exports.
**Baseline:** recorded PR #1914 evidence as of 2026-10-14. **Not live**.
**Authority:** external repository controls. This package does not authorize merges or accept its own security reviews.

## Start

Open `dashboard/index.html` in a normal desktop browser. This is a self-contained document: inline SVGs, data, styles and controls, with no CDN requests. Select diagram tabs, search root candidates, export JSON or import an updated snapshot. Browser-imported data is labeled untrusted; its status does not establish a trusted native receipt.

Run from project root (Python 3.10+; local POSIX path leases):

```bash
python src/everred.py verify
python src/everred.py snapshot
python scripts/build_dashboard.py
python -m unittest discover -s tests
```

To append a *new event* without overwriting history:

```bash
cp samples/new_event.json /tmp/everred-event.json
# Edit /tmp/everred-event.json: unique id, real evidence, correct exact SHA.
python src/everred.py append --event /tmp/everred-event.json
python src/everred.py verify
python src/everred.py snapshot
python scripts/build_dashboard.py
```

## Structure

- `src/everred.py` — strict event validation, SHA binding, append-only hash-chain ledger, local POSIX path-lease serialization, guarded admission, projection.
- `src/metrics.py` — source-comparable fingerprint and coverage deltas; root recurrence, replay and queue KPIs with explicit denominators.
- `data/ledger.jsonl` — 14 historical source-reported events seeded from #1914 (two root **candidates**, not confirmed causes).
- `data/snapshot.json` — deterministic projection of the event set (generated_at is the export time).
- `dashboard/template.html` — responsive dashboard source; `dashboard/index.html` — compiled standalone HTML.
- `diagrams/*.mmd` — editable Mermaid semantics; `diagrams/*.dot` — publication-layout source; `diagrams/*.svg` — vector exports (parallel semantic render).
- `tests/*.py` — unit contract/negative tests plus optional browser QA harness.
- `docs/IMPLEMENTATION_PLAN.md` — admission/rollout roadmap.

## Provenance constraints

Coverage must be reported as `covered / eligible`, with SHA, scope, unit, configuration and producer identity. The historical data include statement-only 49/61 focused, 3/3 changed-lines and 12,731/29,093 broad. The reported *combined* figures 82.80% (focused) and 42.63% (broad) are separate values, not ratios of the statement-only counts.

Bandit full 6,363 and separately configured 3 are incomparable totals. Safety exit 64 remains an independent red. `UNKNOWN` is never inferred as PASS or zero. Browser-imported snapshots are unverified manual views. `ADMIT` is disabled in the local event engine; a hardened external admission integration shall validate server-side protection/reviews/native terminal checks.

## How to build diagrams

```bash
for f in diagrams/*.dot; do dot -Tsvg "$f" -o "${f%.dot}.svg"; done
python scripts/build_dashboard.py
```

Graphviz is needed only when re-rendering the SVG sources; prebuilt SVG/HTML run without Graphviz. Mermaid `.mmd` sources retain the logical workflow for GitHub/Markdown rendering.

## Exact-head reference and status

- ABACUS PR #1914 head: `e9f34b22967064c779891a4d2ac40541f370e812`
- Historical main: `02cca5020d59cc339cea486ed38857f53eea3e88`
- Bandit census PASS: https://github.com/GBOGEB/ABACUS/actions/runs/38532010232
- Workflow governance PASS: https://github.com/GBOGEB/ABACUS/actions/runs/38532010504
- MIP B0 PASS: https://github.com/GBOGEB/ABACUS/actions/runs/38532010296
- Broad CI still blocked in supplied evidence: https://github.com/GBOGEB/ABACUS/actions/runs/38532010346
- Server-side default-branch enforcement reported ineffective: https://github.com/GBOGEB/ABACUS/settings/rules/24494381

This package has been unit-tested locally; a managed Chromium URL policy blocked interactive browser QA in the authoring environment, so publication-grade cross-browser visual certification is **not** claimed. Use the optional browser QA harness on an unrestricted local runner before production deployment.

## ABACUS-native BD / LDAB bridge

Current ABACUS main already contains `scripts/bd_ldab_join_census.py` (schema `bd.ldab.joined.census.v1`) and a separate `BD_LDAB_JOIN_CONTRACT_20261014.md`. V3 **consumes** its operator-provided output instead of cloning/replacing that producer:

```bash
python scripts/ingest_bd_ldab_join.py --input path/to/abacus_join_output.json
python src/everred.py verify
python src/everred.py snapshot
python scripts/build_dashboard.py
```

The bridge checks schema, source SHA, run/job provenance fields and immutable HOLD/no-authority flags. It imports aggregated observation counts as an unverified `note`, never as confirmed causal root IDs or new security credit. A real joined artifact still has to be provided to populate the dashboard. It uses the current ABACUS published producer contract as a read-only consumer.
