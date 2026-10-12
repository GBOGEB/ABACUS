# DAB Full-Red Gates, Proof Completeness and Coverage Growth

## Purpose

This control joins three previously separate views:

1. repository-wide Flake8/DAB red debt,
2. Python 3.10/3.11/3.12 proof completeness,
3. executed test/check coverage.

A reduction in static-analysis count is not sufficient to close a gate when
proof coverage regresses, a required job is skipped without classification,
or a protected hold changes without source-bound authority.

## Measured reference state

Reference Python-changing main lineage:

- source SHA: `3f16d6ffc92d4c4d3994e264971c5dd32e7032a7`
- DAB run: `37113810834`
- DAB artifact: `11271181698`
- DAB artifact SHA-256:
  `ac39b8f8aa16fbfab5ff8c2e4da54523071ff655461e512a5102e9522faa1491`
- full Flake8 red total: **3112**
- E303: **1**
- E999: **1**, source-bound HOLD

The generated metrics commit `fd5cad73...` contains no Python mutation, so this
remains the measured static-analysis reference for this proposal.

## DAB G1-G3 ladder

| Gate | Static budget | Companion proof |
| --- | ---: | --- |
| G1 | total < 3000 | exact SHA; hold; compatible proposal |
| G2 | total < 2500 | G1 + Python role/skip audit + coverage non-regression |
| G3 | total < 2000 | G2 + critical-skip audit + red-root visibility + growth |

At the reference state, none of G1-G3 is closed because **3112 > 3000**.

The thresholds are intentionally progressive. G3 is the requested **below 2000**
full-red control boundary; it is not a substitute for terminal zero-debt
cleanup.

## Python 3.10/3.11/3.12 main audit

Main matrix run: `37113810869`.

All three selected Python jobs and the compatibility gate completed GREEN. The
step-level proof is deliberately asymmetric:

- Python 3.10: functional compatibility executes; canonical coverage, Phase0 and
  QPS-W08 are role-based skips.
- Python 3.11: functional compatibility executes; canonical coverage, Phase0 and
  QPS-W08 are role-based skips.
- Python 3.12: canonical coverage, Phase0 and QPS-W08 execute; functional
  compatibility is a role-based skip.
- artifact upload is optional when the job produced no runtime payload.
- the runner-migration canary is schedule-only and is not part of normal
  push/PR admission.

The new Python proof manifest makes each of those skips machine-visible as
`CLASSIFIED_ROLE_SKIP` or `OPTIONAL_NO_PAYLOAD`. Missing manifests,
unexpected skips, upstream-failure skips and unexplained zero-step jobs are
proof debt.

## Hidden red roots found outside the green matrix

Main CI/CD Test Suite run: `37113810916`.

Measured red roots:

- Black failed first in Code Quality Checks, which previously hid isort, Flake8
  and Pylint execution.
- Bandit failed first in Security Scanning, which previously hid Safety and
  report upload.
- broad repository coverage measured **29.19%** and failed the governed **75%**
  threshold.
- Integration Tests, Docker Integration Tests and Comprehensive Test Suite were
  skipped by dependency propagation rather than being independently measured.

Main DOW + Recursive DMAIC Unified-CD run: `37113810723`.

The pre-commit step failed on a mixed baseline containing invalid YAML,
end-of-file/trailing-whitespace mutation pressure, the preserved source-bound
E999 syntax defect, TestPilot preflight findings and Ruff debt. The downstream
Ubuntu/RHEL/DMAIC/release jobs were skipped.

Those skipped surfaces are now treated as **proof debt**, not as green or absent
evidence.

## PR admission: new-debt ratchet (proposal, #1859)

Status: proposal pending an owner decision in #1860. It changes PR admission
only; main pushes, schedules and manual runs keep enforcing every red root
above, and the G1-G3 ladder and 75% target are unchanged.

On a `pull_request` event the full-repository Black/isort/Flake8, Bandit and
coverage scans still run and report their totals, and admission for those
three tools moves to checks scoped to what the PR changes:

- `scripts/ci_pr_debt_ratchet.py` compares each changed Python file at the
  PR base and at the head. A file clean at the base must stay clean and a
  new file must be clean; for Flake8-critical (E9, F63, F7, F82) codes and
  for Bandit test id, severity and flagged source lines, no per-file count
  may rise, so removing one finding cannot pay for a different new one.
  B101 is not counted in files under a `tests/` directory. A renamed file
  is compared with its original path.
- The ratchet fails closed: a missing tool, a tool that resolves inside the
  checkout, a crash or unparseable output fails the PR. Tools run in an
  isolated interpreter (`python -I`). CI runs the base revision's copy of
  the ratchet, so a PR cannot weaken the check that admits it; the PR that
  introduces it is judged by the full scans. Inline `# nosec` and `# noqa`
  are ignored, so a PR cannot silence its own new finding, and Bandit
  still compares changed files when `.bandit` changes. A PR that changes
  lint configuration (`pyproject.toml`, `setup.cfg`, `tox.ini`, `.flake8`, `.isort.cfg`,
  `.bandit`, `.editorconfig`, `.gitignore`, in any directory) is not
  admitted by the ratchet for the tools that read that file, because such
  a change can alter every file's result; the full-repository scan for
  those tools decides, and the workflow triggers on each of those files.
  A Flake8 or Bandit config change can only suppress findings, so the
  PR's code must also pass that tool's full scan under the base's version
  of the changed config; otherwise the ratchet fails, and a PR cannot
  silence its own new finding by editing `.bandit` or `.flake8`.
  A `.bandit` change leaves the Black/isort/Flake8 ratchet in place, and a
  `.flake8` change leaves the Bandit ratchet in place. The same holds for
  `ci-cd-tests.yml` and the ratchet script, which install and run every
  tool, and for the root `requirements-test.txt`, which the Code Quality
  job installs after the lint tools (it does not affect Bandit). A file
  renamed to `.py` from another extension, or a symlink or submodule
  replaced by a regular file, counts as new. A rename's base side is
  scanned at its original path, so it keeps its test-file status. The
  base side is the whole base tree, so isort classifies its imports
  against the base's own packages. A PR that adds, removes or renames a
  top-level package or module changes how isort classifies its imports in
  files the PR did not touch, so isort then compares the whole tree on
  both sides.
  Black and isort are pinned to the root configuration, as the full
  `black .` and `isort .` scans are.
- Safety is not relaxed and stays enforced on pull requests.
- `diff-cover` measures coverage of the lines the PR adds or changes and
  reports it next to the repository-wide figure. No PR coverage threshold is
  enforced until the owner sets one.

## Coverage/check growth rule for every proposal

Every compatible DAB/MIP/3P*/DOW/CI proposal must declare one coverage-growth
choice:

1. add or strengthen a test,
2. increase the executed workflow/check surface,
3. convert an unclassified skip into a classified role-based skip,
4. make an advisory result explicit and governed while preserving its owning
   hard gate,
5. for mechanical-only edits, prove non-regression and record
   `NOT_APPLICABLE_MECHANICAL_ONLY`.

For semantic Python changes, option 5 is not sufficient.

## Scaled batch execution

Low-risk mechanical DAB families may be proposed in batches of at most **12
findings**, at most **3 files**, and one family per batch. Medium-risk proposals
are bounded to **4 findings in one file**. High/protected findings remain
one-at-a-time and are never auto-merged.

Proposal generation may use **2-8 parallel read-only workers**. Repository
mutation remains **single-writer only**. Any source-SHA change invalidates the
pending proposal envelope and requires a fresh DAB receipt.

This preserves:

- `authority_transfer=false`
- `formal_credit_delta=0`
- `engineering_credit_delta=0`
