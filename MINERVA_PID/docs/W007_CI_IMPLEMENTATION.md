# W007 — CI/CD Pipeline Implementation

**Wave:** W007 &nbsp;|&nbsp; **Status:** delivered &nbsp;|&nbsp; **Depends on:** W001–W006

This document records *what was actually built* for the W007 CI/CD wave, how it
maps to the plan in [`W007_CICD_PLAN.md`](W007_CICD_PLAN.md), and — importantly —
**where the implementation deviates from a generic "add pytest + pytest-cov"
recipe and why**.

---

## 1. The one decision that shapes everything: NO pytest

This project has a documented, non-negotiable convention (AGENTS.md and
`W007_CICD_PLAN.md` §1): **tests are standalone runners**, not pytest modules.
Every `tests/test_*.py` exposes assert-raising `test_*` functions, an internal
`_run_all()` aggregator, optional `_data_available()` skip-guards for
data-dependent suites, and a `if __name__ == "__main__"` entry point. They are
executed as `python3 tests/test_x.py`.

A naive CI/CD wave would introduce `pytest`, `pytest-cov`, and `--golden`
markers. **That would break this project's contract and the existing test
battery.** So W007 delivers the *spirit* of every requested capability without
pytest:

| Requested capability | Generic recipe | What W007 actually uses |
|---|---|---|
| Run tests in CI | `pytest tests/` | loop `for t in tests/test_*.py; do python3 "$t"; done` (already present, kept) |
| Coverage reporting | `pytest --cov` (pytest-cov) | **`coverage.py` directly**: `coverage run -p <runner>` → `coverage combine` → `coverage report`/`xml`. pytest-cov is *just* pytest+coverage glue; we use coverage's own runner instead. |
| Golden-file tests | custom `@pytest.mark.golden` | **standalone runner** `tests/test_golden_files.py` with a `_data_available()` guard, same as every other suite |
| Determinism gate | flaky-test reruns | explicit `./make.sh --clean` rebuild + artifact-existence assertions; golden files pin only invariant fields (never volatile XLSX bytes) |

This is the honest engineering choice: the pipeline is green *because* it
respects the existing convention, not in spite of it.

---

## 2. Deliverables

### 2.1 Workflow — `ci/minerva-pid-test.yml`
Enhanced from the W005-era stub. Changes:
- **Python matrix bumped** `3.8/3.9/3.10/3.11` → **`3.10/3.11/3.12`**.
- **System packages added**: `poppler-utils`, `libxml2-dev`, `libxslt1-dev`
  (alongside the existing `libcairo2`/`libcairo2-dev` for CairoSVG).
- **Coverage**: installs `coverage`, wraps each standalone runner with
  `coverage run -p`, then `coverage combine` + `coverage report` + `coverage xml`;
  pushes a compact table into the GitHub job summary.
- **Golden-file gate**: runs `tests/test_golden_files.py`.
- **Reproducibility step**: `./make.sh --clean` then asserts the key derived
  artifacts exist; re-runs the golden gate after the clean rebuild.
- **Artifact upload** (`actions/upload-artifact@v4`): `coverage.xml`,
  `reports/*.md`, `reports/*.json`, `publish/*.html`.
- **Codecov** upload step included but **commented out** (needs a maintainer
  `CODECOV_TOKEN` secret; the pipeline is green without it).

> **Deployment caveat (unchanged from earlier waves):** the connected GitHub App
> lacks the `workflows` permission, so this file cannot be pushed under
> `.github/workflows/`. It is staged at `ci/minerva-pid-test.yml`; a maintainer
> activates it once — see §4.

### 2.2 Golden-file framework — `tests/golden/` + `tests/test_golden_files.py`
Three committed snapshots, **generated from verified runtime output** (not
hand-authored, no fabricated numbers):

| Golden file | Pins (invariants only) | Source artifact |
|---|---|---|
| `expected_line_model_structure.json` | `line_count=9`; per-line `line_id`/`canonical_name`/`role`/`process_code` | `data/model/line_model.json` |
| `expected_component_counts.json` | `unique_count=165`, `real_count=141`, `template_count=24`, `instrument_sheets`, `real_prefix_histogram` | `data/excel/catalog_register.json` |
| `expected_crossmap_stats.json` | `total_design_tags=97`, `mapped=43` (0 HIGH / 39 MED / 4 LOW), `unmapped_design=54`, … | `reports/W006_crossmap_statistics.json` |

The runner adds **internal-consistency assertions** too (histogram sums to
`real_count`; confidence tiers sum to `mapped`). Volatile geometry/coordinate
fields and the known ~1-byte XLSX jitter are deliberately excluded, so the gate
is deterministic.

### 2.3 Coverage config — `.coveragerc` + `[tool.coverage.*]` in `pyproject.toml`
`source = src/abacus_svg_pid`, branch coverage, parallel mode (for the per-runner
`-p` merge), `tests/` omitted, `show_missing`. No hidden `fail_under` — the CI
job decides any gate explicitly so the threshold is visible in the pipeline.

### 2.4 Pre-commit — `.pre-commit-config.yaml`
**Advisory / opt-in.** Safe hygiene hooks (trailing-whitespace, EOF, check-yaml,
check-json with a `tests/golden/` allowance, large-file guard, merge-conflict,
LF endings) plus `black`/`flake8` (line length 100) which are intentionally
*not* auto-run against the tree (would create a large reformatting diff and could
perturb reproducible outputs).

---

## 3. Local verification (what was actually run)

```bash
./make.sh                                   # exit 0, regenerates all outputs
export PYTHONPATH=src
for t in tests/test_*.py; do python3 "$t"; done
#   test_colour_model.py          5/5
#   test_golden_files.py          4/4   (NEW)
#   test_integration_pipeline.py  5/5
#   test_w003_w004.py            10/10
#   test_w005_reconciliation.py  11/11
#   test_w006_crossmap.py        13/13
#   -------------------------------------
#   48 assertions across 6 standalone runners — all green

# coverage (pytest-cov-free):
rm -f .coverage .coverage.* coverage.xml
for t in tests/test_*.py; do coverage run -p "$t"; done
coverage combine && coverage report && coverage xml   # → coverage.xml (~98 KB)
```

Measured line coverage is **~18 %** overall. This is expected and honest: the
test battery targets pure/derivation functions; the large `build_*` scripts run
their main bodies through `./make.sh` (as `__main__`), not through imports, so
their module-level code is not counted. The number is reported transparently
rather than inflated with a token threshold.

> After a full `./make.sh`, revert the known XLSX byte jitter before committing:
> `git checkout -- reports/W005_validation_report.md`.

---

## 4. Activating the workflow (maintainer, one-time)

```bash
# from the monorepo root, on a branch a maintainer can push to:
cp MINERVA_PID/ci/minerva-pid-test.yml .github/workflows/minerva-pid-test.yml
git add .github/workflows/minerva-pid-test.yml
git commit -m "ci: activate MINERVA P&ID workflow (W007)"
git push
```

The bot cannot do this step itself (missing `workflows` scope). Granting the
[Abacus GitHub App](https://github.com/apps/abacusai/installations/select_target)
the workflows permission would let a future wave land it directly.

---

## 5. Known gaps / deferred

- **Coverage floor not enforced.** Reported, not gated — a meaningful floor
  needs either build-script refactoring for importability or a separate
  integration-coverage strategy. Tracked for a later wave.
- **Codecov disabled** pending a maintainer `CODECOV_TOKEN`.
- **pre-commit not enforced in CI** (advisory only) to avoid a mass reformat.
- The CI cross-drawing QCELL↔RFCELL reconciliation and 4.5K/2K/warm
  per-segment classification mentioned in the wave registry remain **modelling**
  scope for a follow-up; W007 here delivers the **CI/CD** half of the wave.
