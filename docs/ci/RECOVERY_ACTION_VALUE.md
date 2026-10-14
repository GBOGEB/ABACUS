# ABACUS Recovery Action Value — operator review surface

Status: **draft, read-only, admission HOLD**. See [ABACUS #1860](
https://github.com/GBOGEB/ABACUS/issues/1860) for governed triage.

## Open the dashboard

From an ABACUS checkout at the exact PR #1967 source revision:

```sh
python -m http.server 8000 --directory docs
```

Open `http://127.0.0.1:8000/ci/recovery_action_value.html`.

- Dashboard: `docs/ci/recovery_action_value.html`
- Governed snapshot: `docs/data/recovery_action_value_v1.json`
- Contract regression: `tests/test_recovery_action_value_contract.py`

A standalone `file://` open may block the relative JSON request. The page
displays UNKNOWN rather than substituting values when source loading fails.

## Exact evidence semantics

- Docs: original main `5ede8c97db4aba99fdcc44109e7230db69a3fd6b`
  reported 13 findings. PR #1966 exact-head native changed-docs lint
  subsequently succeeded: **13 to 0 on the PR scope**, not current main.
- DOW/Ruff: PR #1965 exact-head identical-four-file census produced
  **11 to 0 Ruff findings**, 0 newly introduced, and 6 CLI tests passed.
  Three separately tracked formatting paths improved, but main-wide
  pre-commit and RHEL fan-out have NOT passed.
- DOW downstream: six jobs were skipped in the original main run.
  Potential downstream reach = 6; verified unblocked jobs = UNKNOWN.
- Coverage: retrieved Cobertura + DAB measured **54.55% combined
  branch-inclusive** at the *predecessor main* SHA above, with
  17,088 / 30,735 covered lines and 4,200 / 8,290 covered branches.
  Current main has advanced; latest-main coverage remains UNKNOWN.
- Coverage gain over the historical 36.85% main baseline is NOT
  comparable without matching instrumented source/config identity.
  PR broad and diff comparable gains also remain UNKNOWN.

The browser queries GitHub's public read-only run/jobs and branch endpoints,
compares exact source SHA, run identity, job identity, terminal status, and
job-census completeness, and shows unavailable or stale data as UNKNOWN.

## Acceptance and QA

The Python contract tests verify historical/after denominators, source IDs,
the no-fake-worker and no-waiver controls, and main-SHA drift logic. Run:

```sh
python -m unittest tests.test_recovery_action_value_contract -v
```

Browser QA at 1440×1000, 1280×800, 390×844 and live GitHub readback are
required before claiming published dashboard acceptance. Neither opening
this static HTML nor passing a visual test authorizes a merge.

Main remains unprotected in the latest server-side readback. An owner/admin
must restore enforceable protection and obtain independent review.

`security_waiver=false` · `authority_transfer=false` ·
`formal_credit_delta=0`
