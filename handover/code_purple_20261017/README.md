# CODE PURPLE · Lossless operational session kit (17 October 2026)

**Read first:** [HANDOVER.md](HANDOVER.md) → [STATE.json](STATE.json)
→ [DROPIN.md](DROPIN.md) → [MONIKERS.json](MONIKERS.json).

This kit follows the existing `LOSSLESS_HANDOVER_V2` process
(`tools/handover_v2/process_spec.json`). It is a **dated operational
handover**, not full transcript export, new SSOT, authenticated Crew receipt,
security waiver, or P0 merge admission.

## Choose the existing moniker

| Desired instruction | Use | What it actually counts |
| --- | --- | --- |
| Burn down source-owned issues/roots | **CBD!** / Char_BD | Verified causal repairs and dispositions |
| Deliver three disjoint tranches | **3W** or **G3W** | Engineering waves attempted/delivered |
| Perform three measure/control loops | **3MP** | Three recorded pulses (not necessarily advances) |
| Govern N to N+3 checkpoints | **G3A** | Three accepted A1/A2/A3 advances, only if proven |
| Inventory exact GitHub populations | **CENSUS** | Explicit issue/PR/run/job denominator |
| Resume context on a new chat | **LOSSLESS_HANDOVER_V2** | Source-bound operational continuity |
| Request a typed evidence return | **RECEIPT / REX** | Actual returned execution proof, not a promise |

For atomic CODEX actions use documented `CLOSE, RED, RUNTIME, SEM,
SSOT, RECEIPT, ENABLE, HARDEN, CLEAN, MAINT, READ, EXP, WATCH`.
Use `MONIKERS.json` as this kit's *navigation copy only*, not a
replacement for CODEX `GLOBAL_GLOSSARY_v1.yaml`.

## Build and verify ZIP from a checked-out PR

Python 3.9+ standard library; no build credentials needed.

```bash
git clone https://github.com/GBOGEB/ABACUS.git
cd ABACUS
git checkout docs/code-purple-lossless-handover-20261017
python handover/code_purple_20261017/cli.py status
python handover/code_purple_20261017/cli.py build --out dist/cp_handover
python handover/code_purple_20261017/cli.py verify --out dist/cp_handover
python handover/code_purple_20261017/cli.py serve --out dist/cp_handover --port 8765
```

Open `http://127.0.0.1:8765/taxonomy.html`.
The deterministic ZIP appears alongside `dist/cp_handover/`.
`manifest.json` records SHA-256 for every included file and is not
self-hashed; `QA_RECEIPT.json` labels unexecuted visual/native checks
DEFER, never PASS.

To print the text for a new ChatGPT chat:

```bash
python handover/code_purple_20261017/cli.py dropin
```

To ask GitHub for *live* rather than snapshotted statuses:

```bash
gh auth status
python handover/code_purple_20261017/cli.py gh-status
gh pr view 2159 -R GBOGEB/ABACUS \
  --json state,mergedAt,mergeCommit,headRefOid,reviewDecision
gh run list -R GBOGEB/ABACUS --limit 30
gh issue list -R GBOGEB/ABACUS --state open --limit 200
gh api repos/GBOGEB/pipeline-automation-hub/branches/master \
  --jq .commit.sha
```

PowerShell wrapper for Windows (define in your profile or paste):

```powershell
$CP = "handover/code_purple_20261017/cli.py"
function cpStatus { python $CP status }
function cpBuild  { python $CP build --out dist/cp_handover }
function cpCheck  { python $CP verify --out dist/cp_handover }
function cpOpen   { python $CP serve --out dist/cp_handover --port 8765 }
function cpDropin { python $CP dropin }
function cpLive   { python $CP gh-status }
```

## Updating the HTML taxonomy safely

The **editable source** is `MONIKERS.json`. Use the HTML's search and
category filter to inspect monikers, tick *Edit local display labels* to
propose friendlier labels, then *Export edited JSON*. Replace or reconcile
the local JSON with that proposal, run `cli.py build` and `verify`, inspect
the local HTML, and submit a reviewed PR. An imported proposal does **not**
alter CODEX global terms or create federation authority.

The template `viewer_template.html` and CLI render **offline**
`taxonomy.html` with embedded data: no CDN, credentials, live remote
actions or GitHub writes. Source paths and official CODEX glossary
remain explicit. If Pages is published later, its deploy URL must be
verified via a native Pages receipt; none is claimed by this kit.

## Native audit commands and red/unknown policy

Use actual GitHub PR base and SHA, not branch names or historical green
CI alone. Bind run attempt, job/step, artifact hash, module source SHA,
line/branch/diff numerator and denominator. GitHub issue `closed`,
PR `merged`, a green B0, and P0 admission are **different states**.
Do not infer Crew/REX dispatch, reviewer approval, root closure or waiver.

Review template source: `tools/handover_v2/process_spec.json`.
For a **fully V2-schema-admitted** evidence capsule, use the existing
`tools/handover_v2/build_handover.py` with a separately governed
`handover_input.schema.json` input and raw native evidence archive;
this lightweight kit makes no V2-schema or full-transcript claim.

## Artifact references

- [GitHub #1860 P0 admission](https://github.com/GBOGEB/ABACUS/issues/1860)
- [GitHub #1929 BD roots](https://github.com/GBOGEB/ABACUS/issues/1929)
- [GitHub #1885 dashboard](https://github.com/GBOGEB/ABACUS/issues/1885)
- [PR #2135 merged B-series](https://github.com/GBOGEB/ABACUS/pull/2135)
- [PR #2159 merged issue/BD census](https://github.com/GBOGEB/ABACUS/pull/2159)
- [CODEX #977 remote dispatch](https://github.com/GBOGEB/CODEX/issues/977)

**Current admission disposition in this dated snapshot: HOLD.**
