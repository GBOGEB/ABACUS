# W007 — CI/CD Pipeline: Validation Report

**Wave:** W007 &nbsp;|&nbsp; **Status:** delivered &nbsp;|&nbsp; **Date:** 2026-06-07

This is the *Normalized-Claim ≠ Complete* record for W007 (per AGENTS.md
governance): every claim below is backed by a file that exists and a runtime
result that was actually produced.

---

## 1. Claim

> The MINERVA P&ID pipeline is continuously verifiable: a GitHub Actions
> workflow regenerates all derived artifacts (`./make.sh`), runs the full
> standalone test battery under coverage, enforces a deterministic golden-file
> regression gate, checks clean-rebuild reproducibility, and uploads artifacts —
> all **without pytest**, honoring the project's standalone-runner convention.

## 2. What exists (files)

| Artifact | Path | Purpose |
|---|---|---|
| Workflow | `ci/minerva-pid-test.yml` | build + test + coverage + golden + reproducibility + artifacts (staged; see §6) |
| Coverage cfg | `.coveragerc`, `[tool.coverage.*]` in `pyproject.toml` | coverage.py settings (source=src, branch, parallel) |
| Golden snapshots | `tests/golden/expected_line_model_structure.json`, `…/expected_component_counts.json`, `…/expected_crossmap_stats.json` | pinned invariants from runtime output |
| Golden runner | `tests/test_golden_files.py` | standalone golden-file regression gate |
| Pre-commit | `.pre-commit-config.yaml` | advisory hygiene/lint hooks |
| Implementation doc | `docs/W007_CI_IMPLEMENTATION.md` | what was built + the no-pytest rationale |
| This report | `reports/W007_CICD_REPORT.md` | validation record |

## 3. Runtime results (actually produced)

```
./make.sh                       → exit 0 (all derived outputs regenerated)
./make.sh --clean ; ./make.sh   → exit 0 (idempotent; artifacts re-created)

Standalone test battery (PYTHONPATH=src python3 tests/test_*.py):
  test_colour_model.py            5/5   PASS
  test_golden_files.py            4/4   PASS   (NEW this wave)
  test_integration_pipeline.py    5/5   PASS
  test_w003_w004.py              10/10  PASS
  test_w005_reconciliation.py    11/11  PASS
  test_w006_crossmap.py          13/13  PASS
  ----------------------------------------------
  TOTAL                          48/48  PASS  (6 runners)

Coverage (coverage run -p → combine → report → xml):
  coverage.xml produced (~98 KB)
  TOTAL line coverage ≈ 17.9%  (reported, not gated — see §5)
```

## 4. Golden-file gate — pinned values (verified)

| Invariant | Value |
|---|---|
| `line_model.line_count` | 9 |
| catalog `unique_count` / `real_count` / `template_count` | 165 / 141 / 24 |
| `real_prefix_histogram` | CV 10, EH 22, HV 12, LS 25, PT 9, TT 63 (= 141) |
| crossmap `total_design_tags` / `total_asdrawn_real_tags` | 97 / 141 |
| crossmap `mapped` (HIGH/MED/LOW) | 43 (0 / 39 / 4) |
| crossmap `unmapped_design` / `asdrawn_unclaimed` | 54 / 98 |

Internal-consistency assertions enforced: histogram Σ = `real_count`;
confidence tiers Σ = `mapped`. Volatile geometry and the ~1-byte XLSX jitter are
excluded from the gate by design → deterministic.

## 5. Known gaps

- **Coverage is reported, not gated.** ~18% reflects that tests target pure
  functions while `build_*` scripts execute via `make.sh` as `__main__`. No
  inflated `fail_under` was added. A real floor needs build-script
  importability refactoring — deferred.
- **Workflow cannot self-activate** — GitHub App lacks `workflows` permission;
  the file is staged at `ci/minerva-pid-test.yml` and a maintainer must copy it
  to `.github/workflows/` (instructions in §6 and the implementation doc).
- **Codecov upload commented out** (needs maintainer `CODECOV_TOKEN`).
- **pre-commit advisory only** — not enforced in CI to avoid a mass reformat
  diff that could perturb reproducible outputs.
- The wave-registry's broader W007 line also names cross-drawing
  QCELL↔RFCELL reconciliation and 4.5K/2K/warm segment classification; those are
  **modelling** scope deferred to a follow-up. This deliverable is the CI/CD half.

## 6. Maintainer activation (one-time)

```bash
cp MINERVA_PID/ci/minerva-pid-test.yml .github/workflows/minerva-pid-test.yml
git add .github/workflows/minerva-pid-test.yml
git commit -m "ci: activate MINERVA P&ID workflow (W007)"
git push
```

## 7. Reproduce locally

```bash
./make.sh
export PYTHONPATH=src
for t in tests/test_*.py; do python3 "$t"; done
# coverage:
for t in tests/test_*.py; do coverage run -p "$t"; done
coverage combine && coverage report && coverage xml
git checkout -- reports/W005_validation_report.md   # revert XLSX byte jitter
```

**pass = true** — output files exist, this validation report exists, runtime
counts are recorded above, and known gaps are listed.
