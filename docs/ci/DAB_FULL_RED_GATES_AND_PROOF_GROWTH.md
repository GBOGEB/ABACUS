# DAB Full-Red Gates, Proof Completeness and Coverage Growth

## Purpose

This control joins three previously separate views:

1. repository-wide Flake8/DAB red debt,
2. Python 3.10/3.11/3.12 proof completeness,
3. executed test/check coverage.

A reduction in static-analysis count is not sufficient to close a gate when proof
coverage regresses, a required job is skipped without classification, or a protected
hold changes without source-bound authority.

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
full-red control boundary; it is not a substitute for terminal zero-debt cleanup.

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
unexpected skips, upstream-failure skips and unexplained zero-step jobs are proof
debt.

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
