# ABACUS root refactor plan

<!-- markdownlint-disable MD013 -->

**JADE task:** J14, the first ABACUS slice of J10 ("root candidate disposition and nonbreaking alias tests")
in `pipeline-automation-hub/mission-control/jade_temple/data/BD_QUEUE.csv`.
**Observed commit:** `1dff4c361f17abc44dfa65cccba2ee052ee01a2a` (inventory); W1 and W2 applied on top of `8d27bca8`.
**Status:** W0 (discover and classify), W1 (generated run reports) and W2 (handover and session notes) are in the first PR (ABACUS#2438): 61 files moved, root 390 → 329. W3a (40 unversioned status reports) is stacked on it: root 329 → 289. W3b to W5 are planned only.
**Find anything:** the [repository map](index.html) (search every former root file, open it on GitHub or in your local checkout).

How to open the map:

- **GitHub Pages** (after merge): <https://gbogeb.github.io/ABACUS/repo-structure/>
- **GitHub source:** <https://github.com/GBOGEB/ABACUS/tree/main/docs/repo-structure>
- **Local checkout (Windows):** from the repository folder run `explorer.exe docs\repo-structure`
  and open `index.html`, or `start docs\repo-structure\index.html` in PowerShell. Enter your
  checkout folder once on the page to get File Explorer links for every file.

The repository root holds 390 loose files next to 95 folders. A person landing on the
repository sees hundreds of reports, handovers and scripts before the README.
This plan moves them, one family per wave, into the folders where the same kind of
file already lives. Nothing is deleted, and every move is recorded.

## Rules

These come from the JADE root contract
(`jade_temple/04_REPO_ROOT_SPINE_CONTRACT.md`): discover, classify, consumer census,
owner review, migrate one slice, recheck. No bulk shuffle, no automatic deletion,
no rename without a grep, import, Pages and CI consumer check.

1. **The root keeps only the front door and the manifests.** That is the README,
   licence, security policy, changelog, build and test configuration, and dotfiles (19 files).
2. **Same kind, same folder.** Each family has one destination. File names do not change,
   so `git log --follow` and old search habits still work.
3. **Reuse folders that already exist or are already promised.** For example, the README
   has described `docs_versioned/handover/` since v2.3, but nothing was ever moved there.
4. **Living docs go in `docs/` (published on Pages); frozen history goes in `docs_versioned/`.**
5. **Every move is a row in [`ROOT_RELOCATION_MAP.csv`](../../docs_versioned/ROOT_RELOCATION_MAP.csv)**
   (old path, new path, family, wave, JADE disposition). To find a file that used to be at the root, search that file.
6. **One family per wave, one PR per wave.** The next wave starts only after the previous PR is merged with CI green.
7. **Pruning (deleting empty files or byte-identical copies) needs an explicit owner yes per file.**
   The inventory lists candidates; the waves only move files.

## Families

[`ROOT_INVENTORY.csv`](ROOT_INVENTORY.csv) has one row per root file, with its family, wave,
inbound references and prune flag. Regenerate it with `python tools/root_refactor/inventory.py --write`.
"Hard-ref files" counts files whose references come from CI, build files, code or tests,
and those are the ones a move could break.

| ID | Family | Files | Hard-ref files | Prune candidates | Destination | JADE disposition | Wave |
| --- | --- | ---: | ---: | ---: | --- | --- | --- |
| KEEP | Front door and manifests | 19 | 12 | 0 | root | CANONICAL_ROOT | — |
| F1 | Generated run reports (timestamped or "Generated:" outputs) | 20 | 0 | 1 | `docs_versioned/generated_reports/` | ARCHIVE_PRESERVE_LINKS | **W1** |
| F2 | Handover and session notes | 42 | 2 | 4 | `docs_versioned/handover/`; the three `V2.2_*` notes to `docs_versioned/v2.2_archived/` as the README layout declares | ARCHIVE_PRESERVE_LINKS (2 MOVE_WITH_CONSUMER_REPLAY) | **W2** |
| F3 | Status, completion and result reports | 118 | 22 | 7 | version folders in `docs_versioned/` when the name carries a version, else `docs_versioned/status_reports/` | ARCHIVE_PRESERVE_LINKS | W3a–W3d (4 slices of up to 40) |
| F4 | Plans, guides, architecture and reference | 126 | 26 | 7 | still-used guides go to `docs/guides/`; superseded ones to `docs_versioned/plans/` or a version folder | LINK_ALIAS_FIRST / ARCHIVE_PRESERVE_LINKS | W4 (at least 3 slices) |
| F5 | Code, automation and the data files they read or write | 65 | 47 | 0 | `scripts/<purpose>/` (deploy, ci, github, dow, …); `abacus_v21_*` next to `ABACUS_V21_DEPLOYMENT_PACKAGE/` | MOVE_WITH_CONSUMER_REPLAY | W5 (slices by consumer) |

**Why this order:** each wave is larger or riskier than the one before.
F1 is the smallest family and nothing executable points at it. F5 goes last:
47 of its 65 files are referenced by workflows, the Makefile, tests or other code, and
coverage measures `source = ["."]`, so moving a `.py` file changes coverage paths.
The three root JSON files that code reads or writes (`bottleneck_report.json`,
`maturity_assessment.json`, `PERFORMANCE_BENCHMARK_REPORT.json`) are classified F5, not F1.

## Wireframes

### Current (`1dff4c36`)

```text
ABACUS/
├── 95 folders  (DMAIC_V3/, docs/, docs_versioned/, scripts/, tests/, tools/, …)
├── 19 KEEP     README.md  LICENSE  SECURITY.md  CHANGELOG.md  pyproject.toml  pytest.ini
│               requirements*.txt  Makefile  Dockerfile  docker-compose.yml  + 7 dotfiles
├── 306 loose *.md
│   ├── F1  20  Report_20251110_*.md  MARKDOWN_FIX_REPORT_*.md  iteration_*_report_*.md  …
│   ├── F2  42  *HANDOVER*  *SESSION*  NEW_SESSION_START.md  …
│   ├── F3 118  *SUMMARY*  *COMPLETE*  *STATUS*  *REPORT*  …
│   └── F4 126  *PLAN*  *GUIDE*  *ARCHITECTURE*  *QUICK_REFERENCE*  …
└── 65 loose code and data   44 *.py  5 *.ps1  3 *.sh  1 *.ipynb  5 *.json  5 *.yaml  2 *.txt   (F5)
                                                                         390 root files
```

### Proposed end state (after W5)

```text
ABACUS/
├── README.md  CHANGELOG.md  SECURITY.md  LICENSE                front door
├── pyproject.toml  pytest.ini  requirements*.txt  Makefile  Dockerfile  docker-compose.yml  (+ 7 dotfiles)
├── .jade/repo.yaml                     JADE pointer: where the real entry points are
├── docs/                               living docs (GitHub Pages)
│   ├── guides/                         ← F4 guides that are still used (W4)
│   └── repo-structure/                 ← this plan + ROOT_INVENTORY.csv
├── docs_versioned/                     frozen history
│   ├── ROOT_RELOCATION_MAP.csv         ← every move, old → new
│   ├── generated_reports/              ← F1 (W1)
│   ├── handover/                       ← F2 (W2)
│   ├── status_reports/                 ← F3 without a version in the name (W3)
│   ├── plans/                          ← F4 superseded plans (W4)
│   └── v2.1/  v2.2_archived/  v2.3/  v2.3_active/  v3.3/  v4.4/   ← version-stamped F3/F4 (W3, W4)
├── scripts/<purpose>/                  ← F5 (W5), root shim only while a consumer still calls the root path
└── (the other existing folders, unchanged)
                                                                          19 root files
```

### Per wave

| Wave | Family | Moves | Root files after | Folders added or filled | Starts when |
| --- | --- | ---: | ---: | --- | --- |
| W0 | inventory, map, tool, test, `.jade` pointer | 0 | 390 | `docs/repo-structure/`, `.jade/` | — |
| **W1** | F1 generated run reports | 20 | **370** | `docs_versioned/generated_reports/` | this PR |
| **W2** | F2 handover and session notes | 41 (1 held) | **329** | `docs_versioned/handover/`, `docs_versioned/v2.2_archived/` (fixes the README "Get Started" links) | this PR |
| **W3a** | F3 unversioned, no code consumer | 40 | **289** | `docs_versioned/status_reports/` | stacked on #2438; opens after it merges green |
| W3b | F3 unversioned, 14 with code or config consumers (+ `COMPLETION_SUMMARY.md`, a name clash in two tracker YAMLs) | 25 | 264 | `docs_versioned/status_reports/` | W3a merged and green |
| W3c | F3 version-stamped V2.1, V2.2, V2.3, v4.4 (3 with code consumers) | 24 | 240 | `docs_versioned/v2.1/`, `v2.2_archived/`, `v2.3/`, `v4.4/` | W3b merged and green |
| W3d | F3 version-stamped V3.x (5 with code consumers) | 22 | 218 (+ 7 F3 prune candidates held) | `docs_versioned/v3.3/` | W3c merged and green |
| W4 | F4 plans, guides, reference | 126 | 92 | `docs/guides/`, `docs_versioned/plans/`, version folders | W3 merged and green |
| W5 | F5 code and data | 65 | 27 (19 + 8 held prune candidates until decided) | `scripts/<purpose>/` | W4 merged and green |

```text
W1  ABACUS/                                 W2  ABACUS/
    ├── docs_versioned/                         ├── docs_versioned/
    │   ├── ROOT_RELOCATION_MAP.csv  (+20)      │   ├── ROOT_RELOCATION_MAP.csv  (+42)
    │   └── generated_reports/       +20        │   ├── handover/                +38
    └── root: 370 files                         │   └── v2.2_archived/           +3
                                                └── root: 329 files

W3  ABACUS/                                 W4  ABACUS/
    ├── docs_versioned/                         ├── docs/guides/                 +n (owner picks)
    │   ├── status_reports/          +n         ├── docs_versioned/plans/        +m
    │   └── v2.x/ v3.3/ v4.4/        +118-n     │   └── v2.x/ v3.3/ v4.4/        +126-n-m
    └── root: 218 files (+7 held)               └── root: 92 files

W5  ABACUS/
    ├── scripts/<purpose>/           +65  (shims where a workflow still calls the root path)
    └── root: 19 files (after the prune decision on the held file)
```

## Wave procedure (the same steps every time)

1. `git fetch`, then merge `origin/main` into the wave branch. Refresh the inventory
   (`inventory.py --write`) and record the commit.
2. Consumer census: every inbound reference of the wave's files is either a link that
   `relocate.py` rewrites or a plain mention in history (tables, backticks, dated snapshots), which is left as written.
   Also grep the federation repos (hub, CODEX, gg_MATH) for the file names.
3. Add the wave's rows to the relocation map.
4. Run the smoke checks below and keep the output (**before**).
5. `python tools/root_refactor/relocate.py apply --wave Wn`: `git mv`, inbound link
   rewrite, re-base of the moved files' own links. Code blocks are left alone.
6. Run the same smoke checks again (**after**). Nothing that passed before may fail.
7. One PR, marked "Do not merge unless green". The next wave waits for the merge.

### Smoke checks

| Check | Command | Pass rule |
| --- | --- | --- |
| Relocation invariant | `python tools/root_refactor/relocate.py check` (also `tests/test_root_relocation.py`) | 0 problems: old paths gone, new paths present, no live link to an old path |
| Repo-wide relative links | link census over every tracked `.md`/`.html` | broken links after ⊆ broken links before |
| Docs site links | `python scripts/validate_docs_links.py` | no new errors |
| Workflow YAML | `bash scripts/verify_workflows.sh` | all valid |
| Tender guard | `python tools/a10_guard.py --diff origin/main` | OK |
| Full test suite | `python -m pytest -n 6 --timeout=600 --timeout-method=thread` | failures after ⊆ failures before |

## W1 + W2 results

Measured locally on Python 3.12 (Windows): before = `5678e2bc` (main `8d27bca8` merged, nothing moved),
after = the W1 + W2 branch. CI on Linux (3.11 and 3.12) is the authority.

| Check | Before | After |
| --- | --- | --- |
| `relocate.py check` | 47 problems (W1 not applied) | **0** (61 mapped files) |
| Relative links in all tracked .md/.html | 1133, 101 broken | 1141, 99 broken: **0 new**, 2 README links fixed |
| `scripts/validate_docs_links.py` | 7 errors | 7, identical |
| `scripts/verify_workflows.sh` | 217/217 valid | 217/217 valid |
| `tools/a10_guard.py --diff origin/main` | — | OK |
| Changed-docs lint (`scripts/validate_changed_docs.py`) | — | pass: 59 pure renames skipped, 3 new docs clean, 14 edited legacy docs add no findings |
| Full pytest (`-n 6`, 5847 tests) | 5699 passed, 26 failed, 110 errors, 12 skipped | identical, test by test: **0 newly failing** |
| Root refactor and validator tests | — | 35 passed |

The 26 failures and 110 errors are the same tests in both runs (Windows-only environment
gaps such as `git init` in temp folders and the `hepak-tools` package shadowing `scripts`).

## Prune and merge candidates (owner decision; none deleted)

Names are the original root names; moved files are now at the location the [repository map](index.html) shows. `DMAIC_V3_CANONICAL_HANDOVER_BOOK.md` is held at the root in W2 because `handover/GLOOB.yaml` still lists it: delete it and the GLOOB entry together, or move both.

| File | Family | Why | Proposal |
| --- | --- | --- | --- |
| `DMAIC Implementation Manifest.md` | F4 | empty (0 bytes) | delete |
| `DMAIC_ACTION_ITEMS.md` | F3 | byte-identical to `dmaic-sprint-system/docs/DMAIC_ACTION_ITEMS.md` | delete the root copy and repoint its links to the twin |
| `DMAIC_QUICK_START_GUIDE.md` | F4 | byte-identical to `dmaic-sprint-system/docs/DMAIC_QUICK_START_GUIDE.md` | delete the root copy and repoint its links to the twin |
| `DMAIC_SPRINT_3_COMPLETION_REPORT.md` | F3 | byte-identical to `dmaic-sprint-system/sprints/archive/DMAIC_SPRINT_3_COMPLETION_REPORT.md` | delete the root copy and repoint its links to the twin |
| `DMAIC_SPRINT_4_COMPLETION_REPORT.md` | F3 | byte-identical to `dmaic-sprint-system/sprints/archive/DMAIC_SPRINT_4_COMPLETION_REPORT.md` | delete the root copy and repoint its links to the twin |
| `DMAIC_SPRINT_5_CRITICAL_FINDINGS.md` | F4 | byte-identical to `dmaic-sprint-system/sprints/archive/DMAIC_SPRINT_5_CRITICAL_FINDINGS.md` | delete the root copy and repoint its links to the twin |
| `DMAIC_SPRINT_5_PLAN.md` | F4 | byte-identical to `dmaic-sprint-system/sprints/archive/DMAIC_SPRINT_5_PLAN.md` | delete the root copy and repoint its links to the twin |
| `DMAIC_SPRINT_5_TASK1_COMPLETION.md` | F4 | byte-identical to `dmaic-sprint-system/sprints/archive/DMAIC_SPRINT_5_TASK1_COMPLETION.md` | delete the root copy and repoint its links to the twin |
| `DMAIC_SPRINT_DASHBOARD.md` | F3 | byte-identical to `dmaic-sprint-system/docs/DMAIC_SPRINT_DASHBOARD.md` | delete the root copy and repoint its links to the twin |
| `DMAIC_SPRINT_FINAL_SUMMARY.md` | F3 | byte-identical to `dmaic-sprint-system/docs/DMAIC_SPRINT_FINAL_SUMMARY.md` | delete the root copy and repoint its links to the twin |
| `DMAIC_V3_CANONICAL_HANDOVER_BOOK.md` | F2 | empty (0 bytes) | delete |
| `ENGINE_DOW_handover_min.md` | F2 | byte-identical to `ENGINE_DOW_handover_min.md_V1_1211_1905.md` | keep one; delete the other |
| `ENGINE_DOW_handover_min.md_V1_1211_1905.md` | F2 | byte-identical to `ENGINE_DOW_handover_min.md` | keep one; delete the other |
| `EXECUTION_SUMMARY_20251111_192641.md` | F1 | empty (0 bytes) | delete |
| `handover_with_code_asMardown.md` | F2 | empty (0 bytes) | delete |
| `OPEN_ACTIONS_CLOSURE_SUMMARY.md` | F3 | byte-identical to `CHANGELOG.md` | delete (a copy of the changelog under another name) |
| `V2.3_EVOLUTION_PLAN_20251111.md` | F4 | byte-identical to `docs_versioned/v2.3_active/V2.3_EVOLUTION_PLAN_20251111.md` | delete the root copy and repoint its links to the twin |
| `V2.3_IMMEDIATE_ACTION_PLAN_20251111.md` | F4 | byte-identical to `docs_versioned/v2.3_active/V2.3_IMMEDIATE_ACTION_PLAN_20251111.md` | delete the root copy and repoint its links to the twin |
| `V2.3_PROGRESS_SUMMARY_20251111.md` | F3 | byte-identical to `docs_versioned/v2.3_active/V2.3_PROGRESS_SUMMARY_20251111.md` | delete the root copy and repoint its links to the twin |

## Open owner decisions

1. **Prune list above:** delete, keep, or replace with a link.
2. **F4 split:** which guides are still current (they go to `docs/guides/` and are published on Pages) and which are history.
3. **F5 consumers:** for each script a workflow or the Makefile calls, either update the caller in the same PR or leave a root shim for one release.
4. **Coverage paths:** W5 changes file paths inside coverage reports (`source = ["."]`). Any coverage baseline keyed by path needs a re-baseline in the same PR.

## JADE first pass (census J14-W0)

Read-only `devops/census.py scan --only GBOGEB/ABACUS` from the hub, at ABACUS head
`3fe7c86b0a0e2f6643a717d68f12b7a8dda8e58e` (tree `7e1bb844`), census digest `265eab833c90…`,
baseline the N10 census head `99faf195`. Root layout is not one of the lifecycle probes;
these are the stage levels the refactor must not lower.

| Stage | Level | Probes passing | Next blocker |
| --- | --- | ---: | --- |
| S0 PLAN | L3 automated | 4/5 | plan.protection UNKNOWN |
| S1 CODE | L5 controlled | 5/5 | — |
| S2 BUILD | L3 automated | 4/5 | build.pinned_actions FAIL |
| S3 TEST | L3 automated | 3/5 | test.fail_closed FAIL |
| S4 SECURE | L3 automated | 3/5 | secure.least_privilege FAIL |
| S5 RELEASE | L4 gated | 4/5 | release.provenance FAIL |
| S6 DEPLOY | L3 automated | 4/5 | deploy.contract FAIL |
| S7 OPERATE | L3 automated | 3/5 | operate.rollback FAIL |
| S8 MONITOR | L3 automated | 4/5 | monitor.live_parity UNKNOWN |
| S9 CONTROL | L3 automated | 3/5 | control.red_trace FAIL |

Tests at that head: 623 files, 7007 cases, 489 of 728 Python modules referenced by a test, 14 files with zero cases.
Re-run after each wave from a hub checkout:

```text
python mission-control/jade_temple/devops/census.py fetch --cache <dir> --only GBOGEB/ABACUS --baseline-census mission-control/jade_temple/data/DEVOPS_CENSUS_N10.json
python mission-control/jade_temple/devops/census.py scan  --cache <dir> --only GBOGEB/ABACUS --baseline-census mission-control/jade_temple/data/DEVOPS_CENSUS_N10.json --out <out>.json --objects <obj>.json --no-pages --no-api --iteration J14-Wn
```
