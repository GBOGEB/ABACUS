# CODE PURPLE — Test Observability V4

This is an additive **review projection**, not merge, safety, compliance, or autonomous dispatch authority. It augments the existing ABACUS EVERRED V3 control plane instead of replacing its ledger or its BD/LDAB producers.

## Start

Open `index.html` directly for read-only GitHub metadata. The browser refreshes its current main exact-SHA scope and configured workflows when GitHub public API/CORS is available. If `file://` access is blocked by enterprise policy, serve the folder via `python -m http.server 8877 --bind 127.0.0.1` and visit `http://127.0.0.1:8877/`. **Do not expose the server to the network.**

To generate more detailed **source-scoped job evidence** from live GitHub (Python standard library; API read-only):

```bash
python test_observability.py \
  --repo GBOGEB/ABACUS \
  --sha YOUR_VERIFIED_40_HEX_COMMIT_SHA \
  --run-limit 100 --job-limit 20 \
  --out evidence/latest.json
```

Use `GITHUB_TOKEN` with read-only Actions/repository permission in the **server-side environment only** when needed to avoid public API rate limits. Never paste the token into HTML; the dashboard does not accept an API token. Choose `Load served evidence/latest.json` or `Load local ...json` from the page, with exact-SHA matching. Imported JSON is marked unverified even if it asserts native provenance, unless separately authenticated by a trusted workflow.

A small `evidence/example.fixture.json` is **synthetic and tests only the interface**. It is not current ABACUS telemetry and must never be promoted as live evidence.

## Test hierarchy and measurements

| Family | What is configured | What execution proves | What still needs independent evidence |
|---|---|---|---|
| Standard unit/integration | pytest, unittest, Python matrix, B0, smoke, CI/CD | exact run/job outcome | JUnit case identities, actual tests collected, branch/line coverage denominator |
| User/SUT acceptance | allowlisted local testflight, preflight profiles | token-authorized local sandbox execution | SUT process receipts and authorized native acceptance |
| Static quality bots | Ruff, Flake8, Black, isort, mypy, YAML | tool executed and exit/step conclusion | matching lint config, file/finding census, first-red patch proof |
| Security bots | Bandit, Semgrep, OSV, Safety, CodeQL | scan workflow completion | scanner config/version, comparable fingerprint sets, independent risk disposition |
| Runtime workers | Docker, RHEL/UBI, debugger LLDB, LDAB session | job/specific native runtime receipt if retrieved | image digest, OS/ports/logs, debugger session ID, worker principal and exact SHA |
| Governance | policies, rulesets, independent review | policy/readback provenance | effective enforced main protection and eligible review at merge time |
| Control plane | EVERRED/DMAIC/MIP, root joining | census producer has emitted a versioned report | causality, same-head replay, recurrence and admission proof |

**Evidence maturity:** `CONFIGURED → EXECUTED → SOURCE-BOUND ARTIFACT → INDEPENDENTLY ACCEPTED`. Do not equate workflow success with JUnit pass rate or security admission. Jobs may be missing due explicit collection bounds. `source_sha`, workflow run ID, attempt, job ID, exact test contract and artifact SHA-256 must be kept separately.

## Metrics and mathematical models

The dashboard's DMAIC stages now list measured counts and acceptance criteria. Define = repo/SHA; Measure = enumerated workflow runs vs API total; Analyze = failures and first-red locations, with unique causal roots **UNKNOWN** until counterfactual receipt; Improve = decisive successes but attributable before/after improvement **UNKNOWN** until comparable test sets; Control = protected-main and independent review hold even if CI is green. **No false completion percentages** are produced for unknown stages.

PCA uses two **observational** numeric job-timing variables: queue delay and execution duration. For `n ≥ 30` complete rows with finite variance, a closed-form standardized 2D PCA gives `PC1 EVR=(1+|corr(queue,execution)|)/2`. The samples may be correlated across workflow/run families, so its result is descriptive only; no confidence interval, independence, calibration or causal claim. The `n ≥ max(30,5p)` rule is a user-facing heuristic, not an independent proof.

Bradley–Terry (BT) is **NOT** calculated from unrelated workflow success/failure counts. `test_observability.py` can accept an optional `--pair-input` JSON list of independent matched tests, each with `source_sha`, `trial_id`, `test_contract_digest` (64 hex), `candidate_a`, `candidate_b`, `winner` and `comparable: true`. Only full same-source and test-contract-qualified outcomes qualify. The directed winning graph must be strongly connected and sample >=30 independent trial receipts before a *descriptive* maximum-likelihood fit is attempted. Without external calibration/uncertainty, even a fit cannot approve autonomous worker ranking. This preserves the gg_MATH provider and source governance boundary.

## Controlled visual taxonomy

- Neutral filled rectangle = activity; not a person, phase completion or approval.
- P1–P8 text = process phase; explicit `Role:` = function; confirmed causal root → one repair owner, not an overall owner.
- Purple-outline diamond = decision *type*, without a truth value.
- Green YES and red HOLD = distinct conditional branches; not interchangeable with process fill.
- Solid line = forward acyclic prerequisite; dashed amber = feedback into next recovery pulse; double cyan = preflight feedforward.
- CI status colors: green completed success, red failure, orange cancelled, cyan in progress, grey queued, muted lilac skipped; each includes a text label. Do not reuse status colors to label ownership or physical plant safety.

Chronology is a **source-SHA workflow-run event sequence**. Clicking the graph opens a larger, horizontally scrollable, keyboard-operable dialog with its own legend and click-for-evidence interaction. It is not a continuous time-domain chart of the entire engineering programme.

## QA and integration

```bash
python -m unittest discover -s tests -p 'test_observability.py' -q
python tests/test_browser.py
node --check qa/script.js
```

Local QA is mocked and is not native exact-SHA admission. Owner/reviewer action is separately required to merge the PR and to establish effective GitHub branch protection. The HTML does not launch arbitrary code or remote workers.
