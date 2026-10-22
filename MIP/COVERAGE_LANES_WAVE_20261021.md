# MIP coverage-lanes wave — 21 October 2026

MERGE_ADMISSION = HOLD. This wave adds tests only. It claims no admission
credit, no causal-root closure and no broad-coverage uplift until CI produces
terminal, source-matched evidence.

## Goal

Raise measured coverage of the eight-module frontier from the 20 October
census. Do it with tests that exercise negative, reverse, adversarial,
duplicate-attempt, stale-SHA and missing-artifact behaviour, without changing a
single production blob.

## Source identity

| Control | Value |
| --- | --- |
| Census HEAD (20 Oct) | `e721bd320f509c65e8e52ce9babccc9a1de3c8bf` |
| Wave base HEAD (21 Oct) | `44caccf716a7c20693a2911566289bfc75ea81d9` (61 commits later) |
| Coverage tool | coverage.py 7.11.3, branch mode, `pyproject.toml` `[tool.coverage]` |
| Combined metric | (covered statements + covered branches) / (statements + branches) |

Production blobs at the wave base (frozen for this wave):

| Module | Git blob |
| --- | --- |
| `github_tracking_manager.py` | `d50b6205b05c013ba5064cf063ee63e16e04d498` |
| `cicd_github_orchestrator.py` | `82a9a707115c58721a2c13c41a7b7baebde6b2c1` |
| `scripts/test_admission_census.py` | `34ed0fdfbc4eda51d74391b56b2a6a0643d7a66e` |
| `tools/w80_observed_outcome_validation.py` | `41600ab1e49e179e514755168347139b49b3eaca` |
| `DMAIC_V3/phases/phase8_todo_management.py` | `d5ab3ea15a720c70b635910e5ced203e2c486353` |
| `DMAIC_V3/agents/self_improvement_agent.py` | `933d5f7087f4519cf93d78aeefc863c23de9a09c` |
| `.../w10/build_global_spine_w10.py` | `e299c822a23862e1822923bc4bc012f7c70c0dbf` |
| `.../w10/refresh_w10_spine.py` | `e94dc55b330f1b23148fe26cd64518c2aa8006ae` |

Drift since the census: only `cicd_github_orchestrator.py` changed
(`f8c48f18`, W73 fail-closed for unknown status). Its denominator moved from 348
to 352 statements, so its census figure (64.19%) is not comparable with this
wave. The phase8 blob is `d5ab3ea1`, which the N15 source guard expected to be
`e9e4edd4`. This wave does not touch it and gives no N15 requalification.

## Matched-cohort baseline

The baseline uses the existing tests that reference each module, with the CI
coverage configuration, at the wave base. For seven of the eight modules it
reproduces the census per-module percentage exactly, which confirms that the
instrumentation matches. The orchestrator differs because of the drift above.

| Module | Stmts | Miss | Combined |
| --- | ---: | ---: | ---: |
| `github_tracking_manager.py` | 250 | 214 | 11.49% |
| `cicd_github_orchestrator.py` | 352 | 107 | 67.78% |
| `scripts/test_admission_census.py` | 133 | 81 | 38.62% |
| `tools/w80_observed_outcome_validation.py` | 305 | 49 | 79.53% |
| `DMAIC_V3/phases/phase8_todo_management.py` | 372 | 62 | 82.65% |
| `DMAIC_V3/agents/self_improvement_agent.py` | 221 | 125 | 45.12% |
| `build_global_spine_w10.py` | 200 | 109 | 48.30% |
| `refresh_w10_spine.py` | 152 | 88 | 38.56% |
| **Frontier total** | **1,985** | **835** | **56.42%** |

## Wave structure — disjoint lanes

Each lane owns only new test files. No lane writes production source, and no two
lanes write the same file, so the lanes can run in parallel.

| Lane | Theme | Modules | Owned files (all under `tests/coverage/`) |
| --- | --- | --- | --- |
| L1 | Tracking and CLI failure propagation | `github_tracking_manager.py`, `cicd_github_orchestrator.py` | `test_github_tracking_manager_lane1.py`, `test_cicd_github_orchestrator_lane1.py` |
| L2 | G3CS W10 refresh and admission-census evidence integrity | `build_global_spine_w10.py`, `refresh_w10_spine.py`, `scripts/test_admission_census.py` | `test_build_global_spine_w10_lane2.py`, `test_refresh_w10_spine_lane2.py`, `test_admission_census_script_lane2.py` |
| L3 | W80 outcome reversal and Phase 8 replay/registry corruption | `tools/w80_observed_outcome_validation.py`, `DMAIC_V3/phases/phase8_todo_management.py` | `test_w80_observed_outcome_lane3.py`, `test_phase8_todo_management_lane3.py` |
| L4 | Agent quality-root preservation | `DMAIC_V3/agents/self_improvement_agent.py` | `test_self_improvement_agent_lane4.py` |

Rules for every lane:

- The tests are hermetic: `tmp_path` only, no network, and no real `git`/`gh`.
- Assertions check behaviour; no test exists only to execute lines.
- Bugs found in production code are documented in tests, not fixed in this wave.

## Out of scope (still RED, not bypassed)

- Security (Bandit, Safety) and code-quality (Black, isort) roots. Tests do not
  change scanner populations.
- Docs-validation YAML line length, the DOW TestPilot pre-commit failure, and the
  `METRICS_PR_TOKEN` credential.
- N15 matched four-module requalification (phase4/phase8 blob mismatch).
- Reachability classification of the 71 zero-covered modules.
- Ruleset governance: required reviews and required status checks.

## Ceiling

The broad 75% gate is 4.04 pp above the census (70.96%). At baseline the frontier
had 835 missed statements and 343 missed branches. That is 1,178 combined units,
or 1.95 pp of the census's broad denominator of 60,436 units (46,492 statements
plus 13,944 branches). Even full frontier coverage cannot close the gap alone.

## Results (local, matched cohort)

The measurement ran on the wave base `44caccf7`, on Windows with CPython 3.12.7,
using the CI `pyproject.toml` coverage configuration in branch mode. The cohort
is the baseline tests plus the eight lane files, run together in one process.
These are local, technical measurements only; CI has not confirmed them.

| Module | Baseline | After wave | Still missed |
| --- | ---: | ---: | --- |
| `github_tracking_manager.py` | 11.49% | 100.00% | none |
| `cicd_github_orchestrator.py` | 67.78% | 99.56% | 197-198 (unreachable `except` under `rglob`) |
| `scripts/test_admission_census.py` | 38.62% | 100.00% | none |
| `tools/w80_observed_outcome_validation.py` | 79.53% | 99.06% | 116, 410 (shadowed or unreachable guards) |
| `DMAIC_V3/phases/phase8_todo_management.py` | 82.65% | 100.00% | none |
| `DMAIC_V3/agents/self_improvement_agent.py` | 45.12% | 100.00% | none |
| `build_global_spine_w10.py` | 48.30% | 98.64% | 286, 326 (`spec is None` guards) |
| `refresh_w10_spine.py` | 38.56% | 99.58% | arc 101->103 |
| **Frontier total** | **56.42%** | **99.59%** | 6 statements, 5 partial branches |

Frontier counters:

- Missed statements fell from 835 to 6.
- Covered branches rose from 375 to 713 (of 718).
- That is +1,167 combined units, about +1.93 pp of the census denominator.

The projection depends on one assumption. The broad suite already covers these
modules exactly as far as the matched cohort did, and for the seven unchanged
blobs the cohort reproduced CI's percentages exactly. Under that assumption, the
broad figure would be about 72.9%, still below the 75% gate. Only a terminal CI
coverage job on this branch can confirm or refute it.

Test execution:

- The wave adds 424 new tests: L1 104, L2 200, L3 83, L4 37.
- The combined cohort result is 801 passed, 1 skipped and 5 strict xfail.
- One test failed, and it fails without the wave too:
  `test_w32_g3cs_neural_dependencies::test_native_import_is_real_not_a_mock_or_skip`.
  The workstation has networkx 3.5 and the test pins 3.6.1, so this is
  environmental.
- Each lane ran its files twice, with identical results and coverage.
- All eight production blobs were identical before and after the wave.

Static gates on the new files:

- `black --check`, `isort --check-only` (repo `.editorconfig`, 120 columns) and
  `flake8 --select=E9,F63,F7,F82` (plus all `F` codes) are clean.
- A static Python 3.10 check (`ast` `feature_version=(3, 10)`, PEP 701 f-string
  scan, 3.11+/3.12+ stdlib API scan) found nothing in either the tests or the
  eight modules. No 3.10 interpreter was available locally. The CI matrix
  (3.10/3.11/3.12 × Ubuntu/Windows/macOS) gives the runtime proof.

Measurement caveat: in 2 of 4 local combined runs, coverage's SQLite data file
ended with `database disk image is malformed`. The tests passed in all four runs,
and the two runs that completed gave identical coverage. The debug log shows a
single writer process with no foreign bytes in the damaged pages. That fits a
torn write: `pyproject.toml` sets `dynamic_context = "test_function"`, so
coverage writes the file on every test switch, with SQLite journaling off. It
does not fit a test writing into the file. The exact trigger is unproven, so the
CI broad-coverage job should be checked for the same error.

## Production findings (pinned by tests, not fixed)

Each finding is pinned either as asserted current behaviour or as
`xfail(strict=True)`. A fix will flip the pin, which makes the test the
regression guard.

| ID | Module | Finding | Pinned by |
| --- | --- | --- | --- |
| F1 | `cicd_github_orchestrator.py` | In live mode a rejected `git push` sets no pipeline status, so `main()` prints success and returns 0. Fail-closed covers only the git-status scan. | `test_cli_push_failure_currently_still_exits_0` |
| F2 | `cicd_github_orchestrator.py` | `has_changes` is sampled before refactoring, so on a clean tree a live run moves and deletes files but never commits them. | lane 1 current behaviour |
| F3 | `scripts/test_admission_census.py` | A JUnit file left in `--junit-dir` by an earlier run is not cleared. If pytest writes no new JUnit (exit 0 or 5), the stale pass is classified `TEST_GREEN`. | `test_main_stale_junit_from_previous_run_is_trusted` |
| F4 | `build_global_spine_w10.py` | `make_html` puts the `local_dod` and `mission_goals` `id` field and the pill CSS class built from `state` into HTML unescaped. | strict xfail ×2 |
| F5 | `build_global_spine_w10.py` | The metrics JSON and handover hardcode `+522` coverage and `+2` CI recoveries instead of reading `history["next_scenario"]`. | `test_main_metrics_follow_history_scenario` (strict xfail) |
| F6 | `phase8_todo_management.py` | Code-scan TODO IDs hash `datetime.now()`, so replaying the same workspace registers the same TODO again. | lane 3 current behaviour |
| F7 | `phase8_todo_management.py` | A TODO with `phase: null` raises `TypeError` in prioritisation, because the check sits outside the guarding `try`. | `test_prioritize_null_phase_raises_current_behaviour` |
| F8 | `phase8_todo_management.py` | On Windows the case-variant `TODO*.yaml`/`todo*.yaml` patterns ingest one file twice. | `test_yaml_todo_file_double_ingestion_is_platform_dependent` |
| F9 | `self_improvement_agent.py` | `_define_opportunities` looks up the literal `"phaseN_*"` against real directory names, so every cycle reports all 9 phases as missing. | strict xfail |
| F10 | `self_improvement_agent.py` | `success_rate` is `len(optimized)/max(len(optimized),1)*100`, which is always 100% when anything survives, so rejected improvements never lower it. `--cycles 0` raises `ZeroDivisionError`. | lane 4 current behaviour |
| F11 | `self_improvement_agent.py` | An existing but empty `agent_registry.json` is falsy, so the 0/12 under-utilisation finding is dropped. | strict xfail |
| F12 | `github_tracking_manager.py` | Feedback and action IDs come only from `utcnow().timestamp()`, so they collide within one clock tick. CI run records store no head SHA. | lane 1 current behaviour |

F1 and F3 are integrity defects in exit-code and evidence propagation. They are
the ones most relevant to admission.

## Disposition

| KPI | Disposition |
| --- | --- |
| Frontier coverage, local matched cohort | 56.42% → 99.59% (technical evidence) |
| Broad coverage uplift, CI source-matched | UNKNOWN until a terminal CI coverage job runs on this branch |
| 75% gate | Projected FAIL (about 72.9%) |
| Production blobs | Unchanged (8/8) |
| N15 matched four-module qualification | FAIL (not addressed by this wave) |
| Correctly governed merge | NOT VERIFIED |
| MERGE_ADMISSION | **HOLD** |
