# MIP coverage-lanes wave — 21 October 2026

MERGE_ADMISSION = HOLD. This wave adds tests only. It claims no admission
credit, no causal-root closure and no broad-coverage uplift until CI produces
terminal, source-matched evidence.

## Goal

Raise measured coverage of the eight-module frontier from the 20 October
census. Do it with tests that exercise negative, reverse, adversarial,
duplicate-attempt, stale-SHA and missing-artifact behaviour, without changing
a single production blob.

## Source identity

- Census HEAD (20 Oct): `e721bd320f509c65e8e52ce9babccc9a1de3c8bf`
- Wave base HEAD (21 Oct): `44caccf716a7c20693a2911566289bfc75ea81d9`,
  61 commits later
- Coverage tool: coverage.py 7.11.3, branch mode, `pyproject.toml`
  `[tool.coverage]`
- Combined metric: (covered statements + covered branches) /
  (statements + branches)

Production blobs at the wave base (frozen for this wave):

- `github_tracking_manager.py`:
  `d50b6205b05c013ba5064cf063ee63e16e04d498`
- `cicd_github_orchestrator.py`:
  `82a9a707115c58721a2c13c41a7b7baebde6b2c1`
- `scripts/test_admission_census.py`:
  `34ed0fdfbc4eda51d74391b56b2a6a0643d7a66e`
- `tools/w80_observed_outcome_validation.py`:
  `41600ab1e49e179e514755168347139b49b3eaca`
- `DMAIC_V3/phases/phase8_todo_management.py`:
  `d5ab3ea15a720c70b635910e5ced203e2c486353`
- `DMAIC_V3/agents/self_improvement_agent.py`:
  `933d5f7087f4519cf93d78aeefc863c23de9a09c`
- `MIP/G3CS_CONVERGENCE_V2/observatory/w10/build_global_spine_w10.py`:
  `e299c822a23862e1822923bc4bc012f7c70c0dbf`
- `MIP/G3CS_CONVERGENCE_V2/observatory/w10/refresh_w10_spine.py`:
  `e94dc55b330f1b23148fe26cd64518c2aa8006ae`

Drift since the census:

- Only `cicd_github_orchestrator.py` changed (`f8c48f18`, W73 fail-closed for
  unknown status). Its denominator moved from 348 to 352 statements, so its
  census figure (64.19%) is not comparable with this wave.
- The phase8 blob is `d5ab3ea1`, but the N15 source guard expects `e9e4edd4`.
  This wave does not touch phase8 and gives no N15 requalification.

## Matched-cohort baseline

The baseline uses the existing tests that reference each module, run with the
CI coverage configuration at the wave base. For seven of the eight modules it
reproduces the census per-module percentage exactly, which confirms the
instrumentation matches. The orchestrator differs because of the drift above.

| Module | Stmts | Miss | Combined |
| --- | ---: | ---: | ---: |
| `github_tracking_manager.py` | 250 | 214 | 11.49% |
| `cicd_github_orchestrator.py` | 352 | 107 | 67.78% |
| `scripts/test_admission_census.py` | 133 | 81 | 38.62% |
| `w80_observed_outcome_validation.py` | 305 | 49 | 79.53% |
| `phase8_todo_management.py` | 372 | 62 | 82.65% |
| `self_improvement_agent.py` | 221 | 125 | 45.12% |
| `build_global_spine_w10.py` | 200 | 109 | 48.30% |
| `refresh_w10_spine.py` | 152 | 88 | 38.56% |
| **Frontier total** | **1,985** | **835** | **56.42%** |

## Wave structure — disjoint lanes

Each lane owns only new test files under `tests/coverage/`. No lane writes
production source, and no two lanes write the same file, so the lanes can run
in parallel.

- **L1, tracking and CLI failure propagation.**
  - Modules: `github_tracking_manager.py`, `cicd_github_orchestrator.py`.
  - Files: `test_github_tracking_manager_lane1.py`,
    `test_cicd_github_orchestrator_lane1.py`.
- **L2, G3CS W10 refresh and admission-census evidence integrity.**
  - Modules: `build_global_spine_w10.py`, `refresh_w10_spine.py`,
    `scripts/test_admission_census.py`.
  - Files: `test_build_global_spine_w10_lane2.py`,
    `test_refresh_w10_spine_lane2.py`,
    `test_admission_census_script_lane2.py`.
- **L3, W80 outcome reversal and Phase 8 replay/registry corruption.**
  - Modules: `tools/w80_observed_outcome_validation.py`,
    `DMAIC_V3/phases/phase8_todo_management.py`.
  - Files: `test_w80_observed_outcome_lane3.py`,
    `test_phase8_todo_management_lane3.py`.
- **L4, agent quality-root preservation.**
  - Module: `DMAIC_V3/agents/self_improvement_agent.py`.
  - File: `test_self_improvement_agent_lane4.py`.

Rules for every lane:

- The tests are hermetic: `tmp_path` only, no network, and no real
  `git`/`gh`.
- Assertions check behaviour; no test exists only to execute lines.
- Bugs found in production code are pinned in tests, not fixed in this wave.
- No `xfail`. The canonical B0 lane and the ABACUS jobs run
  `test_evidence_census.py --max-xfails 0`, so known bugs are pinned as
  asserted current behaviour.
- No reliance on directory enumeration order. `Path.glob` is alphabetical on
  NTFS but arbitrary on ext4 and APFS.

## Out of scope (still RED, not bypassed)

- Security (Bandit, Safety) and code-quality (Black, isort) roots. Tests do
  not change scanner populations.
- Docs-validation YAML line length, the DOW TestPilot pre-commit failure, and
  the `METRICS_PR_TOKEN` credential.
- N15 matched four-module requalification (phase4/phase8 blob mismatch).
- Reachability classification of the 71 zero-covered modules.
- Ruleset governance: required reviews and required status checks.

## Ceiling

The broad 75% gate is 4.04 pp above the census (70.96%). At baseline the
frontier had 835 missed statements and 343 missed branches. That is 1,178
combined units, or 1.95 pp of the census's broad denominator of 60,436 units
(46,492 statements plus 13,944 branches). Even full frontier coverage cannot
close the gap alone.

## Results (local, matched cohort)

The measurement ran on the wave base `44caccf7`, on Windows with CPython
3.12.7, using the CI `pyproject.toml` coverage configuration in branch mode.
The cohort is the baseline tests plus the eight lane files, run together in
one process. These are local, technical measurements only; CI has not
confirmed them.

| Module | Baseline | After | Still missed |
| --- | ---: | ---: | --- |
| `github_tracking_manager.py` | 11.49% | 100.00% | none |
| `cicd_github_orchestrator.py` | 67.78% | 99.56% | 197-198 (a) |
| `scripts/test_admission_census.py` | 38.62% | 100.00% | none |
| `w80_observed_outcome_validation.py` | 79.53% | 99.06% | 116, 410 (b) |
| `phase8_todo_management.py` | 82.65% | 100.00% | none |
| `self_improvement_agent.py` | 45.12% | 100.00% | none |
| `build_global_spine_w10.py` | 48.30% | 98.64% | 286, 326 (c) |
| `refresh_w10_spine.py` | 38.56% | 99.58% | arc 101->103 |
| **Frontier total** | **56.42%** | **99.59%** | 6 stmts, 5 arcs |

Notes on the remaining misses:

- (a) An `except` that cannot be reached, because `rglob` only yields paths
  under the workspace.
- (b) Guards that are shadowed (116) or unreachable (410).
- (c) `spec is None` guards; `spec_from_file_location` on a `.py` path always
  returns a loader.

Frontier counters:

- Missed statements fell from 835 to 6.
- Covered branches rose from 375 to 713 (of 718).
- That is +1,167 combined units, about +1.93 pp of the census denominator.

The projection rests on one assumption: that the broad suite covers these
modules exactly as far as the matched cohort did. For the seven unchanged
blobs, the cohort did reproduce CI's percentages exactly. Under that
assumption the broad figure would be about 72.9%, still below the 75% gate.
Only a terminal CI coverage job on this branch can confirm or refute it.

Test execution:

- The wave adds 421 tests: L1 103, L2 199, L3 83, L4 36, with no xfails.
- The final local cohort (384 baseline plus 421 lane tests) has 803 passed,
  1 skipped, 0 xfailed and 1 failed. Coverage is 99.59%, unchanged.
- The one failure happens without the wave too:
  `test_native_import_is_real_not_a_mock_or_skip` in
  `tests/test_w32_g3cs_neural_dependencies.py`. The workstation has
  networkx 3.5 and the test pins 3.6.1, so it is environmental.
- All 421 lane tests pass with normal and with reversed `Path.glob` order.
  The reversed order simulates non-alphabetical filesystems.
- All eight production blobs are identical before and after the wave.

Static gates on the new files:

- `black --check` (88 columns) is clean.
- `isort --check-only` (the repo's `.editorconfig`, 120 columns) is clean.
- `flake8 --select=E9,F63,F7,F82` is clean, and so are all `F` codes.
- A static Python 3.10 check found nothing in the tests or the eight modules.
  It parses with `ast` `feature_version=(3, 10)`, scans for PEP 701 f-strings,
  and scans for stdlib APIs added in 3.11 and 3.12. No 3.10 interpreter is
  available locally, so the CI matrix (3.10, 3.11, 3.12 on Ubuntu, Windows
  and macOS) gives the runtime proof.

Measurement caveat: in 2 of 4 local combined runs, coverage's SQLite data
file ended with `database disk image is malformed`. The tests passed every
time, and the runs that completed gave identical coverage. The debug log
showed a single writer and no foreign bytes, which fits a torn write rather
than a test writing into the file. `dynamic_context = "test_function"` means
coverage writes on every test switch, and SQLite journaling is off. The exact
trigger is unproven, so check the CI broad-coverage job for the same error.

## CI readback and corrections (22 October)

The first CI run on head `09c0b44c` found three roots, all in this wave:

1. **R1, glob order.** A phase8 lane test assumed `phase4_a` is listed before
   `phase4_b`. That failed on Ubuntu and macOS unit tests and on the ABACUS
   Ubuntu jobs. Fixed: the test now uses the run's own registration order.
   The production behaviour behind it is recorded as F13.
2. **R2, xfail ratchet.** Five strict xfails broke the repo's
   `--max-xfails 0` ratchet, which turned red the B0 canonical producer (all
   6,320 tests had passed), the downstream B0 report-only census, the ABACUS
   jobs and Python proof completeness. Fixed: the xfails are now asserted
   current-behaviour pins. The F9 xfail is dropped as a duplicate of its
   existing pin.
3. **R3, docs lint.** MD013 reported 30 lines of this document over 80
   columns. Fixed: the document is rewrapped to 80 columns.

Security Scanning (Safety) is red on `main` and on #2391 as well, so it is not
caused by this wave.

## Production findings

F1 and F3 are fixed in draft PR #2391. Their regression tests live there, so
this wave asserts neither the old nor the new behaviour, and the two PRs merge
in either order. The other findings are pinned here as asserted current
behaviour and remain unfixed. A fix flips its pin, and the flipped test
becomes the regression guard.

- **F1, `cicd_github_orchestrator.py`.** In live mode a rejected `git push`
  set no pipeline status, so `main()` printed success and returned 0. Fixed in
  #2391 (`tests/test_f1_orchestrator_push_failure_exit.py`).
- **F2, `cicd_github_orchestrator.py`.** `has_changes` is sampled before
  refactoring, so on a clean tree a live run moves and deletes files but
  never commits them. Pinned in lane 1.
- **F3, `scripts/test_admission_census.py`.** A JUnit file left in
  `--junit-dir` by an earlier run was not cleared. If pytest wrote no new
  JUnit, the stale pass was classified `TEST_GREEN`. Fixed in #2391
  (`tests/test_f3_census_stale_junit.py`).
- **F4, `build_global_spine_w10.py`.** `make_html` puts the
  `local_dod`/`mission_goals` `id` field, and the pill class built from
  `state`, into HTML unescaped. Pinned by
  `test_make_html_dod_identifier_unescaped_current_behaviour` and
  `test_make_html_state_class_attribute_unescaped_current_behaviour`.
- **F5, `build_global_spine_w10.py`.** The metrics JSON and handover hardcode
  `+522` coverage and `+2` CI recoveries instead of reading
  `history["next_scenario"]`. Pinned by
  `test_main_metrics_ignore_history_scenario_current_behaviour`.
- **F6, `phase8_todo_management.py`.** Code-scan TODO IDs hash
  `datetime.now()`, so replaying the same workspace registers the same TODO
  again. Pinned in lane 3.
- **F7, `phase8_todo_management.py`.** A TODO with `phase: null` raises
  `TypeError` in prioritisation, because the check sits outside the guarding
  `try`. Pinned by `test_prioritize_null_phase_raises_current_behaviour`.
- **F8, `phase8_todo_management.py`.** On Windows the case-variant
  `TODO*.yaml` and `todo*.yaml` patterns ingest one file twice. Pinned by
  `test_yaml_todo_file_double_ingestion_is_platform_dependent`.
- **F9, `self_improvement_agent.py`.** `_define_opportunities` looks up the
  literal `"phaseN_*"` against real directory names, so every cycle reports
  all 9 phases as missing. Pinned by
  `test_define_current_behaviour_phase_with_output_still_flagged`.
- **F10, `self_improvement_agent.py`.** `success_rate` is always 100% when
  anything survives, so rejected improvements never lower it, and
  `--cycles 0` raises `ZeroDivisionError`. Pinned in lane 4.
- **F11, `self_improvement_agent.py`.** An existing but empty
  `agent_registry.json` is falsy, so the 0/12 under-utilisation finding is
  dropped. Pinned by
  `test_define_empty_registry_drops_underutilization_current_behaviour`.
- **F12, `github_tracking_manager.py`.** Feedback and action IDs come only
  from `utcnow().timestamp()`, so they collide within one clock tick, and CI
  run records store no head SHA. Pinned in lane 1.
- **F13, `phase8_todo_management.py`.** When two phase outputs carry the same
  TODO ID, the registry keeps whichever is registered last, and that order
  follows unsorted `Path.glob` enumeration. The surviving `source_file` is
  therefore filesystem-dependent: alphabetical on NTFS, arbitrary on ext4 and
  APFS. Sorting the glob results would make it deterministic. Pinned,
  order-independently, by
  `test_duplicate_todo_ids_collapse_in_registry_but_not_in_local_list`.

F1 and F3 are integrity defects in exit-code and evidence propagation. They
matter most for admission, and #2391 addresses them.

## Disposition

| KPI | Disposition |
| --- | --- |
| Frontier coverage, local matched cohort | 56.42% → 99.59% (technical) |
| Broad coverage uplift, CI source-matched | UNKNOWN until terminal CI |
| 75% gate | Projected FAIL (about 72.9%) |
| Production blobs | Unchanged (8/8) |
| N15 matched four-module qualification | FAIL (not addressed here) |
| Correctly governed merge | NOT VERIFIED |
| MERGE_ADMISSION | **HOLD** |
