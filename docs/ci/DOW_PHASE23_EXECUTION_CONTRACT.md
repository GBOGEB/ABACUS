# DOW Phase 2/3 CI execution contract - source-bound census

**Basis:** Current Bootstrap Statistics CI/CD workflow at .github/workflows/ci-cd.yml.
**Status:** REQUIRED EXECUTABLES MISSING on inspected main. No algorithmically
equivalent replacement established. The DMAIC V3 Phase2Measure and Phase3Analyze
classes implement different interfaces and are not proven substitutes.

## Phase 2: required command and output

- Command: python dow_phase2_statistics.py --results-dir test_data.csv --dow-root dow_output --alpha 0.05 --mode csv
- CI prepares CSV columns group,score with four sample observations.
- Metadata location: dow_output/**/phase2_metadata.json.
- Metadata schema and statistical interpretation are UNKNOWN.

## Phase 3: required command and output

- Command: python dow_phase3_reporting.py --phase2-metadata <phase2_metadata_path>
- Workflow upload patterns include phase3_reports/**/*, dow_output/**/*.md,
  dow_output/**/*.json, and dow_output/**/*.png.
- The existing upload step does not establish nonempty Phase 3 artifacts.
- Report schema and acceptance criteria are UNKNOWN.

## Fail-closed treatment

Run: python scripts/dow_ci_contract_census.py --require-sources --output test_reports/dow/source-contract.json

- A parseable source file is not evidence that either algorithm ran.
- The census never reports merge-admission PASS. When source files are absent,
  the --require-sources mode exits nonzero.
- Do not replace these entrypoints with unrelated DMAIC classes, placeholders,
  skipped steps, an empty artifact, or a report-only green.
- Before promoting source restoration, require tests for malformed/empty CSV,
  missing or malformed phase2 metadata, phase3 output presence, deterministic
  reruns, and provenance-linked native execution results.
- The AHT repair in PR #1937 is separately merged; do not duplicate it.
- This bounded source census does not modify the workflow, CI thresholds,
  scanner settings, existing admissions, or branch protection.
