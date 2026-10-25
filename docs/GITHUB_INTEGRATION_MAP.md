# GitHub Integration / Merge / Prune Map

**Owner:** `GBOGEB` (user `gbogeb`) · **Generated:** integration pass, W008 sequence
**Scope:** `GBOGEB/ABACUS`, `GBOGEB/CODES`, `GBOGEB/cryoplant-project`
**Source of record for this project:** `/home/ubuntu/pid_project` (branch `pr1-w001-w005`,
base commit `d418160` + the W008 viewer and AD_01 aux-building assimilation added in this pass).

> **Status honesty.** Every status below was read from the GitHub API during this pass,
> not assumed. Where the prior task context disagreed with the live API, the API wins and
> the discrepancy is called out explicitly.

---

## 1. Repository access results

| Repo | Access | Visibility | Default | Size | Languages | Role |
|---|---|---|---|---|---|---|
| `GBOGEB/ABACUS` | ✅ 200 OK | public | `main` | ~21.7 MB | Python | Mono-repo of record; `MINERVA_PID/` merged into `main` through W007 |
| `GBOGEB/cryoplant-project` | ✅ 200 OK | **private** (folder access granted) | `main` | ~35.9 MB | HTML / Python (1480 py, 435 html) | **Domain data home** (see §4) |
| `GBOGEB/CODES` | ❌ **404 BLOCKED** | — | — | — | — | Does not exist under this name |

**`CODES` is a 404.** The authenticated account owns 93 repos; none is named `CODES`. The
closest names are `CODEX`, `codespaces-jupyter`, `CODESPACES_jyperter`. Recorded as **BLOCKED
(HTTP 404)**; no work was attempted against it. If the intended repo is one of those three,
re-point this map to the correct name.

> The user's `c:/repos` and `c:/DEV` trees live on their local PC and are unreachable from the
> VM — out of scope for this pass.

---

## 2. What belongs in which repo

| Concern | Belongs in | Rationale |
|---|---|---|
| QCELL/RFCELL **domain source** (SVGs, PID nomenclature xlsx, PPTX masters, QSYS slides) | `cryoplant-project` | These exact inputs are already audited there under `triage/w367/.../PID_PROCESS_LOGIC_EXTRACT/` with a 97-row nomenclature register that is 1:1 with MINERVA's design register (§4). |
| **MINERVA_PID pipeline** (`src/abacus_svg_pid/`, `make.sh`, waves W001–W008, cross-map, interactive viewer) | `ABACUS/MINERVA_PID/` **today**, trending → a private home | The advanced re-implementation. But the org is *already* moving it out of the public mono-repo — see **PR#2434** in §3. |
| **AD_01 auxiliary-building** drawings (PCW, Instrument Air, legend, layouts) | `MINERVA_PID/data/aux_building/` (inputs git-ignored) + generated `reports/aux_building_inventory.*` | Support-systems scope adjacent to MINERVA; a different tag namespace (§5) so it is additive, not a merge into the cryo register. |
| CI / governance gates | `ABACUS` (mono-repo governance already lives here) | Note: the GitHub App cannot push `.github/workflows/`; MINERVA CI ships as `ci/minerva-pid-test.yml`. |

### Alternative / new integration point (the headline recommendation)

**`cryoplant-project` is the natural domain home for the MINERVA P&ID work, and the
organisation is already moving in exactly that direction.** Two independent signals:

1. **Duplicate audit of identical inputs** (evidence in §4): `cryoplant-project` already
   contains the same QCELL/RFCELL source files and a nomenclature register that matches
   MINERVA's 97 design tags one-for-one.
2. **Live org intent — PR#2434** (`chore/move-minerva-pid-private-20261025`, opened
   2026‑10‑25, 247 files, open/unmerged): *"move MINERVA_PID subproject to a private repo."*
   The org has concluded the public mono-repo is the wrong long-term home.

**Recommended target state:** MINERVA_PID becomes a standalone **private** project (either
inside `cryoplant-project` as a submodule/subtree, or as a dedicated private repo), with
`cryoplant-project` owning the domain source of truth and MINERVA consuming it. Until that
move lands, `ABACUS/MINERVA_PID/` remains the integration point and this W008 PR targets it
(see §6).

---

## 3. ABACUS PR merge order — **actual live status**

> **Context correction.** The task context listed #547 as "uncertain" and #556 / #560 as
> "open". The live API shows **all four MINERVA PRs are already closed-and-merged into
> `main`.** There is therefore no pending MINERVA merge-order to sequence for #546–#560; the
> only remaining MINERVA merge is the **new W008 PR** opened in this pass.

| PR | Branch → base | Live status | Notes |
|---|---|---|---|
| #546 | `minerva-pid-w001-w005` → `main` | **closed, merged ✅** | W001–W005 |
| #547 | `minerva-pid-improvements` → `main` | **closed, merged ✅** | deps / Dependabot manifests |
| #556 | `minerva-pid-w006` → `main` | **closed, merged ✅** | W006 cross-map |
| #560 | `minerva-pid-w007` → `main` | **closed, merged ✅** | W007 CI/CD |
| **NEW (this pass)** | `minerva-pid-w008` → `main` | **open (do not merge)** | W008 viewer + AD_01 aux assimilation |

**Effective merge order going forward:** `#546 → #547 → #556 → #560` are **done**; the new
**`minerva-pid-w008`** PR is next and stacks on `main` (its predecessor branch
`minerva-pid-w007` was auto-deleted after #560 merged, so `main` is the only clean base).

**Other open ABACUS PRs touching MINERVA** (not part of this pass, flagged for the owner):
- **#2434** — move MINERVA_PID to a private repo (247 files, open). Decides the long-term home.
- **#2435** — `docs(qps_line_s)` RTM-292 binding (9 files, open). Governance/docs, adjacent.
- #2368 / #2360 — W50/W51 CBD cohort work, unrelated to MINERVA.

---

## 4. Duplicated code / data to consolidate

**Primary duplication — MINERVA_PID ⟷ cryoplant-project.**
`cryoplant-project/triage/w367/archive_incubator/PID_PROCESS_LOGIC_EXTRACT/PID_PROCESS_LOGIC_EXTRACT/`
audits the **same inputs** MINERVA ingests (`QCELL-LB.svg`, `RFCELL.svg`,
`PID Nomenclature MINERVA CryoCell (QCELL-LB).xlsx`, `RFCELL MASTER.pptx`, QSYS slides).

Measured evidence (`summary.json` + `02_REGISTERS/nomenclature_register_QCELL.csv`):

| Metric (cryoplant w367 extract) | Value | MINERVA equivalent |
|---|---|---|
| `nomenclature_rows` | **97** | **97 design tags** (1:1 — V001, CV001, FV001, PT001…) |
| `process_segments` | 97 | matches design cardinality |
| `instrumentation_occurrences` | 549 | — |
| `unique_tags` | 264 | — |
| `line_candidates` | 858 | line extraction |
| `color_bins` | 37 | colour-band pass |

**Consolidation recommendation:** treat `cryoplant-project`'s w367 extract as the **upstream
nomenclature source**; have MINERVA's W005 ingest consume that register instead of
re-deriving it, eliminating the parallel 97-row register. Keep MINERVA's *downstream*
advances (cross-map, colour bands, interactive viewer) — they are not duplicated upstream.

Secondary (within ABACUS): hundreds of loose top-level `.md` files and multiple overlapping
subprojects (`ABACUS-UNIFIED`, `ABACUS-v031`, `ABACUS-v032`, `DMAIC_V3`, `qplant`, `MIP`) —
broad consolidation surface, out of scope for this pass, noted for the owner.

---

## 5. AD_01 auxiliary-building assimilation — honest cross-check

19 PDFs, 43 pages, 46.7 MB. **111 unique instrument-style tags, 44 pipe-line numbers.**

- Overlap with MINERVA **design register (97)**: **0**
- Overlap with **as-drawn real set (141)**: **0**

**This zero is the truthful, expected result — not a failure.** AD_01 covers PCW
(Process Cooling Water / adiabatic cooling, `AD_01.10` = `PS01.PAB12`), Instrument Air
(`AD_01.11` = `PS01.QFB10`), legend, floor loads, fire escapes and layouts. These use their
own namespace — air-actuated valves `AA####`, pipe-lines `BR####-size-class`, system codes
`=NA.PSxx` — which is **disjoint from the QCELL cryogenic register** (`CV001`, `TT514`…). No
matches were fabricated to force an overlap. Full inventory: `reports/aux_building_inventory.{json,md}`.

---

## 6. W008 propagation decision

- **Branch:** `minerva-pid-w008`, created from **`main`** (not stacked on
  `minerva-pid-w007`, which was auto-deleted after #560 merged — `main` already contains all
  of W001–W007, so it is the only clean base).
- **PR target:** `main`. Leave **open; do not merge.**
- **Excluded from the push:** `*_preview/` dirs (base64 trips secret scanning), anything
  regenerable by `make.sh` (`publish/`, `output_v6/`, `data/model|pemo|excel/`,
  `reports/*.xlsx`), raw `data/aux_building/pdfs/` inputs, `__pycache__`. `.github/workflows/`
  is **not** pushed (App lacks the `workflows` permission); MINERVA CI stays as
  `ci/minerva-pid-test.yml`.
- **Forced-add:** the mono-repo `.gitignore` globally ignores `*.json`/`*.pdf`, so intended
  reports/configs are added with `git add -f` (deliberate reports and golden files only).

---

## 7. Prune candidates — **RECOMMEND ONLY (nothing was deleted)**

| Candidate | Where | Why | Action |
|---|---|---|---|
| `pr1-w001-w005` | `ABACUS` origin | W001–W005 already merged via #546; stale duplicate of merged work | **Recommend delete** after W008 PR is cut from `main` |
| `minerva-pid-w001-w005`, `minerva-pid-w006`, `minerva-pid-w007`, `minerva-pid-improvements` | `ABACUS` origin | already **auto-deleted** post-merge | none — already pruned (confirm) |
| ~457 branches total on ABACUS (e.g. 100+ `auto/update-docs-*`) | `ABACUS` origin | huge stale automation surface | **Recommend bulk prune** of merged `auto/*` / `update-docs-*` branches (owner review) |

> Pruning is a **recommendation only**. No branch was deleted in this pass, per the
> never-destroy constraint.

---

## 8. Summary of actions taken this pass

- ✅ Cloned/fetched `ABACUS` and `cryoplant-project`; recorded `CODES` as 404 BLOCKED.
- ✅ Assimilated AD_01 (19 PDFs) → `build_aux_inventory.py` + `reports/aux_building_inventory.{json,md}` + `tests/test_aux_inventory.py`.
- ✅ Honest tag cross-check (0 overlap, documented why).
- ✅ This map written.
- ⏭ Open `minerva-pid-w008` PR → `main` (open, unmerged); commit the same in `pid_project`.
- ⏭ Update `docs/CAPABILITY_MATRIX.md` + `reports/wave_status.json`.
- ❎ No `CODES` PR possible (404). `cryoplant-project` PR evaluated in the final report.
